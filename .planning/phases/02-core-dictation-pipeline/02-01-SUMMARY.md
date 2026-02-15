---
phase: 02-core-dictation-pipeline
plan: 01
subsystem: input
tags: [evdev, sounddevice, hotkey-detection, audio-recording, faster-whisper, scipy]
dependency_graph:
  requires:
    - phase: 01-foundation
      provides: package-structure
  provides: [hotkey-detection, audio-recording, input-permissions]
  affects: [02-02, 02-03, pipeline-coordination]
tech_stack:
  added: [evdev, sounddevice, faster-whisper, scipy]
  patterns: [callback-based-audio, queue-draining, device-auto-detection]
key_files:
  created:
    - src/linuxwhisper/hotkey/__init__.py
    - src/linuxwhisper/hotkey/detector.py
    - src/linuxwhisper/hotkey/permissions.py
    - src/linuxwhisper/audio/__init__.py
    - src/linuxwhisper/audio/recorder.py
  modified:
    - pyproject.toml
decisions:
  - "Use evdev device grabbing to prevent hotkey propagation to other applications"
  - "Support both KEY_F13 and F13 formats for hotkey configuration flexibility"
  - "16kHz mono int16 WAV format for optimal Whisper compatibility"
  - "Queue-based non-blocking audio recording with callback pattern"
metrics:
  duration: "5 minutes"
  completed: "2026-02-15"
  tasks: 2
  commits: 2
---

# Phase 02 Plan 01: Hotkey Detection and Audio Recording Summary

**One-liner:** evdev-based hotkey detector with device auto-selection and callback-based audio recorder producing 16kHz mono WAV files for Whisper.

## Overview

Built the two input-side components of the dictation pipeline: a hotkey detector using Linux evdev for keyboard monitoring, and an audio recorder using sounddevice for microphone capture. Both components are independently testable and provide the foundation for pipeline coordination.

## Tasks Completed

### Task 1: Implement evdev hotkey detection with permission checking
**Commit:** `b2a6ad9`

Created a complete hotkey detection system with:
- **HotkeyDetector class** with automatic keyboard device selection via evdev
- **Permission checking** for input group membership validation
- **Keycode resolution** supporting both "KEY_F13" and "F13" formats
- **Device auto-detection** with filtering for non-keyboard devices (power buttons, etc.)
- **USB device preference** in auto-selection algorithm
- **Exclusive device grabbing** to prevent hotkey propagation to other apps
- **Dependencies added:** evdev>=1.9, sounddevice>=0.5, faster-whisper, scipy

**Files created:**
- `/home/rob/Documents/Projects/LinuxWhisper/src/linuxwhisper/hotkey/__init__.py`
- `/home/rob/Documents/Projects/LinuxWhisper/src/linuxwhisper/hotkey/detector.py`
- `/home/rob/Documents/Projects/LinuxWhisper/src/linuxwhisper/hotkey/permissions.py`

**Files modified:**
- `/home/rob/Documents/Projects/LinuxWhisper/pyproject.toml`

**Key implementation details:**
- `_find_keyboard()` filters devices by EV_KEY capability and phys attribute
- `_resolve_keycode()` normalizes hotkey names with KEY_ prefix
- `start()` method blocks in read_loop for event monitoring (designed for thread execution)
- `devices` property provides diagnostic info for all detected keyboards

### Task 2: Implement queue-based audio recorder with WAV output
**Commit:** `e887511`

Created a non-blocking audio recording system with:
- **AudioRecorder class** using sounddevice InputStream with callbacks
- **Queue-based buffering** to prevent blocking in audio callback
- **NumPy array output** from queue draining on stop
- **WAV file saving** with int16 conversion and mono enforcement
- **Temporary file support** for transient recordings
- **Audio clipping** to [-1.0, 1.0] range for safety

**Files created:**
- `/home/rob/Documents/Projects/LinuxWhisper/src/linuxwhisper/audio/__init__.py`
- `/home/rob/Documents/Projects/LinuxWhisper/src/linuxwhisper/audio/recorder.py`

**Key implementation details:**
- `_callback()` uses `indata.copy()` (critical - sounddevice reuses buffers)
- `start()` clears queue before recording to prevent data leakage
- `stop()` concatenates all queue chunks into single NumPy array
- `save_wav()` converts float32 to int16 for Whisper compatibility (16-bit PCM)
- `is_recording` property for state checking

## Verification Results

All verification checks passed:
- ✓ evdev, sounddevice, scipy dependencies installed
- ✓ HotkeyDetector resolves "F13" and "KEY_F13" to same keycode (183)
- ✓ Permission checker returns boolean for input group membership
- ✓ AudioRecorder saves valid 16kHz mono int16 WAV files
- ✓ All modules import without errors

## Decisions Made

1. **evdev device grabbing**: Use `device.grab()` to exclusively capture hotkey events and prevent propagation to other applications. This ensures the dictation hotkey doesn't trigger other key bindings.

2. **Flexible hotkey format**: Support both "KEY_F13" and "F13" in config by auto-prepending "KEY_" prefix if missing. Improves user experience.

3. **16kHz mono int16 WAV**: This is the optimal format for faster-whisper - matches Whisper's training data and minimizes file size.

4. **Queue-based audio architecture**: Non-blocking callback pattern is essential for real-time audio capture without dropouts. Queue draining on stop ensures all samples are captured.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all tasks completed without problems.

## User Setup Required

**Input group membership required for hotkey detection.**

Users must add themselves to the `input` group to access evdev devices:
```bash
sudo usermod -aG input $USER
# Log out and back in for changes to take effect
```

This is detected at runtime by `check_input_permissions()` and will be surfaced in user-facing error messages when the daemon starts.

## Next Phase Readiness

**Ready for pipeline coordination (Plan 02-02):**
- ✓ HotkeyDetector provides start/stop interface for event monitoring
- ✓ AudioRecorder provides start/stop interface for recording
- ✓ Both components independently verified
- ✓ WAV output format compatible with Whisper transcription

**Known limitations to address in future plans:**
- Hotkey detection blocks in read_loop (requires threading in coordinator)
- Audio recording has no timeout mechanism (coordinator must handle)
- No error recovery for device disconnection during operation

## Self-Check: PASSED

All SUMMARY.md claims verified:
- ✓ All created files exist on disk
- ✓ All commits exist in git history
- ✓ pyproject.toml modification verified in Task 1 commit
- ✓ No missing artifacts

---
*Phase: 02-core-dictation-pipeline*
*Completed: 2026-02-15*
