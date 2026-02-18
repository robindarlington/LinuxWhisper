---
phase: "06-recording-overlay"
plan: "02"
subsystem: "pipeline-overlay-integration"
tags: [overlay, pipeline, amplitude, callback, coordinator, config]
dependency-graph:
  requires: ["overlay-manager-api"]
  provides: ["pipeline-overlay-integration", "amplitude-callback-hook", "overlay-config-defaults"]
  affects: ["dictation-pipeline", "audio-recorder", "config-defaults"]
tech-stack:
  added: []
  patterns: ["observer callback on audio stream", "conditional overlay lifecycle in state machine"]
key-files:
  created: []
  modified:
    - src/linuxwhisper/config/defaults.py
    - src/linuxwhisper/audio/recorder.py
    - src/linuxwhisper/pipeline/coordinator.py
decisions:
  - "Amplitude callback in audio _callback (not separate thread) -- trivial RMS on ~1024 samples"
  - "Overlay lifecycle in coordinator, not daemon -- single ownership, clean state machine integration"
  - "No daemon/main.py changes needed -- pipeline.stop() already called on shutdown handles overlay cleanup"
metrics:
  duration: "2 min"
  completed: "2026-02-18"
  tasks: 2
  files-modified: 3
---

# Phase 6 Plan 02: Pipeline Overlay Integration Summary

Wired OverlayManager into dictation pipeline with RMS amplitude callback, config defaults, and state-machine-driven show/hide lifecycle.

## What Was Built

Three files modified to connect the standalone overlay module (06-01) to the dictation pipeline:

1. **`src/linuxwhisper/config/defaults.py`** -- Added `overlay` section to DEFAULT_CONFIG with keys: `enabled` (True), `position` ("bottom-right"), `width` (200), `height` (60). Placed between `auto_space` and `audio` sections.

2. **`src/linuxwhisper/audio/recorder.py`** -- Added amplitude callback hook to AudioRecorder:
   - `_on_amplitude_callback` attribute (None by default)
   - `set_amplitude_callback(callback)` method to register a callback
   - RMS computation in `_callback()` after queue put: flattens to mono if needed, computes `sqrt(mean(chunk**2))`, invokes callback with float

3. **`src/linuxwhisper/pipeline/coordinator.py`** -- Full OverlayManager integration:
   - Import `OverlayManager` from `linuxwhisper.overlay`
   - Create `OverlayManager` in `__init__` (conditional on `overlay.enabled` config)
   - Wire `set_amplitude_callback` to `_on_audio_amplitude` bridge method
   - `show()` called after `recorder.start()` in both HOLD and TOGGLE hotkey press branches
   - `hide()` called at top of `_process_recording()` (before try block)
   - `hide()` called in `_cancel_toggle_recording()` after CANCELLING transition
   - `hide()` called in `stop()` after stopping recorder

## Integration Points

```
AudioRecorder._callback()
    |
    |-- queue.put(indata.copy())     [existing]
    |-- _on_amplitude_callback(rms)  [NEW: RMS float]
           |
           v
DictationPipeline._on_audio_amplitude(rms)
           |
           v
OverlayManager.send_amplitude(rms)
           |
           v  (stdin pipe)
Overlay subprocess -> WaveformWidget
```

## Overlay Lifecycle in State Machine

| Pipeline Event | Overlay Action |
|---------------|----------------|
| Hotkey press (IDLE -> RECORDING) | `show()` |
| Hold release / toggle stop (RECORDING -> PROCESSING) | `hide()` (in `_process_recording`) |
| Escape cancel (RECORDING -> CANCELLING) | `hide()` (in `_cancel_toggle_recording`) |
| Toggle timeout (RECORDING -> PROCESSING) | `hide()` (via `_process_recording`) |
| Pipeline stop | `hide()` (in `stop()`) |
| Overlay disabled in config | `_overlay = None`, all None-checks skip overlay calls |

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Amplitude callback in audio _callback | RMS on ~1024 float32 samples is trivial (~microseconds); avoids extra thread |
| Overlay lifecycle in coordinator only | Single ownership; daemon already calls `pipeline.stop()` which chains to `overlay.hide()` |
| No daemon/main.py changes | Clean separation of concerns; overlay is a pipeline component, not a daemon concern |
| Conditional overlay via config check | `overlay.enabled = false` sets `_overlay = None`; all call sites None-guarded |

## Deviations from Plan

None -- plan executed exactly as written.

## Verification Results

| Check | Result |
|-------|--------|
| `DEFAULT_CONFIG['overlay']` prints config dict | PASS |
| `AudioRecorder().set_amplitude_callback(lambda: None)` | PASS |
| `from linuxwhisper.pipeline.coordinator import DictationPipeline` | PASS |

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | `a7745e7` | Config defaults and amplitude callback on AudioRecorder |
| 2 | `0669252` | Integrate overlay into pipeline coordinator |

## Self-Check: PASSED

All 3 modified files verified on disk. Both commit hashes (a7745e7, 0669252) verified in git log. SUMMARY file exists.
