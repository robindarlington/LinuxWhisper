# Phase 1: Foundation - Research

**Researched:** 2026-02-15
**Domain:** Python daemon infrastructure, CLI management, configuration systems
**Confidence:** HIGH

## Summary

Phase 1 establishes daemon infrastructure for LinuxWhisper: background process management, CLI control interface, TOML configuration, and structured logging. Modern Python daemons on Linux integrate with systemd rather than implementing POSIX daemonization, use standard libraries for configuration (tomllib/tomli), and leverage systemd's journal for logging. The core pattern is Type=simple or Type=notify systemd service controlled via CLI that communicates with the daemon through signals (SIGHUP for reload, SIGTERM for stop) and PID files for process tracking.

**Primary recommendation:** Use systemd Type=simple service with click CLI, tomllib for config reading, structured logging to systemd journal, and PID file in $XDG_RUNTIME_DIR or ~/.local/run/ for process management.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| **click** | 8.1+ | CLI framework | Industry standard, composable commands, automatic help generation, type coercion. More ergonomic than argparse for multi-command CLIs. |
| **tomllib** | stdlib (3.11+) | TOML config reading | Native Python 3.11+ stdlib, read-only parser for TOML 1.0. Zero dependencies for reading config. |
| **tomli** | 2.0+ | TOML backport | tomllib backport for Python 3.9-3.10. Same API as stdlib tomllib. |
| **tomli-w** | 1.0+ | TOML writing | Write-only counterpart to tomli/tomllib. Needed for writing default config file. |
| **xdg-base-dirs** | 6.0+ | XDG directory paths | Returns XDG Base Directory spec paths ($XDG_CONFIG_HOME, $XDG_RUNTIME_DIR). Single-file, no dependencies. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **python-systemd** | 235+ | systemd integration | Optional. Use for Type=notify with sd_notify("READY=1"). Can implement sd_notify manually if avoiding dependencies. |
| **sdnotify** | 0.3+ | Pure Python sd_notify | Alternative to python-systemd. Lighter weight, no C bindings. Use if python-systemd unavailable. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| click | argparse (stdlib) | argparse more verbose, lacks composability. Adequate for simple CLIs but click cleaner for subcommands (start/stop/reload). |
| click | typer | typer uses type hints, very modern. Built on click. Good choice but click more established for daemon CLIs. |
| tomllib/tomli | python-toml | python-toml deprecated. tomllib is stdlib replacement. No reason to use python-toml. |
| tomllib/tomli | YAML (PyYAML) | TOML more human-friendly for config files. YAML parsing complexity and security issues (arbitrary code execution). TOML designed for configs. |
| xdg-base-dirs | pyxdg | pyxdg heavier, more features than needed. xdg-base-dirs minimal, single purpose. |
| systemd Type=simple | python-daemon | python-daemon implements POSIX daemonization (double fork). Unnecessary on systemd systems. systemd handles daemonization. |

**Installation:**

```bash
# Python 3.11+
pip install click tomli-w xdg-base-dirs

# Python 3.9-3.10 (add tomli backport)
pip install click tomli tomli-w xdg-base-dirs

# Optional systemd integration
pip install sdnotify  # Pure Python, lightweight
# OR
pip install systemd-python  # C bindings, more features
```

## Architecture Patterns

### Recommended Project Structure

```
linuxwhisper/
├── src/
│   └── linuxwhisper/
│       ├── __init__.py
│       ├── daemon/
│       │   ├── __init__.py
│       │   ├── main.py          # Daemon entry point, main loop
│       │   ├── lifecycle.py     # Startup/shutdown/reload logic
│       │   └── pid.py           # PID file management
│       ├── config/
│       │   ├── __init__.py
│       │   ├── loader.py        # Config loading with defaults
│       │   ├── defaults.py      # Default configuration dict
│       │   └── validator.py     # Config validation
│       ├── cli/
│       │   ├── __init__.py
│       │   └── commands.py      # Click commands (start/stop/reload)
│       └── logging/
│           ├── __init__.py
│           └── setup.py         # Logging configuration
├── config/
│   └── default_config.toml      # Shipped default config (reference)
├── systemd/
│   └── linuxwhisper.service     # systemd user service unit
├── pyproject.toml               # Python project metadata
└── README.md
```

### Pattern 1: CLI-to-Daemon Communication via Signals

**What:** CLI commands (stop/reload) send Unix signals to daemon process identified by PID file. No socket/IPC needed for simple control.

**When to use:** Daemon control operations are simple (start/stop/reload config). Systemd already manages lifecycle. Signals are standard Unix pattern.

