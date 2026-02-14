"""CLI commands for LinuxWhisper."""

import click
import os
import signal
import subprocess
import sys
import time
from linuxwhisper.daemon.pid import read_pid


@click.group()
@click.version_option(version="0.1.0", prog_name="linuxwhisper")
def cli():
    """LinuxWhisper voice dictation daemon."""
    pass


@cli.command()
def start():
    """Start the LinuxWhisper daemon in the background."""
    # Check if daemon is already running
    pid = read_pid()
    if pid is not None:
        click.echo(f"Daemon already running (PID {pid})")
        sys.exit(0)

    # Fork daemon into background
    subprocess.Popen(
        [sys.executable, "-m", "linuxwhisper"],
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    # Wait briefly for daemon to start
    time.sleep(0.5)

    # Verify daemon started
    pid = read_pid()
    if pid is not None:
        click.echo(f"LinuxWhisper daemon started (PID {pid})")
    else:
        click.echo("Failed to start daemon")
        sys.exit(1)


@cli.command()
def stop():
    """Stop the LinuxWhisper daemon."""
    # Read PID
    pid = read_pid()
    if pid is None:
        click.echo("Daemon not running")
        sys.exit(1)

    # Send SIGTERM
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError as e:
        click.echo(f"Failed to send stop signal to daemon (PID {pid}): {e}")
        sys.exit(1)

    # Wait up to 3 seconds for process to exit
    for _ in range(30):
        try:
            os.kill(pid, 0)  # Check if process exists
            time.sleep(0.1)
        except OSError:
            # Process has exited
            click.echo("LinuxWhisper daemon stopped")
            return

    # Still running after timeout
    click.echo(f"Failed to stop daemon (PID {pid})")
    sys.exit(1)


@cli.command()
def reload():
    """Reload the daemon configuration."""
    # Read PID
    pid = read_pid()
    if pid is None:
        click.echo("Daemon not running")
        sys.exit(1)

    # Send SIGHUP
    try:
        os.kill(pid, signal.SIGHUP)
        click.echo(f"Configuration reload signal sent to daemon (PID {pid})")
    except OSError as e:
        click.echo(f"Failed to send reload signal to daemon (PID {pid}): {e}")
        sys.exit(1)


@cli.command()
def status():
    """Check daemon status."""
    pid = read_pid()
    if pid is not None:
        click.echo(f"LinuxWhisper daemon is running (PID {pid})")
    else:
        click.echo("LinuxWhisper daemon is not running")
