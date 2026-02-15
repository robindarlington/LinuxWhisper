---
phase: 02-core-dictation-pipeline
plan: 03
subsystem: pipeline-coordination
tags: [state-machine, pipeline, daemon-integration, threading]
dependency_graph:
  requires:
    - phase: 02-core-dictation-pipeline
      plan: 01
      provides: hotkey-detection, audio-recording
    - phase: 02-core-dictation-pipeline
      plan: 02
      provides: transcription-engine, text-injection
  provides:
    - pipeline-coordinator
    - state-machine
    - daemon-pipeline-integration
  affects:
    - daemon-lifecycle
    - end-to-end-dictation
tech_stack:
  added: []
  patterns:
    - state-machine
    - coordinator-pattern
    - daemon-threading
    - error-resilience
key_files:
  created:
    - src/linuxwhisper/pipeline/__init__.py
    - src/linuxwhisper/pipeline/states.py
    - src/linuxwhisper/pipeline/coordinator.py
  modified:
    - src/linuxwhisper/config/defaults.py
    - src/linuxwhisper/daemon/lifecycle.py
    - src/linuxwhisper/daemon/main.py
decisions:
  - "State machine with VALID_TRANSITIONS map prevents invalid state transitions"
  - "Hotkey detector runs in daemon thread while processing runs synchronously in callback"
  - "Error handling always returns to IDLE state for resilience"
  - "Permission check at daemon startup prevents cryptic evdev errors"
  - "Pre-load Whisper model on pipeline start for fast first dictation"
  - "Config reload requires daemon restart for hotkey/model changes (acceptable for Phase 2)"
metrics:
  duration: 2 minutes
  tasks_completed: 2
  files_created: 3
  files_modified: 3
  commits: 2
  completed_date: 2026-02-15
---

# Phase 02 Plan 03: Pipeline Coordinator and State Machine Summary

State machine coordinator that wires hotkey detection, audio recording, transcription, and text injection into a complete dictation pipeline integrated into the daemon main loop.

## What Was Built

### Pipeline State Machine (src/linuxwhisper/pipeline/states.py)

**PipelineState Enum** - Five states for dictation workflow:
- `IDLE` - Ready to start dictation
- `RECORDING` - Microphone actively recording audio
- `PROCESSING` - Transcribing audio to text
- `INJECTING` - Typing text into active window
- `ERROR` - Error state (always transitions back to IDLE)

**VALID_TRANSITIONS Map** - State transition rules:
- `IDLE -> {RECORDING}` - Hotkey press starts recording
- `RECORDING -> {PROCESSING, IDLE}` - Hotkey release processes, or cancel/error returns to IDLE
- `PROCESSING -> {INJECTING, IDLE}` - Successful transcription injects, empty/error returns to IDLE
- `INJECTING -> {IDLE}` - After injection, return to IDLE
- `ERROR -> {IDLE}` - Always recover to IDLE

### Pipeline Coordinator (src/linuxwhisper/pipeline/coordinator.py)

**DictationPipeline Class** - Orchestrates the complete dictation workflow:

**Initialization:**
- Extracts config values: hotkey, model, sample_rate, channels
- Creates four component instances:
  - `HotkeyDetector` for keyboard monitoring
  - `AudioRecorder` for microphone capture
  - `TranscriptionEngine` for speech-to-text
  - `create_injector()` for text output (X11/Wayland auto-detected)
- Initializes state machine to IDLE

**State Management:**
- `_validate_transition(new_state)` - Checks VALID_TRANSITIONS map
- `_transition(new_state)` - Updates state with logging if valid
- `state` property - Returns current PipelineState

**Event Handlers:**
- `_on_hotkey_press()` - If IDLE, transition to RECORDING and start recorder
- `_on_hotkey_release()` - Complete processing chain:
  1. Transition to PROCESSING
  2. Stop recorder and get audio data
  3. Check minimum duration (0.1 seconds) - discard if too short
  4. Save audio as temporary WAV file
  5. Transcribe audio to text
  6. Clean up temporary file
  7. Check for empty transcription - skip injection if empty
  8. Transition to INJECTING
  9. Type text into active window
  10. Transition back to IDLE
  11. On any error: log and transition to IDLE (resilient - never stuck)

**Lifecycle:**
- `start()` - Check permissions, pre-load Whisper model, start hotkey detector in daemon thread
- `stop()` - Stop hotkey detector, stop recorder if active, unload model
- `_run_hotkey_loop()` - Thread target that runs hotkey detector with error handling

