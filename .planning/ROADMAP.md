# Roadmap: LinuxWhisper

## Overview

LinuxWhisper delivers local voice dictation for Linux through eight phases, starting with daemon foundation and basic dictation pipeline, then progressively adding modes (toggle), optimizations (VAD, model selection), and production features (system tray, AUR packaging). The architecture validates critical decisions early (evdev hotkeys, ydotool injection, daemon-loaded models) to avoid costly rewrites.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [ ] **Phase 1: Foundation** - Daemon process, config management, project structure
- [ ] **Phase 2: Core Dictation Pipeline** - Hold-to-talk hotkey, audio capture, Whisper transcription, text injection
- [ ] **Phase 3: Enhanced Input Modes** - Toggle mode, configurable hotkeys, non-interference validation
- [ ] **Phase 4: Audio Optimization** - Voice Activity Detection, PipeWire/PulseAudio integration, proper audio format
- [ ] **Phase 5: Transcription Features** - Model selection, daemon memory loading, sentence formatting
- [ ] **Phase 6: Output Refinement** - Display server detection, Unicode support, spacing control
- [ ] **Phase 7: System Integration** - System tray icon, desktop notifications, systemd service
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
- [ ] 01-01-PLAN.md — Project structure, packaging, and config system
- [ ] 01-02-PLAN.md — Daemon core, CLI commands, PID management, logging

### Phase 2: Core Dictation Pipeline
**Goal**: User can hold hotkey, speak, release, and text appears in active window
**Depends on**: Phase 1
**Requirements**: DICT-01, DICT-03, INPUT-01, TRANS-01, OUTPUT-01
**Success Criteria** (what must be TRUE):
  1. User can press and hold F13 to start recording
  2. Releasing F13 stops recording and triggers transcription
  3. Transcribed text appears in the active window within 2 seconds
  4. Works on both X11 and Wayland sessions (runtime detection)
  5. Non-ASCII text (café, emoji) transcribes correctly
**Plans**: TBD

Plans:
- [ ] 02-01: TBD during planning

### Phase 3: Enhanced Input Modes
**Goal**: User can choose between hold-to-talk and toggle modes with custom hotkeys
**Depends on**: Phase 2
**Requirements**: DICT-02, INPUT-02, INPUT-03
**Success Criteria** (what must be TRUE):
  1. User can press hotkey once to start recording, press again to stop (toggle mode)
  2. User can configure hotkey binding via config file
  3. Configured hotkey does not interfere with compositor bindings (validated at startup)
  4. Mode selection persists across daemon restarts
**Plans**: TBD

Plans:
- [ ] 03-01: TBD during planning

### Phase 4: Audio Optimization
**Goal**: Audio capture works reliably across audio stacks with automatic silence detection
**Depends on**: Phase 2
**Requirements**: AUDIO-01, AUDIO-02, AUDIO-03
**Success Criteria** (what must be TRUE):
  1. Audio captured from default microphone via PipeWire on Arch systems
  2. Audio captured via PulseAudio fallback on non-PipeWire systems
  3. Recording format is 16kHz mono WAV optimized for Whisper
  4. Voice Activity Detection auto-stops recording after 2 seconds of silence (toggle mode)
  5. Audio quality is sufficient for accurate transcription
**Plans**: TBD

Plans:
- [ ] 04-01: TBD during planning

### Phase 5: Transcription Features
**Goal**: User can select Whisper models and get fast, formatted transcriptions
**Depends on**: Phase 2
**Requirements**: TRANS-02, TRANS-03, TRANS-04
**Success Criteria** (what must be TRUE):
  1. User can select model size (tiny, base, small, medium) via config
  2. Whisper model loads once at daemon startup and stays in memory
  3. Transcription completes in under 500ms after recording stops
  4. Sentences auto-capitalize first word and add period at end (full sentence mode)
  5. Model switches apply after daemon reload without restarting system
**Plans**: TBD

Plans:
- [ ] 05-01: TBD during planning

### Phase 6: Output Refinement
**Goal**: Text injection works universally across display servers with proper formatting
**Depends on**: Phase 2
**Requirements**: DICT-04, OUTPUT-02, OUTPUT-03
**Success Criteria** (what must be TRUE):
  1. Text injection auto-detects X11 vs Wayland and uses appropriate backend
  2. Works on Hyprland, Sway, GNOME Wayland, and KDE Wayland compositors
  3. Unicode characters and special characters render correctly
  4. Consecutive dictations separated by space automatically
  5. Injection works in native Wayland apps (Firefox, Chrome), not just terminals
**Plans**: TBD

Plans:
- [ ] 06-01: TBD during planning

### Phase 7: System Integration
**Goal**: LinuxWhisper integrates with system as autostart service with visual feedback
**Depends on**: Phase 1
**Requirements**: SYS-02, SYS-03
**Success Criteria** (what must be TRUE):
  1. systemd user service starts daemon on login
  2. Service automatically restarts on crash
  3. System tray icon shows idle/recording/transcribing state
  4. Desktop notifications show transcription start/complete/error
  5. Service stops cleanly on logout without orphaned processes
**Plans**: TBD

Plans:
- [ ] 07-01: TBD during planning

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
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 0/2 | Planned | - |
| 2. Core Dictation Pipeline | 0/? | Not started | - |
| 3. Enhanced Input Modes | 0/? | Not started | - |
| 4. Audio Optimization | 0/? | Not started | - |
| 5. Transcription Features | 0/? | Not started | - |
| 6. Output Refinement | 0/? | Not started | - |
| 7. System Integration | 0/? | Not started | - |
| 8. Distribution | 0/? | Not started | - |

---
*Roadmap created: 2026-02-15*
*Ready for planning: Phase 1*
