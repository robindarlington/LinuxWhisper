# Feature Research

**Domain:** Linux Desktop Voice Dictation
**Researched:** 2026-02-15
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Push-to-talk hotkey | Industry standard input method. All major tools (TalkType, Voxtype, nerd-dictation, VOXD) support this | LOW | Single hotkey press/release to record/transcribe |
| System-wide text injection | Users expect dictation anywhere, not just specific apps | MEDIUM | Requires uinput/ydotool for Wayland, xdotool for X11 |
| Offline/local processing | Privacy concern - users don't want voice sent to cloud | MEDIUM | Requires local model (Whisper/Vosk). Models 39MB-3GB |
| Basic punctuation support | Speaking "period", "comma", "question mark" is expected | LOW | Simple text replacement in post-processing |
| Auto-spacing | Automatic spaces between words is fundamental expectation | LOW | Built into most STT engines |
| Configurable hotkeys | Users need custom shortcuts to avoid conflicts | LOW | Standard keyboard binding mechanism |
| Basic visual feedback | Users need to know when recording is active | LOW | Icon change, notification, or simple indicator |
| Multiple input methods | Wayland AND X11 support is non-negotiable on Linux | HIGH | Must support ydotool/wtype (Wayland) + xdotool (X11) |
| Model selection | Users want to trade speed for accuracy based on hardware | MEDIUM | Tiny/small/medium/large model variants |
| Language model download | Large models can't be bundled - must download on-demand | MEDIUM | Model manager with download progress |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not expected, but valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Toggle mode (vs push-to-talk only) | Some users prefer click-to-start, click-to-stop workflow | LOW | State management + timeout handling |
| Voice Activity Detection (VAD) | Auto-detect speech end without timeout - VOXD's "flux mode" | MEDIUM | Requires VAD library (Silero VAD, WebRTC GMM) |
| CPU-first optimization | Most tools assume GPU. CPU optimization = broader hardware support | HIGH | Requires faster-whisper with int8 quantization, thread tuning |
| Daemon architecture | Fast response - model loaded in memory. Most tools reload each time | MEDIUM | Background service + IPC for client communication |
| Hyprland-native support | Specific Wayland compositor support is rare - hyprvoice differentiates here | MEDIUM | PipeWire audio capture + compositor-specific integration |
| Voice commands for editing | "undo last word", "new paragraph" - TalkType feature | MEDIUM | Command detection + text manipulation in active window |
| Custom command framework | Let users define their own voice shortcuts - nerd-dictation's Python config | HIGH | Scriptable processing pipeline |
| AI post-processing | LLM cleanup of transcripts for grammar/formatting - VOXD's AIPP feature | HIGH | Requires local LLM integration (llama.cpp/Ollama) |
| Waveform UI during recording | Visual audio feedback - turbo-whisper, whisper-dictation, wisper | MEDIUM | Real-time audio visualization + overlay window |
| Session persistence (suspend/resume) | Keep model in memory when paused - nerd-dictation feature for slow CPUs | LOW | State management without full teardown |
| Smart quotes | Convert straight quotes to curly - TalkType feature | LOW | Post-processing text transformation |
| Number conversion | "three hundred twenty one" → "321" - nerd-dictation --numbers-as-digits | MEDIUM | NLP number parsing logic |
| Full sentence mode | Auto-capitalize first word, add period at end - nerd-dictation --full-sentence | LOW | Simple text transformation |
| Clipboard output mode | Alternative to keystroke simulation for speed - OpenWhispr fallback | LOW | Copy to clipboard instead of typing |
| Multi-language support | Switch languages without restart - Speech Note supports 100+ | MEDIUM | Multiple model downloads + language selector |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Real-time streaming transcription | Users want to see words appear as they speak | Whisper is NOT real-time - requires chunk processing. Streaming adds complexity for marginal UX gain. Leads to correction flicker | Optimize chunk latency (<500ms). Show waveform during recording, then fast insert |
| Cloud API support | "Just use OpenAI API for better accuracy" | Defeats core value prop (privacy, offline). Adds API key management, costs, network dependency | Invest in local model quality. Use faster-whisper optimizations |
| GUI-first design | Non-technical users want point-and-click setup | Increases maintenance burden for feature that doesn't serve core use case. Daemon + CLI serves power users better | Simple config file + good defaults. Tray icon for status only |
| Automatic capitalization everywhere | "Why doesn't it capitalize 'I' and sentence starts?" | Context-dependent. Hard to get right. VOSK models output lowercase. Post-processing adds latency | Let users add custom word mappings in config. Use --full-sentence mode for simple cases |
| Voice control (commands like "open Firefox") | Users conflate dictation with voice assistant | Scope creep. Different problem domain. Requires intent detection, desktop automation | Stay focused on dictation. Users can use other tools for commands |
| Recording file export | "Save my audio for later transcription" | Not the use case (live dictation). Adds file management complexity | Recommend dedicated recording tools for archival |
| Multiple simultaneous languages | "Switch languages mid-sentence" | Models are language-specific. Auto-detection is slow/unreliable. Adds complexity for rare use case | Support quick language switch via hotkey. One language per session |
| Perfect punctuation | Users expect AI to add all punctuation automatically | Whisper doesn't do this reliably. Third-party LLM post-processing is slow and changes meaning | Voice punctuation commands. Optional AI cleanup as explicit user action |

