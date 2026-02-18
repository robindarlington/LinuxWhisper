"""Input mode definitions for LinuxWhisper."""

import enum


class InputMode(enum.Enum):
    """Input modes for dictation activation."""
    HOLD = "hold"
    TOGGLE = "toggle"


# Default timeout in seconds for toggle mode safety (2 minutes)
DEFAULT_TOGGLE_TIMEOUT = 120


def get_mode_from_config(config: dict) -> InputMode:
    """Get the InputMode from a config dict.

    Args:
        config: Configuration dictionary. Reads config.get("mode", "hold").

    Returns:
        InputMode enum value.

    Raises:
        ValueError: If the mode value is not a valid InputMode.
    """
    value = config.get("mode", "hold")
    try:
        return InputMode(value)
    except ValueError:
        raise ValueError(
            f"Invalid mode: '{value}'. Valid modes: hold, toggle"
        )
