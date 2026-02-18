"""Clipboard-based text injection for Unicode support."""

import logging
import os
import shutil
import subprocess
import time

from .base import InjectorBackend

logger = logging.getLogger(__name__)


class ClipboardWaylandBackend(InjectorBackend):
    """Text injector using clipboard paste on Wayland.

    Saves clipboard, copies text, pastes via Ctrl+V (ydotool), restores clipboard.
    Works on all Wayland compositors. Requires wl-clipboard and ydotool.
    """

    def __init__(self, restore_delay_ms: int = 300):
        self._restore_delay_ms = restore_delay_ms

    def name(self) -> str:
        return "clipboard-wayland"

    def is_available(self) -> bool:
        return (
            shutil.which("wl-copy") is not None
            and shutil.which("wl-paste") is not None
            and shutil.which("ydotool") is not None
        )

    def supports_unicode(self) -> bool:
        return True

    def type_text(self, text: str) -> None:
        # Save current clipboard
        try:
            old_clipboard = subprocess.run(
                ["wl-paste", "--no-newline"],
                capture_output=True, timeout=2,
            ).stdout
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            old_clipboard = b""

        try:
            # Copy text to clipboard
            subprocess.run(
                ["wl-copy", "--", text],
                check=True, timeout=2,
            )

            # Simulate Ctrl+V via ydotool (29=LCtrl, 47=V)
            subprocess.run(
                ["ydotool", "key", "29:1", "47:1", "47:0", "29:0"],
                check=True, timeout=5,
            )

            # Wait for app to process paste before restoring clipboard
            time.sleep(self._restore_delay_ms / 1000.0)

            # Restore original clipboard
            if old_clipboard:
                subprocess.run(
                    ["wl-copy", "--"],
                    input=old_clipboard, timeout=2,
                )
            else:
                subprocess.run(["wl-copy", "--clear"], timeout=2)

            logger.debug(f"Injected {len(text)} chars via clipboard (Wayland)")
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"Clipboard paste timeout: {e}") from e
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Clipboard paste failed: {e}") from e


class ClipboardX11Backend(InjectorBackend):
    """Text injector using clipboard paste on X11.

    Saves clipboard, copies text, pastes via Ctrl+V (xdotool), restores clipboard.
    Requires xclip and xdotool.
    """

    def __init__(self, restore_delay_ms: int = 300):
        self._restore_delay_ms = restore_delay_ms

    def name(self) -> str:
        return "clipboard-x11"

    def is_available(self) -> bool:
        return (
            shutil.which("xclip") is not None
            and shutil.which("xdotool") is not None
            and os.environ.get("DISPLAY") is not None
        )

    def supports_unicode(self) -> bool:
        return True

    def type_text(self, text: str) -> None:
        # Save current clipboard
        try:
            old_clipboard = subprocess.run(
                ["xclip", "-selection", "clipboard", "-o"],
                capture_output=True, timeout=2,
            ).stdout
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            old_clipboard = b""

        try:
            # Copy text to clipboard
            subprocess.run(
                ["xclip", "-selection", "clipboard"],
                input=text.encode("utf-8"),
                check=True, timeout=2,
            )

            # Simulate Ctrl+V
            subprocess.run(
                ["xdotool", "key", "--clearmodifiers", "ctrl+v"],
                check=True, timeout=5,
            )

            # Wait for app to process paste before restoring clipboard
            time.sleep(self._restore_delay_ms / 1000.0)

            # Restore original clipboard
            if old_clipboard:
                subprocess.run(
                    ["xclip", "-selection", "clipboard"],
                    input=old_clipboard, timeout=2,
                )

            logger.debug(f"Injected {len(text)} chars via clipboard (X11)")
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"Clipboard paste timeout: {e}") from e
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Clipboard paste failed: {e}") from e
