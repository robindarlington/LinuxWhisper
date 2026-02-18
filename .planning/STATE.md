# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-14)

**Core value:** Hold a key, speak, text appears in the active window — fast, reliable, and works on any Linux display server.
**Current focus:** Phase 2 complete, ready for Phase 3

## Current Position

Phase: 2 of 8 (Core Dictation Pipeline) - COMPLETE
Plan: 4 of 4 in current phase
Status: Complete
Last activity: 2026-02-18 — Completed plan 02-04 (End-to-End Verification)

Progress: [██████░░░░] 75%

## Performance Metrics

**Velocity:**
- Total plans completed: 6
- Average duration: 5 minutes
- Total execution time: 0.7 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01    | 2     | 6 min  | 3 min    |
| 02    | 4     | 30 min | 7.5 min  |

**Recent Trend:**
- Last 5 plans: 02-01 (5m), 02-02 (11m), 02-03 (2m), 02-04 (12m)
- Trend: 02-04 was longer due to interactive debugging and system config fixes

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Daemon + CLI first, tray later — Reduces initial complexity, validates architecture in Phase 1-2
- evdev for hotkey detection — Works on both X11 and Wayland, validates in Phase 2
- Local Whisper only (no API) — Privacy and offline capability, validates in Phase 2
- Use stdlib tomllib (Python 3.11+) for reading TOML, tomli-w for writing — 01-01
- Create virtual environment (.venv) for development isolation — 01-01
- Implement deep merge for config to allow partial user overrides — 01-01
- Use subprocess.Popen with start_new_session for daemon backgrounding (Phase 1 only, systemd in Phase 7) — 01-02
- XDG runtime dir for PID file with fallback to ~/.local/run — 01-02
- Signal-based daemon control: SIGTERM/SIGINT for stop, SIGHUP for reload — 01-02
- Log to stdout for systemd journal capture — 01-02
- Use evdev device grabbing to prevent hotkey propagation to other applications — 02-01
- Support both KEY_F13 and F13 formats for hotkey configuration flexibility — 02-01
- 16kHz mono int16 WAV format for optimal Whisper compatibility — 02-01
- Queue-based non-blocking audio recording with callback pattern — 02-01
- INT8 quantization for CPU, int8_float16 for GPU — optimal speed for local transcription — 02-02
- Lazy model loading — daemon controls when expensive model load happens — 02-02
- VAD filtering with custom parameters — better transcription quality — 02-02
- Multi-method session detection — robust X11/Wayland identification — 02-02
- Factory pattern for injector creation — clean auto-selection based on session — 02-02
- Validate tool availability at init — fail fast with clear error messages — 02-02
- State machine with VALID_TRANSITIONS map prevents invalid state transitions — 02-03
- Hotkey detector runs in daemon thread while processing runs synchronously in callback — 02-03
- Error handling always returns to IDLE state for resilience — 02-03
- Permission check at daemon startup prevents cryptic evdev errors — 02-03
- Pre-load Whisper model on pipeline start for fast first dictation — 02-03
- Config reload requires daemon restart for hotkey/model changes (acceptable for Phase 2) — 02-03
- PAUSE key doesn't support hold-to-talk (instant press+release) — changed default to HOME — 02-04
- UInput passthrough via UInput.from_device re-injects non-hotkey events — 02-04
- udev rule for uinput may not apply on boot — manual chmod needed, defer to Phase 7/8 — 02-04

### Pending Todos

None yet.

### Blockers/Concerns

**From Research:**
- PipeWire vs PulseAudio detection fallback logic unclear (Phase 4)
- Keyboard layout detection method needs compositor-specific commands (Phase 6)

**From Phase 2 UAT:**
- /dev/uinput permissions not auto-applied by udev rule on boot — needs Phase 7/8 fix
- PAUSE key unsuitable for hold-to-talk — need configurable hotkey docs in Phase 8

## Session Continuity

Last session: 2026-02-18 (verification)
Stopped at: Completed 02-04 - End-to-End Verification. Phase 2 complete.
Resume file: None

---
*State initialized: 2026-02-15*
*Last updated: 2026-02-18*
