# Architecture Research

**Domain:** Linux voice dictation system
**Researched:** 2026-02-15
**Confidence:** HIGH

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      User Interface Layer                    │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │   CLI    │  │  System  │  │   Tray   │  │  Config  │    │
│  │ Commands │  │  Notify  │  │   Icon   │  │   File   │    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘    │
│       │             │             │             │           │
├───────┴─────────────┴─────────────┴─────────────┴───────────┤
│                    Daemon / Event Loop                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │            Main Coordination Loop (asyncio)          │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐           │   │
│  │  │  Hotkey  │→ │  State   │→ │  Audio   │           │   │
│  │  │ Monitor  │  │ Machine  │  │  Queue   │           │   │
│  │  └──────────┘  └──────────┘  └──────────┘           │   │
│  └──────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│                      Processing Pipeline                     │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │  Audio   │→ │   VAD    │→ │ Whisper  │→ │   Text   │    │
│  │ Capture  │  │ Filter   │  │ Transc.  │  │ Injector │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
├─────────────────────────────────────────────────────────────┤
│                    Hardware Abstraction                      │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │  evdev   │  │PipeWire/ │  │  X11 /   │  │ Whisper  │    │
│  │  Input   │  │PulseAudio│  │ Wayland  │  │  Model   │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| **Hotkey Monitor** | Detects global hotkey press/release events | evdev reading from /dev/input/eventX devices |
| **State Machine** | Manages recording states (idle, recording, transcribing) | Python enum + state transition logic |
| **Audio Capture** | Records audio while hotkey held/toggled | PipeWire/PulseAudio via parec/pw-cat/ffmpeg |
| **Audio Queue** | Buffers captured audio for processing | Python queue or asyncio queue |
| **VAD Filter** | Removes silence, validates speech presence | Silero VAD (optional, improves quality) |
| **Whisper Transcriber** | Converts audio to text | faster-whisper or whisper.cpp |
| **Text Injector** | Types text into active window | xdotool (X11) or wtype/ydotool (Wayland) |
| **Display Server Detector** | Runtime detection of X11 vs Wayland | Check $WAYLAND_DISPLAY or $XDG_SESSION_TYPE |
| **Config Manager** | Loads/saves user preferences | JSON file at ~/.config/linuxwhisper/config.json |
| **System Notifier** | Desktop notifications for status | libnotify (notify-send) |

## Recommended Project Structure

```
linuxwhisper/
├── src/
│   ├── daemon/              # Main daemon process
│   │   ├── __init__.py
│   │   ├── main.py          # Entry point, event loop setup
│   │   ├── state.py         # State machine (idle/recording/transcribing)
│   │   └── config.py        # Configuration loading/validation
│   ├── input/               # Hotkey detection
│   │   ├── __init__.py
│   │   ├── hotkey.py        # evdev-based hotkey monitoring
│   │   └── detector.py      # Device enumeration and filtering
│   ├── audio/               # Audio capture and processing
│   │   ├── __init__.py
│   │   ├── capture.py       # PipeWire/PulseAudio recording
│   │   ├── vad.py           # Voice activity detection (optional)
│   │   └── formats.py       # Audio format conversion (16kHz mono WAV)
│   ├── transcription/       # Whisper integration
│   │   ├── __init__.py
│   │   ├── engine.py        # faster-whisper wrapper
│   │   └── model_manager.py # Model download/selection
│   ├── output/              # Text injection
│   │   ├── __init__.py
│   │   ├── injector.py      # Abstract base for text injection
│   │   ├── x11.py           # xdotool implementation
│   │   ├── wayland.py       # wtype/ydotool implementation
│   │   └── detector.py      # Display server detection
│   ├── notification/        # User feedback
│   │   ├── __init__.py
│   │   └── notifier.py      # Desktop notifications
│   └── cli/                 # CLI interface
│       ├── __init__.py
│       └── commands.py      # Start/stop/config commands
├── config/
│   └── default_config.json  # Default configuration
├── systemd/
│   └── linuxwhisper.service # systemd unit file
├── setup.py                 # Python package setup
├── PKGBUILD                 # AUR package definition
└── README.md
```

### Structure Rationale

