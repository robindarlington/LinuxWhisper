# LinuxWhisper

## What This Is

A Linux desktop voice dictation tool for Arch-based distros. The user holds a hotkey (or toggles it), speaks, and the transcribed text is typed into whatever window is currently focused. Uses OpenAI's Whisper model locally — no cloud API, no internet required for transcription. Targets both X11 and Wayland (Hyprland as primary Wayland compositor).

## Core Value

Hold a key, speak, text appears in the active window — fast, reliable, and works on any Linux display server.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Global hotkey triggers audio recording (hold-to-talk and toggle modes)
- [ ] Audio captured and transcribed locally via OpenAI Whisper
- [ ] Transcribed text typed into the active window automatically
- [ ] Works on both X11 and Wayland (Hyprland, Sway, GNOME Wayland, etc.)
- [ ] Configurable Whisper model size (tiny, base, small, medium)
- [ ] Hardware-aware model recommendation (CPU vs GPU detection)
- [ ] User-configurable hotkey binding (default: F13)
- [ ] Config file at ~/.config/linuxwhisper/config.json
- [ ] Background daemon with CLI configuration
- [ ] AUR package for installation on Arch-based distros
- [ ] System tray icon with recording state indicator (nice-to-have, phase 2)
- [ ] Desktop notifications for transcription status

### Out of Scope

- Cloud/API-based transcription — local-only by design
- Mobile or non-Linux platforms — Linux desktop only
- Code dictation optimization — optimized for prose/messages
- Real-time streaming transcription — record-then-transcribe model
- GUI settings dialog — CLI config is sufficient for v1

## Context

- **Target distros:** Arch-based (Arch, Manjaro, EndeavourOS, Omarchy)
- **Primary display server:** Hyprland (Wayland compositor), but must support X11 too
- **Hardware range:** Works on CPU-only machines (user's primary use case) up to NVIDIA GPU machines
- **Audio stack:** ALSA via arecord or ffmpeg for capture, 16kHz mono WAV optimized for Whisper
- **Text input challenge:** xdotool for X11, wtype/ydotool for Wayland — need runtime detection
- **Hotkey challenge:** pynput doesn't work on Wayland — evdev reads input devices directly, works everywhere but needs input group permissions
- **Use case:** Prose and messages — flowing natural language text, not code or commands
- **Latency goal:** As fast as possible. tiny/base models for CPU, larger models available for GPU users

## Constraints

- **Display server:** Must support both X11 and Wayland at runtime — auto-detect and use appropriate backend
- **Permissions:** evdev for hotkeys requires user in `input` group — document in install instructions
- **Python:** Use Python ecosystem (openai-whisper, evdev, pystray) — Whisper's native language
- **Packaging:** Must produce a working PKGBUILD for AUR distribution
- **No network:** Transcription must work fully offline after initial model download
- **Audio format:** 16kHz mono WAV — Whisper's expected input format

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Local Whisper only (no API) | Privacy, offline capability, no ongoing costs | — Pending |
| evdev for hotkey detection | Works on both X11 and Wayland unlike pynput | — Pending |
| Both hold-to-talk and toggle modes | User preference varies, toggle is easier on Wayland | — Pending |
| Daemon + CLI first, tray later | Reduces initial complexity, tray is nice-to-have | — Pending |
| AUR package distribution | Target audience is Arch users, proper packaging | — Pending |
| Auto-detect display server | Runtime detection of X11/Wayland for text input backend | — Pending |
| CPU-first optimization | User's machine is CPU-only, must be fast on base/tiny | — Pending |

---
*Last updated: 2026-02-14 after initialization*
