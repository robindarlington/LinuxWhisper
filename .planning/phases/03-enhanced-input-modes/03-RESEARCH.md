# Phase 3: Enhanced Input Modes - Research

**Researched:** 2026-02-15
**Domain:** Input mode state management, hotkey configuration, evdev event handling
**Confidence:** HIGH

## Summary

Phase 3 extends Phase 2's hold-to-talk implementation to support toggle mode (press-to-start, press-to-stop) and user-configurable hotkeys. The core technical challenge is state management for toggle mode while avoiding race conditions, proper evdev key press/release event detection, and validating that user-configured hotkeys don't conflict with compositor bindings.

Python-evdev provides robust key press (value=1) and key release (value=0) event detection needed for toggle mode. The existing daemon SIGHUP signal handler already supports configuration reload, and TOML-based configuration is established in Phase 1. The main implementation work involves adding toggle state tracking to the pipeline coordinator, extending configuration validation, and implementing compositor binding conflict detection.

**Primary recommendation:** Use explicit state machine with IDLE/RECORDING/PROCESSING states for toggle mode, validate hotkey configuration at daemon startup with user warnings (not blocking), leverage existing SIGHUP reload infrastructure, and extend Phase 2's evdev implementation to track key press/release transitions.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| python-evdev | latest | Hotkey detection with key press/release events | Direct kernel event access, works on X11 and Wayland, already validated in Phase 2 |
| tomllib | stdlib (3.11+) | TOML configuration parsing | Built-in standard library, zero dependencies |
| tomli-w | latest | TOML writing for config generation | Counterpart to tomllib for config file creation |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pydantic | 2.x | Configuration validation with type safety | Optional enhancement for strict config validation |
| python-statemachine | 2.5+ | Formal state machine implementation | If pipeline coordinator needs complex state transitions |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Built-in enum states | python-statemachine library | Library adds formalism but increases complexity for simple IDLE/RECORDING/PROCESSING states |
| Manual TOML validation | pydantic settings | Pydantic adds dependency but provides better error messages and type safety |
| Hotkey conflict detection | Skip validation | Detection prevents user confusion but adds startup complexity |

**Installation:**
```bash
# Core dependencies (already in project)
pip install evdev tomli-w

# Optional validation enhancement
pip install pydantic>=2.0
```

## Architecture Patterns

### Recommended Project Structure
```
src/linuxwhisper/
├── config/
│   ├── validation.py    # Hotkey config validation, compositor conflict detection
│   └── defaults.py      # Add "mode" field (existing)
├── input/
│   ├── modes.py         # InputMode enum, mode-specific handlers
│   └── detector.py      # Extend Phase 2 evdev detector for press/release
└── pipeline/
    └── coordinator.py   # State machine with toggle support
```

### Pattern 1: Toggle Mode State Machine
**What:** Explicit state tracking with state-dependent event handling
**When to use:** Toggle mode requires tracking whether currently recording or idle

**Example:**
```python
# Source: Python state machine pattern + evdev event handling
from enum import Enum, auto

class PipelineState(Enum):
    IDLE = auto()
    RECORDING = auto()
    PROCESSING = auto()

class ToggleModeHandler:
    def __init__(self):
        self.state = PipelineState.IDLE

    def handle_keypress(self, event):
        """Handle hotkey press in toggle mode."""
        if event.value == 1:  # Key down
            if self.state == PipelineState.IDLE:
                self.state = PipelineState.RECORDING
                self.start_recording()
            elif self.state == PipelineState.RECORDING:
                self.state = PipelineState.PROCESSING
                self.stop_recording()
        # Ignore key up (value=0) in toggle mode
```

### Pattern 2: evdev Key Press/Release Detection
**What:** Filter evdev events by value field to distinguish press from release
**When to use:** Required for toggle mode, optional for hold mode optimization

