"""Configuration loading and management for LinuxWhisper."""

import tomllib
from pathlib import Path
from typing import Any

import tomli_w
from xdg_base_dirs import xdg_config_home

from .defaults import DEFAULT_CONFIG


def get_config_path() -> Path:
    """Get the path to the LinuxWhisper config file.

    Returns:
        Path to ~/.config/linuxwhisper/config.toml (respects XDG_CONFIG_HOME)
    """
    return xdg_config_home() / "linuxwhisper" / "config.toml"


def merge_config(defaults: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
    """Deep merge user config over defaults.

    User values override defaults at any nesting level. Unset keys
    preserve their default values.

    Args:
        defaults: Default configuration dictionary
        user: User-provided configuration dictionary

    Returns:
        Merged configuration dictionary
    """
    result = defaults.copy()

    for key, value in user.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Recursively merge nested dictionaries
            result[key] = merge_config(result[key], value)
        else:
            # Override with user value
            result[key] = value

    return result


def write_default_config(path: Path) -> None:
    """Write default configuration to TOML file.

    Creates parent directories if needed.

    Args:
        path: Path to write config file to
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        tomli_w.dump(DEFAULT_CONFIG, f)


def load_config() -> dict[str, Any]:
    """Load configuration from file, creating defaults if missing.

    On first run, creates ~/.config/linuxwhisper/config.toml with defaults.
    On subsequent runs, deep-merges user config over defaults so users only
    need to specify overrides.

    Returns:
        Merged configuration dictionary
    """
    config_path = get_config_path()

    # Create default config if it doesn't exist
    if not config_path.exists():
        write_default_config(config_path)
        return DEFAULT_CONFIG.copy()

    # Load and merge user config
    with open(config_path, "rb") as f:
        user_config = tomllib.load(f)

    return merge_config(DEFAULT_CONFIG, user_config)
