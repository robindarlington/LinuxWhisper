# LinuxWhisper

Hold a key, speak, text appears in the active window. Local voice dictation for Linux that works on both X11 and Wayland.

LinuxWhisper uses OpenAI's Whisper model running entirely on your machine — no cloud API, no internet required for transcription. It runs as a background daemon, captures audio while you hold a hotkey, transcribes it locally, and types the result into whatever window is focused.

## Disclaimer

This project is **100% vibecoded** — built entirely with AI assistance to scratch my own itch. I needed voice dictation on Linux that actually works on Wayland, and nothing else fit the bill. It works on my machine (Arch + Hyprland). It might work on yours. Use at your own risk.

This is early-stage software. Expect rough edges, missing features, and the occasional "why does it do that?" moment.

## Features

- **Hold-to-talk dictation** — hold your hotkey, speak, release, text appears
- **Fully local transcription** — Whisper runs on your machine, nothing leaves your computer
- **X11 + Wayland support** — runtime detection, works on both display servers
- **CPU and GPU** — runs on CPU-only machines (tiny/base models) or takes advantage of NVIDIA GPUs
- **Background daemon** — starts once, stays out of your way
- **Configurable** — hotkey, model size, audio device, all via TOML config

## Requirements

- **OS:** Arch-based Linux distro (Arch, Manjaro, EndeavourOS, etc.)
- **Python:** 3.11+
- **Audio:** Working microphone accessible via PipeWire/PulseAudio
- **Text injection:** `ydotool` (Wayland) or `xdotool` (X11)
- **Permissions:** User must be in the `input` group (for hotkey detection via evdev)

## Installation

```bash
# Clone the repo
git clone https://github.com/robindarlington/linuxwhisper.git
cd linuxwhisper

# Create a virtual environment and install
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### System setup

```bash
# Add yourself to the input group (required for hotkey detection)
sudo usermod -aG input $USER

# Install and enable ydotool (Wayland text injection)
# Install via your package manager, then:
systemctl --user enable --now ydotool

# Log out and back in for group changes to take effect
```

## Usage

```bash
# Start the daemon
linuxwhisper start

# Check status
linuxwhisper status

# Stop the daemon
linuxwhisper stop

# Reload config without restarting
linuxwhisper reload
```

Once the daemon is running, hold your configured hotkey (default: `F13`), speak, and release. Your words will be typed into the active window.

### Running in foreground (for debugging)

```bash
python -m linuxwhisper
```

## Configuration

Config lives at `~/.config/linuxwhisper/config.toml`. The daemon uses sensible defaults — you only need a config file to override something.

```toml
# Hotkey to trigger dictation (evdev key name)
hotkey = "HOME"

# Dictation mode: "hold" (hold-to-talk)
mode = "hold"

# Whisper model: "tiny.en", "base.en", "small.en", "medium.en"
# Smaller = faster (good for CPU), larger = more accurate (good for GPU)
model = "base.en"

[audio]
sample_rate = 16000
channels = 1
# device = null  # Uses default audio device

[logging]
level = "INFO"
```

### Choosing a model

| Model | Size | Speed (CPU) | Best for |
|-------|------|-------------|----------|
| `tiny.en` | ~75 MB | Fastest | Quick notes, low-end hardware |
| `base.en` | ~150 MB | Fast | Daily use on CPU (recommended) |
| `small.en` | ~500 MB | Moderate | Better accuracy, mid-range hardware |
| `medium.en` | ~1.5 GB | Slow on CPU | High accuracy, GPU recommended |

## Project Status

LinuxWhisper is under active development. The core dictation pipeline (hold key, speak, get text) works. Many planned features are still in progress:

- [x] Daemon with CLI control (start/stop/reload/status)
- [x] Hold-to-talk hotkey detection (evdev)
- [x] Audio capture (sounddevice)
- [x] Local transcription (faster-whisper)
- [x] Text injection (ydotool for Wayland, xdotool for X11)
- [x] Pipeline state machine
- [ ] Toggle mode (press once to start, again to stop)
- [ ] Voice Activity Detection (auto-stop on silence)
- [ ] System tray icon with recording indicator
- [ ] Desktop notifications
- [ ] systemd user service
- [ ] AUR package

## Troubleshooting

**"Permission denied" on hotkey detection:**
Make sure you're in the `input` group: `groups $USER` should include `input`. Log out and back in after adding.

**ydotool not working:**
Ensure the service is running: `systemctl --user status ydotool`. The service name is `ydotool` (not `ydotoold`).

**Text not appearing in focused window:**
On Wayland, make sure `ydotool` is installed and its user service is enabled. On X11, make sure `xdotool` is installed.

**Daemon won't start:**
Check if it's already running with `linuxwhisper status`. Check permissions on `/dev/uinput` — you may need `sudo chmod 0660 /dev/uinput` until proper udev rules are set up.

## License

MIT

## Contributing

This is a personal project built to solve my own problem. Issues and PRs are welcome, but set your expectations accordingly — I may be slow to respond, and the codebase is entirely vibecoded.
