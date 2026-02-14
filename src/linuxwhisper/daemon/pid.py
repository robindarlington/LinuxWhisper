"""PID file management for LinuxWhisper daemon."""

import os
from pathlib import Path
from xdg_base_dirs import xdg_runtime_dir


def get_pid_path() -> Path:
    """Get the path to the PID file.

    Returns XDG runtime directory path if available, falls back to
    ~/.local/run if not. Creates fallback directory if needed.

    Returns:
        Path to linuxwhisper.pid file
    """
    runtime_dir = xdg_runtime_dir()

    if runtime_dir:
        return runtime_dir / "linuxwhisper.pid"
    else:
        # Fallback to ~/.local/run
        fallback_dir = Path.home() / ".local" / "run"
        fallback_dir.mkdir(parents=True, exist_ok=True)
        return fallback_dir / "linuxwhisper.pid"


def write_pid_file() -> None:
    """Write the current process PID to the PID file."""
    pid_path = get_pid_path()
    pid_path.write_text(str(os.getpid()))


def remove_pid_file() -> None:
    """Remove the PID file if it exists.

    Does not raise if the file is already gone.
    """
    pid_path = get_pid_path()
    pid_path.unlink(missing_ok=True)


def read_pid() -> int | None:
    """Read PID from file and verify the process exists.

    Returns None if:
    - PID file doesn't exist
    - PID file is corrupt (invalid integer)
    - Process with that PID doesn't exist (stale PID file)

    Removes stale PID files automatically.

    Returns:
        Process ID if daemon is running, None otherwise
    """
    pid_path = get_pid_path()

    if not pid_path.exists():
        return None

    try:
        pid = int(pid_path.read_text().strip())

        # Verify process exists by sending signal 0 (no-op)
        os.kill(pid, 0)

        return pid

    except ValueError:
        # Corrupt PID file - remove it
        remove_pid_file()
        return None

    except OSError:
        # Process doesn't exist - remove stale PID file
        remove_pid_file()
        return None