**Example:**

```python
# cli/commands.py
import click
import signal
import os
from pathlib import Path

@click.group()
def cli():
    """LinuxWhisper voice dictation daemon."""
    pass

@cli.command()
def start():
    """Start the daemon (via systemd)."""
    os.system("systemctl --user start linuxwhisper")

@cli.command()
def stop():
    """Stop the daemon."""
    os.system("systemctl --user stop linuxwhisper")

@cli.command()
def reload():
    """Reload daemon configuration."""
    pid = read_pid_file()
    if pid:
        os.kill(pid, signal.SIGHUP)
        click.echo("Configuration reload signal sent")
    else:
        click.echo("Daemon not running", err=True)

def read_pid_file() -> int | None:
    """Read PID from file."""
    pid_path = Path.home() / ".local/run/linuxwhisper.pid"
    if pid_path.exists():
        return int(pid_path.read_text().strip())
    return None
```

### Pattern 2: Layered Configuration with Default Fallback

**What:** Ship default config embedded in package, write user config to ~/.config/linuxwhisper/config.toml on first run, merge defaults with user values (user overrides).

**When to use:** Configuration has many options with sensible defaults, user should only configure what they want to change.

**Example:**

```python
# config/defaults.py
DEFAULT_CONFIG = {
    "hotkey": "F13",
    "mode": "hold",  # or "toggle"
    "model": "base.en",
    "audio": {
        "sample_rate": 16000,
        "channels": 1,
        "format": "s16le",
    },
    "logging": {
        "level": "INFO",
        "daemon_events": True,
    },
}

# config/loader.py
import tomllib  # Python 3.11+
import tomli_w
from pathlib import Path
from xdg_base_dirs import xdg_config_home

def get_config_path() -> Path:
    """Return path to user config file."""
    return xdg_config_home() / "linuxwhisper" / "config.toml"

def load_config() -> dict:
    """Load config, merging user values with defaults."""
    config_path = get_config_path()

    # Start with defaults
    config = DEFAULT_CONFIG.copy()

    # Create config directory if missing
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # If user config exists, load and merge
    if config_path.exists():
        with open(config_path, "rb") as f:
            user_config = tomllib.load(f)
        config = merge_config(config, user_config)
    else:
        # First run: write default config for user to edit
        write_default_config(config_path)

    return config

def merge_config(defaults: dict, user: dict) -> dict:
    """Deep merge user config into defaults (user overrides)."""
    merged = defaults.copy()
    for key, value in user.items():
        if isinstance(value, dict) and key in merged:
            merged[key] = merge_config(merged[key], value)
        else:
            merged[key] = value
    return merged

def write_default_config(path: Path):
    """Write default config to file."""
    with open(path, "wb") as f:
        tomli_w.dump(DEFAULT_CONFIG, f)
```

### Pattern 3: Daemon Lifecycle with Signal Handlers

**What:** Daemon responds to SIGTERM (shutdown), SIGHUP (reload config), SIGINT (Ctrl+C during development). Graceful shutdown pattern.

**When to use:** Any daemon that needs clean resource cleanup (close files, flush logs, notify systemd).

**Example:**

```python
# daemon/main.py
import signal
import logging
from .lifecycle import setup_daemon, shutdown_daemon, reload_config

logger = logging.getLogger(__name__)
running = True

def signal_handler(signum, frame):
    """Handle Unix signals."""
    global running

    if signum == signal.SIGTERM or signum == signal.SIGINT:
        logger.info(f"Received {signal.Signals(signum).name}, shutting down...")
        running = False
    elif signum == signal.SIGHUP:
        logger.info("Received SIGHUP, reloading configuration...")
        reload_config()

def run_daemon():
    """Main daemon entry point."""
    # Set up signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGHUP, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Initialize daemon
    setup_daemon()
    logger.info("LinuxWhisper daemon started")

    # Main loop
    try:
        while running:
            # Phase 1: Just idle loop
            # Phase 2+: Process hotkey events, audio, etc.
            time.sleep(0.1)
    finally:
        shutdown_daemon()
        logger.info("LinuxWhisper daemon stopped")
```

### Pattern 4: PID File Management

**What:** Write process ID to file at startup, remove on shutdown. Used by CLI to send signals and check if daemon is running.

**When to use:** CLI needs to communicate with background daemon. Systemd already tracks PID but PID file useful for direct CLI interaction.

**Example:**

