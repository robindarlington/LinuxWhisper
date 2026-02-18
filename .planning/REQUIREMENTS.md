# Requirements: LinuxWhisper

**Defined:** 2026-02-15
**Core Value:** Hold a key, speak, text appears in the active window — fast, reliable, and works on any Linux display server.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Dictation

- [ ] **DICT-01**: User can hold hotkey to record and release to transcribe (push-to-talk)
- [x] **DICT-02**: User can press hotkey to start recording, press again to stop (toggle mode)
- [ ] **DICT-03**: Transcribed text appears in the active window automatically
- [ ] **DICT-04**: Dictation works on both X11 and Wayland (Hyprland, Sway, GNOME, KDE)

### Audio

- [ ] **AUDIO-01**: Audio captured from default microphone via PipeWire/PulseAudio
- [ ] **AUDIO-02**: Audio recorded in 16kHz mono format optimized for Whisper
- [ ] **AUDIO-03**: Voice Activity Detection auto-stops recording on silence (toggle mode)

### Transcription

- [ ] **TRANS-01**: Audio transcribed locally via faster-whisper with INT8 quantization
- [ ] **TRANS-02**: User can select Whisper model size (tiny, base, small, medium)
- [ ] **TRANS-03**: Whisper model stays loaded in memory via daemon (sub-500ms response)
- [ ] **TRANS-04**: Full sentence mode auto-capitalizes first word and adds period at end

### Input

- [ ] **INPUT-01**: Global hotkey detected via evdev (works on X11 and Wayland)
- [x] **INPUT-02**: User can configure hotkey binding (default: F13)
- [x] **INPUT-03**: Hotkey does not interfere with compositor or other application bindings

### Output

- [ ] **OUTPUT-01**: Text injected via ydotool on Wayland, xdotool on X11 (auto-detected)
- [ ] **OUTPUT-02**: Unicode and special characters handled correctly
- [ ] **OUTPUT-03**: Consecutive dictations separated by space

### System

- [ ] **SYS-01**: Background daemon with CLI start/stop/reload commands
- [ ] **SYS-02**: systemd user service for autostart and crash recovery
- [ ] **SYS-03**: System tray icon showing idle/recording/transcribing state
- [ ] **SYS-04**: Config file at ~/.config/linuxwhisper/config.toml

### Packaging

- [ ] **PKG-01**: AUR package with PKGBUILD for Arch-based distros
- [ ] **PKG-02**: Post-install instructions for input group and ydotool setup

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Voice Commands

- **VCMD-01**: User can say "period", "comma", "question mark" to insert punctuation
- **VCMD-02**: User can say "new line" or "new paragraph" for formatting
- **VCMD-03**: User can say "undo" to remove last dictated text

### Advanced Features

- **ADV-01**: Waveform visualization during recording
- **ADV-02**: AI post-processing for grammar/formatting cleanup via local LLM
- **ADV-03**: Multi-language support with language switching
- **ADV-04**: Custom voice command framework (user-defined shortcuts)
- **ADV-05**: Number conversion ("three hundred" to "300")
- **ADV-06**: Desktop notifications for transcription status

### GUI

- **GUI-01**: Settings dialog for configuration (GTK or Qt)
- **GUI-02**: Model download manager with progress indicator

## Out of Scope

| Feature | Reason |
|---------|--------|
| Cloud/API-based transcription | Local-only by design — privacy, offline, no ongoing costs |
| Real-time streaming transcription | Whisper architecture requires complete audio chunks, not streaming |
| Code dictation optimization | Optimized for prose/messages; code dictation is a different problem |
| Voice control / assistant commands | Different product category; stay focused on dictation |
| Mobile or non-Linux platforms | Linux desktop only |
| Clipboard paste mode | Direct text injection preferred; clipboard overwrites user data |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DICT-01 | Phase 2 | Pending |
| DICT-02 | Phase 3 | Complete |
| DICT-03 | Phase 2 | Pending |
| DICT-04 | Phase 6 | Pending |
| AUDIO-01 | Phase 4 | Pending |
| AUDIO-02 | Phase 4 | Pending |
| AUDIO-03 | Phase 4 | Pending |
| TRANS-01 | Phase 2 | Pending |
| TRANS-02 | Phase 5 | Pending |
| TRANS-03 | Phase 5 | Pending |
| TRANS-04 | Phase 5 | Pending |
| INPUT-01 | Phase 2 | Pending |
| INPUT-02 | Phase 3 | Complete |
| INPUT-03 | Phase 3 | Complete |
| OUTPUT-01 | Phase 2 | Pending |
| OUTPUT-02 | Phase 6 | Pending |
| OUTPUT-03 | Phase 6 | Pending |
| SYS-01 | Phase 1 | Pending |
| SYS-02 | Phase 7 | Pending |
| SYS-03 | Phase 7 | Pending |
| SYS-04 | Phase 1 | Pending |
| PKG-01 | Phase 8 | Pending |
| PKG-02 | Phase 8 | Pending |

**Coverage:**
- v1 requirements: 23 total
- Mapped to phases: 23
- Unmapped: 0

---
*Requirements defined: 2026-02-15*
*Last updated: 2026-02-15 after roadmap creation*
