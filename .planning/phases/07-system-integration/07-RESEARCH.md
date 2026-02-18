# Phase 7: System Integration - Research

**Researched:** 2026-02-18
**Domain:** systemd user services, Wayland session integration, Python daemon lifecycle
**Confidence:** HIGH

## Summary

LinuxWhisper needs to run as a systemd user service that auto-starts with the graphical session and recovers from crashes. The daemon already has the right architecture for this: it runs in the foreground via `python -m linuxwhisper`, logs to stdout, handles SIGTERM/SIGINT/SIGHUP, and spawns an overlay subprocess that it manages. The key challenges are (1) getting the service file right with proper session dependencies, (2) ensuring the venv Python path works in a systemd context, (3) managing coexistence between CLI manual start and systemd-managed start, and (4) ensuring the overlay subprocess (and all children) are properly cleaned up.

The user's system is confirmed running Hyprland with UWSM (Universal Wayland Session Manager), which properly activates `graphical-session.target` and exports `WAYLAND_DISPLAY`, `DISPLAY`, and `XDG_CURRENT_DESKTOP` to the systemd user environment. This simplifies environment handling significantly.

**Primary recommendation:** Use `Type=simple` with `PartOf=graphical-session.target` and `After=graphical-session.target`. Point `ExecStart=` at the venv Python binary directly. Use `KillMode=control-group` (default) to ensure overlay subprocess cleanup. Modify the CLI so `linuxwhisper start/stop/status` delegate to `systemctl --user` when the service is enabled.

---

## Domain Analysis

### 1. Service Type: Type=simple (not Type=notify)

**Confidence: HIGH** (verified via freedesktop.org official docs)

`Type=simple` is the correct choice for LinuxWhisper:

