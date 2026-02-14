---
phase: 01-foundation
plan: 02
subsystem: daemon
tags: [daemon, cli, pid-management, logging, subprocess]
dependency_graph:
  requires: [package-structure, config-system]
  provides: [daemon-lifecycle, cli-commands, pid-file-management, signal-handling]
  affects: [all-future-modules]
tech_stack:
  added: []
  patterns: [daemon-fork, signal-handlers, pid-file, subprocess-launch]
key_files:
  created:
    - src/linuxwhisper/__main__.py
    - src/linuxwhisper/daemon/main.py
    - src/linuxwhisper/daemon/lifecycle.py
    - src/linuxwhisper/daemon/pid.py
    - src/linuxwhisper/logging/setup.py
  modified:
    - src/linuxwhisper/daemon/__init__.py
    - src/linuxwhisper/logging/__init__.py
    - src/linuxwhisper/cli/__init__.py
    - src/linuxwhisper/cli/commands.py
decisions:
  - "Use subprocess.Popen with start_new_session for daemon backgrounding (Phase 1 only, systemd in Phase 7)"
  - "XDG runtime dir for PID file with fallback to ~/.local/run"
  - "Signal-based daemon control: SIGTERM/SIGINT for stop, SIGHUP for reload"
  - "Log to stdout for systemd journal capture"
metrics:
  duration: "3 minutes"
  completed: "2026-02-15"
  tasks: 2
  commits: 2
---

# Phase 01 Plan 02: Daemon Process and CLI Commands Summary

**One-liner:** Background daemon with PID management, signal-based lifecycle control, and CLI commands for start/stop/reload/status.

## Overview

Implemented the LinuxWhisper daemon process that runs in the background, accepts control signals for lifecycle management, and provides CLI commands for user interaction. The daemon uses proper PID file management to prevent double-start, handles SIGTERM/SIGINT for clean shutdown, and SIGHUP for configuration reload. All lifecycle events are logged to stdout for systemd journal capture.

## Tasks Completed

### Task 1: Implement daemon core with PID management and logging
**Commit:** `7bfd9aa`

Created the daemon infrastructure with:
- **Logging setup** (`logging/setup.py`): Configures Python logging from config dict, sets level, formats output, logs to stdout
- **PID management** (`daemon/pid.py`):
  - `get_pid_path()`: Returns XDG runtime dir path with fallback to ~/.local/run
  - `write_pid_file()`: Writes current PID to file
  - `read_pid()`: Reads PID and verifies process exists (removes stale PID files)
  - `remove_pid_file()`: Cleans up PID file on shutdown
- **Lifecycle orchestration** (`daemon/lifecycle.py`):
  - `setup_daemon()`: Configures logging, writes PID file, stores config reference
  - `shutdown_daemon()`: Removes PID file, logs shutdown event
  - `reload_config()`: Re-reads config, updates logging level if changed, logs reload event
- **Main daemon** (`daemon/main.py`):
  - `run_daemon()`: Entry point that loads config, sets up daemon, registers signal handlers, runs main loop
  - Signal handler for SIGTERM/SIGINT (stop) and SIGHUP (reload)
  - Main loop using `while running: time.sleep(0.1)` (placeholder for future functionality)
- **Module entry point** (`__main__.py`): Enables `python -m linuxwhisper` for daemon startup

**Files created:**
- `/home/rob/Documents/Projects/LinuxWhisper/src/linuxwhisper/__main__.py`
- `/home/rob/Documents/Projects/LinuxWhisper/src/linuxwhisper/daemon/main.py`
- `/home/rob/Documents/Projects/LinuxWhisper/src/linuxwhisper/daemon/lifecycle.py`
- `/home/rob/Documents/Projects/LinuxWhisper/src/linuxwhisper/daemon/pid.py`
- `/home/rob/Documents/Projects/LinuxWhisper/src/linuxwhisper/logging/setup.py`

**Files modified:**
- `/home/rob/Documents/Projects/LinuxWhisper/src/linuxwhisper/daemon/__init__.py`
- `/home/rob/Documents/Projects/LinuxWhisper/src/linuxwhisper/logging/__init__.py`

### Task 2: Implement CLI commands for daemon control
**Commit:** `29cdb55`

