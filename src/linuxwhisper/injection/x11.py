"""X11 text injection via xdotool."""

import logging
import os
import shutil
import subprocess

logger = logging.getLogger(__name__)


class X11Injector:
    """Text injector for X11 using xdotool."""

    def __init__(self):
        """Initialize X11 injector with validation checks."""
        # Check if xdotool is installed
        if not shutil.which("xdotool"):
            raise RuntimeError(
                "xdotool not found. Install with: sudo pacman -S xdotool"
            )

        # Check if DISPLAY is set (X11 session requirement)
        if not os.environ.get("DISPLAY"):
            raise RuntimeError("DISPLAY not set - not an X11 session")

        logger.info("X11Injector initialized")

    def type_text(self, text: str, delay_ms: int = 12) -> None:
        """Type text into the active window.

        Args:
            text: Text to type
            delay_ms: Delay between keystrokes in milliseconds

        Raises:
            RuntimeError: If text injection fails
        """
        try:
            # Set LANG to ensure proper UTF-8 handling
            env = {**os.environ, "LANG": "en_US.UTF-8"}

            subprocess.run(
                ["xdotool", "type", "--delay", str(delay_ms), "--", text],
                check=True,
                timeout=10,
                env=env,
            )
            logger.info(f"Injected {len(text)} characters via xdotool")
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"xdotool timeout: {e}") from e
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"xdotool failed: {e}") from e
