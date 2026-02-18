"""Wayland text injection via ydotool."""

import logging
import os
import shutil
import subprocess

logger = logging.getLogger(__name__)


class WaylandInjector:
    """Text injector for Wayland using ydotool."""

    def __init__(self):
        """Initialize Wayland injector with validation checks."""
        # Check if ydotool is installed
        if not shutil.which("ydotool"):
            raise RuntimeError(
                "ydotool not found. Install with: sudo pacman -S ydotool"
            )

        # Check if ydotoold socket exists
        socket_path = os.environ.get("YDOTOOL_SOCKET", "/tmp/.ydotool_socket")
        alt_socket = f"/run/user/{os.getuid()}/.ydotool_socket"

        socket_exists = os.path.exists(socket_path) or os.path.exists(alt_socket)

        if not socket_exists:
            raise RuntimeError(
                "ydotoold daemon not running. "
                "Start with: systemctl --user start ydotool"
            )

        logger.info("WaylandInjector initialized")

    def type_text(self, text: str, delay_ms: int = 12) -> None:
        """Type text into the active window.

        Args:
            text: Text to type
            delay_ms: Delay between keystrokes in milliseconds

        Raises:
            RuntimeError: If text injection fails
        """
        try:
            subprocess.run(
                ["ydotool", "type", "--key-delay", str(delay_ms), "--", text],
                check=True,
                timeout=10,
            )
            logger.info(f"Injected {len(text)} characters via ydotool")
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"ydotool timeout: {e}") from e
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"ydotool failed: {e}") from e