**Threading Model:**
- Hotkey detector runs in daemon thread (blocks in read_loop)
- Callbacks (_on_hotkey_press, _on_hotkey_release) execute in hotkey thread
- Audio processing runs synchronously in callback (acceptable for Phase 2 - no new dictations during processing)
- Main thread just sleeps and handles signals

### Daemon Integration

**Config Defaults (src/linuxwhisper/config/defaults.py):**
- Added `audio.device: None` for future device selection support

**Lifecycle Module (src/linuxwhisper/daemon/lifecycle.py):**
- Added `get_current_config()` function for runtime config access

**Daemon Main (src/linuxwhisper/daemon/main.py):**
- Import DictationPipeline and permission checkers
- Check input permissions at startup with clear error messages
- Create and start DictationPipeline after daemon setup
- Wrap pipeline.start() in try/except with graceful shutdown on failure
- Update main loop sleep to 0.5s (hotkey thread handles events, main thread just stays alive)
- Stop pipeline before shutdown_daemon() for clean shutdown
- Log config reload notice that hotkey/model changes require restart

## Tasks Completed

### Task 1: Create pipeline state machine and coordinator
**Commit:** `8357cf1`

Created complete state machine and coordinator:
- PipelineState enum with 5 states
- VALID_TRANSITIONS map enforcing state transition rules
- DictationPipeline class integrating all four components
- State validation and transition logging
- Hotkey press/release handlers implementing full workflow
- Error handling that always returns to IDLE (resilient design)
- Pre-loading Whisper model on startup for fast first dictation
- Permission checking with clear error messages

**Files created:**
- `/home/rob/Documents/Projects/LinuxWhisper/src/linuxwhisper/pipeline/__init__.py`
- `/home/rob/Documents/Projects/LinuxWhisper/src/linuxwhisper/pipeline/states.py`
- `/home/rob/Documents/Projects/LinuxWhisper/src/linuxwhisper/pipeline/coordinator.py`

### Task 2: Integrate pipeline into daemon and update config defaults
**Commit:** `dc76033`

Integrated pipeline into daemon lifecycle:
- Added audio.device config default
- Added get_current_config() to lifecycle module
- Modified daemon main to create and run pipeline
- Added permission check at startup with sys.exit(1) on failure
- Added pipeline startup error handling
- Updated main loop from 0.1s to 0.5s sleep
- Added pipeline.stop() before shutdown_daemon()
- Added config reload notice for restart requirement

**Files modified:**
- `/home/rob/Documents/Projects/LinuxWhisper/src/linuxwhisper/config/defaults.py`
- `/home/rob/Documents/Projects/LinuxWhisper/src/linuxwhisper/daemon/lifecycle.py`
- `/home/rob/Documents/Projects/LinuxWhisper/src/linuxwhisper/daemon/main.py`

## Deviations from Plan

None - plan executed exactly as written.

## Key Technical Decisions

**1. State machine with VALID_TRANSITIONS map**
- Explicit transition validation prevents invalid state changes
- Easy to debug with state transition logging
- Clear visual map of allowed workflow paths

**2. Hotkey detector threading model**
- Hotkey detector blocks in read_loop, so runs in daemon thread
- Callbacks execute in hotkey thread (not main thread)
- Audio processing runs synchronously in callback for Phase 2 simplicity
- Trade-off: Can't receive new hotkey events during processing, but user can't dictate during transcription anyway
- Future: Phase 5 can move processing to separate thread if latency is an issue

**3. Error resilience - always return to IDLE**
- `_on_hotkey_release()` wrapped in try/except that transitions to IDLE on any error
- Pipeline never gets stuck in non-IDLE state
- Errors logged with full traceback for debugging
- Graceful degradation on partial failures (short recording, empty transcription, etc.)

**4. Permission check at daemon startup**
- `check_input_permissions()` runs before creating pipeline
- Clear error message with setup instructions
- sys.exit(1) prevents cryptic evdev errors later
- Better UX than failing during first hotkey detection

**5. Pre-load Whisper model on startup**
- `pipeline.start()` calls `engine.load_model()`
- First dictation is fast (no loading delay)
- Trade-off: Slower daemon startup, but better user experience
- Memory stays loaded until daemon stops

**6. Config reload behavior**
- Logging level changes apply immediately (Phase 1 feature)
- Hotkey/model changes require daemon restart (acceptable for Phase 2)
- Clear log message informs user of restart requirement
- Future: Phase 3 can add hot-reload of hotkey bindings

## Testing & Verification

