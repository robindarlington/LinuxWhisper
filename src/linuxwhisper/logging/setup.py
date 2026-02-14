"""Logging configuration for LinuxWhisper daemon."""

import logging
import sys


def setup_logging(config: dict) -> None:
    """Configure Python logging for the daemon.

    Reads logging level from config["logging"]["level"].
    Logs to stdout (systemd captures this to journal).

    Args:
        config: Configuration dictionary with logging settings
    """
    log_level = config.get("logging", {}).get("level", "INFO")

    # Convert string level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Configure root logger
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
        force=True  # Override any existing configuration
    )

    # Log the configuration
    logger = logging.getLogger(__name__)
    logger.debug(f"Logging configured with level: {log_level}")