## Feature Dependencies

```
Core Engine
    ├──requires──> Whisper/faster-whisper (STT model)
    └──requires──> Audio Capture (PipeWire/PulseAudio)

System-wide Injection
    ├──requires──> uinput permissions
    └──requires──> ydotool/wtype (Wayland) OR xdotool (X11)

Daemon Mode
    ├──requires──> Core Engine (must keep model loaded)
    ├──requires──> IPC mechanism (Unix socket/DBus)
    └──enables──> Fast response time (<500ms)

Toggle Mode
    ├──requires──> Voice Activity Detection (silence timeout)
    └──conflicts──> Pure push-to-talk (different state machine)

Voice Activity Detection (VAD)
    ├──enhances──> Toggle Mode (auto-stop on silence)
    └──requires──> VAD library (Silero/WebRTC)

Voice Commands
    ├──requires──> Command detection in transcript
    ├──requires──> Text manipulation in target window
    └──enhances──> Basic dictation (editing capability)

AI Post-Processing
    ├──requires──> Local LLM (llama.cpp/Ollama)
    ├──requires──> Async processing (user confirmation)
    └──conflicts──> Real-time dictation (adds latency)

Waveform UI
    ├──requires──> Audio stream access
    ├──requires──> Overlay window rendering
    └──enhances──> User feedback

Multi-Language
    ├──requires──> Multiple model downloads
    ├──requires──> Language selector UI
    └──increases──> Disk usage significantly

Custom Commands
    ├──requires──> Scriptable processing pipeline
    └──enables──> User extensibility
```

### Dependency Notes

- **System-wide Injection requires uinput permissions:** This is a critical setup step. Without /dev/uinput access, Wayland support fails
- **Daemon Mode enables Fast response time:** Loading Whisper models takes 2-5 seconds. Daemon keeps model in memory for sub-500ms response
- **Toggle Mode conflicts with Pure push-to-talk:** Different state machines. Can support both with mode toggle, but code complexity increases
- **AI Post-Processing conflicts with Real-time dictation:** LLM processing adds 1-3 seconds. Should be explicit user action, not automatic
- **Multi-Language increases disk usage:** Each language model is 75MB-3GB. Supporting 10 languages = 5-30GB disk

## MVP Recommendation

Prioritize:
1. **Push-to-talk hotkey** - Core interaction model (LOW complexity)
2. **Offline Whisper (faster-whisper)** - Privacy + core capability (MEDIUM complexity)
3. **System-wide injection (ydotool/xdotool)** - Works anywhere (MEDIUM complexity)
4. **Daemon architecture** - Fast response, keeps model loaded (MEDIUM complexity)
5. **Basic voice punctuation** - "period", "comma" commands (LOW complexity)
6. **X11 + Wayland support** - Both environments required (HIGH complexity)
7. **Model selection (tiny/small/medium)** - Hardware flexibility (MEDIUM complexity)
8. **Toggle mode** - User preference differentiator (LOW complexity)
9. **Configurable hotkeys** - Avoid keybind conflicts (LOW complexity)
10. **Basic visual feedback** - Tray icon with recording state (LOW complexity)

