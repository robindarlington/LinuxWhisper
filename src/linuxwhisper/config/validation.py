"""Hotkey validation and compositor conflict detection for LinuxWhisper."""

import json
import logging
import os
import shutil
import subprocess

from evdev import ecodes

logger = logging.getLogger(__name__)


# Maps user-friendly hotkey names (lowercase) to canonical evdev KEY_ names
FRIENDLY_ALIASES: dict[str, str] = {
    "scroll_lock": "KEY_SCROLLLOCK",
    "scrolllock": "KEY_SCROLLLOCK",
    "pause": "KEY_PAUSE",
    "break": "KEY_PAUSE",
    "home": "KEY_HOME",
    "end": "KEY_END",
    "insert": "KEY_INSERT",
    "delete": "KEY_DELETE",
    "page_up": "KEY_PAGEUP",
    "pageup": "KEY_PAGEUP",
    "page_down": "KEY_PAGEDOWN",
    "pagedown": "KEY_PAGEDOWN",
    "print_screen": "KEY_SYSRQ",
    "printscreen": "KEY_SYSRQ",
    "sysrq": "KEY_SYSRQ",
    "num_lock": "KEY_NUMLOCK",
    "numlock": "KEY_NUMLOCK",
    "caps_lock": "KEY_CAPSLOCK",
    "capslock": "KEY_CAPSLOCK",
}


def resolve_hotkey_name(hotkey_str: str) -> str:
    """Resolve a user-provided hotkey string to a canonical KEY_ evdev name.

    Args:
        hotkey_str: User-provided hotkey string (e.g., "scroll_lock", "HOME", "KEY_F13").

    Returns:
        Canonical evdev key name (e.g., "KEY_SCROLLLOCK", "KEY_HOME", "KEY_F13").
    """
    # Normalize to lowercase for alias lookup
    normalized = hotkey_str.strip().lower()

    # Check friendly aliases first
    if normalized in FRIENDLY_ALIASES:
        return FRIENDLY_ALIASES[normalized]

    # Apply standard KEY_ prefix normalization
    upper = hotkey_str.strip().upper()
    if not upper.startswith("KEY_"):
        upper = f"KEY_{upper}"
    return upper


def validate_hotkey(hotkey_str: str) -> tuple[bool, int | None, str]:
    """Validate a hotkey configuration string and return its evdev key code.

    Args:
        hotkey_str: User-provided hotkey string.

    Returns:
        Tuple of (is_valid, key_code, error_message).
        On success: (True, int_code, "")
        On failure: (False, None, helpful_error_message)
    """
    key_name = resolve_hotkey_name(hotkey_str)
    key_code = getattr(ecodes, key_name, None)

    if key_code is None:
        # Build a helpful list of available keys
        available_names: set[str] = set()

        # Add alias targets (deduplicated)
        for alias_target in FRIENDLY_ALIASES.values():
            available_names.add(alias_target)

        # Add function keys F1-F24 that exist in ecodes
        for i in range(1, 25):
            fname = f"KEY_F{i}"
            if hasattr(ecodes, fname):
                available_names.add(fname)

        # Convert to display form: strip KEY_ prefix and lowercase
        available_display = sorted(
            name[4:].lower() if name.startswith("KEY_") else name.lower()
            for name in available_names
        )

        error_msg = (
            f"Unknown hotkey: '{hotkey_str}'. "
            f"Available keys include: {', '.join(available_display)}"
        )
        return False, None, error_msg

    return True, key_code, ""


