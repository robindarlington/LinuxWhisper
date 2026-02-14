"""Entry point for running LinuxWhisper daemon as a module.

This enables: python -m linuxwhisper
Used by systemd ExecStart and CLI subprocess launch.
"""

from linuxwhisper.daemon import run_daemon

if __name__ == "__main__":
    run_daemon()
