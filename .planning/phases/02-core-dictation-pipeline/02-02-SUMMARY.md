---
phase: 02-core-dictation-pipeline
plan: 02
subsystem: dictation-pipeline
tags: [transcription, text-injection, whisper, x11, wayland]
dependency_graph:
  requires:
    - config-system
    - logging-system
  provides:
    - transcription-engine
    - text-injection
    - session-detection
  affects:
    - daemon-lifecycle
tech_stack:
  added:
    - faster-whisper (INT8 quantization)
    - ydotool (Wayland text injection)
    - xdotool (X11 text injection)
  patterns:
    - lazy-loading
    - factory-pattern
    - runtime-detection
key_files:
  created:
    - src/linuxwhisper/transcription/__init__.py
    - src/linuxwhisper/transcription/engine.py
    - src/linuxwhisper/injection/__init__.py
    - src/linuxwhisper/injection/detector.py
    - src/linuxwhisper/injection/wayland.py
    - src/linuxwhisper/injection/x11.py
  modified: []
decisions:
  - INT8 quantization for CPU, int8_float16 for GPU - optimal speed for local transcription
  - Lazy model loading - daemon controls when expensive model load happens
  - VAD filtering with custom parameters - better transcription quality
  - Multi-method session detection - robust X11/Wayland identification
  - Factory pattern for injector creation - clean auto-selection based on session
  - Validate tool availability at init - fail fast with clear error messages
metrics:
  duration: 11 minutes
  tasks_completed: 2
  files_created: 6
  commits: 2
  completed_date: 2026-02-15
---

# Phase 02 Plan 02: Transcription Engine and Text Injection Summary

Faster-whisper transcription engine with INT8 quantization and X11/Wayland text injection with auto-detection.

## What Was Built

### Transcription Engine (src/linuxwhisper/transcription/)

**TranscriptionEngine** - Wraps faster-whisper with INT8 quantization for fast CPU transcription:
- Lazy model loading - `__init__` doesn't load model, daemon controls when load happens
- INT8 quantization on CPU, int8_float16 on GPU for optimal performance
- VAD filtering with custom parameters (threshold 0.5, min speech 250ms, min silence 2s)
- Explicit load/unload methods for memory management
- `is_loaded` property to check model state
- Auto-load on first `transcribe()` call if not already loaded