```python
# daemon/pid.py
import os
from pathlib import Path
from xdg_base_dirs import xdg_runtime_dir

def get_pid_path() -> Path:
    """Get PID file path, preferring XDG_RUNTIME_DIR."""
    runtime_dir = xdg_runtime_dir()
    if runtime_dir:
        return runtime_dir / "linuxwhisper.pid"
    else:
        # Fallback to ~/.local/run/
        fallback = Path.home() / ".local/run"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback / "linuxwhisper.pid"

def write_pid_file():
    """Write current process PID to file."""
    pid_path = get_pid_path()
    pid_path.write_text(str(os.getpid()))

def remove_pid_file():
    """Remove PID file."""
    pid_path = get_pid_path()
    if pid_path.exists():
        pid_path.unlink()

def read_pid() -> int | None:
    """Read PID from file if exists and process is running."""
    pid_path = get_pid_path()
    if not pid_path.exists():
        return None

    try:
        pid = int(pid_path.read_text().strip())
        # Check if process is actually running
        os.kill(pid, 0)  # Raises OSError if process doesn't exist
        return pid
    except (ValueError, OSError):
        # PID file is stale
        remove_pid_file()
        return None
```

### Pattern 5: Structured Logging to systemd Journal

**What:** Log to systemd journal with structured fields (PRIORITY, CODE_FILE, CODE_LINE). Use Python logging framework with optional JournalHandler.

**When to use:** Daemon runs as systemd service. Journal provides centralized logging, automatic rotation, metadata.

**Example:**

```python
# logging/setup.py
import logging
import sys

def setup_logging(config: dict):
    """Configure logging for daemon."""
    level = config.get("logging", {}).get("level", "INFO")

    # Basic stdout logging (captured by systemd)
    logging.basicConfig(
        level=getattr(logging, level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout  # systemd captures stdout to journal
    )

    # Optional: Use systemd JournalHandler for structured logging
    try:
        from systemd.journal import JournalHandler

        journal_handler = JournalHandler()
        journal_handler.setFormatter(logging.Formatter(
            '[%(levelname)s] %(message)s'
        ))

        logger = logging.getLogger()
        logger.addHandler(journal_handler)
    except ImportError:
        # systemd.journal not available, stdout logging sufficient
        pass

# Usage in daemon
logger = logging.getLogger(__name__)
logger.info("Daemon started")  # Appears in journalctl -u linuxwhisper
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| TOML parsing | Custom TOML parser | tomllib (stdlib 3.11+) or tomli | TOML spec is complex, edge cases. Stdlib implementation tested and maintained. |
| PID file locking | Custom file locking | Use os.kill(pid, 0) to verify process | Race conditions, stale locks. os.kill is atomic check. |
| Daemon double-fork | POSIX daemonization | systemd Type=simple | systemd handles daemonization, process supervision, restart on crash. No need to implement fork/setsid/chdir dance. |
| Config validation | Manual dict checking | pydantic or dataclasses | Type safety, automatic validation, better error messages. For Phase 1, basic dict validation sufficient. |
| XDG directory paths | Hardcoded ~/.config | xdg-base-dirs library | XDG spec has fallbacks, environment variable overrides. Library handles edge cases. |
| Signal handling | Raw signal module | signal.signal() with proper cleanup | Signal handlers have constraints (no blocking operations). Pattern is standard but use established cleanup patterns. |

**Key insight:** Python standard library and systemd provide most daemon infrastructure. Don't reimplement what the platform provides.

## Common Pitfalls

### Pitfall 1: Not Waiting for Subprocess to Write PID File

**What goes wrong:** CLI starts daemon via systemd, immediately tries to read PID file, fails because daemon hasn't written it yet.

**Why it happens:** Process startup takes time. Writing PID file is not instant.

**How to avoid:**
- Use systemd's Type=notify to signal readiness
- CLI should check systemd status, not PID file existence
- PID file is for reload/manual operations, not startup verification

**Warning signs:**
- CLI reports "daemon not running" immediately after start
- Race conditions in integration tests

### Pitfall 2: Stale PID Files After Crash

**What goes wrong:** Daemon crashes, PID file remains. CLI reads stale PID, sends signals to wrong process or fails.

**Why it happens:** PID file not removed on abnormal exit (kill -9, crash, power loss).

**How to avoid:**
- Always verify process exists with `os.kill(pid, 0)` before trusting PID file
- Remove stale PID file if process doesn't exist
- Use systemd service management as source of truth for daemon state

**Warning signs:**
- "Daemon running" but no process
- PID file points to different process (PID reused)

### Pitfall 3: Config File Permission Issues

**What goes wrong:** Config file created with restrictive permissions (600), later edited by user with different umask, daemon can't read it.

**Why it happens:** Default file creation permissions (umask) vary by system and user.

**How to avoid:**
- Create config directory with `mkdir(mode=0o755)`
- Write config file with `open(mode="wb")` (default permissions)
- Document that config file should be user-readable
- Don't store secrets in config file (no need for 600 permissions)

**Warning signs:**
- Permission denied errors on config load
- Works for one user, fails for another

### Pitfall 4: Blocking Main Loop with Heavy Operations

**What goes wrong:** Daemon main loop does heavy processing (like loading Whisper model), becomes unresponsive to signals.

**Why it happens:** Signal handlers only run between Python bytecode instructions. Long-running C extensions block signal delivery.

**How to avoid:**
- Keep main loop lightweight (sleep, check flags)
- Do heavy initialization before main loop
- Use asyncio or threading for concurrent operations (Phase 2+)
- Signal handlers should only set flags, actual work happens in main loop

**Warning signs:**
- SIGTERM doesn't stop daemon immediately
- Daemon appears "stuck" during operations

### Pitfall 5: Hardcoded Config Path

**What goes wrong:** Config path hardcoded to `~/.config/linuxwhisper/config.toml`, breaks when XDG_CONFIG_HOME set by user.

**Why it happens:** Assuming default XDG directories, not reading environment variables.

**How to avoid:**
- Use xdg-base-dirs library to get XDG paths
- Respect XDG_CONFIG_HOME, XDG_RUNTIME_DIR environment variables
- Fall back to ~/.config, ~/.local/run only if XDG vars unset

**Warning signs:**
- Works on developer machine, fails on user's system
- Config not found when XDG_CONFIG_HOME set

### Pitfall 6: Logging Before systemd Capture

**What goes wrong:** Daemon logs to file before systemd service starts, logs not in journal.

**Why it happens:** Logging configured before systemd takes over stdout.

**How to avoid:**
- Always log to stdout in systemd services
- Set `StandardOutput=journal` in service unit
- systemd captures stdout and adds metadata
- Don't configure file handlers unless explicitly needed

**Warning signs:**
- Logs appear in console but not `journalctl`
- Early startup messages missing from journal

## Code Examples

Verified patterns from official sources:

### Basic CLI with Click

```python
# cli/commands.py
import click
import os

