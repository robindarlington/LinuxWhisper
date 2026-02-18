---
phase: 03-enhanced-input-modes
plan: 02
subsystem: daemon
tags: [config, defaults, reload, sighup, lifecycle, validation, compositor]

# Dependency graph
requires:
  - phase: 03-enhanced-input-modes
    plan: 01
    provides: validate_config_input, check_compositor_conflicts, update_config, restart_hotkey_detector
provides:
  - DEFAULT_CONFIG with HOME hotkey, toggle_timeout=120, mode comments
  - reload_config_safe() with state-aware deferral, validation, change detection
  - set_pipeline_ref() for pipeline lifecycle binding
  - Daemon startup: fail-fast validation + compositor conflict warnings
  - SIGHUP handler using reload_config_safe (defers during recording)
affects: [04-system-tray, 07-system-integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "State-aware reload: check pipeline.state != IDLE before applying config"
    - "Fail-fast validation at daemon startup with sys.exit(1) on invalid config"
    - "Module-level _pipeline_ref set via set_pipeline_ref() after pipeline.start()"
    - "Change detection: compare old/new config keys before updating pipeline"

key-files:
  created: []
  modified:
    - src/linuxwhisper/config/defaults.py
    - src/linuxwhisper/daemon/lifecycle.py
    - src/linuxwhisper/daemon/main.py

key-decisions:
  - "DEFAULT_CONFIG hotkey changed from F13 to HOME — more universally available key"
  - "toggle_timeout=120 added to DEFAULT_CONFIG — feeds toggle mode pipeline"
  - "reload_config_safe defers (not fails) when pipeline busy — user retries with SIGHUP"
  - "Invalid new config during reload is rejected silently (old config preserved)"
  - "set_pipeline_ref called after pipeline.start() — ensures pipeline is ready before wiring"
  - "Compositor conflict check at daemon startup is warning-only — evdev grab takes priority"

requirements-completed: [DICT-02, INPUT-02, INPUT-03]

# Metrics
duration: 2min
completed: 2026-02-18
---

# Phase 3 Plan 02: Config Defaults, Validation Wiring, and State-Aware Reload Summary

**HOME hotkey default, toggle_timeout=120 in defaults, fail-fast config validation at daemon startup, compositor conflict warnings, and SIGHUP reload that defers during recording via reload_config_safe()**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-18T10:17:05Z
- **Completed:** 2026-02-18T10:19:19Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Updated DEFAULT_CONFIG: hotkey changed from F13 to HOME, toggle_timeout=120 added with inline docs explaining behavior
- Added reload_config_safe() to lifecycle: defers if pipeline not idle, validates new config before applying, detects hotkey/mode/timeout changes, checks compositor conflicts on hotkey change, restarts hotkey detector when hotkey changes
- Added set_pipeline_ref() to lifecycle: daemon registers pipeline after start() so reload can check state
- Daemon startup now validates config (fail-fast, sys.exit(1) on bad hotkey/mode), detects compositor conflicts (warnings only), and logs startup info with mode, hotkey, and toggle_timeout (for toggle mode)
- SIGHUP handler updated from reload_config() to reload_config_safe() — no more "restart for hotkey changes" message; changes apply live

## Task Commits

Each task was committed atomically:

1. **Task 1: Update config defaults and implement state-aware config reload** - `58bff16` (feat)
2. **Task 2: Wire validation, conflict detection, and safe reload into daemon** - `cdccadd` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `src/linuxwhisper/config/defaults.py` - hotkey changed to HOME, toggle_timeout=120 added with comments
- `src/linuxwhisper/daemon/lifecycle.py` - Added _pipeline_ref, set_pipeline_ref(), reload_config_safe(); kept reload_config() with deprecation note
- `src/linuxwhisper/daemon/main.py` - Added validate_config_input (fail-fast), check_compositor_conflicts (warnings), set_pipeline_ref (after start), reload_config_safe in SIGHUP handler, enriched startup log message

## Decisions Made

- DEFAULT_CONFIG hotkey changed F13 -> HOME (more common key, avoids user confusion per Phase 2 UAT)
- toggle_timeout=120 in defaults so toggle mode works out-of-box without user setting it
- reload_config_safe defers (not fails) when pipeline is recording — user can retry with next SIGHUP
- Invalid new config during reload: old config preserved, errors logged, None returned — no partial apply
- Compositor conflict check at daemon startup is warning-only — evdev grab takes priority anyway (per 03-01 decision)
- set_pipeline_ref called after pipeline.start() ensures detector is running before reload can trigger restart

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. All verification checks passed first run. Compositor conflict detection confirmed working — HOME key has 2 Hyprland conflicts detected in test environment (same as 03-01 UAT).

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Phase 3 complete: toggle mode (03-01) + config defaults/reload wiring (03-02) both done
- Daemon now validates, warns, and reloads config intelligently — ready for Phase 4 (System Tray)
- All Phase 3 requirements (DICT-02, INPUT-02, INPUT-03) completed across plans 03-01 and 03-02

## Self-Check: PASSED

All modified files verified present. Both task commits (58bff16, cdccadd) verified in git history.
