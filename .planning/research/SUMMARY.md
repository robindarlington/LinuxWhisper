# Project Research Summary

**Project:** LinuxWhisper
**Domain:** Linux Desktop Voice Dictation
**Researched:** 2026-02-15
**Confidence:** MEDIUM-HIGH

## Executive Summary

LinuxWhisper is a Linux desktop voice dictation tool targeting Wayland/Hyprland environments with CPU-first optimization. Expert implementations reveal that modern dictation on Linux requires three architectural pillars: (1) daemon-first architecture keeping Whisper models loaded in memory for sub-500ms response times, (2) kernel-level input handling via evdev/uinput to bypass Wayland's input restrictions, and (3) display-server agnostic design supporting both X11 and Wayland through runtime detection.

The recommended approach uses faster-whisper (CTranslate2-optimized, 4x faster than OpenAI Whisper) with INT8 quantization for CPU efficiency, evdev for global hotkey detection (the only reliable method on Wayland), and ydotool for text injection via /dev/uinput. This stack avoids the fatal mistakes of competitor tools: subprocess Whisper calls causing 5-10 second latency, xdotool-only implementations failing on native Wayland apps, and PyAudio/sounddevice incompatibility with PipeWire. Critical validation must happen in Phase 1 to avoid architectural rewrites.

The primary risks are Wayland input injection architecture mismatches (wtype fails on GNOME/KDE, only ydotool via uinput works universally) and Unicode/keyboard layout assumptions (xdotool breaks with non-US layouts and emoji). These pitfalls are discovered too late in most projects — testing must include native Wayland applications (Firefox, not terminal), non-ASCII text (café, 中文, 🎉), and PipeWire audio capture on Arch. The daemon architecture with pre-loaded models is non-negotiable; refactoring from subprocess approach requires complete rewrite and is the difference between 300ms and 10-second response times.

## Key Findings

### Recommended Stack

The research converges on a Wayland-native, display-server agnostic stack using kernel-level APIs (evdev, uinput) to bypass compositor restrictions. This approach works on both X11 and Wayland with a single codebase, avoiding the fragmentation plague affecting other Linux dictation tools.

**Core technologies:**
- **faster-whisper 1.2.1+** — Speech-to-text engine using CTranslate2 optimization, 4x faster than OpenAI Whisper with INT8 quantization support for CPU efficiency. Industry standard for offline transcription in 2025.
- **python-evdev 1.9.3+** — Global hotkey detection via kernel-level /dev/input reading. The ONLY reliable method on Wayland since desktop portals remain unimplemented by major compositors (GNOME, wlroots/Hyprland).
- **ydotool 1.0.0+** — Text injection via /dev/uinput. Display-server agnostic, works on both X11 and Wayland where wtype fails (GNOME, KDE). Requires ydotoold daemon and input group membership.
- **pipewire_python** — Direct PipeWire audio capture avoiding PortAudio compatibility issues. Fallback to pasimple (PulseAudio Simple API) for older systems. sounddevice/PyAudio fail on modern distros due to PortAudio 19.7.0 missing PulseAudio hostapi.

**Critical version requirements:**
- Python 3.9+ (faster-whisper minimum, 3.10+ recommended)
- PipeWire 0.3+ for modern Arch systems
- Linux kernel 2.6.36+ for uinput support

**Stack risks identified:**
- pystray unmaintained (no updates since Sept 2023) — defer system tray to Phase 2+, evaluate Qt alternatives
- pipewire_python less mature than sounddevice but necessary for PipeWire compatibility
- ydotool requires daemon setup (ydotoold) — document in AUR post-install

### Expected Features

Research reveals clear feature tiers based on competitor analysis (nerd-dictation, TalkType, VOXD, Speech Note) and user expectations for dictation tools in 2026.

**Must have (table stakes):**
- Push-to-talk hotkey (industry standard, all major tools support)
- System-wide text injection (works anywhere, not just specific apps)
- Offline/local processing (privacy — users refuse cloud transcription)
- Basic punctuation commands ("period", "comma" → symbols)
- Configurable hotkeys (avoid conflicts with compositor bindings)
- Wayland AND X11 support (non-negotiable on Linux)
- Model selection (tiny/small/medium — hardware flexibility)
- Basic visual feedback (recording state indicator)

