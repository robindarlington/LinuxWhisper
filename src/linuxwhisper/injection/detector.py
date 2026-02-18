"""Session type detection for X11 vs Wayland."""

import logging
import os
import subprocess

logger = logging.getLogger(__name__)


def detect_session_type() -> str:
    """Detect whether running under X11 or Wayland.

    Returns:
        'x11', 'wayland', or 'unknown'
    """
    # Method 1: Check XDG_SESSION_TYPE environment variable
    session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if session_type in ("x11", "wayland"):
        logger.info(f"Detected session type: {session_type} (via XDG_SESSION_TYPE)")
        return session_type

    # Method 2: Check for Wayland display
    if os.environ.get("WAYLAND_DISPLAY"):
        logger.info("Detected session type: wayland (via WAYLAND_DISPLAY)")
        return "wayland"

    # Method 3: Check for X11 display
    if os.environ.get("DISPLAY"):
        logger.info("Detected session type: x11 (via DISPLAY)")
        return "x11"

    # Method 4: Try loginctl as last resort
    try:
        result = subprocess.run(
            ["loginctl", "show-session", "-p", "Type"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            # Parse output like "Type=wayland" or "Type=x11"
            for line in result.stdout.splitlines():
                if line.startswith("Type="):
                    detected = line.split("=", 1)[1].strip().lower()
                    if detected in ("x11", "wayland"):
                        logger.info(
                            f"Detected session type: {detected} (via loginctl)"
                        )
                        return detected
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    logger.warning("Could not detect session type - returning 'unknown'")
    return "unknown"


def detect_compositor() -> str:
    """Detect the running Wayland compositor.

    Returns one of: 'hyprland', 'sway', 'gnome', 'kde', 'unknown'
    """
    # Check environment variables (fast path)
    if os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"):
        logger.info("Detected compositor: hyprland (via HYPRLAND_INSTANCE_SIGNATURE)")
        return "hyprland"
    if os.environ.get("SWAYSOCK"):
        logger.info("Detected compositor: sway (via SWAYSOCK)")
        return "sway"

    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
    if "hyprland" in desktop:
        logger.info("Detected compositor: hyprland (via XDG_CURRENT_DESKTOP)")
        return "hyprland"
    if "sway" in desktop:
        logger.info("Detected compositor: sway (via XDG_CURRENT_DESKTOP)")
        return "sway"
    if "gnome" in desktop:
        logger.info("Detected compositor: gnome (via XDG_CURRENT_DESKTOP)")
        return "gnome"
    if "kde" in desktop or "plasma" in desktop:
        logger.info("Detected compositor: kde (via XDG_CURRENT_DESKTOP)")
        return "kde"

    # Fallback: check running processes
    for compositor, process_name in [
        ("hyprland", "Hyprland"),
        ("sway", "sway"),
        ("gnome", "gnome-shell"),
        ("kde", "kwin_wayland"),
    ]:
        try:
            result = subprocess.run(
                ["pgrep", "-x", process_name],
                capture_output=True, timeout=2,
            )
            if result.returncode == 0:
                logger.info(f"Detected compositor: {compositor} (via pgrep)")
                return compositor
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    logger.info("Could not detect compositor - returning 'unknown'")
    return "unknown"


def is_wlroots_compositor(compositor: str) -> bool:
    """Check if compositor supports zwp_virtual_keyboard_v1 (wtype works).

    Args:
        compositor: Compositor name from detect_compositor().

    Returns:
        True if compositor is wlroots-based (Hyprland, Sway).
    """
    return compositor in ("hyprland", "sway")
