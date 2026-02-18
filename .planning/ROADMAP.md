# Roadmap: LinuxWhisper

## Overview

LinuxWhisper delivers local voice dictation for Linux through eight phases, starting with daemon foundation and basic dictation pipeline, then progressively adding modes (toggle), optimizations (model selection), visual feedback (waveform overlay), and production features (systemd service, AUR packaging). The architecture validates critical decisions early (evdev hotkeys, ydotool injection, daemon-loaded models) to avoid costly rewrites.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [x] **Phase 1: Foundation** - Daemon process, config management, project structure ✓ 2026-02-15
- [x] **Phase 2: Core Dictation Pipeline** - Hold-to-talk hotkey, audio capture, Whisper transcription, text injection ✓ 2026-02-18
- [x] **Phase 3: Enhanced Input Modes** - Toggle mode, configurable hotkeys, non-interference validation ✓ 2026-02-18
- [x] **Phase 4: Transcription Features** - Model selection, daemon memory loading, sentence formatting ✓ 2026-02-18
- [x] **Phase 5: Output Refinement** - Display server detection, Unicode support, spacing control ✓ 2026-02-18
- [x] **Phase 6: Recording Overlay** - Live waveform widget during recording, layer-shell positioning ✓ 2026-02-18
- [x] **Phase 7: System Integration** - systemd user service, auto-start, crash recovery ✓ 2026-02-18
- [ ] **Phase 8: Distribution** - AUR package, post-install instructions

## Phase Details

### Phase 1: Foundation
**Goal**: Daemon infrastructure ready for dictation components to integrate with
**Depends on**: Nothing (first phase)
**Requirements**: SYS-01, SYS-04
**Success Criteria** (what must be TRUE):
  1. Daemon process starts via CLI command and runs in background
  2. Config file loads from ~/.config/linuxwhisper/config.toml with defaults if missing
  3. Daemon accepts stop/reload commands via CLI
  4. Basic logging captures daemon lifecycle events
**Plans**: 2 plans

Plans:
- [x] 01-01-PLAN.md — Project structure, packaging, and config system
- [x] 01-02-PLAN.md — Daemon core, CLI commands, PID management, logging

### Phase 2: Core Dictation Pipeline
**Goal**: User can hold hotkey, speak, release, and text appears in active window
**Depends on**: Phase 1
**Requirements**: DICT-01, DICT-03, INPUT-01, TRANS-01, OUTPUT-01
**Success Criteria** (what must be TRUE):
  1. User can press and hold F13 to start recording
  2. Releasing F13 stops recording and triggers transcription
  3. Transcribed text appears in the active window within 2 seconds
  4. Works on both X11 and Wayland sessions (runtime detection)
  5. Non-ASCII text (cafe, emoji) transcribes correctly
**Plans**: 4 plans

Plans:
- [x] 02-01-PLAN.md — Hotkey detection (evdev) and audio recording (sounddevice)
- [x] 02-02-PLAN.md — Transcription engine (faster-whisper) and text injection (ydotool/xdotool)
- [x] 02-03-PLAN.md — Pipeline state machine coordinator and daemon integration
- [x] 02-04-PLAN.md — End-to-end verification checkpoint

### Phase 3: Enhanced Input Modes
**Goal**: User can choose between hold-to-talk and toggle modes with custom hotkeys
**Depends on**: Phase 2
**Requirements**: DICT-02, INPUT-02, INPUT-03
**Success Criteria** (what must be TRUE):
  1. User can press hotkey once to start recording, press again to stop (toggle mode)
  2. User can configure hotkey binding via config file
  3. Configured hotkey does not interfere with compositor bindings (validated at startup)
  4. Mode selection persists across daemon restarts
  5. Toggle timeout (2 min default) auto-stops recording as safety net for forgotten toggles
**Plans**: 2 plans

Plans:
- [x] 03-01-PLAN.md — Toggle mode with timeout and escape cancel, InputMode enum, friendly hotkey aliases, compositor conflict detection (Hyprland/Sway/GNOME/KDE/X11)
- [x] 03-02-PLAN.md — Updated config defaults (HOME hotkey, toggle_timeout), state-aware config reload, daemon integration

### Phase 4: Transcription Features
**Goal**: User can select Whisper models and get fast, formatted transcriptions
**Depends on**: Phase 2
**Requirements**: TRANS-02, TRANS-03, TRANS-04
**Success Criteria** (what must be TRUE):
  1. User can select model size (tiny, base, small, medium) via config
  2. Whisper model loads once at daemon startup and stays in memory
  3. Transcription completes in under 500ms after recording stops
  4. Sentences auto-capitalize first word and add period at end (full sentence mode)
  5. Model switches apply after daemon reload without restarting system
**Plans**: 1 plan

