"""Wayland text injection via wtype (wlroots compositors only)."""

import logging
import shutil
import subprocess

from .base import InjectorBackend

logger = logging.getLogger(__name__)


class WtypeBackend(InjectorBackend):
    """Text injector using wtype for wlroots-based Wayland compositors.

    Uses zwp_virtual_keyboard_v1 protocol to generate a keymap on-the-fly,
    providing full Unicode support. Only works on wlroots compositors
    (Hyprland, Sway, river).
    """

    def name(self) -> str:
        return "wtype"

    def is_available(self) -> bool:
        return shutil.which("wtype") is not None

    def supports_unicode(self) -> bool:
        return True

    def type_text(self, text: str) -> None:
        try:
            subprocess.run(
                ["wtype", "--", text],
                check=True,
                timeout=10,
            )
            logger.debug(f"Injected {len(text)} chars via wtype")
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"wtype timeout: {e}") from e
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"wtype failed: {e}") from e
