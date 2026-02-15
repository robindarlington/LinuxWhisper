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