@click.group()
def cli():
    """LinuxWhisper voice dictation daemon."""
    pass

@cli.command()
def start():
    """Start the daemon."""
    click.echo("Starting LinuxWhisper daemon...")
    os.system("systemctl --user start linuxwhisper")

@cli.command()
def stop():
    """Stop the daemon."""
    click.echo("Stopping LinuxWhisper daemon...")
    os.system("systemctl --user stop linuxwhisper")

@cli.command()
def status():
    """Show daemon status."""
    os.system("systemctl --user status linuxwhisper")

@cli.command()
def reload():
    """Reload configuration."""
    from .daemon.pid import read_pid
    import signal

    pid = read_pid()
    if pid:
        os.kill(pid, signal.SIGHUP)
        click.echo("Configuration reload signal sent")
    else:
        click.echo("Daemon not running", err=True)
        raise click.Abort()

if __name__ == '__main__':
    cli()
```

### systemd User Service Unit

```ini
# systemd/linuxwhisper.service
[Unit]
Description=LinuxWhisper Voice Dictation Daemon
Documentation=https://github.com/user/linuxwhisper
After=sound.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 -m linuxwhisper.daemon
Restart=on-failure
RestartSec=5s

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=linuxwhisper

# Security hardening
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=default.target
```

### Config Loading with Defaults

```python
# config/loader.py
import sys
from pathlib import Path

# Python 3.11+ uses tomllib, earlier versions use tomli
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

import tomli_w
from xdg_base_dirs import xdg_config_home

DEFAULT_CONFIG = {
    "hotkey": "F13",
    "mode": "hold",
    "model": "base.en",
    "logging": {
        "level": "INFO",
    },
}

def load_config() -> dict:
    """Load configuration with defaults."""
    config_path = xdg_config_home() / "linuxwhisper" / "config.toml"

    # Ensure config directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Write default config if doesn't exist
    if not config_path.exists():
        with open(config_path, "wb") as f:
            tomli_w.dump(DEFAULT_CONFIG, f)
        return DEFAULT_CONFIG.copy()

    # Load user config
    with open(config_path, "rb") as f:
        user_config = tomllib.load(f)

    # Merge with defaults (user overrides)
    return merge_config(DEFAULT_CONFIG, user_config)

