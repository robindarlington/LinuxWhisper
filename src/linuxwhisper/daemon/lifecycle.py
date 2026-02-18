"""Daemon lifecycle management for LinuxWhisper."""

import logging
from linuxwhisper.logging import setup_logging
from linuxwhisper.daemon.pid import write_pid_file, remove_pid_file
from linuxwhisper.config import load_config
from linuxwhisper.config.validation import validate_hotkey, validate_config_input, check_compositor_conflicts
from linuxwhisper.pipeline.states import PipelineState

logger = logging.getLogger(__name__)

# Store config reference for reload
_current_config = None

# Store pipeline reference for state-aware reload
_pipeline_ref = None


def set_pipeline_ref(pipeline) -> None:
    """Store a reference to the DictationPipeline instance.

    Called by daemon/main.py after pipeline creation so lifecycle can
    access the pipeline state during config reload.

    Args:
        pipeline: DictationPipeline instance
    """
    global _pipeline_ref
    _pipeline_ref = pipeline


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

    # Note: prefer reload_config_safe() for state-aware reload (Phase 3+)

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


def reload_config_safe() -> dict | None:
    """State-aware config reload for SIGHUP handling.

    Defers reload if pipeline is currently recording, validates the new
    config before applying (rejecting invalid configs and preserving the
    old config), detects hotkey/mode/timeout changes, checks compositor
    conflicts on hotkey change, and restarts the hotkey detector when the
    hotkey changes.

    Returns:
        New configuration dictionary on success, None if deferred or failed.
    """
    global _current_config

    # Defer reload if pipeline is currently active (not idle)
    if _pipeline_ref is not None and _pipeline_ref.state != PipelineState.IDLE:
        logger.warning(
            f"Config reload deferred: pipeline is {_pipeline_ref.state.name}. "
            "Will retry on next SIGHUP."
        )
        return None

    logger.info("Reloading configuration")

    # Load new config from disk
    new_config = load_config()

    # Validate new config before applying
    errors = validate_config_input(new_config)
    if errors:
        for err in errors:
            logger.error(f"Config validation error: {err}")
        logger.error(
            "Config reload aborted: validation errors in new config. Old config preserved."
        )
        return None

    # Detect changes
    hotkey_changed = _current_config.get("hotkey") != new_config.get("hotkey")
    mode_changed = _current_config.get("mode") != new_config.get("mode")
    timeout_changed = _current_config.get("toggle_timeout") != new_config.get("toggle_timeout")
    model_changed = _current_config.get("model") != new_config.get("model")

    # Log hotkey change and check compositor conflicts
    if hotkey_changed:
        conflicts = check_compositor_conflicts(new_config.get("hotkey", "HOME"))
        for conflict in conflicts:
            logger.warning(f"Hotkey conflict detected: {conflict}")
        logger.info(
            f"Hotkey changed: {_current_config.get('hotkey')} -> {new_config.get('hotkey')}"
        )

    if mode_changed:
        logger.info(f"Mode changed: {_current_config.get('mode')} -> {new_config.get('mode')}")

    if timeout_changed:
        logger.info(
            f"Toggle timeout changed: {_current_config.get('toggle_timeout')} "
            f"-> {new_config.get('toggle_timeout')}"
        )

    if model_changed:
        logger.info(
            f"Model changed: {_current_config.get('model')} -> {new_config.get('model')}"
        )

    # Update logging level if changed
    old_level = _current_config.get("logging", {}).get("level", "INFO") if _current_config else "INFO"
    new_level = new_config.get("logging", {}).get("level", "INFO")
    if old_level != new_level:
        setup_logging(new_config)
        logger.info(f"Logging level changed: {old_level} -> {new_level}")

    # Apply new config
    _current_config = new_config

    # Update pipeline if running and any relevant config changed
    if _pipeline_ref is not None and any([hotkey_changed, mode_changed, timeout_changed, model_changed]):
        _pipeline_ref.update_config(new_config)
        if hotkey_changed:
            logger.info("Restarting hotkey detector for new key...")
            _pipeline_ref.restart_hotkey_detector()
        if model_changed:
            logger.info("Reloading Whisper model for new model size...")
            _pipeline_ref.reload_model(new_config.get("model", "base.en"))

    logger.info("Configuration reloaded successfully")
    return new_config


def get_current_config() -> dict:
    """Get the current configuration without re-reading from disk.

    Returns:
        Current configuration dictionary, or empty dict if not initialized
    """
    return _current_config if _current_config is not None else {}