**Should have (competitive advantage):**
- Toggle mode (click-start, click-stop vs hold-to-talk) — user preference differentiator
- Daemon architecture (fast response, model loaded in memory) — differentiates from competitors
- CPU-first optimization (INT8 quantization, thread tuning) — broader hardware support
- Voice Activity Detection (auto-detect speech end) — enhances toggle mode
- Hyprland-native support (PipeWire + compositor integration) — project-specific

**Defer to v2+:**
- Voice commands for editing ("undo last word", "new paragraph")
- Waveform UI during recording (visual polish)
- AI post-processing (LLM cleanup adds 1-3 sec latency)
- Multi-language support (each model 75MB-3GB disk)
- Custom command framework (advanced extensibility)

**Explicitly exclude (anti-features):**
- Real-time streaming transcription (Whisper requires chunk processing, adds complexity for marginal gain)
- Cloud API support (defeats privacy value proposition)
- GUI-first design (daemon + CLI serves power users better)
- Voice control/assistant features (different product domain, scope creep)

### Architecture Approach

Standard Linux voice dictation architecture uses an event-driven state machine with asyncio coordination, processing audio through a pipeline (capture → VAD → transcription → injection) while maintaining clean separation between platform-specific backends (X11/Wayland, PipeWire/PulseAudio).

**Major components:**
1. **Hotkey Monitor** — evdev reads /dev/input/eventX devices, detects global hotkey press/release. User must be in input group for permissions. Async event handler prevents blocking.
2. **State Machine** — Manages idle/recording/transcribing states. Supports both hold-to-talk (press starts, release stops) and toggle mode (press toggles recording on/off). Callbacks trigger audio capture and transcription pipeline.
3. **Audio Capture** — Subprocess-based recording using parecord (PulseAudio/PipeWire compatibility) or arecord (ALSA fallback). Outputs 16kHz mono 16-bit PCM WAV format required by Whisper. Lifecycle management critical (terminate + wait).
4. **Transcription Engine** — faster-whisper wrapper running in thread pool to avoid blocking event loop. Model loaded once at daemon startup (2-3 seconds cold start), kept in memory for sub-500ms transcription. INT8 quantization for CPU efficiency.
5. **Text Injector** — Hardware abstraction layer with runtime display server detection. X11 path uses xdotool (widely available), Wayland path uses ydotool via /dev/uinput (bypasses virtual-keyboard protocol limitations).
6. **Daemon Process** — systemd user service (Type=notify) keeps model loaded, exposes control via CLI commands. Graceful shutdown on SIGTERM/SIGINT. XDG_RUNTIME_DIR required for audio session access.

**Key architectural patterns:**
- Event-driven state machine prevents race conditions between audio capture and hotkey monitoring
- Pipeline processing with asyncio queues decouples capture (real-time) from transcription (batch)
- Hardware abstraction layer enables single codebase for X11/Wayland, PipeWire/PulseAudio
- Daemon-first architecture with systemd integration provides always-available service, automatic recovery

**Critical implementation notes:**
- Whisper transcription must run in thread pool (`loop.run_in_executor()`) to avoid blocking event loop
- Audio recording subprocess requires proper cleanup (terminate + wait) to avoid zombie processes and file corruption
- Display server detection via environment variables ($WAYLAND_DISPLAY, $DISPLAY) with graceful fallback
- evdev keyboard detection must validate device capabilities (check for KEY_A presence) before grabbing

### Critical Pitfalls

Research identified six critical pitfalls that break core functionality if not addressed in Phase 1. Most competitor tools fail due to discovering these too late.

1. **Wayland Input Injection Architecture Mismatch** — wtype fails on GNOME (no virtual-keyboard-unstable-v1 protocol) and KDE (no zwp_virtual_keyboard_v1). Text appears in XWayland windows only, not native Wayland apps like Firefox/Chrome. AVOID: Use ydotool via /dev/uinput (kernel-level, bypasses Wayland restrictions). Test on native Wayland apps (Firefox), not terminals (XWayland). Document per-compositor limitations.

2. **Whisper Model Cold Start Latency** — Loading model on each request takes 5-10 seconds (SHA256 hash check, CUDA init). Users think app is broken on first use. AVOID: Daemon architecture with model pre-loaded in memory. Use faster-whisper with INT8 quantization. This is non-negotiable — subprocess approach creates unfixable UX problem.

3. **evdev Permissions and Exclusive Grab Conflicts** — /dev/input requires input group membership. Exclusive grab breaks compositor hotkeys, wrong device selection (keyboards expose multiple event nodes). AVOID: udev rules for input group (not root), non-exclusive grab first, validate device capabilities (KEY_A presence), InputDevice.grab_context() for cleanup.