**Defer to v1.x:**
- Voice Activity Detection (VAD) - Nice to have, but timeout-based toggle works
- Voice commands (undo, new paragraph) - Power user feature
- Waveform UI - Visual polish, not core function
- AI post-processing - Scope creep, adds complexity
- Multi-language - Most users need 1-2 languages max
- Custom command framework - Advanced extensibility

**Explicitly exclude from v1:**
- Real-time streaming - Not possible with Whisper architecture
- Cloud API support - Against core value proposition
- Voice control/assistant - Different product category
- Perfect auto-punctuation - Unreliable with current models

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Push-to-talk hotkey | HIGH | LOW | P1 |
| Offline Whisper | HIGH | MEDIUM | P1 |
| System-wide injection | HIGH | MEDIUM | P1 |
| Daemon architecture | HIGH | MEDIUM | P1 |
| X11 + Wayland support | HIGH | HIGH | P1 |
| Toggle mode | MEDIUM | LOW | P1 |
| Basic voice punctuation | MEDIUM | LOW | P1 |
| Model selection | MEDIUM | MEDIUM | P1 |
| Configurable hotkeys | MEDIUM | LOW | P1 |
| Tray icon status | LOW | LOW | P1 |
| Voice Activity Detection | MEDIUM | MEDIUM | P2 |
| Voice commands (editing) | MEDIUM | MEDIUM | P2 |
| Waveform UI | LOW | MEDIUM | P2 |
| Number conversion | LOW | MEDIUM | P2 |
| Full sentence mode | LOW | LOW | P2 |
| Clipboard output mode | LOW | LOW | P2 |
| AI post-processing | MEDIUM | HIGH | P2 |
| Multi-language support | MEDIUM | MEDIUM | P3 |
| Custom command framework | LOW | HIGH | P3 |
| Smart quotes | LOW | LOW | P3 |
| Session persistence | LOW | LOW | P3 |

**Priority key:**
- P1: Must have for launch (MVP)
- P2: Should have, add post-validation
- P3: Nice to have, future consideration

## Competitor Feature Analysis

| Feature | nerd-dictation | TalkType | VOXD | Speech Note | OpenWhispr | Our Approach |
|---------|----------------|----------|------|-------------|------------|--------------|
| Push-to-talk | ✓ (begin/end) | ✓ (F8) | ✓ (hotkey) | ✓ (hotkey) | ✓ | ✓ Hotkey-based |
| Toggle mode | ✓ (continuous) | ✓ (F9) | ✓ (VAD beta) | ✓ | ✓ | ✓ Both modes |
| Offline processing | ✓ VOSK | ✓ Whisper | ✓ Whisper.cpp | ✓ Multiple engines | ✓ Whisper/Parakeet | ✓ faster-whisper (CPU optimized) |
| Daemon mode | ✓ (suspend/resume) | ✗ | ✓ (systemd) | ✗ | ✗ | ✓ Core architecture |
| Wayland support | ✓ (ydotool) | ✓ | ✓ (ydotool) | ✓ | ✓ (wtype/ydotool) | ✓ Hyprland primary |
| Voice commands | ✗ | ✓ (undo, punctuation) | ✗ | ✗ | ✗ | Defer to P2 |
| VAD | ✗ | ✗ | ✓ (beta "flux") | ✗ | ✗ | Defer to P2 |
| Waveform UI | ✗ | ✗ | ✗ | ✗ | ✗ | Defer to P2 |
| AI post-processing | ✗ | ✗ | ✓ (AIPP with LLM) | ✗ | ✗ | Defer to P2 |
| Model selection | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ tiny/small/medium |
| Custom commands | ✓ (Python config) | ✓ | ✗ | ✗ | ✗ | Defer to P3 |
| Number conversion | ✓ | ✗ | ✗ | ✗ | ✗ | Defer to P2 |
| GPU acceleration | ✗ | ✓ (CUDA) | ✗ (CPU focus) | ✓ (CUDA/ROCm) | ✓ (CUDA) | CPU-first, GPU optional |
| Multi-language | ✓ (20+) | ✓ (100+) | ✓ (99+) | ✓ (100+) | ✓ (58+) | Defer to P3 |

**Our Differentiation Strategy:**
1. **Daemon-first architecture** - Fastest response time by keeping model loaded
2. **CPU optimization** - Accessible on broader hardware (most tools assume GPU)
3. **Hyprland native** - Wayland compositor integration (not just "works on Wayland")
4. **Both push-to-talk AND toggle** - User choice from day one

