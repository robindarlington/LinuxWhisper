---
phase: 03-enhanced-input-modes
plan: 01
subsystem: input
tags: [evdev, toggle-mode, hotkey, compositor, hyprland, sway, gnome, kde, x11]

# Dependency graph
requires:
  - phase: 02-core-dictation-pipeline
    provides: HotkeyDetector, DictationPipeline, PipelineState state machine, AudioRecorder
provides:
  - InputMode enum (HOLD/TOGGLE) with DEFAULT_TOGGLE_TIMEOUT=120s
  - Friendly hotkey aliases (scroll_lock, pause, home, insert, delete, etc.) via FRIENDLY_ALIASES
  - validate_hotkey with helpful error messages listing available keys
  - check_compositor_conflicts for Hyprland, Sway, GNOME, KDE, and X11
  - validate_config_input validates hotkey + mode + toggle_timeout fields
  - DictationPipeline toggle mode: press-to-start, press-to-stop with timeout and Escape cancel
  - PipelineState.CANCELLING state for escape cancel flow
  - HotkeyDetector.start on_escape callback (intercepted only in toggle mode)
  - _process_recording extracted as shared method for hold-release/toggle-stop/timeout paths
  - update_config and restart_hotkey_detector methods for Plan 02 config reload
affects: [03-02-config-reload, 04-system-tray, 07-system-integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "InputMode enum drives dispatch behavior in DictationPipeline hotkey handlers"
    - "threading.Timer for toggle timeout with cancel on stop/complete"
    - "FRIENDLY_ALIASES dict + resolve_hotkey_name for case-insensitive key resolution"
    - "Compositor conflict detection via subprocess calls, all wrapped in try/except"
    - "CANCELLING state for explicit cancel-without-transcribe flow"

key-files:
  created:
    - src/linuxwhisper/input/__init__.py
    - src/linuxwhisper/input/modes.py
    - src/linuxwhisper/config/validation.py
  modified:
    - src/linuxwhisper/pipeline/states.py
    - src/linuxwhisper/hotkey/detector.py
    - src/linuxwhisper/pipeline/coordinator.py

key-decisions:
  - "Toggle timeout transcribes captured audio (does not discard) — text appearing is the cue that timeout fired"
  - "Escape cancel discards audio without transcribing — only active in toggle mode"
  - "Compositor conflict check is warning-only at startup, never blocks daemon start"
  - "on_escape callback passed to HotkeyDetector only in toggle mode — Escape passes through in hold mode"
  - "validate_config_input called at DictationPipeline.__init__ — invalid config raises ValueError before any component creation"

patterns-established:
  - "Friendly alias resolution: lowercase lookup in FRIENDLY_ALIASES, then uppercase + KEY_ prefix normalization"
  - "All subprocess calls in check_compositor_conflicts wrapped in try/except — never raises"
  - "InputMode.TOGGLE dispatch: IDLE->press starts recording+timer, RECORDING->press stops+processes, PROCESSING/INJECTING->press ignored"

requirements-completed: [DICT-02, INPUT-02, INPUT-03]

# Metrics
duration: 3min
completed: 2026-02-18
---

# Phase 3 Plan 01: Toggle Mode, Hotkey Aliases, Compositor Conflict Detection Summary

**Toggle mode with press-to-start/press-to-stop, 120s timeout that transcribes, Escape-to-cancel, friendly hotkey aliases (scroll_lock/pause/home), and compositor conflict detection for Hyprland/Sway/GNOME/KDE/X11**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-18T00:30:35Z
- **Completed:** 2026-02-18T00:33:59Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- InputMode enum (HOLD/TOGGLE) with configurable DEFAULT_TOGGLE_TIMEOUT (120s) and full toggle dispatch logic in DictationPipeline
- Friendly hotkey alias resolution: "scroll_lock", "pause", "home", "insert", etc. map to correct evdev KEY_ constants
- Compositor conflict detection covering all major Linux environments without crashing
- PipelineState.CANCELLING added for Escape-to-cancel flow; _process_recording extracted as shared method
- HotkeyDetector extended with optional on_escape callback (intercepted only in toggle mode)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create InputMode enum, friendly hotkey aliases, and compositor conflict detection** - `3711c44` (feat)
2. **Task 2: Add toggle mode dispatch, timeout, escape cancel, and hotkey detector escape support** - `dc41950` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `src/linuxwhisper/input/__init__.py` - New module exporting InputMode, get_mode_from_config
- `src/linuxwhisper/input/modes.py` - InputMode enum, get_mode_from_config, DEFAULT_TOGGLE_TIMEOUT
- `src/linuxwhisper/config/validation.py` - FRIENDLY_ALIASES, resolve_hotkey_name, validate_hotkey, check_compositor_conflicts, validate_config_input
- `src/linuxwhisper/pipeline/states.py` - Added CANCELLING state with RECORDING->CANCELLING->IDLE transitions
- `src/linuxwhisper/hotkey/detector.py` - Added escape_keycode param to __init__, on_escape param to start()
- `src/linuxwhisper/pipeline/coordinator.py` - Full toggle mode dispatch, _process_recording, _cancel_toggle_recording, _start_timeout/_cancel_timeout/_on_timeout, mode property, update_config, restart_hotkey_detector

## Decisions Made
- Toggle timeout transcribes captured audio (does not discard) per 03-CONTEXT.md decision — text appearing is the user's feedback
- Escape cancel is only wired in toggle mode; in hold mode Escape passes through to system normally
- compositor conflict detection is warning-only — daemon starts regardless since evdev grab takes priority anyway
- validate_config_input raised as ValueError at init so daemon refuses to start with clear message on bad config

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. All verification checks passed first run. The compositor conflict check correctly detected 2 Hyprland bindings for the HOME key (the test hotkey), confirming the detection works in the test environment.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Toggle mode fully implemented and verified. Plan 02 (config reload via SIGHUP) can use update_config and restart_hotkey_detector methods already added.
- All three input-mode requirements (DICT-02, INPUT-02, INPUT-03) completed.
- Compositor conflict detection provides logging foundation; future phases can surface these warnings via tray/CLI.

---
*Phase: 03-enhanced-input-modes*
*Completed: 2026-02-18*