4. **Unicode and Special Character Text Injection Failures** — xdotool assumes US keyboard layout and ASCII, breaks with emoji/accented chars/CJK. "/" types as "q" on non-US layouts. AVOID: Test with café, 中文, 🎉, Arabic/Hebrew early. Use keysym mapping or clipboard fallback for problematic characters. Query active keyboard layout before injection.

5. **Audio Capture Reliability Across PipeWire/PulseAudio** — PyAudio/sounddevice fail on PipeWire due to PortAudio 19.7.0 missing PulseAudio hostapi. Device enumeration returns empty list or captures silence. systemd services lack XDG_RUNTIME_DIR for audio session. AVOID: Use pipewire_python or pasimple, not sounddevice/PyAudio. Test on Arch (PipeWire default) and Ubuntu (PulseAudio). Ensure XDG_RUNTIME_DIR in systemd service environment.

6. **AUR PKGBUILD Missing Transitive Dependencies** — Package works on dev system (has dependencies from other packages) but fails on clean install. AVOID: List all direct dependencies even if transitive. Use namcap to analyze. Test in clean chroot (systemd-nspawn), not local system. Distinguish depends/makedepends/optdepends correctly.

**Phase 1 validation requirements:**
- Text injection must work in Firefox (native Wayland), not just terminal
- First-run transcription <2 seconds from hotkey release (model pre-loaded)
- Install on fresh Arch without root, hotkey detection works (udev rules correct)
- Dictate "café 🎉 中文" and verify exact output (Unicode support)
- Audio capture works on both Arch (PipeWire) and Ubuntu (PulseAudio)

## Implications for Roadmap

Based on dependency analysis and pitfall prevention, the roadmap should prioritize architectural validation before feature expansion. The critical path is daemon architecture → input/output abstraction → system integration → packaging.

### Phase 1: Core Dictation Pipeline (daemon + hotkey + audio + Whisper + injection)

**Rationale:** All critical architectural decisions and pitfalls converge here. Daemon architecture is non-negotiable (cannot refactor from subprocess later). Input injection method must be correct from day one (Wayland restrictions). Unicode and keyboard layout support cannot be retrofitted without rewriting injection layer.

**Delivers:** Working end-to-end dictation — press F13, speak, release, text appears in active window. Sub-500ms latency with model pre-loaded. Works on both X11 and Wayland sessions. Supports non-ASCII text and non-US keyboard layouts.

**Addresses features:**
- Push-to-talk hotkey (table stakes)
- Offline Whisper transcription (table stakes)
- System-wide text injection (table stakes)
- Daemon architecture (differentiator)
- X11 + Wayland support (table stakes)
- Basic visual feedback (desktop notification)

**Avoids pitfalls:**
- Wayland input injection (test ydotool on native apps)
- Whisper cold start (daemon with model pre-loaded)
- evdev permissions (udev rules, input group)
- Unicode support (test café, emoji, CJK)
- Audio capture PipeWire (test on Arch)

**Implementation components:**
1. Config management (JSON, TOML fallback)
2. Daemon process (asyncio event loop, systemd integration)
3. Hotkey monitor (evdev, device detection, grab management)
4. State machine (idle/recording/transcribing, hold-to-talk mode)
5. Audio capture (parecord subprocess, 16kHz mono WAV)
6. Transcription engine (faster-whisper, thread pool execution, INT8 quantization)
7. Text injector (display server detection, ydotool for Wayland, xdotool for X11)
8. Desktop notifications (libnotify, optional)

**Research flag:** SKIP — architecture patterns are well-documented from competitor analysis (nerd-dictation, VOXD, whisper-overlay). Implementation is straightforward, focus on validation testing.

### Phase 2: Toggle Mode + Voice Punctuation

**Rationale:** Phase 1 delivers hold-to-talk. Toggle mode (press-to-start, press-to-stop) requires state machine modification but leverages existing components. Voice punctuation ("period" → ".") is simple text replacement, low complexity differentiator.

**Delivers:** User choice between hold and toggle modes. Basic voice commands for punctuation. Configurable hotkeys to avoid compositor conflicts.

**Addresses features:**
- Toggle mode (differentiator)
- Basic voice punctuation (table stakes)
- Configurable hotkeys (table stakes)

**Uses stack elements:**
- State machine (extend for toggle logic)
- Existing Whisper transcription (post-process text)

**Implements architecture:**
- State machine enhancement (mode toggle, timeout handling)
- Command detection in transcript (regex replacement)

