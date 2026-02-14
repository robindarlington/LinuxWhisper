"""Main daemon process for LinuxWhisper."""

import logging
import signal
import time
from linuxwhisper.config import load_config
from linuxwhisper.daemon.lifecycle import setup_daemon, shutdown_daemon, reload_config

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

    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGHUP, signal_handler)

    logger.info("LinuxWhisper daemon started")

    # Main loop - just keep running until stopped
    # Future phases will add real functionality here
    try:
        while running:
            time.sleep(0.1)
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        logger.info("Keyboard interrupt received")
        running = False

    # Clean shutdown
    logger.info("LinuxWhisper daemon stopped")
    shutdown_daemon()
