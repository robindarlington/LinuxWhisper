# Technology Stack

**Project:** LinuxWhisper
**Researched:** 2026-02-15
**Confidence:** MEDIUM-HIGH

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| faster-whisper | 1.2.1+ | Speech-to-text engine | 4x faster than OpenAI Whisper, CTranslate2-optimized, supports CPU inference with 8-bit quantization, VAD filtering included, no FFmpeg dependency (uses PyAV). Industry standard for offline transcription in 2025. |
| python-evdev | 1.9.3+ | Global hotkey detection | Direct kernel-level input via /dev/input, works on both X11 and Wayland, evdev is the ONLY reliable method for global hotkeys on Wayland (desktop portals not yet supported by major compositors). |
| ydotool | 1.0.0+ | Text input simulation | Only mature cross-platform solution for keyboard simulation on Wayland via uinput. Works on X11 and Wayland, display-server agnostic. Requires ydotoold daemon. |
| Python | 3.9+ | Runtime | Minimum for faster-whisper and evdev. Python 3.10+ recommended for performance improvements. |

### Audio Capture

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pipewire_python | Latest | Direct PipeWire audio capture | PRIMARY choice for Arch/modern distros. Direct PipeWire API, no PortAudio compatibility issues. Configurable sample rates/channels. |
| pasimple | Latest | PulseAudio Simple API | FALLBACK for older systems. Works with both PulseAudio and PipeWire. Simpler API than full PulseAudio bindings. |
| sounddevice | 0.5.5 | PortAudio-based capture | AVOID on PipeWire systems. PortAudio 19.7.0 lacks PulseAudio hostapi, causing device detection failures on modern distros. Only use if targeting older ALSA-only systems. |

### CLI and Configuration

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| click | 8.3.x+ | CLI framework | Command-line interface creation. Composable, well-documented, industry standard. Note: Dropped Python 3.7-3.9 support as of May 2025. |
| tomllib | stdlib | Configuration parsing | Read TOML config files. Built-in since Python 3.11. Use tomli for Python 3.9-3.10 compatibility. |
| python-daemon | 3.0+ | Daemon process management | OPTIONAL. Use systemd Type=simple instead for modern systems. Only needed if supporting non-systemd distros. |

### System Tray (Phase 2+)

| Library | Version | Purpose | Notes |
|---------|---------|---------|-------|
| pystray | 0.19.5 | System tray implementation | Cross-platform, GTK backend on Linux. WARNING: No updates since Sept 2023, may be unmaintained. Consider Qt alternative for long-term maintenance. |
| PyQt6/PySide6 | Latest | Qt-based tray (alternative) | More actively maintained. QSystemTrayIcon for tray. Heavier dependency but better Wayland support. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| pytest | Testing framework | Industry standard for Python testing |
| black | Code formatting | Opinionated formatter, zero-config |
| ruff | Linting | Fast Rust-based linter, replaces flake8/isort |
| mypy | Type checking | Optional but recommended for larger codebase |

## Installation

### Core Dependencies

```bash
# System packages (Arch/Manjaro)
sudo pacman -S python python-pip pipewire ydotool

# Enable ydotool daemon
systemctl --user enable --now ydotoold.service

# Python packages
pip install faster-whisper==1.2.1 evdev pipewire_python click

# Fallback audio (if pipewire_python unavailable)
pip install pasimple
```

### Optional Dependencies

```bash
# System tray (Phase 2+)
pip install pystray pillow

# Or Qt-based alternative
pip install PyQt6

# Development
pip install -e ".[dev]"  # pytest, black, ruff, mypy
```

## Alternatives Considered