**Key implementation details:**
- Transcribes 16kHz mono WAV files (Whisper's expected format)
- Returns joined text from all segments
- Logs character count and detected language with probability

### Text Injection (src/linuxwhisper/injection/)

**Session Detection** - Multi-method X11 vs Wayland detection:
1. Check `XDG_SESSION_TYPE` environment variable
2. Check `WAYLAND_DISPLAY` environment variable
3. Check `DISPLAY` environment variable
4. Fall back to `loginctl show-session` if all env checks fail
5. Return 'unknown' if all methods fail

**WaylandInjector** - ydotool wrapper for Wayland:
- Validates ydotool binary exists at init
- Checks for ydotoold socket at `/tmp/.ydotool_socket` or `/run/user/{uid}/.ydotool_socket`
- Raises clear RuntimeError if tool or daemon missing
- Wraps `ydotool type --key-delay {ms} -- {text}` with timeout protection
- Logs character count on successful injection

**X11Injector** - xdotool wrapper for X11:
- Validates xdotool binary exists at init
- Checks DISPLAY environment variable is set
- Raises clear RuntimeError if tool or session invalid
- Wraps `xdotool type --delay {ms} -- {text}` with LANG=en_US.UTF-8
- Logs character count on successful injection

**Factory Function** - Auto-selects injector based on session:
- `create_injector()` calls `detect_session_type()`
- Returns WaylandInjector for 'wayland' session
- Returns X11Injector for 'x11' session
- For 'unknown', tries WaylandInjector first, falls back to X11Injector
- Raises RuntimeError with install instructions if both fail

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Missing faster-whisper dependency**
- **Found during:** Task 1 verification
- **Issue:** ModuleNotFoundError when importing TranscriptionEngine
- **Fix:** Installed faster-whisper via pip in virtual environment
- **Files modified:** .venv/lib/python3.*/site-packages/
- **Commit:** Not committed (dependency installation)

No other deviations - plan executed as written.

## Key Technical Decisions

**1. INT8 quantization strategy**
- CPU gets `int8` compute type (fastest on CPU)
- GPU gets `int8_float16` (better GPU performance)
- Trade-off: slight quality loss for significant speed gain on CPU

**2. Lazy model loading**
- Model NOT loaded in `__init__`
- Daemon can initialize engine without expensive model load
- Auto-loads on first `transcribe()` call
- Explicit `load_model()` for daemon control

**3. VAD parameters**
- Threshold: 0.5 (moderate sensitivity)
- Min speech: 250ms (filter very short noises)
- Min silence: 2s (don't split on brief pauses)
- Speech padding: 400ms (capture word edges)
- Result: Better transcription quality by filtering non-speech

**4. Multi-method session detection**
- Four detection methods in priority order
- Graceful degradation if one method fails
- Logs which method succeeded for debugging
- Returns 'unknown' only if all methods fail

**5. Fail-fast validation**
- Both injectors validate tools at `__init__` time
- Clear error messages with install instructions
- Better UX than failing during first text injection
- Daemon can check injector availability early

## Testing & Verification

**Verification completed:**
1. TranscriptionEngine initializes without loading model (lazy load confirmed)
2. TranscriptionEngine loads tiny model and transcribes silent WAV (works)
3. detect_session_type() returns 'wayland' correctly for current session
4. create_injector() properly validates tool dependencies (expected failure without ydotool)
5. All modules import without errors

**Expected runtime dependencies** (not installed in dev environment):
- `ydotool` package for Wayland (pacman -S ydotool)
- `ydotoold` service running (systemctl --user start ydotoold)
- `xdotool` package for X11 (pacman -S xdotool)

These will be documented in install instructions and validated at runtime.

## Integration Points

**Upstream dependencies:**
- Config system (for model size, device selection)
- Logging system (for transcription and injection logging)

**Downstream consumers:**
- Daemon will instantiate TranscriptionEngine and create_injector()
- Audio recorder will produce WAV files for transcription
- Hotkey handler will trigger the transcription → injection pipeline

**Session detection usage:**
- Daemon startup: call detect_session_type() and log result
- Injector creation: create_injector() called once at daemon init
- No runtime session switching (would require daemon restart)

## Next Steps

This plan completes the output-side components of the dictation pipeline. Next plans will implement:

**02-03**: Audio capture via arecord/ffmpeg (input side)
**02-04**: Hotkey detection via evdev (trigger side)

After Phase 02 completes, the core pipeline will be functional end-to-end.

## Self-Check

Verifying all claimed artifacts exist:

**Files created:**
- src/linuxwhisper/transcription/__init__.py: EXISTS
- src/linuxwhisper/transcription/engine.py: EXISTS
- src/linuxwhisper/injection/__init__.py: EXISTS
- src/linuxwhisper/injection/detector.py: EXISTS
- src/linuxwhisper/injection/wayland.py: EXISTS
- src/linuxwhisper/injection/x11.py: EXISTS

**Commits:**
- 2bf5fb3 (Task 1 - TranscriptionEngine): EXISTS
- 252f377 (Task 2 - Injection module): EXISTS

**Module imports:**
- from linuxwhisper.transcription import TranscriptionEngine: WORKS
- from linuxwhisper.injection import detect_session_type, create_injector: WORKS

**Key functionality:**
- TranscriptionEngine.is_loaded property: WORKS
- TranscriptionEngine.load_model(): WORKS (tiny model tested)
- detect_session_type(): WORKS (returned 'wayland')
- WaylandInjector validation: WORKS (proper error for missing ydotool)

## Self-Check: PASSED

All files, commits, and functionality verified.