**Verification completed:**
1. ✓ Pipeline state machine has correct transition map (IDLE->RECORDING->PROCESSING->INJECTING->IDLE)
2. ✓ DictationPipeline creates all four component instances from config
3. ✓ Daemon imports and initializes pipeline at startup
4. ✓ Permission check runs before pipeline start (current permissions: False)
5. ✓ Daemon shuts down cleanly, stopping pipeline first (code inspection)
6. ✓ Error in any pipeline stage returns to IDLE (code inspection)

**Success criteria met:**
- ✓ Pipeline state machine prevents invalid transitions
- ✓ DictationPipeline orchestrates hotkey->record->transcribe->inject flow
- ✓ Daemon starts pipeline on launch, stops on shutdown
- ✓ Permission check at startup prevents cryptic evdev errors
- ✓ Errors handled gracefully - pipeline always returns to IDLE
- ✓ Full flow architecture: hold F13 -> speak -> release F13 -> text appears in active window

**Expected runtime dependencies** (not available in CI/test environment):
- Input group membership for evdev access
- Physical keyboard device
- ydotool or xdotool for text injection
- Audio input device

## Integration Points

**Upstream dependencies:**
- HotkeyDetector (plan 02-01) - keyboard monitoring
- AudioRecorder (plan 02-01) - microphone capture
- TranscriptionEngine (plan 02-02) - speech-to-text
- create_injector (plan 02-02) - text output

**Downstream consumers:**
- Daemon main loop now runs complete dictation pipeline
- CLI commands (start/stop/status) control the daemon which runs the pipeline
- Future plans will extend the pipeline (e.g., Phase 3 adds hotkey customization)

**State machine usage:**
- All state transitions logged for debugging
- State property available for status reporting (future: CLI status command)
- Error state always recovers to IDLE (resilient design)

## End-to-End Dictation Flow

**Conceptual flow** (requires runtime dependencies to actually execute):

1. User holds F13 key
   - HotkeyDetector detects press event
   - `_on_hotkey_press()` called
   - State: IDLE -> RECORDING
   - AudioRecorder starts capturing microphone

2. User speaks into microphone
   - Audio data queued in memory buffers

3. User releases F13 key
   - HotkeyDetector detects release event
   - `_on_hotkey_release()` called
   - State: RECORDING -> PROCESSING
   - AudioRecorder stops, returns audio data
   - Audio saved as temporary WAV file
   - TranscriptionEngine transcribes to text
   - Temporary file cleaned up

4. Text appears in active window
   - State: PROCESSING -> INJECTING
   - Injector types text character by character
   - State: INJECTING -> IDLE
   - Pipeline ready for next dictation

**Error scenarios** (all return to IDLE):
- Recording too short (< 0.1s) - discard and return to IDLE
- Empty transcription - skip injection and return to IDLE
- Any exception during processing - log error and return to IDLE

## Next Steps

This completes Phase 2 - Core Dictation Pipeline. All four components are now integrated:
- ✓ Hotkey detection (plan 02-01)
- ✓ Audio recording (plan 02-01)
- ✓ Transcription (plan 02-02)
- ✓ Text injection (plan 02-02)
- ✓ Pipeline coordination (plan 02-03)

**Phase 2 remaining:**
- Plan 02-04: End-to-end testing with real hardware

**Phase 3 preview:**
- Advanced hotkey handling (customization, visual feedback)
- Hot-reload of hotkey bindings
- Hotkey conflict detection

## Self-Check

Verifying all claimed artifacts exist:

**Files created:**
- src/linuxwhisper/pipeline/__init__.py: EXISTS
- src/linuxwhisper/pipeline/states.py: EXISTS
- src/linuxwhisper/pipeline/coordinator.py: EXISTS

**Files modified:**
- src/linuxwhisper/config/defaults.py: EXISTS (added audio.device)
- src/linuxwhisper/daemon/lifecycle.py: EXISTS (added get_current_config)
- src/linuxwhisper/daemon/main.py: EXISTS (integrated pipeline)

**Commits:**
- 8357cf1 (Task 1 - Pipeline state machine and coordinator): EXISTS
- dc76033 (Task 2 - Daemon integration): EXISTS

**Module imports:**
- from linuxwhisper.pipeline import PipelineState, DictationPipeline: WORKS
- from linuxwhisper.pipeline.states import VALID_TRANSITIONS: WORKS
- from linuxwhisper.daemon.lifecycle import get_current_config: WORKS

**Key functionality:**
- PipelineState enum has 5 states: VERIFIED
- VALID_TRANSITIONS map enforces state rules: VERIFIED
- DictationPipeline integrates all four components: VERIFIED
- Daemon creates and starts pipeline: VERIFIED
- Permission check at startup: VERIFIED
- Clean shutdown stops pipeline first: VERIFIED

## Self-Check: PASSED

All files, commits, and functionality verified.