| Category | Recommended | Alternative | Why Not Alternative |
|----------|-------------|-------------|---------------------|
| Speech Engine | faster-whisper | whisper.cpp + Python bindings | faster-whisper is more Pythonic, CTranslate2 optimized specifically for Whisper architecture. whisper.cpp bindings often outdated/broken. Performance similar on CPU, faster-whisper better for Python integration. |
| Speech Engine | faster-whisper | OpenAI whisper | 4x slower, requires FFmpeg installation, same accuracy. No production use case for original implementation. |
| Speech Engine | faster-whisper | Nerd Dictation (VOSK) | VOSK models significantly less accurate than Whisper. Nerd Dictation is a good reference implementation but VOSK is outdated for 2025. |
| Audio Capture | pipewire_python | sounddevice | PortAudio lacks PulseAudio/PipeWire support in current versions. sounddevice fails device detection on modern distros. |
| Audio Capture | pipewire_python | PyAudio | Same PortAudio issues as sounddevice. More complex API with no benefits for this use case. |
| Hotkey Detection | evdev | Wayland GlobalShortcuts portal | Portal not implemented by GNOME or wlroots compositors as of 2025. evdev is only reliable method. |
| Hotkey Detection | evdev | Hyprland pass dispatcher | Hyprland-specific, not portable. Use evdev for cross-compositor compatibility. |
| Text Input | ydotool | xdotool | xdotool X11-only. Project requirement is Wayland support. |
| Text Input | ydotool | wl-clipboard + Ctrl+V | Unreliable clipboard race conditions. Overwrites user clipboard. ydotool types directly. |
| CLI Framework | click | argparse | click more composable, better help text generation, type coercion built-in. argparse adequate but more verbose. |
| Config Format | TOML | JSON/YAML | TOML designed for config files, better human-editability. Native stdlib support (tomllib). |
| System Tray | pystray (defer decision) | systray alternatives | Evaluate during Phase 2. pystray unmaintained risk, Qt more active but heavier. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| sounddevice/PyAudio on PipeWire | PortAudio 19.7.0 missing PulseAudio hostapi causes device detection failures on Arch-based distros | pipewire_python or pasimple |
| Wayland desktop portals for hotkeys | GlobalShortcuts portal unsupported by major compositors (GNOME, wlroots/Hyprland) as of 2025 | evdev with /dev/input access |
| xdotool | X11-only, project requires Wayland support | ydotool |
| python-daemon | Systemd Type=simple is simpler and more integrated on target platform (Arch) | Direct systemd service file |
| OpenAI whisper package | 4x slower than faster-whisper with no accuracy benefit | faster-whisper |
| VOSK models | Significantly lower accuracy than Whisper models, outdated for 2025 | faster-whisper |
| whisper.cpp Python bindings | Often broken/outdated, complex build process, minimal benefit over faster-whisper on CPU | faster-whisper |

## Stack Patterns by Variant

### CPU-Only Deployment (PRIMARY TARGET)

```bash
pip install faster-whisper==1.2.1
# Use tiny.en or base.en models
# 8-bit quantization: int8, int8_float32
```

**Rationale:**
- faster-whisper supports efficient CPU inference via CTranslate2
- 8-bit quantization reduces memory and improves speed on CPU
- tiny/base models sufficient for dictation (vs transcription)

### GPU Deployment (OPTIONAL)

```bash
pip install faster-whisper==1.2.1
# Requires CUDA 12 + cuDNN 9 (or CUDA 11 + cuDNN 8 with ctranslate2==3.24.0)
# Use small.en or medium.en models
```

**Rationale:**
- faster-whisper has excellent GPU support
- larger models viable with GPU acceleration
- ctranslate2 version pinning required for CUDA 11 systems

### Wayland-Only Deployment (HYPRLAND PRIMARY)

```bash
# Minimal dependencies, no X11 fallbacks needed
pip install evdev pipewire_python faster-whisper click
sudo pacman -S ydotool pipewire
```

**Rationale:**
- evdev works on both X11/Wayland, no need for dual implementations
- ydotool Wayland-native via uinput
- pipewire_python direct PipeWire API

### X11 Compatibility (LOWER PRIORITY)

```bash
# Same stack works on X11
# evdev reads kernel input, display-server agnostic
# ydotool uses uinput, works on X11/Wayland/console
```

**Rationale:**
- Chosen stack is display-server agnostic by design
- No special X11 packages needed
- Architecture supports both with single codebase

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| faster-whisper 1.2.1 | Python 3.9+ | Requires ctranslate2 (auto-installed). CUDA 12 + cuDNN 9 for GPU. |
| evdev 1.9.3 | Python 3.9+ | Linux kernel 2.6.36+ for uinput. Binary wheels available via evdev-binary. |
| pipewire_python | PipeWire 0.3+ | May require manual installation on some distros. |
| ydotool 1.0.0+ | Linux kernel with uinput | Requires ydotoold daemon running. Install via AUR: ydotool-bin or ydotool-git. |
| click 8.3.x | Python 3.8+ | Dropped 3.7-3.9 support in May 2025, but 3.9 still works in practice. |

## Packaging for AUR

### Package Structure

