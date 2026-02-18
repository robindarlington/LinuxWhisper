"""Text injection for X11 and Wayland with auto-detection and fallback."""

import logging

from .base import InjectorBackend
from .clipboard import ClipboardWaylandBackend, ClipboardX11Backend
from .detector import detect_compositor, detect_session_type, is_wlroots_compositor
from .fallback import FallbackInjector
from .wayland import YdotoolBackend
from .wtype import WtypeBackend
from .x11 import XdotoolBackend

logger = logging.getLogger(__name__)

__all__ = [
    "InjectorBackend",
    "WtypeBackend",
    "ClipboardWaylandBackend",
    "ClipboardX11Backend",
    "YdotoolBackend",
    "XdotoolBackend",
    "FallbackInjector",
    "detect_session_type",
    "detect_compositor",
    "is_wlroots_compositor",
    "create_injector",
]


def create_injector(config: dict | None = None) -> FallbackInjector:
    """Create a FallbackInjector with appropriate backends for current session.

    Backend selection order:

    Wayland (wlroots: Hyprland, Sway, or unknown compositor):
        1. wtype (Unicode, no daemon needed)
        2. clipboard-wayland (Unicode, requires wl-clipboard)
        3. ydotool (ASCII only)

    Wayland (GNOME, KDE):
        1. clipboard-wayland (Unicode, requires wl-clipboard)
        2. ydotool (ASCII only)

    X11:
        1. xdotool (ASCII)
        2. clipboard-x11 (Unicode fallback, requires xclip)

    Unknown session:
        All backends in order (unavailable ones filtered automatically).

    Args:
        config: Optional config dict. Reads clipboard_restore_delay_ms (default: 300).

    Returns:
        FallbackInjector with appropriate backends.

    Raises:
        RuntimeError: If no backends are available.
    """
    config = config or {}
    restore_delay = config.get("clipboard_restore_delay_ms", 300)

    session_type = detect_session_type()

    if session_type == "wayland":
        compositor = detect_compositor()
        logger.info(f"Detected compositor: {compositor}")

        backends: list[InjectorBackend] = []
        # wtype works on wlroots; also try on unknown compositors
        if compositor not in ("gnome", "kde"):
            backends.append(WtypeBackend())
        backends.append(ClipboardWaylandBackend(restore_delay_ms=restore_delay))
        backends.append(YdotoolBackend())

    elif session_type == "x11":
        backends = [
            XdotoolBackend(),
            ClipboardX11Backend(restore_delay_ms=restore_delay),
        ]

    else:
        # Unknown session -- try everything
        logger.warning("Session type unknown, building full fallback chain")
        backends = [
            WtypeBackend(),
            ClipboardWaylandBackend(restore_delay_ms=restore_delay),
            YdotoolBackend(),
            XdotoolBackend(),
            ClipboardX11Backend(restore_delay_ms=restore_delay),
        ]

    return FallbackInjector(backends)