**What we're NOT competing on:**
- Voice command complexity (TalkType wins here)
- Multi-engine support (Speech Note wins with 9+ TTS/STT engines)
- AI post-processing (VOXD's AIPP is unique but niche)
- Custom extensibility (nerd-dictation's Python config is powerful but technical)

## Performance Benchmarks from Ecosystem

**Model Size vs Speed (Whisper):**
- Tiny (39MB): ~50ms latency per chunk, 15% WER, acceptable for simple dictation
- Small (244MB): ~150ms latency, 8% WER, recommended for CPU-only
- Medium (769MB): ~400ms latency, 5% WER, requires good CPU or GPU
- Large-v3 (~3GB): ~1000ms+ latency on CPU, 3% WER, GPU recommended

**faster-whisper optimization:**
- Up to 4x faster than openai/whisper at same accuracy
- 8-bit quantization: Additional 30-40% speed improvement
- CPU-only recommendation: Small model with int8 quantization

**Latency targets (from research):**
- Sub-500ms first result: Required for natural UX
- Sub-300ms ideal: Feels instantaneous
- >2000ms: Breaks flow, users abandon

**Real-world performance (faster-whisper small model, CPU):**
- Model load: 2-3 seconds (cold start)
- Per-chunk transcription: 100-200ms
- Total push-to-talk latency: 150-300ms (daemon mode, model pre-loaded)

## Sources

### Primary Tool Research
- [nerd-dictation GitHub](https://github.com/ideasman42/nerd-dictation) - Features, configuration, VOSK integration
- [TalkType GitHub](https://github.com/ronb1964/TalkType) - Voice commands, hotkey modes, Whisper models
- [VOXD GitHub](https://github.com/jakovius/voxd) - Daemon architecture, VAD, AI post-processing
- [Speech Note GitHub](https://github.com/mkiol/dsnote) - Multi-engine support, offline processing
- [OpenWhispr GitHub](https://github.com/HeroTools/open-whispr) - Parakeet models, paste fallback
- [Speech Note on OMG! Linux](https://www.omglinux.com/speech-note-transcribe-voice-to-text-on-linux/)
- [Nerd Dictation Blog Post](https://www.suramya.com/blog/2022/01/nerd-dictation-a-fantastic-open-source-speech-to-text-software-for-linux/)
- [Hacker News Discussion - Nerd-dictation](https://news.ycombinator.com/item?id=29972579)

### Whisper Ecosystem
- [faster-whisper GitHub](https://github.com/SYSTRAN/faster-whisper) - CPU optimization, quantization
- [turbo-whisper GitHub](https://github.com/knowall-ai/turbo-whisper) - Waveform UI, Linux dictation
- [Whisper-Dictation GitHub](https://github.com/LumenYoung/Whisper-Dictation) - Daemon server architecture
- [whisper-dictation (NixOS) GitHub](https://github.com/jacopone/whisper-dictation) - Real-time feedback, push-to-talk
- [Whisper AI Discussion - Continuous Dictation](https://github.com/openai/whisper/discussions/1282)
- [AlterFlow Whisper Guide](https://alterflow.ai/blog/offline-voice-typing-on-ubuntu) - Ubuntu Wayland setup
- [Whisper.cpp Voice Mode Docs](https://voice-mode.readthedocs.io/en/stable/whisper.cpp/)

### Wayland/X11 Integration
- [hyprvoice GitHub](https://github.com/LeonardoTrapani/hyprvoice) - Wayland/Hyprland integration
- [voxtype GitHub](https://github.com/peteonrails/voxtype) - Wayland voice-to-text
- [waystt GitHub](https://github.com/sevos/waystt) - Wayland STT with PipeWire
- [OpenWhispr Issue #240](https://github.com/OpenWhispr/openwhispr/issues/240) - Wayland paste challenges
- [AlterFlow Vosk + ydotool Guide](https://alterflow.ai/offline-voice-typing-on-ubuntu/)
- [ydotool Info](https://gadgeteer.co.za/ydotool-is-an-alternative-to-xdotool-that-works-on-both-x11-and-wayland/)

### Additional Linux Tools
- [Voxtype](https://voxtype.io/) - Push-to-talk, offline, Whisper-based
- [Handy GitHub](https://github.com/cjpais/Handy) - Cross-platform, privacy-focused
- [Vocalinux](https://vocalinux.com/) - Offline voice dictation installer
- [VoxInput GitHub](https://github.com/BigRigVibeCoder/VoxInput) - Vosk/Whisper, system tray
- [wisper GitHub](https://github.com/taraksh01/wisper) - Glassmorphism UI, waveform
- [voice_typing GitHub](https://github.com/themanyone/voice_typing) - State-of-the-art offline typing
- [voice2json](http://voice2json.org/) - Command-line STT tools

### Performance & Latency
- [Northflank - Best STT Models 2026](https://northflank.com/blog/best-open-source-speech-to-text-stt-model-in-2026-benchmarks)
- [AssemblyAI - Real-time Speech Recognition APIs](https://www.assemblyai.com/blog/best-api-models-for-real-time-speech-recognition-and-transcription)
- [Speechify - AI Dictation Accuracy](https://speechify.com/blog/ai-dictation-accuracy-word-error-rate-latency-noise/)
- [Picovoice - Latency in Speech Recognition](https://picovoice.ai/blog/latency-in-speech-recognition/)
- [AssemblyAI - 300ms Rule](https://www.assemblyai.com/blog/low-latency-voice-ai)
- [Phonely - Sub-second Latency](https://www.phonely.ai/blogs/performance-reliability-in-voice-ai-why-sub-second-latency-matters)

### Voice Activity Detection
- [Deepgram - VAD Overview](https://deepgram.com/learn/voice-activity-detection)
- [QED42 - How Real-time VAD Works](https://www.qed42.com/insights/voice-activity-detection-in-text-to-speech-how-real-time-vad-works)
- [OpenAI - VAD Documentation](https://platform.openai.com/docs/guides/realtime-vad)
- [Picovoice - Complete VAD Guide 2026](https://picovoice.ai/blog/complete-guide-voice-activity-detection-vad/)
- [Google Cloud - Voice Activity Events](https://cloud.google.com/speech-to-text/v2/docs/voice-activity-events)
- [DeepWiki - faster-whisper VAD](https://deepwiki.com/SYSTRAN/faster-whisper/5.2-voice-activity-detection)

### Privacy & Offline Processing
- [VoiceScriber - Apple Dictation Alternatives](https://voicescriber.com/apple-dictation-private-offline-alternative)
- [Wispr Flow Review 2026](https://weesperneonflow.ai/en/blog/2026-02-09-wispr-flow-review-cloud-dictation-2026/)
- [Voibe - Wispr Flow Alternatives](https://www.getvoibe.com/blog/wispr-flow-alternatives/)
- [CamoVoice](https://camovoice.com/) - Offline, no subscription
- [VoiceScriber - Best Offline Apps](https://voicescriber.com/best-offline-transcription-apps)

### Feature Comparisons
- [SourceForge - Speech to Text Linux 2026](https://sourceforge.net/software/speech-to-text/linux/)
- [Slashdot - Speech to Text Linux](https://slashdot.org/software/speech-to-text/linux/)
- [GetApp - Speech Recognition Linux](https://www.getapp.com/emerging-technology-software/speech-recognition/os/linux/)
- [Wikipedia - Speech Recognition for Linux](https://en.wikipedia.org/wiki/Speech_recognition_software_for_Linux)
- [Vibe Typer - WisprFlow Alternative](https://vibetyper.com/blog/wisprflow-alternative-linux-guide-2026)

### General Dictation Features
- [BlabbyAI - Linux Speech to Text](https://www.blabby.ai/linux-speech-to-text)
- [VoiceToTextOnline - Punctuation Commands](https://www.voicetotextonline.com/voice-typing-punctuation-commands)
- [Willowvoice - Multi-Language Apps](https://willowvoice.com/blog/best-voice-to-text-apps-multi-language-users)
- [Microsoft - Voice Typing Windows](https://support.microsoft.com/en-us/windows/use-voice-typing-to-talk-instead-of-type-on-your-pc-fec94565-c4bd-329d-e59a-af033fa5689f)

---
*Feature research for: LinuxWhisper - Linux Desktop Voice Dictation*
*Researched: 2026-02-15*