**Example:**
```python
# Source: https://python-evdev.readthedocs.io/en/latest/tutorial.html
from evdev import InputDevice, categorize, ecodes

async def read_hotkey_events(device_path: str, hotkey_code: int):
    """Read and filter hotkey events."""
    device = InputDevice(device_path)

    async for event in device.async_read_loop():
        if event.type == ecodes.EV_KEY and event.code == hotkey_code:
            if event.value == 1:
                # Key pressed
                yield "press"
            elif event.value == 0:
                # Key released
                yield "release"
            # event.value == 2 is key hold (auto-repeat), ignore
```

### Pattern 3: Configuration Reload with State Preservation
**What:** Reload config (hotkey, mode) without losing current pipeline state
**When to use:** SIGHUP signal received during active recording

**Example:**
```python
# Source: Existing daemon/lifecycle.py + hot reload pattern
def reload_config_safe(coordinator):
    """Reload config while preserving recording state."""
    new_config = load_config()

    # Don't reload hotkey/mode if currently recording
    if coordinator.state == PipelineState.RECORDING:
        logger.warning("Config reload deferred: recording in progress")
        return False

    # Safe to reload
    coordinator.update_config(new_config)
    return True
```

### Pattern 4: Hotkey Configuration Validation
**What:** Validate hotkey string (e.g., "F13") to evdev key code at startup
**When to use:** Daemon startup, configuration reload

**Example:**
```python
# Source: evdev.ecodes key mapping
from evdev import ecodes

def validate_hotkey(hotkey_str: str) -> tuple[bool, int | None, str]:
    """Validate hotkey configuration and return evdev code.

    Returns:
        (valid, key_code, error_message)
    """
    key_name = f"KEY_{hotkey_str.upper()}"

    if not hasattr(ecodes, key_name):
        return False, None, f"Unknown key: {hotkey_str}"

    key_code = getattr(ecodes, key_name)
    return True, key_code, ""

# Usage
valid, code, error = validate_hotkey(config["hotkey"])
if not valid:
    logger.error(f"Invalid hotkey configuration: {error}")
    sys.exit(1)
```

### Anti-Patterns to Avoid
- **Polling instead of async events:** Don't use sleep loops to check state, use async/await with evdev's async_read_loop
- **Race conditions on state transitions:** Don't allow simultaneous state changes from hotkey and timeout events
- **Blocking config reload:** Don't allow SIGHUP to interrupt active recording, defer until IDLE
- **Silent config errors:** Don't start daemon with invalid hotkey config, fail fast at startup

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| TOML parsing | Custom TOML parser | tomllib (stdlib) | TOML spec has edge cases (datetime, multiline strings), stdlib handles them |
| State machine | String-based states ("idle") | Enum (stdlib) or python-statemachine | Type safety, exhaustive case checking, formal transitions |
| Debouncing | Manual timestamp tracking | evdev event filtering | Kernel already debounces, filtering event.value==2 (hold) is sufficient |
| Input device enumeration | Custom /dev/input scanning | evdev.list_devices() | Handles permissions, device probing, symlink resolution |

**Key insight:** Input handling has many subtle edge cases (key auto-repeat, device hotplug, race conditions). Use battle-tested libraries and follow established patterns rather than custom implementations.

## Common Pitfalls

### Pitfall 1: Ignoring Key Auto-Repeat Events
**What goes wrong:** Hold-to-talk mode triggers multiple recordings when user holds key longer than auto-repeat threshold
**Why it happens:** Linux kernel sends event.value=2 (hold) repeatedly when key is held, evdev exposes these
**How to avoid:** Filter out event.value==2 in hold mode, only process value==1 (press) and value==0 (release)
**Warning signs:** Recording starts multiple times during single hold action, logs show duplicate press events

### Pitfall 2: Configuration Reload During Recording
**What goes wrong:** Hotkey changes mid-recording, release event goes to wrong handler, recording never stops
**Why it happens:** SIGHUP can arrive any time, including during active recording
**How to avoid:** Defer configuration reload if state != IDLE, apply on next transition to IDLE
**Warning signs:** Stuck in RECORDING state after config reload, audio file keeps growing

