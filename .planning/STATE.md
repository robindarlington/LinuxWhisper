# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-14)

**Core value:** Hold a key, speak, text appears in the active window — fast, reliable, and works on any Linux display server.
**Current focus:** Phase 2 - Core Dictation Pipeline

## Current Position

Phase: 2 of 8 (Core Dictation Pipeline)
Plan: 2 of 4 in current phase
Status: In progress
Last activity: 2026-02-15 — Completed plan 02-01 (Hotkey Detection and Audio Recording)

Progress: [███░░░░░░░] 37.5%

## Performance Metrics

**Velocity:**
- Total plans completed: 3
- Average duration: 4 minutes
- Total execution time: 0.2 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01    | 2     | 6 min | 3 min    |
| 02    | 1     | 5 min | 5 min    |

**Recent Trend:**
- Last 5 plans: 01-01 (3m), 01-02 (3m), 02-01 (5m)
- Trend: Consistent execution velocity

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

### Pending Todos

None yet.

### Blockers/Concerns

**From Research:**
- evdev device selection algorithm needs hands-on testing (Phase 2)
- ydotool daemon setup steps need documentation (Phase 2)
- PipeWire vs PulseAudio detection fallback logic unclear (Phase 4)
- Keyboard layout detection method needs compositor-specific commands (Phase 6)

## Session Continuity

Last session: 2026-02-15 (plan execution)
Stopped at: Completed 02-01-PLAN.md - Hotkey Detection and Audio Recording
Resume file: None

---
*State initialized: 2026-02-15*
*Last updated: 2026-02-15*
