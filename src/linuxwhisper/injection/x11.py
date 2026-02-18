"""X11 text injection via xdotool."""

import logging
import os
import shutil
import subprocess

from .base import InjectorBackend

logger = logging.getLogger(__name__)


class XdotoolBackend(InjectorBackend):
    """Text injector using xdotool for X11.

    Partial Unicode support (locale-dependent). Does NOT work in native
    Wayland windows -- only XWayland.
    """

    def name(self) -> str:
        return "xdotool"

    def is_available(self) -> bool:
        return (
            shutil.which("xdotool") is not None
            and os.environ.get("DISPLAY") is not None
        )

    def supports_unicode(self) -> bool:
        return False

    def type_text(self, text: str) -> None:
        try:
            env = {**os.environ, "LANG": "en_US.UTF-8"}
            subprocess.run(
                ["xdotool", "type", "--delay", "12", "--clearmodifiers", "--", text],
                check=True,
                timeout=10,
                env=env,
            )
            logger.debug(f"Injected {len(text)} chars via xdotool")
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"xdotool timeout: {e}") from e
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"xdotool failed: {e}") from e
