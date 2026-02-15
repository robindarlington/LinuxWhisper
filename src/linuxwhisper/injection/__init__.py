"""Text injection for X11 and Wayland with auto-detection."""

import logging

from .detector import detect_session_type
from .wayland import WaylandInjector
from .x11 import X11Injector

logger = logging.getLogger(__name__)

__all__ = ["detect_session_type", "WaylandInjector", "X11Injector", "create_injector"]


def create_injector():
    """Create appropriate text injector for current session.

    Returns:
        WaylandInjector or X11Injector instance

    Raises:
        RuntimeError: If no suitable injector can be created
    """
    session_type = detect_session_type()

    if session_type == "wayland":
        try:
            injector = WaylandInjector()
            logger.info("Created WaylandInjector")
            return injector
        except RuntimeError as e:
            logger.error(f"Failed to create WaylandInjector: {e}")
            raise

    elif session_type == "x11":
        try:
            injector = X11Injector()
            logger.info("Created X11Injector")
            return injector
        except RuntimeError as e:
            logger.error(f"Failed to create X11Injector: {e}")
            raise

    else:
        # Session type unknown - try both
        logger.warning("Session type unknown, trying Wayland first then X11")

        try:
            injector = WaylandInjector()
            logger.info("Created WaylandInjector (fallback)")
            return injector
        except RuntimeError:
            pass

        try:
            injector = X11Injector()
            logger.info("Created X11Injector (fallback)")
            return injector
        except RuntimeError:
            pass

        raise RuntimeError(
            "Could not create text injector. "
            "Please ensure either ydotool (Wayland) or xdotool (X11) is installed "
            "and the appropriate session is running."
        )