**Research flag:** SKIP — standard patterns, no new technical challenges.

### Phase 3: Voice Activity Detection (VAD) + Model Selection

**Rationale:** VAD enhances toggle mode (auto-detect speech end) and improves transcription quality. Model selection provides hardware flexibility (tiny for weak CPUs, medium for GPUs). Both features integrate with existing Whisper engine.

**Delivers:** Auto-stop on silence (toggle mode). User-configurable model (tiny/small/medium). Better transcription quality through silence filtering.

**Addresses features:**
- Voice Activity Detection (differentiator)
- Model selection (table stakes)

**Uses stack elements:**
- faster-whisper built-in VAD (Silero, vad_filter=True)
- Model manager (download on-demand, cache management)

**Implements architecture:**
- VAD integration in transcription engine
- Model download/selection UI or config
- Hardware detection (CPU vs GPU) for model recommendation

**Research flag:** MINOR — VAD parameters may need tuning based on real-world testing. faster-whisper documentation adequate.

### Phase 4: System Integration + AUR Packaging

**Rationale:** Phases 1-3 deliver functional tool. Phase 4 makes it production-ready for Arch users with proper systemd integration, CLI control, and AUR distribution.

**Delivers:** systemd user service, CLI commands (start/stop/config), AUR package, installation documentation.

**Addresses:**
- System integration (service management)
- AUR distribution (user requested)
- Production deployment

**Avoids pitfalls:**
- systemd service environment (XDG_RUNTIME_DIR, session variables)
- AUR missing dependencies (namcap validation, clean chroot testing)

**Implementation components:**
1. systemd service file (Type=notify, user service, Restart=on-failure)
2. CLI interface (click framework, daemon control commands)
3. PKGBUILD (dependencies, build method, post-install message)
4. Installation documentation (udev rules, input group, ydotoold setup)

**Research flag:** SKIP — AUR packaging is well-documented in Arch Wiki. systemd user services are standard pattern.

### Phase 5: Advanced Features (defer to v1.x)

**Rationale:** Voice commands, waveform UI, AI post-processing, multi-language support are competitive features but not essential for launch. Defer until core functionality validated by users.

**Delivers:** Editing commands ("undo", "new paragraph"), visual audio feedback, LLM cleanup, language switching.

**Research flag:** NEEDED — Each feature requires deeper research during planning:
- Voice commands need window text manipulation research (accessibility APIs, clipboard tricks)
- Waveform UI needs overlay window research (GTK4, Qt)
- AI post-processing needs local LLM integration research (llama.cpp, Ollama)
- Multi-language needs model management research (download UI, disk usage)

### Phase Ordering Rationale

- **Phase 1 first** because all architectural decisions (daemon vs subprocess, ydotool vs wtype, evdev permissions) are irreversible. Discovering pitfalls in Phase 2+ requires complete rewrites.
- **Phase 2 extends Phase 1** with minimal new code (state machine mode, regex replacement). Quick win for user preference feature.
- **Phase 3 optimizes Phase 1** with existing faster-whisper capabilities (VAD, model selection). No new external dependencies.
- **Phase 4 production-izes Phases 1-3** without changing functionality. Clean separation between development and deployment concerns.
- **Phase 5 deferred** because features require significant research and implementation but aren't differentiators (other tools already have them). Focus on core reliability first.

**Dependency chain:**
```
Phase 1 (daemon + core pipeline)
    ↓
Phase 2 (toggle mode, punctuation) — depends on Phase 1 state machine
    ↓
Phase 3 (VAD, models) — depends on Phase 1 Whisper engine
    ↓
Phase 4 (systemd, AUR) — depends on Phases 1-3 working
    ↓
Phase 5 (advanced features) — independent additions
```

### Research Flags

**Phases needing deeper research during planning:**
- **Phase 5 (Voice Commands):** Window text manipulation requires research into accessibility APIs (AT-SPI), clipboard tricks, or compositor-specific methods. Sparse documentation.
- **Phase 5 (Waveform UI):** Real-time audio visualization overlay needs research into GTK4/Qt overlay windows, PipeWire stream tapping, rendering performance.
- **Phase 5 (AI Post-Processing):** Local LLM integration requires research into llama.cpp Python bindings, Ollama API, prompt engineering for transcription cleanup.
- **Phase 5 (Multi-Language):** Model management UX needs research — download UI, disk space monitoring, language auto-detection feasibility.

