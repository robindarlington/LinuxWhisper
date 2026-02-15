"""Main daemon process for LinuxWhisper."""

import logging
import signal
import sys
import time
from linuxwhisper.config import load_config
from linuxwhisper.daemon.lifecycle import setup_daemon, shutdown_daemon, reload_config
from linuxwhisper.pipeline import DictationPipeline
from linuxwhisper.hotkey import check_input_permissions, get_permission_instructions

logger = logging.getLogger(__name__)

# Global flag for main loop
running = True


def signal_handler(signum: int, frame) -> None:
    """Handle signals sent to the daemon.

    SIGTERM/SIGINT: Stop the daemon cleanly
    SIGHUP: Reload configuration
    """
    global running

    if signum in (signal.SIGTERM, signal.SIGINT):
        logger.info(f"Received signal {signum}, stopping daemon")
        running = False
    elif signum == signal.SIGHUP:
        logger.info(f"Received SIGHUP, reloading configuration")
        reload_config()
        logger.info("Config reloaded. Restart daemon for hotkey/model changes to take effect.")


def run_daemon() -> None:
    """Main daemon entry point.

    Loads config, sets up daemon, registers signal handlers,
    and runs the main loop until shutdown is requested.
    """
    global running

    # Load configuration
    config = load_config()

    # Set up daemon (logging, PID file)
    setup_daemon(config)

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
    except Exception as e:
        logger.error(f"Failed to start dictation pipeline: {e}", exc_info=True)
        shutdown_daemon()
        sys.exit(1)

    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGHUP, signal_handler)

    logger.info("LinuxWhisper daemon started")

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
