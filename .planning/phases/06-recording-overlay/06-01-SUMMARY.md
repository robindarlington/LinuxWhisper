---
phase: "06-recording-overlay"
plan: "01"
subsystem: "overlay"
tags: [gtk4, layer-shell, cairo, waveform, subprocess, wayland]
dependency-graph:
  requires: []
  provides: ["overlay-manager-api", "overlay-subprocess", "waveform-widget"]
  affects: ["pipeline-coordinator"]
tech-stack:
  added: ["PyGObject (gi)", "GTK4", "gtk4-layer-shell", "pycairo"]
  patterns: ["subprocess isolation", "stdin pipe IPC", "GLib.idle_add thread-safety", "layer-shell overlay"]
key-files:
  created:
    - src/linuxwhisper/overlay/__init__.py
    - src/linuxwhisper/overlay/__main__.py
    - src/linuxwhisper/overlay/window.py
    - src/linuxwhisper/overlay/waveform.py
    - src/linuxwhisper/overlay/reader.py
  modified: []
decisions:
  - "Subprocess isolation for GTK overlay — avoids main loop conflicts with daemon"
  - "ctypes CDLL preload of libgtk4-layer-shell.so before any gi imports"
  - "System packages only (PyGObject, pycairo, gtk4-layer-shell) — no pip deps"
  - "load_from_string for CSS (GTK 4.12+ modern API)"
metrics:
  duration: "3 min"
  completed: "2026-02-18"
  tasks: 2
  files-created: 5
---

# Phase 6 Plan 01: Overlay Module Summary

GTK4 layer-shell overlay subprocess with Cairo waveform rendering and OverlayManager API for daemon control via stdin pipe.

## What Was Built

Five-file overlay package (`src/linuxwhisper/overlay/`) that provides:

1. **`__init__.py`** -- OverlayManager class: `show()` spawns subprocess, `hide()` terminates it, `send_amplitude(rms)` writes floats to stdin pipe, `is_running()` polls process state. Accepts optional config dict for future extensibility.

2. **`__main__.py`** -- Subprocess entry point (`python -m linuxwhisper.overlay`). Critically preloads `libgtk4-layer-shell.so` via `ctypes.CDLL` before any gi imports. Creates GTK Application, wires activate handler that builds window + waveform widget + stdin reader.

3. **`window.py`** -- `create_overlay_window()` function. Layer-shell path: anchors to bottom-right, TOP layer, `KeyboardMode.NONE` (no focus stealing), `exclusive_zone -1`, namespace "linuxwhisper-overlay". X11 fallback: undecorated small window. CSS: rounded corners, blue background (#2164AD).

4. **`waveform.py`** -- `WaveformWidget` subclassing `Gtk.DrawingArea`. Stores amplitude history in `deque(maxlen=100)`. Cairo draw function renders mirrored white fill waveform on blue background. 30fps refresh via `GLib.timeout_add(33)`. Idle state shows thin center line.

5. **`reader.py`** -- `StdinReader` with daemon thread reading float lines from stdin. Pushes values to waveform via `GLib.idle_add(widget.push_amplitude, rms)`. On EOF, requests `app.quit()` for clean exit.

## Architecture

```
Daemon Process                    Overlay Subprocess
+-----------------+    stdin     +--------------------+
| OverlayManager  |---pipe--->  | __main__.py        |
| .show()         |  floats     |   StdinReader      |
| .send_amplitude |             |     |               |
| .hide()         |             |   GLib.idle_add     |
+-----------------+             |     v               |
                                |   WaveformWidget   |
                                |   (Cairo 30fps)    |
                                |     |               |
                                |   GTK4 Window      |
                                |   (layer-shell)    |
                                +--------------------+
```

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Subprocess over threading/multiprocessing | GTK4 owns main loop; multiprocessing fork() breaks GLib |
| ctypes CDLL preload | Required by gtk4-layer-shell to intercept Wayland calls before GTK init |
| System packages only | PyGObject/pycairo/gtk4-layer-shell are GI bindings, not pip-installable |
| load_from_string for CSS | Modern GTK 4.12+ API, verified working on target system |
| deque(maxlen=100) for history | Limits Cairo draw complexity; ~3s of visible waveform at 30fps |

## Deviations from Plan

None -- plan executed exactly as written.

## Verification Results

| Check | Result |
|-------|--------|
| `OverlayManager` import (venv) | PASS |
| All module imports (system Python with gi) | PASS |
| Interface assertions (show/hide/send_amplitude/is_running) | PASS |
| `python -m linuxwhisper.overlay` entry point valid | PASS (structure verified) |

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | `4b89605` | OverlayManager API, __main__.py entry point, StdinReader |
| 2 | `71294de` | GTK4 window with layer-shell, Cairo waveform widget |

## Self-Check: PASSED

All 5 created files verified on disk. Both commit hashes (4b89605, 71294de) verified in git log.