**Phases with standard patterns (skip research-phase):**
- **Phase 1 (Core Pipeline):** Well-documented in competitor projects (nerd-dictation, VOXD, whisper-overlay). Architecture patterns clear from research.
- **Phase 2 (Toggle Mode):** State machine modification is standard CS pattern. Regex text replacement trivial.
- **Phase 3 (VAD/Models):** faster-whisper documentation covers both features. Community examples available.
- **Phase 4 (System Integration):** Arch Wiki has comprehensive systemd/AUR guidance. Established patterns.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | faster-whisper, evdev, ydotool all verified with official docs and real-world projects (whisper-overlay). PipeWire audio path medium confidence (pipewire_python less mature). |
| Features | HIGH | Feature landscape validated across 7+ competitor tools (nerd-dictation, TalkType, VOXD, Speech Note, OpenWhispr) with consistent patterns. User expectations clear. |
| Architecture | HIGH | Standard daemon + event loop + pipeline patterns documented in multiple reference implementations. Component boundaries well-defined. |
| Pitfalls | MEDIUM | Critical pitfalls verified with issue trackers and forum discussions, but some based on inference from user reports rather than direct documentation. Need Phase 1 validation. |

**Overall confidence:** MEDIUM-HIGH

Research is solid for core functionality (Phases 1-3). Stack choices are proven, architecture patterns are established, and pitfalls are well-documented in competitor projects. Medium confidence areas are newer technologies (pipewire_python, ydotool stability) and advanced features (Phase 5) requiring deeper research during planning.

### Gaps to Address

**During Phase 1 planning:**
- Exact evdev device selection algorithm needs hands-on testing — research shows multiple event nodes per keyboard, need heuristic to pick correct one
- ydotool daemon (ydotoold) setup steps — research mentions it but details sparse. Need to document exact systemd service requirements
- PipeWire vs PulseAudio detection fallback logic — research identifies issue but implementation details unclear. May need runtime probing
- Keyboard layout detection method — research identifies problem but solution vague. Need Hyprland-specific `hyprctl` commands

**During Phase 3 planning:**
- VAD parameter tuning for dictation (vs transcription) — research mentions Silero VAD but optimal min_silence_duration_ms unclear for short phrases
- Model download UX — faster-whisper auto-downloads but progress feedback requires research into download hooks

**During Phase 5 planning:**
- Window text manipulation approach — accessibility APIs vs clipboard vs compositor-specific (Hyprland IPC). Requires hands-on research
- Local LLM selection criteria — llama.cpp vs Ollama vs other. Model size vs quality tradeoffs for transcription cleanup

**Validation needed (cannot be resolved from research alone):**
- Actual latency on target hardware (Hyprland + CPU-only) — research provides benchmarks but need real-world measurement
- Microphone quality impact on transcription accuracy — research assumes good audio, but cheap mics may require pre-processing
- Hotkey conflict detection with Hyprland bindings — need to query Hyprland config at runtime for conflict warnings

## Sources

### Primary (HIGH confidence)
- faster-whisper PyPI and GitHub — version requirements, CTranslate2 optimization, INT8 quantization, VAD support
- evdev PyPI and python-evdev documentation — device capabilities, grab management, async event loop
- Arch Wiki (PipeWire, PKGBUILD, systemd) — PipeWire on Arch, AUR packaging standards, systemd user services
- nerd-dictation GitHub — reference implementation, architecture patterns, VOSK comparison
- whisper-overlay GitHub — Wayland dictation with evdev + faster-whisper + GTK4
- VOXD GitHub — daemon architecture, VAD integration, systemd service patterns

### Secondary (MEDIUM confidence)
- TalkType, Speech Note, OpenWhispr GitHub repos — feature comparison, Whisper model selection, hotkey modes
- ydotool GitHub — uinput-based text injection, daemon requirements, Wayland compatibility
- Wayland protocol documentation — virtual-keyboard limitations, compositor variations
- Python asyncio documentation — event loop patterns, thread pool execution
- PipeWire/PulseAudio forums — audio capture issues, device detection, compatibility layer

### Tertiary (LOW confidence, needs validation)
- pystray maintenance status — inferred from release dates, no official abandonment statement
- ydotool JavaScript rewrite — mentioned in GitHub discussions, no concrete timeline
- wtype GNOME/KDE failures — user reports, not systematically verified
- Hyprland pass dispatcher details — limited documentation, unclear integration patterns

---
*Research completed: 2026-02-15*
*Ready for roadmap: yes*