- **src/daemon/**: Core orchestration — keeps state machine and config separate from I/O concerns
- **src/input/**: Hotkey detection isolated — evdev code is platform-specific and can be swapped
- **src/audio/**: Audio handling isolated — enables testing with recorded files without capture hardware
- **src/transcription/**: Whisper integration isolated — allows swapping faster-whisper for whisper.cpp later
- **src/output/**: Text injection abstracted — X11/Wayland backends implement common interface
- **src/notification/**: UI feedback isolated — optional dependency, daemon works without it
- **Clear separation enables:** Component testing in isolation, easier backend swapping, gradual feature addition

## Architectural Patterns

### Pattern 1: Event-Driven State Machine

**What:** Central state machine coordinated by asyncio event loop, transitioning between idle/recording/transcribing states based on hotkey events and processing completion.

**When to use:** Voice dictation is inherently event-driven (hotkey press → record → transcribe → inject). State machine prevents race conditions and manages concurrent operations (audio capture while monitoring hotkey release).

**Trade-offs:**
- Pros: Clean state transitions, no blocking operations, handles hold-to-talk and toggle modes uniformly
- Cons: Async code complexity, debugging event ordering can be harder than synchronous flow

**Example:**
```python
import asyncio
from enum import Enum, auto

class State(Enum):
    IDLE = auto()
    RECORDING = auto()
    TRANSCRIBING = auto()

class DictationDaemon:
    def __init__(self):
        self.state = State.IDLE
        self.audio_queue = asyncio.Queue()

    async def on_hotkey_press(self):
        if self.state == State.IDLE:
            self.state = State.RECORDING
            asyncio.create_task(self.record_audio())

    async def on_hotkey_release(self):
        if self.state == State.RECORDING:
            self.state = State.TRANSCRIBING
            asyncio.create_task(self.transcribe_and_inject())

    async def record_audio(self):
        while self.state == State.RECORDING:
            chunk = await self.capture_audio_chunk()
            await self.audio_queue.put(chunk)

    async def transcribe_and_inject(self):
        audio = await self.finalize_audio()
        text = await self.transcribe(audio)
        await self.inject_text(text)
        self.state = State.IDLE
```

### Pattern 2: Hardware Abstraction Layer

**What:** Abstract interfaces for platform-specific backends (X11/Wayland text injection, PipeWire/PulseAudio capture) with runtime detection and selection.

**When to use:** When code must work across multiple display servers or audio systems without user intervention. Critical for Linux where X11/Wayland coexist and users shouldn't configure backends manually.

**Trade-offs:**
- Pros: Single codebase for all platforms, runtime adaptability, easier testing with mock backends
- Cons: Additional abstraction layer, potential for lowest-common-denominator API

**Example:**
```python
from abc import ABC, abstractmethod

class TextInjector(ABC):
    @abstractmethod
    async def inject(self, text: str) -> None:
        pass

class X11Injector(TextInjector):
    async def inject(self, text: str) -> None:
        # Use xdotool
        await asyncio.create_subprocess_exec('xdotool', 'type', '--', text)

class WaylandInjector(TextInjector):
    async def inject(self, text: str) -> None:
        # Use wtype
        await asyncio.create_subprocess_exec('wtype', text)

def get_injector() -> TextInjector:
    if os.environ.get('WAYLAND_DISPLAY'):
        return WaylandInjector()
    return X11Injector()
```

### Pattern 3: Pipeline Processing with Queues

**What:** Audio flows through processing stages (capture → VAD → transcription → injection) using asyncio queues to decouple producers and consumers.

**When to use:** When processing stages have different speeds (audio capture is real-time, transcription is batch) and you want to avoid blocking the main event loop.

**Trade-offs:**
- Pros: Non-blocking capture, can process audio while still recording, graceful buffering
- Cons: Memory usage for queued audio, complexity of queue lifecycle management

**Example:**
```python
class AudioPipeline:
    def __init__(self):
        self.capture_queue = asyncio.Queue(maxsize=100)
        self.transcription_queue = asyncio.Queue(maxsize=10)

    async def run(self):
        await asyncio.gather(
            self.capture_stage(),
            self.vad_stage(),
            self.transcription_stage(),
            self.injection_stage()
        )

    async def capture_stage(self):
        while True:
            chunk = await self.audio_source.read()
            await self.capture_queue.put(chunk)

    async def vad_stage(self):
        while True:
            chunk = await self.capture_queue.get()
            if self.has_speech(chunk):
                await self.transcription_queue.put(chunk)
```

### Pattern 4: Daemon-First Architecture with systemd Integration

**What:** Core functionality runs as a background daemon (systemd service), exposing control via CLI commands that communicate with the daemon.

**When to use:** For always-available services like dictation that must respond to global hotkeys. Systemd integration provides automatic startup, restart on crash, and standardized service management.

**Trade-offs:**
- Pros: Always running, fast response to hotkeys, proper Linux service integration, automatic recovery
- Cons: Resource usage when idle, more complex deployment than standalone script

**Example:**
```python
# daemon/main.py
async def run_daemon():
    daemon = DictationDaemon()
    await daemon.setup()

    # Notify systemd we're ready
    if 'NOTIFY_SOCKET' in os.environ:
        daemon.sd_notify("READY=1")

    try:
        await daemon.run_forever()
    except asyncio.CancelledError:
        await daemon.shutdown()

# systemd/linuxwhisper.service
[Unit]
Description=LinuxWhisper Voice Dictation Daemon
After=network.target sound.target

[Service]
Type=notify
User=%u
ExecStart=/usr/bin/linuxwhisper daemon
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=default.target
```

## Data Flow

### Hold-to-Talk Flow

```
[User presses F13]
    ↓
[evdev detects key press] → [State: IDLE → RECORDING]
    ↓
[Audio capture starts] → [16kHz mono WAV buffer]
    ↓
[User releases F13]
    ↓
[evdev detects release] → [State: RECORDING → TRANSCRIBING]
    ↓
[Audio capture stops] → [Buffer finalized]
    ↓
[VAD filter (optional)] → [Silence removed]
    ↓
[Whisper transcription] → [Text output]
    ↓
[Display server detection] → [X11 or Wayland injector selected]
    ↓
[Text injection] → [xdotool type / wtype]
    ↓
[Desktop notification] → [State: TRANSCRIBING → IDLE]
```

### Toggle-to-Talk Flow

```
[User presses F13 (first time)]
    ↓
[evdev detects press] → [State: IDLE → RECORDING]
    ↓
[Audio capture starts] → [Continuous recording]
    ↓
[User presses F13 (second time)]
    ↓
[evdev detects press] → [State: RECORDING → TRANSCRIBING]
    ↓
[Continue with transcription flow as above...]
```

### Component Communication

```
┌──────────────┐
│ Hotkey       │
│ Monitor      │────┐
└──────────────┘    │
                    ↓
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Audio        │→ │ State        │→ │ Audio        │
│ Capture      │  │ Machine      │  │ Queue        │
└──────────────┘  └──────────────┘  └──────────────┘
                        │
                        ↓
                  ┌──────────────┐  ┌──────────────┐
                  │ Whisper      │→ │ Text         │
                  │ Engine       │  │ Injector     │
                  └──────────────┘  └──────────────┘
```

### Key Data Flows

1. **Hotkey → State Machine:** evdev events trigger state transitions. Async event handlers prevent blocking the input monitor.

2. **Audio Capture → Buffer:** Audio chunks (100ms each) accumulate in memory buffer during RECORDING state. Buffer written to temp file or held in memory (typically 5-30 seconds total).

3. **Buffer → Transcription:** Complete audio passed to Whisper. faster-whisper runs in thread pool to avoid blocking event loop.

4. **Transcription → Injection:** Text flows through display server detector to appropriate backend (xdotool subprocess for X11, wtype/ydotool for Wayland).

5. **State Notifications:** State changes trigger desktop notifications (optional) for user feedback (recording started, transcribing, completed).

## X11/Wayland Handling Strategy

### Recommended Approach: Runtime Detection with Backend Selection

**Why:** Users switch between display servers, and auto-detection provides seamless experience without configuration.

| Approach | Pros | Cons | Recommendation |
|----------|------|------|----------------|
| Runtime detection | Works automatically, no user config | Slight complexity | **RECOMMENDED** |
| User config | Simple implementation | User must configure, breaks if they switch | Avoid |
| Support only Wayland | Simpler code | Excludes X11 users (still common) | Too limiting |

### Detection Implementation

```python
def detect_display_server() -> str:
    """Detect if running under X11 or Wayland."""
    if os.environ.get('WAYLAND_DISPLAY'):
        return 'wayland'
    elif os.environ.get('DISPLAY'):
        return 'x11'
    else:
        raise RuntimeError("No display server detected")
```

### Text Injection Backends

| Backend | Works On | Requires | Notes |
|---------|----------|----------|-------|
| **xdotool** | X11, XWayland | apt/pacman install xdotool | Best for X11, widely available |
| **wtype** | Wayland | pacman install wtype | Wayland-native, no daemon, fast |
| **ydotool** | X11, Wayland | pacman install ydotool, ydotoold daemon | Requires daemon, uses uinput (needs root or input group) |
| **dotool** | X11, Wayland | Manual install | Lightweight but less common |

**Recommendation for LinuxWhisper:**
- **X11:** Use xdotool (standard, reliable, widely packaged)
- **Wayland:** Use wtype (no daemon required, simpler than ydotool)
- Fall back to ydotool if wtype unavailable (document ydotoold setup)

### Hotkey Detection

**evdev is universal:** Works on both X11 and Wayland by reading kernel input events directly.

**Requirements:**
- User must be in `input` group: `sudo usermod -aG input $USER`
- Read access to `/dev/input/event*` devices
- Device selection: Find keyboard device, not mouse/touchpad

**Implementation pattern:**
```python
import evdev
from evdev import InputDevice, ecodes

def find_keyboard_devices():
    """Find all keyboard input devices."""
    devices = [InputDevice(path) for path in evdev.list_devices()]
    keyboards = []
    for device in devices:
        capabilities = device.capabilities(verbose=False)
        # Check if device has key events and common keyboard keys
        if ecodes.EV_KEY in capabilities:
            keys = capabilities[ecodes.EV_KEY]
            # Most keyboards have KEY_A through KEY_Z
            if ecodes.KEY_A in keys:
                keyboards.append(device)
    return keyboards

async def monitor_hotkey(device, key_code):
    """Monitor device for specific key press/release."""
    async for event in device.async_read_loop():
        if event.type == ecodes.EV_KEY and event.code == key_code:
            if event.value == 1:  # Key press
                await on_hotkey_press()
            elif event.value == 0:  # Key release
                await on_hotkey_release()
```

## Audio Capture Architecture

### PipeWire/PulseAudio Strategy

**Modern Linux uses PipeWire** (replaces PulseAudio), but PipeWire provides PulseAudio compatibility layer.

| Tool | Works With | Command Example | Notes |
|------|------------|-----------------|-------|
| **parecord** | PulseAudio, PipeWire | `parecord --format=s16le --rate=16000 --channels=1 output.wav` | Standard, widely available |
| **pw-cat** | PipeWire native | `pw-cat --record --format=s16 --rate=16000 --channels=1 output.wav` | PipeWire-native, lower latency |
| **ffmpeg** | ALSA, PulseAudio, PipeWire | `ffmpeg -f pulse -i default -ar 16000 -ac 1 output.wav` | Universal fallback |
| **arecord** | ALSA | `arecord -f S16_LE -r 16000 -c 1 output.wav` | Low-level, works everywhere |

**Recommendation:**
- **Primary:** Try `parecord` (works with both PulseAudio and PipeWire via compatibility)
- **Fallback:** Use `arecord` if parecord unavailable
- **Detection:** Check for `parecord` in PATH, fall back to `arecord`

### Audio Format Requirements

Whisper expects **16kHz, mono, 16-bit PCM WAV**.

```python
# Correct parecord invocation
subprocess.Popen([
    'parecord',
    '--format=s16le',    # 16-bit signed little-endian
    '--rate=16000',       # 16kHz sample rate
    '--channels=1',       # Mono
    output_file
])
```

### Capture Process Lifecycle

```python
class AudioCapture:
    async def start_recording(self, output_path: str):
        """Start audio capture subprocess."""
        self.process = await asyncio.create_subprocess_exec(
            'parecord',
            '--format=s16le',
            '--rate=16000',
            '--channels=1',
            output_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

    async def stop_recording(self):
        """Stop recording and wait for process to finalize file."""
        if self.process:
            self.process.terminate()
            await self.process.wait()
            self.process = None
```

## Whisper Transcription Architecture

### Engine Selection: faster-whisper vs whisper.cpp

| Factor | faster-whisper | whisper.cpp | Recommendation |
|--------|----------------|-------------|----------------|
| Language | Python | C/C++ | **faster-whisper** (Python ecosystem) |
| CPU Performance | 4x faster than openai/whisper | Highly optimized, comparable | Both excellent |
| Integration | `pip install faster-whisper` | Requires compilation/bindings | **faster-whisper** (easier) |
| Quantization | INT8 support | INT4/INT8/INT16 support | Both adequate |
| Memory Usage | Moderate | Lower with aggressive quant | Comparable for INT8 |
| GPU Support | CUDA via CTranslate2 | Experimental, CPU-focused | **faster-whisper** for GPU path |

**Recommendation for LinuxWhisper:** Use faster-whisper
- Native Python integration (no compilation)
- Excellent CPU performance (4x faster than openai/whisper)
- Easy to install via pip/AUR
- Good quantization support (INT8 reduces memory)
- GPU support for users who want it later

### Model Selection Strategy

**Hardware-aware recommendations:**

| Hardware | Model | Rationale |
|----------|-------|-----------|
| CPU-only (user's case) | tiny.en or base.en | Fastest, 1-3s transcription for 10s audio |
| CPU with 8GB+ RAM | small.en | Better accuracy, still fast on modern CPUs |
| NVIDIA GPU | medium.en or large-v3 | Leverage GPU acceleration, higher accuracy |

**Configuration approach:**
```python
def recommend_model(config):
    """Recommend model based on hardware detection."""
    if has_cuda():
        return config.get('model', 'medium.en')  # User can override
    else:
        return config.get('model', 'base.en')    # CPU default
```

### Transcription Implementation

```python
from faster_whisper import WhisperModel

class TranscriptionEngine:
    def __init__(self, model_size='base.en', device='cpu'):
        self.model = WhisperModel(
            model_size,
            device=device,
            compute_type='int8'  # Quantization for speed/memory
        )

    async def transcribe(self, audio_path: str) -> str:
        """Transcribe audio file to text."""
        # Run in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        segments, info = await loop.run_in_executor(
            None,
            self._transcribe_sync,
            audio_path
        )

        # Combine segments into full text
        text = ' '.join(segment.text for segment in segments)
        return text.strip()

    def _transcribe_sync(self, audio_path: str):
        """Synchronous transcription (runs in thread)."""
        return self.model.transcribe(
            audio_path,
            language='en',
            vad_filter=True,  # Enable VAD if available
            vad_parameters=dict(
                min_silence_duration_ms=500
            )
        )
```

### Voice Activity Detection (VAD)

**Purpose:** Filter silence and non-speech audio before/after speech, improving transcription quality and reducing processing time.

**Implementation options:**

1. **faster-whisper built-in VAD (Silero):** Enable with `vad_filter=True` in transcribe()
2. **Separate pre-processing:** Run Silero VAD before Whisper to trim audio file
3. **Skip VAD:** For short dictations (< 30s), VAD overhead may exceed benefits

**Recommendation for LinuxWhisper:**
- Use faster-whisper's built-in VAD (`vad_filter=True`)
- Configurable: Let users disable if it causes issues
- Most useful for toggle mode (longer recordings)

## Daemon Structure

### Lifecycle Management

```python
# src/daemon/main.py
import asyncio
import signal

class LinuxWhisperDaemon:
    def __init__(self, config):
        self.config = config
        self.running = False

        # Components
        self.state_machine = StateMachine()
        self.hotkey_monitor = HotkeyMonitor(config.hotkey)
        self.audio_capture = AudioCapture()
        self.transcription = TranscriptionEngine(config.model)
        self.text_injector = get_text_injector()  # Auto-detect X11/Wayland

    async def setup(self):
        """Initialize components before main loop."""
        await self.hotkey_monitor.setup()
        await self.state_machine.setup()

        # Connect hotkey events to state machine
        self.hotkey_monitor.on_press = self.state_machine.on_hotkey_press
        self.hotkey_monitor.on_release = self.state_machine.on_hotkey_release

        # Connect state machine to processing pipeline
        self.state_machine.on_start_recording = self.start_recording
        self.state_machine.on_stop_recording = self.stop_recording

    async def run_forever(self):
        """Main daemon loop."""
        self.running = True

        # Set up signal handlers for graceful shutdown
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.shutdown()))

        # Run all components concurrently
        await asyncio.gather(
            self.hotkey_monitor.run(),
            self.state_machine.run(),
            self.process_queue()
        )

    async def shutdown(self):
        """Clean shutdown."""
        self.running = False
        await self.hotkey_monitor.shutdown()
        await self.audio_capture.shutdown()

    async def start_recording(self):
        """Called when recording starts."""
        await self.audio_capture.start()

    async def stop_recording(self):
        """Called when recording stops."""
        audio_file = await self.audio_capture.stop()
        text = await self.transcription.transcribe(audio_file)
        await self.text_injector.inject(text)

async def main():
    config = load_config()
    daemon = LinuxWhisperDaemon(config)
    await daemon.setup()
    await daemon.run_forever()

if __name__ == '__main__':
    asyncio.run(main())
```

### State Machine Implementation

```python
from enum import Enum, auto

class DictationState(Enum):
    IDLE = auto()
    RECORDING = auto()
    TRANSCRIBING = auto()

class StateMachine:
    def __init__(self, mode='hold'):
        self.state = DictationState.IDLE
        self.mode = mode  # 'hold' or 'toggle'

        # Callbacks (set by daemon)
        self.on_start_recording = None
        self.on_stop_recording = None

    async def on_hotkey_press(self):
        """Handle hotkey press event."""
        if self.mode == 'hold':
            await self._handle_hold_mode_press()
        else:  # toggle
            await self._handle_toggle_mode_press()

    async def on_hotkey_release(self):
        """Handle hotkey release event."""
        if self.mode == 'hold':
            await self._handle_hold_mode_release()
        # Toggle mode ignores release

    async def _handle_hold_mode_press(self):
        if self.state == DictationState.IDLE:
            self.state = DictationState.RECORDING
            if self.on_start_recording:
                await self.on_start_recording()

    async def _handle_hold_mode_release(self):
        if self.state == DictationState.RECORDING:
            self.state = DictationState.TRANSCRIBING
            if self.on_stop_recording:
                await self.on_stop_recording()
            self.state = DictationState.IDLE

    async def _handle_toggle_mode_press(self):
        if self.state == DictationState.IDLE:
            self.state = DictationState.RECORDING
            if self.on_start_recording:
                await self.on_start_recording()
        elif self.state == DictationState.RECORDING:
            self.state = DictationState.TRANSCRIBING
            if self.on_stop_recording:
                await self.on_stop_recording()
            self.state = DictationState.IDLE
```

## Build Order and Component Dependencies

### Recommended Implementation Phases

**Phase 1: Core Pipeline (No Dependencies)**
1. Config management (JSON loading/saving)
2. Audio capture (parecord/arecord subprocess)
3. Whisper transcription (faster-whisper integration)
4. Basic file-based testing (manual audio files)

**Phase 2: Input Detection (Depends on Phase 1)**
1. Display server detection (environment variables)
2. Text injection backends (xdotool/wtype subprocess)
3. Test with pre-transcribed text

**Phase 3: Hotkey Integration (Depends on Phase 1)**
1. evdev keyboard detection
2. Hotkey monitoring (async event loop)
3. State machine (idle/recording/transcribing)

**Phase 4: Daemon Architecture (Depends on Phases 1-3)**
1. Integrate all components in asyncio event loop
2. State machine connects hotkey → audio → transcription → injection
3. Signal handling for graceful shutdown

**Phase 5: System Integration (Depends on Phase 4)**
1. systemd service unit file
2. CLI commands (start/stop/config)
3. Desktop notifications (optional)

**Phase 6: Packaging (Depends on Phase 5)**
1. setup.py for Python package
2. PKGBUILD for AUR
3. Installation documentation

### Critical Path

```
Config + Audio + Whisper (Phase 1)
         ↓
Display Detection + Text Injection (Phase 2)
         ↓
evdev + Hotkey + State Machine (Phase 3)
         ↓
Daemon Integration (Phase 4)
         ↓
systemd + CLI (Phase 5)
         ↓
AUR Packaging (Phase 6)
```

**Early validation opportunities:**
- After Phase 1: Test transcription with pre-recorded audio files
- After Phase 2: Test text injection with hardcoded strings
- After Phase 3: Test hotkey detection without transcription
- After Phase 4: End-to-end manual testing

## Anti-Patterns

### Anti-Pattern 1: Blocking the Event Loop with Whisper

**What people do:** Call `whisper.transcribe()` directly in async function, blocking the event loop for seconds.

**Why it's wrong:** Whisper transcription is CPU-intensive and synchronous. Blocking the event loop prevents hotkey monitoring and other async tasks from running.

**Do this instead:** Run transcription in thread pool using `loop.run_in_executor()`:

```python
# WRONG - blocks event loop
async def transcribe(audio):
    return model.transcribe(audio)  # Blocks for 2-10 seconds!

# RIGHT - runs in thread pool
async def transcribe(audio):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, model.transcribe, audio)
```

### Anti-Pattern 2: Subprocess Without Cleanup

**What people do:** Start audio recording subprocess but don't properly terminate or wait for it to finish writing files.

**Why it's wrong:** Leaves zombie processes, can corrupt audio files if process killed mid-write, leaks file descriptors.

**Do this instead:** Always terminate and wait:

```python
# WRONG
process = subprocess.Popen(['parecord', 'output.wav'])
# Process might still be writing when we try to read the file!

# RIGHT
process = await asyncio.create_subprocess_exec('parecord', 'output.wav')
# ... later ...
process.terminate()
await process.wait()  # Wait for process to finish and flush file
```

### Anti-Pattern 3: Hardcoded Backend Selection

**What people do:** Check if Wayland is running and only support Wayland, or only support X11.

**Why it's wrong:** Users switch between X11 and Wayland sessions. Code breaks when user changes display server.

**Do this instead:** Runtime detection with graceful fallback:

```python
# WRONG
injector = WaylandInjector()  # Breaks on X11!

# RIGHT
def get_injector():
    if os.environ.get('WAYLAND_DISPLAY'):
        if shutil.which('wtype'):
            return WaylandInjector()
        elif shutil.which('ydotool'):
            return YdotoolInjector()
    if os.environ.get('DISPLAY'):
        if shutil.which('xdotool'):
            return X11Injector()
    raise RuntimeError("No supported text injection backend found")
```

### Anti-Pattern 4: Ignoring VAD for Toggle Mode

**What people do:** Skip VAD entirely because hold-to-talk recordings are short.

**Why it's wrong:** Toggle mode can result in long recordings with silence at start/end. Without VAD, transcription quality degrades and processing time increases.

**Do this instead:** Enable VAD for toggle mode, optional for hold mode:

```python
# WRONG
model.transcribe(audio, vad_filter=False)  # Always disabled

# RIGHT
vad_enabled = config.get('vad_filter', True) if mode == 'toggle' else False
model.transcribe(audio, vad_filter=vad_enabled)
```

### Anti-Pattern 5: Running Daemon as Root

**What people do:** Run daemon as root to access /dev/input/event* devices.

**Why it's wrong:** Security risk. Compromised daemon has full system access. Violates principle of least privilege.

**Do this instead:** Add user to `input` group:

```bash
# Installation step
sudo usermod -aG input $USER
# User logs out and back in

# systemd service runs as user
[Service]
User=%u  # Run as the user who enabled the service
```

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| **systemd** | D-Bus notification, service unit file | Use `sd_notify("READY=1")` for Type=notify |
| **PipeWire/PulseAudio** | Subprocess (parecord) | Check for parecord binary at startup |
| **Desktop notifications** | Subprocess (notify-send) or python-notify2 | Optional dependency, daemon works without it |
| **evdev** | Direct device file reading | Requires user in `input` group |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| **Hotkey Monitor ↔ State Machine** | Async callbacks | HotkeyMonitor calls state_machine.on_press/on_release |
| **State Machine ↔ Audio Capture** | Async callbacks | State machine calls audio.start/stop, audio returns file path |
| **Audio Capture ↔ Transcription** | File path | Audio writes to temp file, transcription reads it |
| **Transcription ↔ Text Injector** | String | Transcription returns text, injector types it |
| **All ↔ Config** | Direct read | All components read config at initialization |

## Suggested Build Order

### Iteration 1: Proof of Concept (1-2 days)
- Config loading (JSON)
- Audio recording to file (parecord)
- Whisper transcription (faster-whisper)
- Text injection (xdotool OR wtype, whichever you have)
- **Goal:** Manual workflow: run script, record audio, transcribe, inject

### Iteration 2: Hotkey Detection (1 day)
- evdev device enumeration
- Keyboard detection
- Key press/release monitoring
- **Goal:** Detect F13 press/release, print to console

### Iteration 3: State Machine (1 day)
- State enum (IDLE/RECORDING/TRANSCRIBING)
- Hold-to-talk logic (press starts, release stops)
- Connect hotkey → state → audio
- **Goal:** Hold F13, speak, release, text appears

### Iteration 4: Display Server Abstraction (0.5 day)
- Runtime detection (X11/Wayland)
- Backend selection
- **Goal:** Works on both X11 and Wayland sessions

### Iteration 5: Daemon Architecture (1-2 days)
- Async event loop
- Component lifecycle (setup/run/shutdown)
- Signal handling
- **Goal:** Run as background process, responds to hotkeys

### Iteration 6: Toggle Mode (0.5 day)
- Toggle state logic in state machine
- Config option for mode
- **Goal:** Both hold and toggle modes work

### Iteration 7: System Integration (1 day)
- systemd service file
- CLI commands (start/stop/reload)
- Desktop notifications
- **Goal:** Start on boot, control via CLI

### Iteration 8: Packaging (1 day)
- setup.py
- PKGBUILD for AUR
- README with installation instructions
- **Goal:** `yay -S linuxwhisper` installs and runs

**Total estimated time:** 7-10 days for full implementation

## Sources

### Voice Dictation Systems
- [Nerd Dictation GitHub](https://github.com/ideasman42/nerd-dictation) - Architecture reference for offline dictation
- [Speech Recognition Software for Linux - Wikipedia](https://en.wikipedia.org/wiki/Speech_recognition_software_for_Linux)
- [Whisper Continuous Dictation Discussion](https://github.com/openai/whisper/discussions/1282)
- [Handy Speech-to-Text](https://github.com/cjpais/Handy) - Privacy-focused Tauri application
- [voice2json](http://voice2json.org/) - Command-line speech recognition tools
- [How to Use Whisper AI for Live Audio Transcription on Linux](https://www.tecmint.com/whisper-ai-audio-transcription-on-linux/)

### X11/Wayland Input Handling
- [ydotool GitHub](https://github.com/ReimuNotMoe/ydotool) - Cross-platform input automation
- [Running Legacy X11 Apps in Wayland (XWayland)](https://openlib.io/running-legacy-x11-apps-in-wayland-xwayland-in-linux/)
- [libinput Documentation](https://wayland.freedesktop.org/libinput/doc/latest/what-is-libinput.html)
- [evdev, libinput, and Xorg: Interfacing with Input Devices](https://openlib.io/evdev-libinput-and-xorg-interfacing-with-input-devices-in-linux/)

### Audio Capture
- [PipeWire ArchWiki](https://wiki.archlinux.org/title/PipeWire)
- [Replacing PulseAudio With PipeWire on Linux](https://www.baeldung.com/linux/pulseaudio-pipewire-replace)
- [PipeWire Official Documentation](https://pipewire.org/)
- [Linux Audio Recording Guide (PulseAudio or PipeWire)](https://ro-che.info/articles/2017-07-21-record-audio-linux)

### evdev Input Monitoring
- [The Input Stack on Linux — An End-To-End Architecture Overview](https://venam.net/blog/unix/2025/11/27/input_devices_linux.html)
- [evdev - Wikipedia](https://en.wikipedia.org/wiki/Evdev)
- [python-evdev Documentation](https://manpages.ubuntu.com/manpages//plucky/man7/python-evdev.7.html)
- [Monitor Device Events in Linux](https://www.baeldung.com/linux/monitor-device-events)

### Whisper Optimization
- [faster-whisper GitHub](https://github.com/SYSTRAN/faster-whisper)
- [whisper.cpp GitHub](https://github.com/ggml-org/whisper.cpp)
- [Choosing between Whisper variants](https://modal.com/blog/choosing-whisper-variants)
- [A Practical Guide To Choosing Between Whisper.cpp And Faster-whisper](https://www.alibaba.com/product-insights/a-practical-guide-to-choosing-between-whisper-cpp-and-faster-whisper-for-offline-transcription.html)
- [Whisper Streaming GitHub](https://github.com/ufal/whisper_streaming) - Real-time transcription architecture
- [WhisperLive GitHub](https://github.com/collabora/WhisperLive)

### VAD (Voice Activity Detection)
- [Voice Activity Detection - faster-whisper](https://deepwiki.com/SYSTRAN/faster-whisper/5.2-voice-activity-detection)
- [VAD vs Speaker Diarization in Whisper](https://www.f22labs.com/blogs/what-is-vad-and-diarization-with-whisper-models-a-complete-guide/)
- [SileroVAD: Machine Learning Model to Detect Speech Segments](https://medium.com/axinc-ai/silerovad-machine-learning-model-to-detect-speech-segments-e99722c0dd41)

### Python Daemon Architecture
- [python-systemd-tutorial GitHub](https://github.com/torfsen/python-systemd-tutorial)
- [From Python to Daemon with Systemd](https://levelup.gitconnected.com/from-python-to-daemon-how-to-turn-your-python-app-into-a-linux-service-controlled-by-systemd-d87b59adfe7a)
- [Writing a secure Systemd daemon with Python](https://blog.hqcodeshop.fi/archives/569-Writing-a-secure-Systemd-daemon-with-Python.html)
- [Python asyncio: Complete Guide to Async Programming 2026](https://devtoolbox.dedyn.io/blog/python-asyncio-complete-guide)
- [Python asyncio Event Loop Documentation](https://docs.python.org/3/library/asyncio-eventloop.html)

---
*Architecture research for: LinuxWhisper*
*Researched: 2026-02-15*
