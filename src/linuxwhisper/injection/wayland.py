"""Wayland text injection via ydotool."""

import logging
import os
import shutil
import subprocess

from .base import InjectorBackend

logger = logging.getLogger(__name__)


class YdotoolBackend(InjectorBackend):
    """Text injector using ydotool for Wayland.

    Works on all Wayland compositors via /dev/uinput (kernel-level).
    ASCII only -- ydotool simulates physical keyboard scancodes which
    have no concept of Unicode code points.
    """

    def name(self) -> str:
        return "ydotool"

    def is_available(self) -> bool:
        if not shutil.which("ydotool"):
            return False
        # Check if ydotoold socket exists
        socket_path = os.environ.get("YDOTOOL_SOCKET", "/tmp/.ydotool_socket")
        alt_socket = f"/run/user/{os.getuid()}/.ydotool_socket"
        return os.path.exists(socket_path) or os.path.exists(alt_socket)

    def supports_unicode(self) -> bool:
        return False

    def type_text(self, text: str) -> None:
        try:
            subprocess.run(
                ["ydotool", "type", "--key-delay", "12", "--", text],
                check=True,
                timeout=10,
            )
            logger.debug(f"Injected {len(text)} chars via ydotool")
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"ydotool timeout: {e}") from e
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"ydotool failed: {e}") from e