Built complete CLI interface with four commands:
- **start**: Checks if daemon already running (via `read_pid()`), forks daemon to background using `subprocess.Popen` with `start_new_session=True`, waits 0.5s and verifies startup, reports PID or failure
- **stop**: Reads PID, sends SIGTERM, polls for up to 3 seconds to confirm exit (checks with `os.kill(pid, 0)`), reports success or timeout failure
- **reload**: Reads PID, sends SIGHUP for config reload, reports signal sent
- **status**: Reads PID, reports running/not running with PID

Edge cases handled:
- Stop when not running: exits with error code 1
- Double start: detects existing daemon and exits cleanly
- Stale PID files: automatically removed by `read_pid()`

**Files modified:**
- `/home/rob/Documents/Projects/LinuxWhisper/src/linuxwhisper/cli/__init__.py`
- `/home/rob/Documents/Projects/LinuxWhisper/src/linuxwhisper/cli/commands.py`

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

All verification criteria passed:

1. **Daemon startup**: `linuxwhisper start` launches daemon in background and prints PID
2. **Status check**: `linuxwhisper status` correctly reports running with PID
3. **Config reload**: `linuxwhisper reload` sends SIGHUP, daemon logs reload event
4. **Clean shutdown**: `linuxwhisper stop` sends SIGTERM, daemon shuts down within timeout
5. **PID file lifecycle**: Created at `/run/user/1000/linuxwhisper.pid` on start, removed on stop
6. **No orphaned processes**: Verified via `ps` and PID file cleanup
7. **Logging output**: All lifecycle events (start, reload, stop) logged to stdout
8. **Edge cases**: Stop when not running exits with error, double start detected and prevented

## Key Technical Decisions

1. **Subprocess daemon launch for Phase 1**: Used `subprocess.Popen` with `start_new_session=True` for daemon backgrounding. This is a temporary approach for Phase 1 self-containment. Phase 7 will add systemd service for production deployment.

2. **XDG runtime directory for PID file**: Chose `/run/user/$UID/linuxwhisper.pid` (XDG runtime dir) with fallback to `~/.local/run/linuxwhisper.pid`. XDG runtime dir is the standard location for per-user runtime files and is automatically cleaned up on logout.

3. **Signal-based lifecycle control**:
   - SIGTERM/SIGINT: Clean shutdown (allows daemon to remove PID file)
   - SIGHUP: Config reload (standard Unix convention)
   - This approach works for both subprocess launch (Phase 1) and systemd (Phase 7)

4. **Logging to stdout**: Daemon logs to stdout instead of file. This enables systemd to capture logs to journal automatically in Phase 7, while still being visible during Phase 1 development.

5. **Stale PID detection**: `read_pid()` verifies process existence using `os.kill(pid, 0)` and removes stale PID files automatically. This prevents false positives after crashes or system reboots.

## Dependencies Added

No new dependencies (all functionality uses stdlib).

## Impact on Future Work

This plan establishes the running daemon that all future components will plug into:

- **Phase 2 (Hotkey Detection)**: evdev listener will run inside the daemon main loop
- **Phase 3 (Audio Capture)**: Audio recording will be triggered by hotkey events in the daemon
- **Phase 4 (Whisper Integration)**: Transcription will run in daemon background threads/processes
- **Phase 5 (Text Injection)**: ydotool commands will be invoked from the daemon after transcription
- **Phase 6 (UI/Indicators)**: System tray icon will communicate with daemon via signals or IPC
- **Phase 7 (Packaging)**: systemd service will replace subprocess launch, using same daemon code

The signal-based control and PID management provide a robust foundation for production deployment.

## Next Steps

With daemon lifecycle and CLI commands working, Phase 2 should:

1. Add evdev hotkey detection to the daemon main loop
2. Detect keyboard devices and filter for hotkey events
3. Log hotkey press/release events (validation before audio capture)
4. Verify hotkey detection works on both X11 and Wayland

## Self-Check: PASSED

Verifying all claimed artifacts exist:

```bash
# Files created
FOUND: /home/rob/Documents/Projects/LinuxWhisper/src/linuxwhisper/__main__.py
FOUND: /home/rob/Documents/Projects/LinuxWhisper/src/linuxwhisper/daemon/main.py
FOUND: /home/rob/Documents/Projects/LinuxWhisper/src/linuxwhisper/daemon/lifecycle.py
FOUND: /home/rob/Documents/Projects/LinuxWhisper/src/linuxwhisper/daemon/pid.py
FOUND: /home/rob/Documents/Projects/LinuxWhisper/src/linuxwhisper/logging/setup.py

# Commits exist
FOUND: 7bfd9aa
FOUND: 29cdb55
```