```
PKGBUILD                    # Package build script
.SRCINFO                    # Generated metadata (makepkg --printsrcinfo)
linuxwhisper.service        # Systemd user service
linuxwhisper.install        # Post-install instructions
```

### PKGBUILD Best Practices

**Naming:**
- Package name: `linuxwhisper` (application name, lowercase)
- Not `python-linuxwhisper` (reserved for library packages)

**Dependencies:**
```bash
depends=('python>=3.9' 'python-pip' 'pipewire' 'ydotool')
makedepends=('python-build' 'python-installer' 'python-wheel')
optdepends=(
    'python-pyqt6: GUI system tray support'
    'cuda: GPU acceleration for faster-whisper'
)
```

**Build Method:**
```bash
# Use python-build + python-installer (modern standard)
build() {
    cd "$srcdir/$pkgname-$pkgver"
    python -m build --wheel --no-isolation
}

package() {
    cd "$srcdir/$pkgname-$pkgver"
    python -m installer --destdir="$pkgdir" dist/*.whl

    # Install systemd service
    install -Dm644 linuxwhisper.service \
        "$pkgdir/usr/lib/systemd/user/linuxwhisper.service"
}
```

**Source:**
```bash
# Use GitHub releases
source=("$pkgname-$pkgver.tar.gz::https://github.com/username/$pkgname/archive/v$pkgver.tar.gz")

# Or PyPI
source=("https://files.pythonhosted.org/packages/source/l/$pkgname/$pkgname-$pkgver.tar.gz")
```

**Post-Install Message:**
```bash
# linuxwhisper.install
post_install() {
    echo "Enable ydotool daemon:"
    echo "  systemctl --user enable --now ydotoold.service"
    echo ""
    echo "Add user to input group for evdev hotkey detection:"
    echo "  sudo usermod -aG input \$USER"
    echo "  (logout/login required)"
}
```

### Version Management

- `pkgver`: Upstream version (e.g., 0.1.0)
- `pkgrel`: Package release (reset to 1 on version bump, increment on PKGBUILD-only changes)
- Update `.SRCINFO` on every change: `makepkg --printsrcinfo > .SRCINFO`

### AUR Submission Workflow

```bash
# 1. Create AUR repository
git clone ssh://aur@aur.archlinux.org/linuxwhisper.git
cd linuxwhisper

# 2. Add files
cp /path/to/PKGBUILD .
makepkg --printsrcinfo > .SRCINFO
git add PKGBUILD .SRCINFO

# 3. Test locally
makepkg -si

# 4. Submit to AUR
git commit -m "Initial import: LinuxWhisper 0.1.0"
git push
```

## Stack Risks and Mitigations

### Risk 1: pystray Unmaintained (MEDIUM)

**Issue:** No updates since Sept 2023, potential abandonment.

**Mitigation:**
- Defer system tray to Phase 2+
- Evaluate alternatives during implementation: PyQt6 QSystemTrayIcon, AppIndicator3
- pystray still works, just lacks active development

### Risk 2: ydotool Rewrite (LOW)

**Issue:** Developer mentioned JavaScript rewrite in 2024.

**Mitigation:**
- Current C implementation stable and packaged in AUR
- Monitor project for breaking changes
- JavaScript version may improve issues, not create them
- Interface likely stable (uinput-based)

### Risk 3: evdev Requires Root/Input Group (MEDIUM)

**Issue:** /dev/input access requires input group membership or root.

**Mitigation:**
- Document in README and AUR post-install
- Standard practice for Linux input tools
- Alternative: udev rules, but input group is cleaner

### Risk 4: PipeWire API Stability (LOW)

**Issue:** pipewire_python may lag PipeWire updates.

**Mitigation:**
- pasimple as fallback (PulseAudio Simple API, stable)
- PipeWire maintains PulseAudio compatibility layer
- Monitor pipewire_python issues, consider contributing fixes

### Risk 5: faster-whisper CUDA Version Lock-in (LOW)

**Issue:** CUDA 12 required for latest ctranslate2, CUDA 11 requires version downgrade.

**Mitigation:**
- Primary target is CPU (no CUDA dependency)
- Document CUDA version requirements clearly
- Use optdepends in PKGBUILD for GPU support

## Sources

### Verified with Official Documentation