Plans:
- [x] 04-01-PLAN.md — Config model validation, numpy passthrough, sentence formatting, model hot-reload via SIGHUP

### Phase 5: Output Refinement
**Goal**: Text injection works universally across display servers with proper formatting
**Depends on**: Phase 2
**Requirements**: DICT-04, OUTPUT-02, OUTPUT-03
**Success Criteria** (what must be TRUE):
  1. Text injection auto-detects X11 vs Wayland and uses appropriate backend
  2. Works on Hyprland, Sway, GNOME Wayland, and KDE Wayland compositors
  3. Unicode characters and special characters render correctly
  4. Consecutive dictations separated by space automatically
  5. Injection works in native Wayland apps (Firefox, Chrome), not just terminals
**Plans**: 2 plans

Plans:
- [x] 05-01-PLAN.md — Multi-backend fallback injector with compositor detection, wtype, clipboard backends, and Unicode support
- [x] 05-02-PLAN.md — Dictation spacing tracker and pipeline integration

### Phase 6: Recording Overlay
**Goal**: Small, discrete live waveform overlay appears during recording as visual feedback
**Depends on**: Phase 2
**Requirements**: UI-01
**Success Criteria** (what must be TRUE):
  1. Waveform overlay appears when recording starts, disappears when recording stops
  2. Overlay displays a live audio waveform (updates in real-time from mic input)
  3. Overlay is small and discrete, positioned at the edge/corner of the screen
  4. Overlay uses Wayland layer-shell (works on Hyprland, Sway) with X11 fallback
  5. Overlay does not steal focus or interfere with text input in the active window
  6. Visual style: white waveform on blue background, polished appearance
**Plans**: 2 plans

Plans:
- [x] 06-01-PLAN.md — Overlay subprocess module: OverlayManager API, GTK4 window with layer-shell, Cairo waveform widget, stdin pipe reader
- [x] 06-02-PLAN.md — Pipeline integration: amplitude callback on AudioRecorder, overlay show/hide in coordinator state machine, overlay config defaults

### Phase 7: System Integration
**Goal**: LinuxWhisper runs as a systemd user service with auto-start and crash recovery
**Depends on**: Phase 1
**Requirements**: SYS-02
**Success Criteria** (what must be TRUE):
  1. systemd user service starts daemon on login
  2. Service automatically restarts on crash
  3. Service stops cleanly on logout without orphaned processes
  4. Service file installed to correct systemd user unit path
**Plans**: 2 plans

Plans:
- [x] 07-01-PLAN.md — Service file template, systemd helpers, `linuxwhisper service install|uninstall|status` CLI subcommands
- [x] 07-02-PLAN.md — CLI systemd delegation: modify start/stop/reload/status to delegate to systemctl when service is enabled

### Phase 8: Distribution
**Goal**: LinuxWhisper installable via AUR with complete setup instructions
**Depends on**: All previous phases
**Requirements**: PKG-01, PKG-02
**Success Criteria** (what must be TRUE):
  1. AUR package installs on clean Arch system via yay/paru
  2. Post-install message guides user through input group and ydotool setup
  3. Package includes all runtime dependencies (no missing transitive deps)
  4. Fresh install works without errors on minimal Arch installation
  5. Package passes namcap validation with no errors
**Plans**: TBD

Plans:
- [ ] 08-01: TBD during planning

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 2/2 | ✓ Complete | 2026-02-15 |
| 2. Core Dictation Pipeline | 4/4 | ✓ Complete | 2026-02-18 |
| 3. Enhanced Input Modes | 2/2 | ✓ Complete | 2026-02-18 |
| 4. Transcription Features | 1/1 | ✓ Complete | 2026-02-18 |
| 5. Output Refinement | 2/2 | ✓ Complete | 2026-02-18 |
| 6. Recording Overlay | 2/2 | ✓ Complete | 2026-02-18 |
| 7. System Integration | 2/2 | ✓ Complete | 2026-02-18 |
| 8. Distribution | 0/? | Not started | - |

---
*Roadmap created: 2026-02-15*
*Phase 1 completed: 2026-02-15*
*Phase 2 completed: 2026-02-18*
*Phase 4 (Audio Optimization) removed: 2026-02-18 — folded into Phase 3, phases renumbered*
*Phase 3 completed: 2026-02-18*
*Phase 4 completed: 2026-02-18*
*Phase 5 completed: 2026-02-18*
*Phases 6-7 restructured: 2026-02-18 — Recording Overlay added as Phase 6, old Phase 6 (System Integration) slimmed and moved to Phase 7, Distribution moved to Phase 8*
*Phase 6 planned: 2026-02-18 — 2 plans, 2 waves*
*Phase 6 completed: 2026-02-18*
*Phase 7 planned: 2026-02-18 — 2 plans, 2 waves*
*Phase 7 completed: 2026-02-18*
