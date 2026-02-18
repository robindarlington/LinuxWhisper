"""Recording overlay — live waveform visualization during dictation.

Public API:
    OverlayManager: spawns/controls the overlay subprocess.

The overlay runs as a separate process (python -m linuxwhisper.overlay)
to avoid GTK main loop conflicts with the daemon. Communication is via
stdin pipe: the daemon writes RMS amplitude floats, the overlay reads
and renders them as a waveform.
"""

import logging
import pathlib
import subprocess
import sys

logger = logging.getLogger(__name__)


def _find_system_python() -> str:
    """Find system Python that has access to gi/GTK system packages."""
    if sys.prefix == sys.base_prefix:
        return sys.executable  # Not in a venv
    # In a venv — resolve base interpreter (has gi, cairo, etc.)
    base = pathlib.Path(sys.base_prefix) / "bin" / "python3"
    if base.exists():
        return str(base)
    return sys.executable  # Fallback


def _overlay_env() -> dict[str, str]:
    """Build environment for the overlay subprocess.

    System Python needs PYTHONPATH to find the linuxwhisper package
    when running from a venv editable install.
    """
    import os

    env = os.environ.copy()
    # Find the src/ directory containing the linuxwhisper package
    pkg_dir = pathlib.Path(__file__).resolve().parent.parent.parent  # src/
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{pkg_dir}:{existing}" if existing else str(pkg_dir)
    return env

__all__ = ["OverlayManager"]


class OverlayManager:
    """Manages the overlay subprocess lifecycle and data pipe.

    Usage:
        manager = OverlayManager()
        manager.show()                # spawn overlay window
        manager.send_amplitude(0.5)   # feed waveform data
        manager.hide()                # kill overlay
    """

    def __init__(self, config: dict | None = None):
        self._config = config or {}
        self._process: subprocess.Popen | None = None

    def show(self) -> None:
        """Spawn the overlay subprocess.

        If already running, this is a no-op.
        """
        if self.is_running():
            return

        try:
            self._process = subprocess.Popen(
                [_find_system_python(), "-m", "linuxwhisper.overlay"],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=_overlay_env(),
            )
            logger.info("Overlay subprocess started (pid=%d)", self._process.pid)
        except OSError:
            logger.exception("Failed to spawn overlay subprocess")
            self._process = None

    def hide(self) -> None:
        """Terminate the overlay subprocess.

        Safe to call even if the process already exited.
        """
        if self._process is None:
            return

        try:
            self._process.terminate()
            self._process.wait(timeout=2)
            logger.info("Overlay subprocess terminated")
        except subprocess.TimeoutExpired:
            logger.warning("Overlay did not exit in time, killing")
            self._process.kill()
            self._process.wait(timeout=1)
        except OSError:
            pass  # Process already dead
        finally:
            self._process = None

    def send_amplitude(self, rms: float) -> None:
        """Send an RMS amplitude value to the overlay for waveform display.

        Silently ignores errors (overlay may have died).
        """
        if self._process is None or self._process.stdin is None:
            return

        try:
            self._process.stdin.write(f"{rms:.4f}\n".encode())
            self._process.stdin.flush()
        except (BrokenPipeError, OSError):
            pass  # Overlay died — will be cleaned up by hide() or next show()

    def is_running(self) -> bool:
        """Check whether the overlay subprocess is alive."""
        return self._process is not None and self._process.poll() is None