- [faster-whisper PyPI](https://pypi.org/project/faster-whisper/) - Version 1.2.1, requirements, features (HIGH confidence)
- [evdev PyPI](https://pypi.org/project/evdev/) - Version 1.9.3, Python requirements (HIGH confidence)
- [sounddevice PyPI](https://pypi.org/project/sounddevice/) - Version 0.5.5, dependencies (HIGH confidence)
- [click documentation](https://click.palletsprojects.com/) - Version 8.3.x, Python support changes (HIGH confidence)
- [Python TOML documentation](https://docs.python.org/3/library/tomllib.html) - stdlib support (HIGH confidence)
- [Arch Wiki: Python package guidelines](https://wiki.archlinux.org/title/Python_package_guidelines) - PKGBUILD best practices (HIGH confidence)
- [Arch Wiki: PipeWire](https://wiki.archlinux.org/title/PipeWire) - PipeWire on Arch Linux (HIGH confidence)

### Community Resources and Project Examples

- [whisper-overlay GitHub](https://github.com/oddlama/whisper-overlay) - Real-world Wayland dictation architecture using evdev, faster-whisper, GTK4 (MEDIUM confidence)
- [Nerd Dictation GitHub](https://github.com/ideasman42/nerd-dictation) - Reference implementation, VOSK-based (MEDIUM confidence)
- [ydotool GitHub](https://github.com/ReimuNotMoe/ydotool) - Wayland text input simulation (MEDIUM confidence)
- [pipewire_python PyPI](https://pypi.org/project/pipewire_python/) - Direct PipeWire bindings (MEDIUM confidence)
- [pasimple GitHub](https://github.com/henrikschnor/pasimple) - PulseAudio/PipeWire simple API (MEDIUM confidence)

### Web Search Findings

- [Python Audio Tools 2025](https://graphlogic.ai/blog/resources-tools/best-python-tools-audio-manipulation/) - sounddevice vs PyAudio comparison (MEDIUM confidence)
- [Wayland global hotkeys limitations](https://dec05eba.com/2024/03/29/wayland-global-hotkeys-shortcut-is-mostly-useless/) - Desktop portal status (MEDIUM confidence)
- [ydotool vs xdotool comparison](https://gadgeteer.co.za/ydotool-is-an-alternative-to-xdotool-that-works-on-both-x11-and-wayland/) - Cross-platform text input (MEDIUM confidence)
- [whisper.cpp vs faster-whisper analysis](https://www.alibaba.com/product-insights/a-practical-guide-to-choosing-between-whisper-cpp-and-faster-whisper-for-offline-transcription.html) - Performance comparison (MEDIUM confidence)
- [PortAudio PipeWire issue](https://github.com/spatialaudio/python-sounddevice/issues/609) - sounddevice compatibility problem (MEDIUM confidence)

### Low Confidence / Needs Validation

- pystray maintenance status - Based on release dates only, no official abandonment statement (LOW confidence)
- ydotool JavaScript rewrite - Mentioned in GitHub discussions but no concrete timeline (LOW confidence)
- Hyprland pass dispatcher details - Limited documentation for application integration (LOW confidence)

---

**Research Notes:**

This stack prioritizes **Wayland-native, display-server agnostic technologies** that work on both X11 and Wayland through kernel-level APIs (evdev, uinput). The choices reflect 2025 best practices for Linux desktop tools on Arch-based systems.

**Key architectural decisions:**
1. **faster-whisper over whisper.cpp**: Python ecosystem integration, CTranslate2 optimization, stable API
2. **evdev over desktop portals**: Only reliable global hotkey solution on Wayland (portals unsupported)
3. **ydotool over xdotool**: Wayland requirement, uinput-based, display-server agnostic
4. **pipewire_python over sounddevice**: Direct PipeWire API avoids PortAudio compatibility issues
5. **TOML over JSON/YAML**: Python 3.11+ stdlib, designed for configuration

**Confidence assessment:**
- Audio capture: MEDIUM (pipewire_python less mature than sounddevice, but necessary for PipeWire)
- Hotkey detection: HIGH (evdev is proven, only viable solution)
- Text input: HIGH (ydotool mature, widely used)
- Whisper integration: HIGH (faster-whisper industry standard)
- System tray: MEDIUM (pystray potentially unmaintained, needs Phase 2 evaluation)

**Gaps for later phases:**
- System tray implementation requires hands-on testing with pystray vs Qt
- GPU optimization needs hardware-specific benchmarking
- Hyprland-specific integration patterns (beyond standard Wayland)