### Pitfall 3: evdev Device Selection Confusion
**What goes wrong:** Multiple /dev/input/event* devices for same keyboard, grabbing wrong one misses events
**Why it happens:** Keyboards often expose multiple event devices (kbd, mouse, consumer control)
**How to avoid:** Use /dev/input/by-id/ paths ending in "event-kbd" instead of /dev/input/event*, validate capability with device.capabilities()
**Warning signs:** Hotkey detection works for some keys but not others, evtest shows events on different device

### Pitfall 4: Compositor Binding Conflicts with Validation Approach
**What goes wrong:** User configures F13 but compositor already uses it, hotkey never reaches evdev layer
**Why it happens:** Wayland compositors (Hyprland, Sway) can grab keys globally before evdev sees them
**How to avoid:** Warn user at startup if compositor bindings conflict (query via hyprctl/swaymsg), recommend high function keys (F13-F24) by default
**Warning signs:** Config valid but hotkey doesn't trigger, evtest shows no events when compositor is running

### Pitfall 5: State Machine Race Conditions
**What goes wrong:** User presses toggle hotkey twice rapidly, state transitions IDLE→RECORDING→PROCESSING→RECORDING (unexpected)
**Why it happens:** No mutex/lock on state transitions, second press handled before first completes
**How to avoid:** Use atomic state checks (compare-and-swap), ignore events in PROCESSING state
**Warning signs:** Debug logs show rapid state transitions, audio files with near-zero duration

### Pitfall 6: F13-F24 Key Support on X11
**What goes wrong:** F13+ keys don't register on X11 even though evdev sees them
**Why it happens:** X11 may need xmodmap configuration to map scancodes to F13-F24 keysyms
**How to avoid:** Document xmodmap setup in README, detect X11 at startup and warn if F13+ configured without xmodmap
**Warning signs:** Works on Wayland, fails on X11; xev doesn't show F13 events but evtest does

## Code Examples

Verified patterns from official sources and existing codebase:

### Mode-Dependent Event Handling
```python
# Source: State pattern + existing config structure
from enum import Enum, auto
from linuxwhisper.config import load_config

class InputMode(Enum):
    HOLD = "hold"
    TOGGLE = "toggle"

class HotkeyHandler:
    def __init__(self, config: dict):
        self.mode = InputMode(config.get("mode", "hold"))
        self.coordinator = PipelineCoordinator()

    async def handle_event(self, event):
        """Route event to mode-specific handler."""
        if self.mode == InputMode.HOLD:
            await self._handle_hold_mode(event)
        elif self.mode == InputMode.TOGGLE:
            await self._handle_toggle_mode(event)

    async def _handle_hold_mode(self, event):
        """Hold: press starts, release stops."""
        if event.value == 1:  # Press
            await self.coordinator.start_recording()
        elif event.value == 0:  # Release
            await self.coordinator.stop_recording()

    async def _handle_toggle_mode(self, event):
        """Toggle: press toggles state."""
        if event.value == 1:  # Only on press
            if self.coordinator.state == PipelineState.IDLE:
                await self.coordinator.start_recording()
            elif self.coordinator.state == PipelineState.RECORDING:
                await self.coordinator.stop_recording()
```

### Configuration Extension for Input Modes
```python
# Source: Existing config/defaults.py
DEFAULT_CONFIG = {
    "hotkey": "F13",
    "mode": "hold",  # "hold" | "toggle"
    "model": "base.en",
    "audio": {
        "sample_rate": 16000,
        "channels": 1,
    },
    "logging": {
        "level": "INFO",
    },
}
```

