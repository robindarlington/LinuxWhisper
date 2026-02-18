"""Manage the systemd user service lifecycle for LinuxWhisper."""

import shutil
import subprocess
import sys
from pathlib import Path

SERVICE_NAME = "linuxwhisper.service"

SERVICE_TEMPLATE = """\
[Unit]
Description=LinuxWhisper voice dictation daemon
After=graphical-session.target
PartOf=graphical-session.target
Wants=ydotool.service
StartLimitIntervalSec=300
StartLimitBurst=5

[Service]
Type=simple
ExecStart={venv_python} -m linuxwhisper
ExecReload=/bin/kill -HUP $MAINPID
Restart=on-failure
RestartSec=5
Environment=PYTHONUNBUFFERED=1
TimeoutStopSec=10

[Install]
WantedBy=graphical-session.target
"""


def get_service_dir() -> Path:
    """Return the systemd user unit directory."""
    return Path.home() / ".config" / "systemd" / "user"


def get_service_path() -> Path:
    """Return the full path to the LinuxWhisper service file."""
    return get_service_dir() / SERVICE_NAME


def generate_service_file() -> str:
    """Generate the systemd service file content with the current Python path."""
    return SERVICE_TEMPLATE.format(venv_python=sys.executable)


def is_systemd_available() -> bool:
    """Check if systemctl is available on this system."""
    return shutil.which("systemctl") is not None


def is_service_installed() -> bool:
    """Check if the service file exists."""
    return get_service_path().is_file()


def is_service_enabled() -> bool:
    """Check if the systemd service is enabled."""
    if not is_systemd_available():
        return False
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-enabled", SERVICE_NAME],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip() == "enabled"
    except (subprocess.TimeoutExpired, OSError):
        return False


def is_service_active() -> bool:
    """Check if the systemd service is currently running."""
    if not is_systemd_available():
        return False
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-active", SERVICE_NAME],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip() == "active"
    except (subprocess.TimeoutExpired, OSError):
        return False


def install_service() -> None:
    """Install the systemd user service file and reload the daemon."""
    if not is_systemd_available():
        raise RuntimeError("systemctl not found. systemd is required for service management.")
    get_service_dir().mkdir(parents=True, exist_ok=True)
    content = generate_service_file()
    get_service_path().write_text(content)
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True, timeout=10)


def uninstall_service() -> None:
    """Uninstall the systemd user service file."""
    if not is_service_installed():
        raise FileNotFoundError(f"Service file not found: {get_service_path()}")
    if is_service_enabled():
        subprocess.run(
            ["systemctl", "--user", "disable", SERVICE_NAME],
            check=True, timeout=10,
        )
    if is_service_active():
        subprocess.run(
            ["systemctl", "--user", "stop", SERVICE_NAME],
            check=True, timeout=10,
        )
    get_service_path().unlink()
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True, timeout=10)


__all__ = [
    "SERVICE_NAME",
    "get_service_dir",
    "get_service_path",
    "generate_service_file",
    "is_systemd_available",
    "is_service_installed",
    "is_service_enabled",
    "is_service_active",
    "install_service",
    "uninstall_service",
]