def check_compositor_conflicts(hotkey_str: str) -> list[str]:
    """Check for compositor keybinding conflicts with the given hotkey.

    Queries all major compositors/desktop environments for bindings that
    may conflict with the specified hotkey. Never raises an exception.

    Args:
        hotkey_str: User-provided hotkey string (passed through resolve_hotkey_name).

    Returns:
        List of conflict description strings. Empty if no conflicts detected.
    """
    try:
        key_name = resolve_hotkey_name(hotkey_str)
        # Short key name: strip KEY_ prefix for comparison
        short_name = key_name[4:] if key_name.startswith("KEY_") else key_name
        conflicts: list[str] = []

        # --- Hyprland ---
        if shutil.which("hyprctl"):
            try:
                result = subprocess.run(
                    ["hyprctl", "binds", "-j"],
                    capture_output=True, text=True, timeout=2
                )
                if result.returncode == 0:
                    bindings = json.loads(result.stdout)
                    for bind in bindings:
                        bind_key = bind.get("key", "")
                        modmask = bind.get("modmask", 0)
                        if bind_key.upper() == short_name.upper():
                            if modmask == 0:
                                dispatcher = bind.get("dispatcher", "unknown")
                                conflicts.append(
                                    f"Hyprland: '{bind_key}' is bound to {dispatcher} "
                                    f"(modmask={modmask})"
                                )
                            else:
                                logger.debug(
                                    f"Hyprland: '{bind_key}' is bound with modifiers "
                                    f"(modmask={modmask}) — not a bare key conflict"
                                )
            except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as e:
                logger.debug(f"Hyprland conflict check failed: {e}")

        # --- Sway ---
        if shutil.which("swaymsg"):
            try:
                result = subprocess.run(
                    ["swaymsg", "-t", "get_tree"],
                    capture_output=True, text=True, timeout=2
                )
                if result.returncode == 0:
                    logger.debug(
                        "Sway detected. Sway IPC does not expose individual keybindings "
                        "-- manual config review recommended."
                    )
                    # Sway has no reliable API to query individual bindings
            except (subprocess.TimeoutExpired, OSError) as e:
                logger.debug(f"Sway detection check failed: {e}")

        # --- GNOME ---
        if shutil.which("gsettings"):
            try:
                probe = subprocess.run(
                    ["gsettings", "get",
                     "org.gnome.desktop.wm.keybindings", "switch-to-workspace-1"],
                    capture_output=True, text=True, timeout=2
                )
                if probe.returncode == 0:
                    # GNOME is running — query keybinding schemas
                    schemas = [
                        "org.gnome.desktop.wm.keybindings",
                        "org.gnome.settings-daemon.plugins.media-keys",
                        "org.gnome.shell.keybindings",
                    ]
                    for schema in schemas:
                        try:
                            result = subprocess.run(
                                ["gsettings", "list-recursively", schema],
                                capture_output=True, text=True, timeout=3
                            )
                            if result.returncode == 0:
                                for line in result.stdout.splitlines():
                                    # Heuristic: check if short key name appears in binding value
                                    if short_name.lower() in line.lower():
                                        conflicts.append(
                                            f"GNOME ({schema}): Possible conflict — "
                                            f"{line.strip()}"
                                        )
                        except (subprocess.TimeoutExpired, OSError) as e:
                            logger.debug(f"GNOME schema query failed for {schema}: {e}")
            except (subprocess.TimeoutExpired, OSError) as e:
                logger.debug(f"GNOME conflict check failed: {e}")

        # --- KDE ---
        kde_bin = shutil.which("kreadconfig6") or shutil.which("kreadconfig5")
        if kde_bin:
            try:
                shortcuts_path = os.path.expanduser("~/.config/kglobalshortcutsrc")
                if os.path.exists(shortcuts_path):
                    with open(shortcuts_path, "r", errors="replace") as f:
                        contents = f.read()
                    # Heuristic: look for the key name in various forms
                    search_terms = [
                        short_name,
                        short_name.lower(),
                        short_name.upper(),
                        short_name.title(),
                        key_name,
                    ]
                    if any(term in contents for term in search_terms):
                        conflicts.append(
                            "KDE: Possible conflict detected in kglobalshortcutsrc "
                            "-- review global shortcuts in System Settings"
                        )
            except OSError as e:
                logger.debug(f"KDE conflict check failed: {e}")

        # --- X11 ---
        if os.environ.get("DISPLAY"):
            if shutil.which("xmodmap"):
                try:
                    result = subprocess.run(
                        ["xmodmap", "-pke"],
                        capture_output=True, text=True, timeout=2
                    )
                    logger.debug(
                        "X11 session detected. Keybinding conflict detection not "
                        "available for X11 window managers."
                    )
                except (subprocess.TimeoutExpired, OSError) as e:
                    logger.debug(f"X11 xmodmap check failed: {e}")
            else:
                logger.debug(
                    "X11 session detected. Keybinding conflict detection not "
                    "available for X11 window managers."
                )

        return conflicts

    except Exception as e:
        logger.debug(f"Compositor conflict check encountered unexpected error: {e}")
        return []


def validate_config_input(config: dict) -> list[str]:
    """Validate input-related config fields.

    Args:
        config: Configuration dictionary.

    Returns:
        List of error message strings. Empty list means config is valid.
    """
    errors: list[str] = []

    # Validate hotkey
    hotkey = config.get("hotkey", "HOME")
    valid, _, err = validate_hotkey(hotkey)
    if not valid:
        errors.append(err)

    # Validate mode
    mode = config.get("mode", "hold")
    if mode not in ("hold", "toggle"):
        errors.append(f"Invalid mode: '{mode}'. Valid modes: hold, toggle")

    # Validate toggle_timeout if present
    timeout = config.get("toggle_timeout")
    if timeout is not None:
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            errors.append(
                f"Invalid toggle_timeout: must be a positive number (got {timeout})"
            )

    return errors