### Hotkey String to evdev Code Conversion
```python
# Source: https://python-evdev.readthedocs.io/en/latest/apidoc.html
from evdev import ecodes

def hotkey_to_code(hotkey: str) -> int:
    """Convert hotkey string (e.g., 'F13') to evdev key code.

    Raises:
        ValueError: If hotkey is not a valid key name
    """
    key_name = f"KEY_{hotkey.upper()}"

    if not hasattr(ecodes, key_name):
        available = [k for k in dir(ecodes) if k.startswith("KEY_F")]
        raise ValueError(
            f"Unknown hotkey: {hotkey}. "
            f"Available function keys: {', '.join(available)}"
        )

    return getattr(ecodes, key_name)
```

### Compositor Binding Detection (Hyprland)
```python
# Source: https://wiki.hypr.land/Configuring/Binds/
import subprocess
import json
import logging

logger = logging.getLogger(__name__)

def check_hyprland_conflicts(hotkey: str) -> list[str]:
    """Check if hotkey conflicts with Hyprland bindings.

    Returns:
        List of conflicting binding descriptions, empty if no conflicts
    """
    try:
        result = subprocess.run(
            ["hyprctl", "binds", "-j"],
            capture_output=True,
            text=True,
            timeout=2.0
        )
        if result.returncode != 0:
            return []  # Hyprland not running or hyprctl not available

        bindings = json.loads(result.stdout)
        conflicts = []

        for bind in bindings:
            if hotkey.upper() in bind.get("key", "").upper():
                conflicts.append(bind.get("dispatcher", "unknown"))

        return conflicts
    except Exception as e:
        logger.debug(f"Could not check Hyprland bindings: {e}")
        return []

# Usage at daemon startup
conflicts = check_hyprland_conflicts(config["hotkey"])
if conflicts:
    logger.warning(
        f"Hotkey {config['hotkey']} conflicts with compositor bindings: {conflicts}. "
        f"Consider using F13-F24 instead."
    )
```

