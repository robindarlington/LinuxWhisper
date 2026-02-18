"""CLI commands for LinuxWhisper."""

import click
import os
import signal
import subprocess
import sys
import time
from linuxwhisper.daemon.pid import read_pid
from linuxwhisper.service import (
    install_service, uninstall_service,
    is_systemd_available, is_service_installed,
    is_service_enabled, is_service_active,
    get_service_path,
)


def _systemctl(action: str) -> subprocess.CompletedProcess:
    """Run a systemctl --user command for the linuxwhisper service."""
    return subprocess.run(
        ["systemctl", "--user", action, "linuxwhisper.service"],
        capture_output=True,
        text=True,
        timeout=30,
    )


@click.group()
@click.version_option(version="0.1.0", prog_name="linuxwhisper")
def cli():
    """LinuxWhisper voice dictation daemon."""
    pass


@cli.command()
def start():
    """Start the LinuxWhisper daemon in the background."""
    if is_service_enabled():
        if is_service_active():
            click.echo("LinuxWhisper daemon is already running (systemd-managed)")
            sys.exit(0)
        result = _systemctl("start")
        if result.returncode == 0:
            click.echo("LinuxWhisper daemon started (systemd-managed)")
        else:
            click.echo(f"Failed to start via systemd: {result.stderr.strip()}")
            sys.exit(1)
        return

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
    if is_service_enabled():
        if not is_service_active():
            click.echo("LinuxWhisper daemon is not running (systemd-managed)")
            sys.exit(1)
        result = _systemctl("stop")
        if result.returncode == 0:
            click.echo("LinuxWhisper daemon stopped (systemd-managed)")
        else:
            click.echo(f"Failed to stop via systemd: {result.stderr.strip()}")
            sys.exit(1)
        return

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
    if is_service_enabled():
        if not is_service_active():
            click.echo("LinuxWhisper daemon is not running (systemd-managed)")
            sys.exit(1)
        result = _systemctl("reload")
        if result.returncode == 0:
            click.echo("Configuration reloaded (systemd-managed)")
        else:
            click.echo(f"Failed to reload via systemd: {result.stderr.strip()}")
            sys.exit(1)
        return

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
    if is_service_enabled():
        result = subprocess.run(
            ["systemctl", "--user", "status", "linuxwhisper.service"],
            capture_output=True, text=True, timeout=30,
        )
        if result.stdout.strip():
            click.echo(result.stdout.strip())
        if is_service_active():
            click.echo("\nLinuxWhisper daemon is running (systemd-managed)")
        else:
            click.echo("\nLinuxWhisper daemon is not running (systemd-managed)")
        return

    pid = read_pid()
    if pid is not None:
        click.echo(f"LinuxWhisper daemon is running (PID {pid})")
    else:
        click.echo("LinuxWhisper daemon is not running")


@cli.group()
def service():
    """Manage the systemd user service."""
    pass


@service.command()
def install():
    """Install the systemd user service file."""
    if not is_systemd_available():
        click.echo("systemctl not found. systemd is required for service management.")
        sys.exit(1)
    if is_service_installed():
        click.echo(f"Service file already exists at {get_service_path()}. Overwriting...")
    try:
        install_service()
    except (RuntimeError, subprocess.CalledProcessError) as e:
        click.echo(f"Failed to install service: {e}")
        sys.exit(1)
    click.echo(f"Service file installed to {get_service_path()}")
    click.echo("")
    click.echo("To start now and enable on login:")
    click.echo("  systemctl --user enable --now linuxwhisper")
    click.echo("")
    click.echo("To view logs:")
    click.echo("  journalctl --user -u linuxwhisper -f")


@service.command()
def uninstall():
    """Uninstall the systemd user service file."""
    if not is_systemd_available():
        click.echo("systemctl not found. systemd is required for service management.")
        sys.exit(1)
    try:
        uninstall_service()
    except FileNotFoundError:
        click.echo("Service is not installed.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        click.echo(f"Failed to uninstall service: {e}")
        sys.exit(1)
    click.echo("Service file removed. LinuxWhisper will no longer start on login.")


@service.command("status")
def service_status():
    """Show systemd service status."""
    if not is_systemd_available():
        click.echo("systemd is not available on this system.")
        return
    installed = is_service_installed()
    enabled = is_service_enabled() if installed else False
    active = is_service_active() if installed else False
    click.echo(f"Installed: {'yes' if installed else 'no'}")
    click.echo(f"Enabled:   {'yes' if enabled else 'no'}")
    click.echo(f"Active:    {'yes' if active else 'no'}")
    if installed and not enabled:
        click.echo("\nRun 'systemctl --user enable --now linuxwhisper' to enable.")
    if not installed:
        click.echo("\nRun 'linuxwhisper service install' to install the service.")
