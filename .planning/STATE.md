# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-14)

**Core value:** Hold a key, speak, text appears in the active window — fast, reliable, and works on any Linux display server.
**Current focus:** Phase 6 in progress (Recording Overlay)

## Current Position

Phase: 6 of 7 (Recording Overlay) - IN PROGRESS
Plan: 1 of 1 in current phase
Status: Plan 06-01 complete
Last activity: 2026-02-18 — Completed plan 06-01 (Overlay module)

Progress: [█████████░] 97%

## Performance Metrics

**Velocity:**
- Total plans completed: 11
- Average duration: 4 minutes
- Total execution time: 1.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01    | 2     | 6 min  | 3 min    |
| 02    | 4     | 30 min | 7.5 min  |
| 03    | 2     | 5 min  | 2.5 min  |
| 04    | 1     | 3 min  | 3 min    |
| 05    | 2     | 5 min  | 2.5 min  |
| 06    | 1     | 3 min  | 3 min    |

**Recent Trend:**
- Last 5 plans: 03-02 (2m), 04-01 (3m), 05-01 (3m), 05-02 (2m), 06-01 (3m)
- Trend: Phases 3-6 executing cleanly — all plans under 3 minutes

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
- DEFAULT_CONFIG hotkey changed from F13 to HOME — more universally available key — 03-02
- toggle_timeout=120 added to DEFAULT_CONFIG — feeds toggle mode pipeline — 03-02
- reload_config_safe defers (not fails) when pipeline busy — user retries with SIGHUP — 03-02
- Invalid new config during reload is rejected silently (old config preserved) — 03-02
- set_pipeline_ref called after pipeline.start() — ensures pipeline ready before wiring — 03-02
- PAUSE key doesn't support hold-to-talk (instant press+release) — changed default to HOME — 02-04
- UInput passthrough via UInput.from_device re-injects non-hotkey events — 02-04
- udev rule for uinput may not apply on boot — manual chmod needed, defer to Phase 7/8 — 02-04
- Toggle timeout transcribes captured audio (does not discard) — text appearing is the user's feedback — 03-01
- Escape cancel discards audio without transcribing, only active in toggle mode — 03-01
- Compositor conflict check is warning-only at startup, never blocks daemon start — 03-01
- on_escape callback passed to HotkeyDetector only in toggle mode — Escape passes through in hold mode — 03-01
- validate_config_input called at DictationPipeline.__init__ — invalid config raises ValueError — 03-01
- VALID_MODEL_SIZES restricts to tiny/base/small/medium (.en variants) — no large models — 04-01
- Numpy array passthrough eliminates WAV file I/O overhead in pipeline — 04-01
- format_sentence() only touches boundaries (capitalize first, add trailing period) — 04-01
- reload_model() checks IDLE state, unloads + gc.collect + reloads — safe hot-swap — 04-01
- Multi-backend FallbackInjector replaces single-backend injector — tries backends in order — 05-01
- wtype primary on wlroots (Hyprland/Sway), clipboard fallback for GNOME/KDE — 05-01
- Compositor detection via env vars (HYPRLAND_INSTANCE_SIGNATURE, SWAYSOCK, XDG_CURRENT_DESKTOP) + pgrep fallback — 05-01
- InjectorBackend ABC defines name(), is_available(), type_text(), supports_unicode() interface — 05-01
- Unicode text routes through Unicode-capable backends first (wtype, clipboard) — 05-01
- Clipboard save/restore with configurable 300ms delay prevents race condition — 05-01
- SpacingTracker prepends space between consecutive dictations — 05-02
- Spacing resets on newlines, cancel, stop, and errors — 05-02
- Subprocess isolation for GTK overlay — avoids main loop conflicts with daemon — 06-01
- ctypes CDLL preload of libgtk4-layer-shell.so before any gi imports — 06-01
- System packages only (PyGObject, pycairo, gtk4-layer-shell) — no pip deps for overlay — 06-01

### Pending Todos

None yet.

### Blockers/Concerns

**From Research:**
- PipeWire vs PulseAudio detection — resolved: sounddevice/PortAudio handles this automatically
- Keyboard layout detection — resolved: wtype handles via libxkbcommon, ydotool uses system layout

**From Phase 2 UAT:**
- /dev/uinput permissions not auto-applied by udev rule on boot — needs Phase 6/7 fix
- PAUSE key unsuitable for hold-to-talk — need configurable hotkey docs in Phase 7

## Session Continuity

Last session: 2026-02-18 (execution)
Stopped at: Completed 06-01-PLAN.md - Overlay module. Phase 6 plan 1/1 done.
Resume file: None

---
*State initialized: 2026-02-15*
*Last updated: 2026-02-18 (06-01 complete)*