def merge_config(defaults: dict, user: dict) -> dict:
    """Deep merge user config into defaults."""
    result = defaults.copy()
    for key, value in user.items():
        if isinstance(value, dict) and key in result and isinstance(result[key], dict):
            result[key] = merge_config(result[key], value)
        else:
            result[key] = value
    return result
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| python-daemon double-fork | systemd Type=simple | ~2015 (systemd adoption) | Simpler code, better integration, automatic restart |
| python-toml library | tomllib (stdlib) | Python 3.11 (2022) | No external dependencies for TOML reading |
| ConfigParser (.ini files) | TOML | ~2020s | Better human readability, richer data types |
| SysV init scripts | systemd user services | ~2015 | User-level daemons without root, standard management |
| File logging | systemd journal | ~2015 | Centralized logs, automatic rotation, structured fields |

**Deprecated/outdated:**
- **python-daemon library:** Still works but unnecessary on systemd. Use systemd Type=simple instead.
- **python-toml (pytoml):** Deprecated in favor of tomllib (stdlib). Use tomli backport for Python <3.11.
- **argparse for multi-command CLIs:** Still works but click more ergonomic for daemon control (start/stop/reload).

## Open Questions

1. **Should we use Type=simple or Type=notify?**
   - What we know: Type=simple works, daemon starts immediately. Type=notify waits for "READY=1" signal.
   - What's unclear: Whether Phase 1 needs Type=notify. Daemon has no long initialization.
   - Recommendation: Use Type=simple in Phase 1. Switch to Type=notify in Phase 2+ if Whisper model loading takes time (startup notification).

2. **Should PID file management be implemented in Phase 1?**
   - What we know: systemd tracks PID. PID file enables direct CLI signal sending.
   - What's unclear: Whether CLI should use systemd commands only or also support signals.
   - Recommendation: Implement PID file in Phase 1 for reload command (SIGHUP). Start/stop use systemd.

3. **Should config validation use pydantic or basic checks?**
   - What we know: pydantic provides automatic validation, type safety. Basic dict checks simpler.
   - What's unclear: Complexity vs benefit for Phase 1 (few config options).
   - Recommendation: Basic validation in Phase 1 (check key existence, types). Consider pydantic in Phase 3+ when config grows.

## Sources

### Primary (HIGH confidence)

- [tomllib documentation](https://docs.python.org/3/library/tomllib.html) - Python 3.11+ stdlib TOML parser
- [click documentation](https://click.palletsprojects.com/) - CLI framework patterns and examples
- [systemd.service documentation](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html) - Service unit configuration
- [signal module documentation](https://docs.python.org/3/library/signal.html) - Unix signal handling in Python
- [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/latest/) - Standard directory locations

### Secondary (MEDIUM confidence)

- [Systemd: The Complete Guide for 2026](https://devtoolbox.dedyn.io/blog/systemd-complete-guide) - Modern systemd best practices
- [From Python to Daemon with systemd](https://levelup.gitconnected.com/from-python-to-daemon-how-to-turn-your-python-app-into-a-linux-service-controlled-by-systemd-d87b59adfe7a) - Python systemd integration
- [Logging to systemd Journal in Python](https://lincolnloop.com/blog/logging-systemds-journal-python/) - JournalHandler usage
- [Python and TOML: Read, Write, and Configure with tomllib](https://realpython.com/python-toml/) - TOML configuration patterns
- [Where to Store PID Files for User-Run Daemons](https://linuxvox.com/blog/storing-pid-file-for-a-daemon-run-as-user/) - PID file location best practices
- [Python Threading: When to Use Daemon Threads and When to Avoid Them](https://levelup.gitconnected.com/python-threading-when-to-use-daemon-threads-and-when-to-avoid-them-4d0b6f66aa74) - Thread management pitfalls
- [Working with Python Configuration Files: Tutorial & Best Practices](https://configu.com/blog/working-with-python-configuration-files-tutorial-best-practices/) - Config management patterns

### Tertiary (LOW confidence, needs validation)

- [python-systemd GitHub](https://github.com/systemd/python-systemd) - systemd Python bindings, not heavily used in research
- [sdnotify PyPI](https://pypi.org/project/sdnotify/) - Pure Python sd_notify, referenced but not verified in depth

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - stdlib (tomllib, signal), click well-documented, xdg-base-dirs straightforward
- Architecture: HIGH - systemd patterns well-established, signal handling documented, config merging standard
- Pitfalls: HIGH - sourced from official docs, web search findings verified with multiple sources
- Code examples: HIGH - based on official documentation and verified patterns

**Research date:** 2026-02-15
**Valid until:** 60 days (stable domain, low churn in daemon patterns)
