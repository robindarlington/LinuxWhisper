"""Daemon lifecycle management for LinuxWhisper."""

import logging
from linuxwhisper.logging import setup_logging
from linuxwhisper.daemon.pid import write_pid_file, remove_pid_file
from linuxwhisper.config import load_config

logger = logging.getLogger(__name__)

# Store config reference for reload
_current_config = None


def setup_daemon(config: dict) -> None:
    """Initialize daemon on startup.

    Configures logging and writes PID file.

    Args:
        config: Configuration dictionary
    """
    global _current_config

    # Configure logging first
    setup_logging(config)

    # Write PID file
    write_pid_file()

    # Store config for reload
    _current_config = config

    logger.info("Daemon setup complete")


def shutdown_daemon() -> None:
    """Clean up daemon on shutdown.

    Removes PID file and logs shutdown event.
    """
    logger.info("Daemon shutting down")
    remove_pid_file()


def reload_config() -> dict:
    """Reload configuration from disk.

    Re-reads config file, updates logging level if changed,
    and logs the reload event.

    Returns:
        New configuration dictionary
    """
    global _current_config

    logger.info("Reloading configuration")

    # Load new config from disk
    new_config = load_config()

    # Update logging level if it changed
    old_level = _current_config.get("logging", {}).get("level", "INFO") if _current_config else "INFO"
    new_level = new_config.get("logging", {}).get("level", "INFO")

    if old_level != new_level:
        setup_logging(new_config)
        logger.info(f"Logging level changed from {old_level} to {new_level}")

    # Update stored config
    _current_config = new_config

    logger.info("Configuration reloaded successfully")

    return new_config


def get_current_config() -> dict:
    """Get the current configuration without re-reading from disk.

    Returns:
        Current configuration dictionary, or empty dict if not initialized
    """
    return _current_config if _current_config is not None else {}