- `run_daemon()` runs in the foreground, making the `ExecStart=` process the main service process. systemd tracks its PID via cgroups, no PID file needed.
- `Type=notify` would require adding `sd_notify("READY=1")` after model loading completes, which means adding a dependency on `python-systemd` or `sdnotify`. This is unnecessary complexity -- systemd considers `Type=simple` services started immediately after fork, which is fine for our use case (we don't need other services to wait for us).
- `Type=forking` (what `linuxwhisper start` does with `subprocess.Popen`) is the *old* way. systemd docs explicitly say "PID files should be avoided in modern projects" and to prefer `Type=simple` or `Type=notify`.

**The `run_daemon()` function is already the perfect systemd entry point.** It runs in the foreground, logs to stdout, and exits cleanly on SIGTERM.

### 2. Service File Installation Path

**Confidence: HIGH** (verified via ArchWiki and freedesktop.org docs)

There are two valid locations, serving different purposes:

| Path | Purpose | When to use |
|------|---------|-------------|
| `~/.config/systemd/user/linuxwhisper.service` | User-local service | pip/venv install, development |
| `/usr/lib/systemd/user/linuxwhisper.service` | Packaged service | PKGBUILD, system package |

For the current project (installed in a venv at a user-specific path), **install to `~/.config/systemd/user/`**. The `ExecStart=` path contains the user's home directory, so it must be per-user anyway.

For future PKGBUILD packaging, the service file would go to `/usr/lib/systemd/user/` with a generic `ExecStart=/usr/bin/linuxwhisper-daemon` path.

### 3. Session Dependencies and Ordering

**Confidence: HIGH** (verified via live system inspection and official docs)

The user's system uses UWSM with Hyprland. Live inspection confirms:

```
graphical-session.target       loaded active active
wayland-session@hyprland.desktop.target  loaded active active
```

Environment variables already in systemd user manager:
```
WAYLAND_DISPLAY=wayland-1
DISPLAY=:1
XDG_CURRENT_DESKTOP=Hyprland
```

**Service file dependency section:**
```ini
[Unit]
Description=LinuxWhisper voice dictation daemon
After=graphical-session.target
PartOf=graphical-session.target
Wants=ydotool.service

[Install]
WantedBy=graphical-session.target
```

Rationale:
- `After=graphical-session.target` -- don't start until the compositor is ready and env vars are exported.
- `PartOf=graphical-session.target` -- stop when the graphical session ends (logout/compositor crash). This is the standard pattern used by mako, waybar, and other Wayland user services. `PartOf=` propagates stop/restart from the target to the service, but does NOT create a forward start dependency (that's what `WantedBy=` in [Install] does).
- `Wants=ydotool.service` -- soft dependency (start ydotool if not already running, but don't fail if it can't start). LinuxWhisper can function without ydotool (it has fallback injection methods), so `Requires=` is too strong.
- `WantedBy=graphical-session.target` -- this is what `systemctl --user enable` creates a symlink for, ensuring LinuxWhisper starts when the graphical session starts.

**Why NOT `ConditionEnvironment=WAYLAND_DISPLAY`:** mako switched to this and it caused problems because it evaluates only once. If the service starts before WAYLAND_DISPLAY is set, it permanently fails. Since we already use `After=graphical-session.target`, the environment is guaranteed to be ready. Additionally, LinuxWhisper's overlay uses Hyprland-specific features but the core daemon (evdev + whisper) works without any display server, so the condition would be unnecessarily restrictive.

### 4. ExecStart Path and Environment

**Confidence: HIGH** (verified by inspecting actual venv binary)

The venv `linuxwhisper` script has this shebang:
```python
#!/home/rob/Documents/Projects/LinuxWhisper/.venv/bin/python3
```

This means calling the venv binary directly works without activating the venv -- the shebang resolves the correct Python interpreter with all installed packages.

**However, for systemd, we should use the module runner approach:**

```ini
[Service]
ExecStart=/home/rob/Documents/Projects/LinuxWhisper/.venv/bin/python -m linuxwhisper
```

This is better than calling the console_script because:
1. It's explicit about which Python interpreter is used
2. It matches the existing `__main__.py` entry point that calls `run_daemon()`
3. It avoids potential issues with setuptools-generated wrapper scripts

**Environment variables needed:**

```ini
Environment=PYTHONUNBUFFERED=1
```

This ensures Python output isn't buffered, so logs appear immediately in journald. No other environment variables are needed because:
- `WAYLAND_DISPLAY`, `DISPLAY`, `XDG_CURRENT_DESKTOP` are already in the systemd user environment (exported by UWSM/Hyprland)
- `PATH` already includes `/usr/bin` where `ydotool`, `wtype`, and other tools live
- The venv Python has all package dependencies installed

**ExecReload for SIGHUP:**

```ini
ExecReload=/bin/kill -HUP $MAINPID
```

This allows `systemctl --user reload linuxwhisper` to trigger config reload, matching the existing SIGHUP handler.

### 5. Crash Recovery Configuration

**Confidence: HIGH** (verified via freedesktop.org official docs)

```ini
[Unit]
StartLimitIntervalSec=300
StartLimitBurst=5

[Service]
Restart=on-failure
RestartSec=5
```

Rationale:
- `Restart=on-failure` -- restart on non-zero exit code or signal kill, but NOT on clean `systemctl stop` (which sends SIGTERM, and the daemon exits with code 0). `Restart=always` would restart even after `systemctl stop`, which is wrong.
- `RestartSec=5` -- 5 second delay prevents rapid restart loops (e.g., if config is broken). This is enough time for transient issues to clear but not so long that the user waits too long.
- `StartLimitIntervalSec=300` and `StartLimitBurst=5` -- allow up to 5 restarts in 5 minutes before giving up. This catches persistent failures (bad config, missing permissions) and prevents infinite restart loops.

**CRITICAL:** `StartLimitIntervalSec` and `StartLimitBurst` go in `[Unit]`, not `[Service]`. Placing them in `[Service]` silently ignores them. This is the #1 mistake in systemd service configuration.

**Verification:** `300 > 5 * 5` (interval > RestartSec * burst), which satisfies the requirement that the interval is large enough to contain all burst restarts.

### 6. Process Tree and Subprocess Cleanup

**Confidence: HIGH** (verified via freedesktop.org systemd.kill docs)

LinuxWhisper spawns an overlay subprocess (`python -m linuxwhisper.overlay`) using `subprocess.Popen`. systemd needs to clean this up on stop.

**`KillMode=control-group` (the default) is correct.** It sends SIGTERM to ALL processes in the service's cgroup, including the overlay subprocess. This means:

1. systemd sends SIGTERM to main daemon process AND overlay subprocess simultaneously
2. The daemon's signal handler sets `running = False`, pipeline stops, `overlay.hide()` is called
3. The overlay also receives SIGTERM directly from systemd (belt and suspenders)
4. If anything survives past `TimeoutStopSec`, systemd sends SIGKILL to the entire cgroup

**No changes needed to the existing code.** The daemon already handles SIGTERM gracefully and cleans up the overlay. systemd's cgroup kill is a safety net.

Do NOT use `KillMode=process` -- it would only kill the main daemon, potentially leaving the overlay orphaned. The official docs explicitly warn against this.

### 7. PID File: Keep for Manual Mode, Skip for systemd

**Confidence: HIGH**

The existing PID file management (`$XDG_RUNTIME_DIR/linuxwhisper.pid`) should be kept but its role changes:

- **Under systemd:** PID file is redundant. systemd tracks the main PID via cgroups. `systemctl --user status linuxwhisper` shows the PID. However, the daemon writes it anyway (harmless), and it provides backward compatibility.
- **Manual mode** (`python -m linuxwhisper` run directly): PID file is still needed for `linuxwhisper stop` to find and signal the process.

**Recommendation:** Keep PID file writing as-is. No code changes needed for PID management.

### 8. CLI Integration: Delegate to systemctl When Service Is Enabled

**Confidence: MEDIUM** (pattern is clear, but CLI change details need careful design)

The current `linuxwhisper start` forks a background process with `subprocess.Popen`. This conflicts with systemd management because:
- systemd doesn't know about the manually started process
- `systemctl --user start linuxwhisper` would try to start a second instance
- PID file becomes a source of confusion

**Recommended approach:**

```python
def is_systemd_managed():
    """Check if linuxwhisper.service is enabled for the current user."""
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-enabled", "linuxwhisper.service"],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() == "enabled"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
```

Then in CLI commands:
- `linuxwhisper start` --> if systemd-managed: `systemctl --user start linuxwhisper`; else: existing Popen behavior
- `linuxwhisper stop` --> if systemd-managed: `systemctl --user stop linuxwhisper`; else: existing SIGTERM behavior
- `linuxwhisper status` --> if systemd-managed: `systemctl --user status linuxwhisper`; else: existing PID check
- `linuxwhisper reload` --> if systemd-managed: `systemctl --user reload linuxwhisper`; else: existing SIGHUP behavior

This gives users the best of both worlds:
- If they've enabled the service, CLI commands are thin wrappers around systemctl
- If they haven't (development, testing), the old manual mode still works

### 9. Post-Install Activation

**Confidence: HIGH**

Service activation MUST NOT happen automatically during `pip install`. The Arch packaging guidelines and systemd best practices both say: packages should install service files but not enable them. The user decides when to enable.

**Installation flow:**

1. `pip install -e .` or package install copies `linuxwhisper.service` to `~/.config/systemd/user/`
2. CLI provides `linuxwhisper service install` command that:
   - Copies the service file (with correct venv path) to `~/.config/systemd/user/`
   - Runs `systemctl --user daemon-reload`
   - Prints instructions: "Run `systemctl --user enable --now linuxwhisper` to start"
3. User explicitly enables: `systemctl --user enable --now linuxwhisper`

For PKGBUILD: service file goes to `/usr/lib/systemd/user/` in the package, post_install message tells user to enable it.

### 10. Logging Under systemd

**Confidence: HIGH**

The existing logging setup is already perfect:

```python
logging.basicConfig(
    level=numeric_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
    force=True
)
```

stdout goes directly to journald when running under systemd. Users view logs with:
```bash
journalctl --user -u linuxwhisper -f       # follow live
journalctl --user -u linuxwhisper --since today  # today's logs
```

The `PYTHONUNBUFFERED=1` environment variable ensures logs appear immediately rather than being buffered.

**Optional improvement:** journald already adds timestamps, so the `%(asctime)s` in the format is redundant under systemd. But it's harmless and useful for manual mode. No change needed.

---

## Technical Findings

### Complete Service File

```ini
[Unit]
Description=LinuxWhisper voice dictation daemon
Documentation=https://github.com/user/linuxwhisper
After=graphical-session.target
PartOf=graphical-session.target
Wants=ydotool.service
StartLimitIntervalSec=300
StartLimitBurst=5

[Service]
Type=simple
ExecStart=%h/Documents/Projects/LinuxWhisper/.venv/bin/python -m linuxwhisper
ExecReload=/bin/kill -HUP $MAINPID
Restart=on-failure
RestartSec=5
Environment=PYTHONUNBUFFERED=1
KillMode=control-group
TimeoutStopSec=10

[Install]
WantedBy=graphical-session.target
```

**Note on `%h`:** systemd specifier for the user's home directory. This avoids hardcoding `/home/rob` and works for any user. However, the rest of the path (`Documents/Projects/LinuxWhisper/...`) is still project-specific. The `linuxwhisper service install` command should template this dynamically.

### Real-World Reference: mako.service

```ini
[Unit]
Description=Lightweight Wayland notification daemon
Documentation=man:mako(1)
PartOf=graphical-session.target
After=graphical-session.target

[Service]
Type=dbus
BusName=org.freedesktop.Notifications
ExecCondition=/bin/sh -c '[ -n "$WAYLAND_DISPLAY" ]'
ExecStart=/usr/bin/mako
ExecReload=/usr/bin/makoctl reload

[Install]
WantedBy=graphical-session.target
```

Our service file follows the same pattern (PartOf, After, WantedBy graphical-session.target) but uses Type=simple instead of Type=dbus, and doesn't need ExecCondition since the core daemon works without a display.

### Real-World Reference: ydotool.service (already on system)

```ini
[Unit]
Description=Starts ydotoold service

[Service]
Type=simple
Restart=always
ExecStart=/usr/bin/ydotoold
ExecReload=/usr/bin/kill -HUP $MAINPID
KillMode=process
TimeoutSec=180

[Install]
WantedBy=default.target
```

Note: ydotool uses `WantedBy=default.target` (not graphical-session), `Restart=always`, and `KillMode=process`. Our service correctly uses `WantedBy=graphical-session.target` since we need display variables.

---

## Architecture Patterns

### Service File Templating

The service file needs to be generated dynamically because the venv path varies per installation. Pattern:

```python
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

def generate_service_file() -> str:
    venv_python = sys.executable  # /path/to/.venv/bin/python
    return SERVICE_TEMPLATE.format(venv_python=venv_python)
```

### CLI Systemd Detection Pattern

```python
import shutil
import subprocess

def is_systemd_available() -> bool:
    """Check if systemctl is available (might not be on non-systemd systems)."""
    return shutil.which("systemctl") is not None

def is_service_enabled() -> bool:
    """Check if linuxwhisper.service is enabled."""
    if not is_systemd_available():
        return False
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-enabled", "linuxwhisper.service"],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() == "enabled"
    except (subprocess.TimeoutExpired, OSError):
        return False

def is_service_active() -> bool:
    """Check if linuxwhisper.service is currently running."""
    if not is_systemd_available():
        return False
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-active", "linuxwhisper.service"],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() == "active"
    except (subprocess.TimeoutExpired, OSError):
        return False
```

### Recommended Project Structure Addition

```
src/linuxwhisper/
  service/
    __init__.py          # Service install/uninstall/status helpers
    template.py          # Service file template and generation
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Process tracking | Custom PID monitoring | systemd cgroups (Type=simple) | systemd already tracks all processes in the service cgroup |
| Crash restart | Custom watchdog/respawn logic | `Restart=on-failure` + `RestartSec` | systemd restart is battle-tested, handles edge cases |
| Session lifecycle | Custom session detection | `PartOf=graphical-session.target` | UWSM/Hyprland already manage the target |
| Log rotation | Custom log file management | journald (stdout capture) | Already works, zero config |
| Service enable/disable | Custom autostart scripts | `systemctl --user enable/disable` | Standard mechanism, users already know it |

---

## Common Pitfalls

### Pitfall 1: StartLimitBurst in Wrong Section
**What goes wrong:** Service restarts indefinitely despite setting rate limits.
**Why it happens:** `StartLimitIntervalSec` and `StartLimitBurst` placed in `[Service]` instead of `[Unit]`.
**How to avoid:** Always put rate limit directives in `[Unit]` section.
**Warning signs:** Service keeps restarting despite `StartLimitBurst=5`.

### Pitfall 2: Python Output Buffering
**What goes wrong:** No logs appear in `journalctl --user -u linuxwhisper` until the service stops.
**Why it happens:** Python buffers stdout by default. journald only sees output when the buffer flushes (every 8KB or on process exit).
**How to avoid:** Set `Environment=PYTHONUNBUFFERED=1` in the service file.
**Warning signs:** Logs appear in bursts or only after service stop.

### Pitfall 3: Dual Instance Conflict
**What goes wrong:** User runs `linuxwhisper start` (manual) while systemd service is also running. Two daemon instances fight over the keyboard device.
**Why it happens:** No coordination between manual and systemd-managed modes.
**How to avoid:** CLI checks if service is active before starting manually. Or CLI delegates to systemctl when service is enabled.
**Warning signs:** evdev "device busy" errors, double transcription, PID file conflicts.

### Pitfall 4: Venv Path Hardcoded in Service File
**What goes wrong:** Service fails after venv is recreated, moved, or Python version changes.
**Why it happens:** The service file contains an absolute path to the venv Python.
**How to avoid:** `linuxwhisper service install` regenerates the service file from the current venv. Document that users need to re-run this after venv recreation.
**Warning signs:** `ExecStart= ... (code=exited, status=203/EXEC)` in journal.

### Pitfall 5: Using BindsTo Instead of PartOf
**What goes wrong:** Service fails to start or has complex dependency issues.
**Why it happens:** `BindsTo=` creates a bidirectional dependency (if graphical-session stops, service stops; if graphical-session starts, service starts). But `BindsTo=` also means if the service fails, it can affect the target. `PartOf=` is the correct one-way "stop when parent stops" relationship.
**How to avoid:** Use `PartOf=graphical-session.target` for user services. `BindsTo=` is for session targets themselves.

### Pitfall 6: Missing Overlay Environment Under systemd
**What goes wrong:** Overlay subprocess fails because it can't connect to Wayland.
**Why it happens:** The overlay subprocess inherits the daemon's environment, which under systemd inherits from the user manager. On systems without UWSM or proper environment export, WAYLAND_DISPLAY may be missing.
**How to avoid:** On this system, UWSM handles it. For broader compatibility, the overlay already falls back gracefully (it just doesn't show). No code change needed, but document the UWSM dependency for the overlay feature.
**Warning signs:** "Failed to spawn overlay subprocess" in logs, but dictation still works.

---

## Code Examples

### Service File Installation Command

```python
@cli.command("install")
def service_install():
    """Install and enable the systemd user service."""
    import sys
    from pathlib import Path

    service_dir = Path.home() / ".config" / "systemd" / "user"
    service_dir.mkdir(parents=True, exist_ok=True)
    service_path = service_dir / "linuxwhisper.service"

    # Generate service file with current venv path
    venv_python = sys.executable
    content = SERVICE_TEMPLATE.format(venv_python=venv_python)

    service_path.write_text(content)
    click.echo(f"Service file written to {service_path}")

    # Reload systemd
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    click.echo("systemd user daemon reloaded")

    click.echo("\nTo start now and enable on login:")
    click.echo("  systemctl --user enable --now linuxwhisper")
```

### Systemd-Aware Start Command

```python
@cli.command()
def start():
    """Start the LinuxWhisper daemon."""
    if is_service_enabled():
        # Delegate to systemd
        result = subprocess.run(
            ["systemctl", "--user", "start", "linuxwhisper.service"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            click.echo("LinuxWhisper started via systemd")
        else:
            click.echo(f"Failed to start: {result.stderr.strip()}")
            sys.exit(1)
    else:
        # Legacy manual mode (existing behavior)
        pid = read_pid()
        if pid is not None:
            click.echo(f"Daemon already running (PID {pid})")
            sys.exit(0)
        subprocess.Popen(
            [sys.executable, "-m", "linuxwhisper"],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        # ... existing verification logic
```

### Systemd-Aware Status Command

```python
@cli.command()
def status():
    """Check daemon status."""
    if is_service_enabled():
        result = subprocess.run(
            ["systemctl", "--user", "status", "linuxwhisper.service"],
            capture_output=True, text=True
        )
        click.echo(result.stdout)
        # Also show if it's active for simple yes/no
        if is_service_active():
            click.echo("LinuxWhisper daemon is running (systemd-managed)")
        else:
            click.echo("LinuxWhisper daemon is not running")
    else:
        pid = read_pid()
        if pid is not None:
            click.echo(f"LinuxWhisper daemon is running (PID {pid})")
        else:
            click.echo("LinuxWhisper daemon is not running")
```

---

## Risks and Mitigations

### Risk 1: Venv Path Fragility (MEDIUM)
**Risk:** Service file hardcodes the venv path. If the user recreates the venv, reinstalls Python, or moves the project, the service breaks.
**Mitigation:** Provide `linuxwhisper service install` to regenerate the file. Print a clear error message when ExecStart path doesn't exist. Document in README.
**Residual risk:** Users forget to re-run after venv changes.

### Risk 2: Non-UWSM Environments (LOW for this user, MEDIUM broadly)
**Risk:** On systems without UWSM or without proper `dbus-update-activation-environment`/`systemctl --user import-environment` in compositor config, `WAYLAND_DISPLAY` won't be in systemd's environment.
**Mitigation:** The overlay gracefully degrades (doesn't show, dictation still works). Add a diagnostic check: `linuxwhisper doctor` that verifies WAYLAND_DISPLAY is set.
**Residual risk:** Overlay won't work on non-UWSM setups without manual env configuration.

### Risk 3: ydotool Not Ready (LOW)
**Risk:** ydotool.service hasn't started yet when LinuxWhisper needs to inject text.
**Mitigation:** `Wants=ydotool.service` ensures systemd tries to start it. LinuxWhisper already has fallback injection methods (wtype, clipboard). The injection happens on-demand (after dictation), not at service start, so ydotool has time to come up.

### Risk 4: Conflict Between Manual and Systemd Modes (MEDIUM)
**Risk:** User has service enabled but also runs `linuxwhisper start` manually, creating dual instances.
**Mitigation:** CLI detects systemd management and delegates. PID file provides secondary lock.

---

## Recommendations

### Implementation Order

1. **Service file template + `linuxwhisper service install` command** -- Core deliverable. Generates and installs the .service file with the correct venv path.
2. **`linuxwhisper service uninstall` command** -- Disable, stop, remove service file.
3. **Modify CLI start/stop/status/reload to detect systemd** -- Check `is-enabled`, delegate when appropriate.
4. **Verify manual mode still works** -- All existing behavior preserved when service is not enabled.
5. **Add `linuxwhisper service status` subcommand** -- Show whether service is installed, enabled, active.

### What NOT to Do

- Do NOT add `python-systemd` or `sdnotify` as a dependency. `Type=simple` works fine without it.
- Do NOT auto-enable the service during `pip install`. Let the user decide.
- Do NOT remove PID file management. It's needed for manual mode and is harmless under systemd.
- Do NOT use `Restart=always`. It restarts even on clean `systemctl stop`, which is confusing.
- Do NOT use `KillMode=process`. It leaves the overlay orphaned.
- Do NOT use `ConditionEnvironment=WAYLAND_DISPLAY`. The core daemon doesn't need Wayland.

---

## Open Questions

1. **Should `linuxwhisper service` be a click group (subcommands: install, uninstall, status) or top-level commands?**
   - Recommendation: Click group (`linuxwhisper service install|uninstall|status`) keeps the CLI organized and signals these are setup operations, not runtime operations.

2. **Should we add a `linuxwhisper service logs` shortcut for `journalctl --user -u linuxwhisper -f`?**
   - Recommendation: Nice to have but low priority. Users who enable systemd probably know journalctl.

3. **What happens if the user has an old manual-mode daemon running when they enable the systemd service?**
   - Recommendation: `linuxwhisper service install` should check for a running manual instance and warn/offer to stop it first.

---

## Sources

### Primary (HIGH confidence)
- [freedesktop.org systemd.service(5)](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html) - Type=simple vs notify, PIDFile guidance, Restart options
- [freedesktop.org systemd.kill(5)](https://www.freedesktop.org/software/systemd/man/latest/systemd.kill.html) - KillMode options, control-group behavior
- [freedesktop.org systemd.special(7)](https://man7.org/linux/man-pages/man7/systemd.special.7.html) - graphical-session.target documentation
- [ArchWiki systemd/User](https://wiki.archlinux.org/title/Systemd/User) - User service paths, environment, lingering
- [mako.service (official)](https://github.com/emersion/mako/blob/master/contrib/systemd/mako.service) - Real-world Wayland user service reference
- Live system inspection of Hyprland UWSM environment and targets

### Secondary (MEDIUM confidence)
- [Hyprland Wiki - Systemd startup](https://wiki.hypr.land/Useful-Utilities/Systemd-start/) - UWSM integration details
- [systemd/systemd#23194](https://github.com/systemd/systemd/issues/23194) - PartOf vs BindsTo clarification
- [Michael Stapelberg - systemd indefinite restarts](https://michael.stapelberg.ch/posts/2024-01-17-systemd-indefinite-service-restarts/) - StartLimit configuration pitfalls
- [Red Hat - Self-healing services with systemd](https://www.redhat.com/en/blog/systemd-automate-recovery) - Restart best practices

### Tertiary (LOW confidence)
- Various Arch Forum threads on graphical-session.target timing issues

---

## Metadata

**Confidence breakdown:**
- Service file design: HIGH - verified against official docs and real-world examples (mako, ydotool)
- Session dependencies: HIGH - verified on live system with UWSM/Hyprland
- Crash recovery: HIGH - standard systemd patterns, well-documented
- CLI integration: MEDIUM - the pattern is clear but implementation details need careful testing
- Broader compatibility: MEDIUM - verified for UWSM/Hyprland, not tested on other Wayland compositors

**Research date:** 2026-02-18
**Valid until:** 2026-04-18 (systemd and Hyprland are stable; patterns unlikely to change)
