"""Default configuration values for LinuxWhisper."""

DEFAULT_CONFIG = {
    # evdev key name: "HOME", "PAUSE", "SCROLL_LOCK", "F13", etc.
    # Friendly aliases supported: scroll_lock, pause, home, insert, etc.
    # Case-insensitive. Both "HOME" and "KEY_HOME" formats accepted.
    "hotkey": "HOME",
    # "hold" = hold key to record, "toggle" = press to start/stop
    "mode": "hold",
    # Maximum recording duration in seconds for toggle mode safety.
    # When timeout fires, captured audio is transcribed (not discarded).
    # Only applies to toggle mode. Set to 0 to disable.
    "toggle_timeout": 120,
    "model": "base.en",
    "sentence_format": True,
    "clipboard_restore_delay_ms": 300,
    "auto_space": True,
    "overlay": {
        "enabled": True,
        "position": "active-window",  # active-window, bottom-right, bottom-left, top-right, top-left
        "width": 120,
        "height": 32,
    },
    "audio": {
        "sample_rate": 16000,
        "channels": 1,
        "device": None,  # Use default audio device
    },
    "logging": {
        "level": "INFO",
    },
}