### Safe Configuration Reload
```python
# Source: Existing daemon/lifecycle.py pattern + state awareness
from linuxwhisper.config import load_config
from linuxwhisper.logging import setup_logging

def reload_config_with_state(coordinator) -> dict | None:
    """Reload configuration if safe to do so.

    Returns:
        New config if reloaded, None if deferred
    """
    # Check if safe to reload
    if coordinator.state != PipelineState.IDLE:
        logger.warning(
            f"Configuration reload deferred: pipeline state is {coordinator.state.name}"
        )
        return None

    logger.info("Reloading configuration")
    new_config = load_config()

    # Validate new hotkey before applying
    try:
        new_code = hotkey_to_code(new_config["hotkey"])
    except ValueError as e:
        logger.error(f"Config reload failed: {e}")
        return None

    # Update logging if changed
    old_level = coordinator.config.get("logging", {}).get("level", "INFO")
    new_level = new_config.get("logging", {}).get("level", "INFO")
    if old_level != new_level:
        setup_logging(new_config)

    # Apply new config
    coordinator.update_config(new_config)
    logger.info("Configuration reloaded successfully")

    return new_config
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| tomli (external) | tomllib (stdlib) | Python 3.11 (Oct 2022) | Zero dependencies for TOML parsing, tomli only for 3.7-3.10 compat |
| Manual signal handling | signal.signal() with handlers | Always standard | SIGHUP pattern established in Phase 1 |
| String-based states | Enum-based states | Python 3.4+ (2014) | Type safety, IDE autocomplete, exhaustive checking |
| Synchronous evdev | async/await with async_read_loop() | Python 3.5+ (2015) | Non-blocking event processing, better concurrency |

**Deprecated/outdated:**
- python2-evdev: Python 2 is EOL, use python3-evdev (package name is just "evdev")
- ConfigParser for structured config: TOML is modern standard for Python config files (PEP 518)
- Threading-based concurrency: asyncio is preferred for I/O-bound tasks like event reading

## Open Questions

1. **Should hotkey conflict detection block daemon startup or just warn?**
   - What we know: Detection is possible via hyprctl/swaymsg for Hyprland/Sway
   - What's unclear: Whether other compositors (KDE, GNOME) provide similar query interfaces
   - Recommendation: Start with warning-only approach, user can fix config and reload via SIGHUP. Blocking startup prevents daemon from running at all, which breaks systemd auto-restart

2. **How to handle toggle mode timeout (user forgets to stop recording)?**
   - What we know: Phase 4 adds Voice Activity Detection for auto-stop
   - What's unclear: Should Phase 3 implement simple timeout, or defer to Phase 4?
   - Recommendation: Defer to Phase 4. Toggle without timeout is valid use case (user wants manual control). Phase 4's VAD is proper solution

3. **Should configuration validation use pydantic or manual checks?**
   - What we know: Current config uses dict with manual validation, pydantic adds type safety
   - What's unclear: Whether added dependency worth benefits for small config surface
   - Recommendation: Start with manual validation (consistent with Phase 1), consider pydantic in future refactoring if config grows complex

4. **Does exclusive grab (dev.grab()) interfere with compositor hotkeys?**
   - What we know: Grab makes evdev sole recipient of events from that device
   - What's unclear: Whether we need grab at all, or if compositor pre-empts evdev anyway
   - Recommendation: Test without grab first. Only use grab() if events leak to other apps during recording (unlikely with evdev-level capture)

## Sources

### Primary (HIGH confidence)
- [Python-evdev Tutorial](https://python-evdev.readthedocs.io/en/latest/tutorial.html) - Event value meanings, read_loop patterns
- [Python-evdev API Reference](https://python-evdev.readthedocs.io/en/latest/apidoc.html) - InputDevice methods, categorize function
- [Python tomllib stdlib](https://docs.python.org/3/library/tomllib.html) - TOML parsing (verified via Real Python article)
- [Real Python: Python and TOML](https://realpython.com/python-toml/) - TOML best practices, validation patterns
- Existing codebase:
  - `src/linuxwhisper/config/loader.py` - TOML loading, merge pattern
  - `src/linuxwhisper/config/defaults.py` - Current config schema
  - `src/linuxwhisper/daemon/lifecycle.py` - SIGHUP reload implementation
  - `src/linuxwhisper/daemon/main.py` - Signal handler pattern

### Secondary (MEDIUM confidence)
- [OneUpTime: Config Hot Reload in Python (2026-01-22)](https://oneuptime.com/blog/post/2026-01-22-config-hot-reload-python/view) - File watching patterns, thread safety
- [Hyprland Binds Wiki](https://wiki.hypr.land/Configuring/Binds/) - hyprctl binds command for conflict detection
- [GitHub: python-evdev issue #70](https://github.com/gvalkov/python-evdev/issues/70) - Long press detection patterns
- [systemd.service manpage](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html) - SIGHUP reload behavior with notify-reload

### Tertiary (LOW confidence - needs validation)
- [Arch Linux Forums: /dev/input permissions](https://bbs.archlinux.org/viewtopic.php?id=273094) - input group membership, udev rules
- [Linux xmodmap F13-F15 keys](http://xahlee.info/linux/linux_xmodmap_f13_f14_f15.html) - X11 function key mapping (user blog, not official docs)
- [F13-F24 global shortcuts on Wayland](https://bbs.archlinux.org/viewtopic.php?id=303293) - Arch forums discussion, anecdotal evidence

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - evdev and tomllib are established, validated in Phase 1/2
- Architecture: HIGH - State machine pattern is well-documented, existing codebase provides SIGHUP foundation
- Pitfalls: MEDIUM - evdev pitfalls verified via official docs, compositor conflicts based on community knowledge
- Code examples: HIGH - Based on official python-evdev docs and existing verified codebase

**Research date:** 2026-02-15
**Valid until:** ~30 days (stable domain, evdev/TOML patterns don't change rapidly)
**Dependencies:** Assumes Phase 2 completes evdev hotkey detection and pipeline coordinator foundation
