"""Main daemon process for LinuxWhisper."""

import logging
import signal
import sys
import time
from linuxwhisper.config import load_config
from linuxwhisper.config.validation import validate_config_input, check_compositor_conflicts
from linuxwhisper.daemon.lifecycle import (
    setup_daemon, shutdown_daemon, reload_config, set_pipeline_ref, reload_config_safe
)
from linuxwhisper.pipeline import DictationPipeline
from linuxwhisper.hotkey import check_input_permissions, get_permission_instructions

logger = logging.getLogger(__name__)

# Global flag for main loop
running = True


def signal_handler(signum: int, frame) -> None:
    """Handle signals sent to the daemon.

    SIGTERM/SIGINT: Stop the daemon cleanly
    SIGHUP: Reload configuration (state-aware, defers during recording)
    """
    global running

    if signum in (signal.SIGTERM, signal.SIGINT):
        logger.info(f"Received signal {signum}, stopping daemon")
        running = False
    elif signum == signal.SIGHUP:
        logger.info(f"Received SIGHUP, reloading configuration")
        result = reload_config_safe()
        if result is None:
            logger.info("Config reload was deferred or failed. See previous log messages for details.")


def run_daemon() -> None:
    """Main daemon entry point.

    Loads config, sets up daemon, validates config, registers signal handlers,
    and runs the main loop until shutdown is requested.
    """
    global running

    # Load configuration
    config = load_config()

    # Set up daemon (logging, PID file)
    setup_daemon(config)

    # Validate input configuration (fail-fast)
    errors = validate_config_input(config)
    if errors:
        for err in errors:
            logger.error(f"Configuration error: {err}")
        logger.error("Daemon cannot start with invalid configuration. Fix config and retry.")
        shutdown_daemon()
        sys.exit(1)

    # Check for compositor binding conflicts (informational only)
    conflicts = check_compositor_conflicts(config.get("hotkey", "HOME"))
    for conflict in conflicts:
        logger.warning(f"Hotkey conflict detected: {conflict}")
    if conflicts:
        logger.warning(
            f"Hotkey '{config.get('hotkey', 'HOME')}' may conflict with compositor bindings. "
            "LinuxWhisper will still work (evdev grab takes priority), but the key may not reach other apps."
        )

    # Check input permissions before starting pipeline
    if not check_input_permissions():
        error_msg = f"Input permissions not available.\n{get_permission_instructions()}"
        logger.error(error_msg)
        shutdown_daemon()
        sys.exit(1)

    # Create and start the dictation pipeline
    pipeline = None
    try:
        pipeline = DictationPipeline(config)
        pipeline.start()
        # Register pipeline reference for state-aware config reload
        set_pipeline_ref(pipeline)
    except Exception as e:
        logger.error(f"Failed to start dictation pipeline: {e}", exc_info=True)
        shutdown_daemon()
        sys.exit(1)

    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGHUP, signal_handler)

    # Log startup info including mode, hotkey, and toggle_timeout (for toggle mode)
    mode = config.get("mode", "hold")
    hotkey = config.get("hotkey", "HOME")
    timeout_info = ""
    if mode == "toggle":
        timeout_info = f", toggle_timeout={config.get('toggle_timeout', 120)}s"
    logger.info(f"LinuxWhisper daemon started (mode={mode}, hotkey={hotkey}{timeout_info})")

    # Main loop - keep running until stopped
    # The pipeline runs in a daemon thread, main thread just sleeps
    try:
        while running:
            time.sleep(0.5)
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        logger.info("Keyboard interrupt received")
        running = False

    # Clean shutdown - stop pipeline before removing PID file
    if pipeline:
        pipeline.stop()

    logger.info("LinuxWhisper daemon stopped")
    shutdown_daemon()
