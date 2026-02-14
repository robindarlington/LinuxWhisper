# Phase 2: Core Dictation Pipeline - Research

**Researched:** 2026-02-15
**Domain:** Linux audio capture, speech-to-text, input automation
**Confidence:** HIGH

## Summary

Phase 2 implements the complete dictation pipeline: global hotkey detection (evdev) → audio recording (sounddevice) → speech-to-text (faster-whisper) → text injection (ydotool/xdotool). This research covers the technical requirements for implementing push-to-talk dictation on Linux with support for both X11 and Wayland.

The pipeline requires careful orchestration of asynchronous components: evdev requires root/input group access for keyboard monitoring, sounddevice needs access to audio devices through PulseAudio/PipeWire user sessions, faster-whisper processes audio with INT8 quantization for speed, and ydotool requires a daemon with uinput permissions for Wayland text injection.

**Primary recommendation:** Use a state machine pattern for managing recording states (IDLE → RECORDING → PROCESSING → INJECTING), implement audio recording with queue-based non-blocking callbacks to prevent buffer overflow, save audio to WAV files (mono, 16kHz) for faster-whisper processing, and detect session type at runtime to choose between ydotool (Wayland) and xdotool (X11) for text injection.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| python-evdev | 1.9.0+ | Global hotkey detection via /dev/input | Only reliable cross-compositor solution for Wayland+X11 |
| sounddevice | 0.5.5+ | Audio recording to NumPy arrays | Modern PortAudio bindings, simpler API than PyAudio, NumPy integration |
| faster-whisper | Latest | Local speech-to-text with INT8 quantization | 4x faster than OpenAI Whisper, efficient CTranslate2 backend |
| ydotool | 1.0.0+ | Text injection on Wayland via uinput | Only reliable Wayland input automation tool |
| xdotool | Any | Text injection on X11 | Standard X11 automation tool, fallback for X11 sessions |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| scipy | Latest | WAV file I/O (scipy.io.wavfile) | Saving recorded audio for faster-whisper |
| python-statemachine | 2.5.0+ | State machine implementation | If explicit state machine library desired (optional) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| sounddevice | PyAudio | PyAudio has lower-level API, bytes instead of NumPy arrays, more complex |
| faster-whisper | openai-whisper | OpenAI Whisper is 4x slower, no built-in INT8 quantization |
| ydotool | dotool | dotool is newer but less mature, fewer users/documentation |
| State machine lib | Manual state tracking | Library adds dependency but provides clear state transition validation |

**Installation:**
```bash
# Core dependencies
pip install evdev sounddevice faster-whisper scipy

# System tools (via package manager)
sudo pacman -S ydotool xdotool  # Arch
sudo apt install ydotool xdotool  # Debian/Ubuntu

# Optional: explicit state machine
pip install python-statemachine
```

## Architecture Patterns

### Recommended Project Structure
```
src/linuxwhisper/
├── hotkey/              # evdev keyboard monitoring
│   ├── detector.py      # Device selection, event loop
│   └── permissions.py   # Input group validation
├── audio/               # sounddevice recording
│   ├── recorder.py      # Non-blocking recording with queue
│   └── processor.py     # WAV file conversion (mono, 16kHz)
├── transcription/       # faster-whisper integration
│   ├── engine.py        # Model loading, transcribe()
│   └── vad.py           # Voice activity detection config
├── injection/           # Text output automation
│   ├── detector.py      # X11/Wayland session detection
│   ├── wayland.py       # ydotool wrapper
│   └── x11.py           # xdotool wrapper
└── pipeline/            # State machine coordinator
    ├── states.py        # IDLE, RECORDING, PROCESSING, INJECTING
    └── coordinator.py   # Event loop orchestration
```

### Pattern 1: State Machine for Push-to-Talk
**What:** Explicit state tracking with transitions for recording lifecycle
**When to use:** Managing complex async flows (hotkey press → record → transcribe → inject)
**Example:**
```python
# Source: https://github.com/fgmacedo/python-statemachine
from statemachine import StateMachine, State

class DictationPipeline(StateMachine):
    idle = State(initial=True)
    recording = State()
    processing = State()
    injecting = State()

    # Transitions
    start_recording = idle.to(recording)
    stop_recording = recording.to(processing)
    inject_text = processing.to(injecting)
    reset = injecting.to(idle) | processing.to(idle)

    def on_enter_recording(self):
        """Start audio capture"""
        self.audio_queue = queue.Queue()
        self.stream = sd.InputStream(callback=self._audio_callback)
        self.stream.start()

    def on_exit_recording(self):
        """Stop and save audio"""
        self.stream.stop()
        audio_data = self._drain_queue()
        self.audio_file = self._save_wav(audio_data)

    def on_enter_processing(self):
        """Transcribe audio"""
        segments, _ = whisper_model.transcribe(self.audio_file)
        self.text = "".join(seg.text for seg in segments)

    def on_enter_injecting(self):
        """Inject transcribed text"""
        injector.type_text(self.text)
```

### Pattern 2: Queue-Based Non-Blocking Audio Recording
**What:** Use sounddevice callbacks with queue.Queue for thread-safe audio buffering
**When to use:** Real-time audio recording to prevent buffer overflow
**Example:**
```python
# Source: https://python-sounddevice.readthedocs.io/
import sounddevice as sd
import queue
import numpy as np

class AudioRecorder:
    def __init__(self, sample_rate=16000, channels=1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.audio_queue = queue.Queue()

    def _callback(self, indata, frames, time, status):
        """Called from audio thread - must not block"""
        if status:
            print(f"Audio status: {status}")
        self.audio_queue.put(indata.copy())

    def start_recording(self):
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            callback=self._callback
        )
        self.stream.start()

    def stop_recording(self):
        self.stream.stop()
        self.stream.close()

        # Drain queue to NumPy array
        chunks = []
        while not self.audio_queue.empty():
            chunks.append(self.audio_queue.get())
        return np.concatenate(chunks) if chunks else np.array([])
```

### Pattern 3: Runtime Session Detection (X11/Wayland)
**What:** Check environment variables to select appropriate text injector
**When to use:** Application startup, before initializing injection module
**Example:**
```python
# Source: https://www.cyberciti.biz/faq/howto-check-for-wayland-or-x11-with-my-linux-desktop/
import os
import subprocess

class SessionDetector:
    @staticmethod
    def get_session_type():
        """Detect X11 vs Wayland session"""
        # Primary method: XDG_SESSION_TYPE
        session_type = os.environ.get('XDG_SESSION_TYPE', '').lower()
        if session_type in ('x11', 'wayland'):
            return session_type

        # Fallback: check for WAYLAND_DISPLAY
        if os.environ.get('WAYLAND_DISPLAY'):
            return 'wayland'

        # Fallback: check for DISPLAY (X11)
        if os.environ.get('DISPLAY'):
            return 'x11'

        # Last resort: loginctl (systemd systems)
        try:
            result = subprocess.run(
                ['loginctl', 'show-session', '-p', 'Type'],
                capture_output=True, text=True, timeout=2
            )
            if 'Type=wayland' in result.stdout:
                return 'wayland'
            elif 'Type=x11' in result.stdout:
                return 'x11'
        except Exception:
            pass

        return 'unknown'

# Usage
injector = (WaylandInjector() if SessionDetector.get_session_type() == 'wayland'
            else X11Injector())
```

### Pattern 4: faster-whisper with INT8 Quantization
**What:** Load model with compute_type="int8" for CPU or "int8_float16" for GPU
**When to use:** Model initialization for local transcription
**Example:**
```python
# Source: https://github.com/SYSTRAN/faster-whisper
from faster_whisper import WhisperModel

class TranscriptionEngine:
    def __init__(self, model_size="base", device="cpu"):
        # INT8 quantization: 4x faster, lower memory
        compute_type = "int8" if device == "cpu" else "int8_float16"

        self.model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
            # Enable VAD for silence trimming
            vad_filter=True,
            vad_parameters={
                "threshold": 0.5,
                "min_speech_duration_ms": 250,
                "max_speech_duration_s": 30,
                "min_silence_duration_ms": 2000,
                "speech_pad_ms": 400
            }
        )

    def transcribe(self, audio_path, language=None):
        """
        Transcribe audio file (must be WAV, mono, 16kHz)
        language=None enables auto-detection
        """
        segments, info = self.model.transcribe(
            audio_path,
            language=language,  # None = auto-detect
            beam_size=5,
            vad_filter=True
        )

        # Join all segments
        return "".join(segment.text for segment in segments).strip()
```

### Pattern 5: Audio Format Conversion for faster-whisper
**What:** Save recorded NumPy array as WAV (mono, 16kHz) using scipy
**When to use:** After recording stops, before transcription
**Example:**
```python
# Source: https://docs.scipy.org/doc/scipy/reference/generated/scipy.io.wavfile.write.html
from scipy.io import wavfile
import numpy as np

class AudioProcessor:
    @staticmethod
    def save_for_whisper(audio_data, sample_rate, output_path):
        """
        Save NumPy array as WAV file for faster-whisper

        faster-whisper requirements:
        - Mono (single channel)
        - 16kHz sample rate
        - Will auto-resample, but pre-converting saves time
        """
        # Ensure mono
        if audio_data.ndim > 1:
            audio_data = audio_data.mean(axis=1)

        # Convert to int16 for WAV format
        if audio_data.dtype == np.float32 or audio_data.dtype == np.float64:
            audio_data = (audio_data * 32767).astype(np.int16)

        # Save as WAV
        wavfile.write(output_path, sample_rate, audio_data)
```

### Anti-Patterns to Avoid

- **Recording on main thread:** sounddevice blocking calls freeze event loop → Use callbacks + queue
- **Skipping state machine:** Manual boolean flags get complex with 4+ states → Use explicit states
- **Passing raw bytes to faster-whisper:** Model expects file path or NumPy array → Save to WAV first
- **Hardcoding X11 tools on Wayland:** xdotool fails silently → Runtime detection mandatory
- **Ignoring evdev permissions:** Daemon crashes on /dev/input access → Check input group membership

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Speech-to-text | Custom ML model, API wrapper | faster-whisper | Pre-optimized with INT8, VAD, multilingual support out-of-box |
| Keyboard monitoring | X11 XGrabKey, polling /dev/input | python-evdev | Handles device enumeration, event parsing, async reading |
| Audio capture | Direct ALSA/PulseAudio bindings | sounddevice | Cross-platform, handles device quirks, NumPy integration |
| State management | Boolean flags (is_recording, is_processing...) | State machine pattern | Prevents invalid transitions, self-documenting |
| WAV file I/O | Manual RIFF header construction | scipy.io.wavfile | Handles format variations, endianness, metadata |
| Text injection on Wayland | Custom uinput device creation | ydotool daemon | Persistent device avoids timing issues, handles layouts |

**Key insight:** Audio, input, and ML domains have sharp edges—device permissions, buffer timing, model formats. Use battle-tested libraries rather than reimplementing kernel interfaces.

## Common Pitfalls

### Pitfall 1: evdev Permission Denied on /dev/input/event*
**What goes wrong:** Daemon crashes immediately with "Permission denied" when trying to read keyboard events
**Why it happens:** /dev/input/event* devices have 0600 permissions (root-only by default)
**How to avoid:** Add user to `input` group: `sudo usermod -aG input $USER` (requires logout)
**Warning signs:**
- Error opening InputDevice: `[Errno 13] Permission denied: '/dev/input/event3'`
- `ls -l /dev/input/event*` shows `crw------- 1 root root`

### Pitfall 2: ydotool "Socket not found" or "Connection refused"
**What goes wrong:** Text injection fails silently or errors with socket connection issues
**Why it happens:** ydotoold daemon not running, or socket has wrong permissions
**How to avoid:**
1. Set up systemd user service (see example in Architecture Patterns)
2. Ensure `chmod 666 /tmp/.ydotool_socket` after daemon starts
3. Verify daemon running: `systemctl --user status ydotoold`
**Warning signs:**
- `Could not connect to socket /tmp/.ydotool_socket`
- ydotool commands hang or do nothing

### Pitfall 3: Audio Buffer Overflow During Recording
**What goes wrong:** Recording produces crackling, gaps, or "Input overflowed" errors
**Why it happens:** Audio callback blocks too long (e.g., doing transcription in callback)
**How to avoid:** Keep callback minimal—only copy data to queue, do all processing outside callback
**Warning signs:**
- sounddevice prints "Input overflow" during recording
- Audio playback has glitches/dropouts
- Callback doing heavy work (file I/O, network, transcription)

### Pitfall 4: faster-whisper Returns Gibberish for Incorrect Audio Format
**What goes wrong:** Transcription output is nonsense characters or wrong language
**Why it happens:** Passing non-16kHz audio, stereo instead of mono, or raw bytes instead of file
**How to avoid:** Always save as WAV with scipy.io.wavfile, ensure mono + 16kHz
**Warning signs:**
- Transcription output: random characters, wrong language detection
- Audio recorded at 44.1kHz or 48kHz without resampling
- Passing bytes or raw NumPy array to model.transcribe()

### Pitfall 5: Unicode/Emoji Not Typing with ydotool
**What goes wrong:** Non-ASCII characters (café, emoji 🎤) missing from typed output
**Why it happens:** ydotool `type` command only supports basic Latin characters (known limitation)
**How to avoid:**
- **If non-ASCII is critical:** Use clipboard + paste on Wayland (via wl-clipboard), not direct typing
- **Workaround:** Detect non-ASCII, fall back to clipboard paste for those chunks
- **Long-term:** Wait for ydotool Unicode support or use alternate injector
**Warning signs:**
- French accents (é, à) not appearing
- Emoji missing from output
- Text stops after first non-ASCII character

### Pitfall 6: evdev Selecting Wrong Keyboard Device
**What goes wrong:** Hotkeys not detected, or system beeps/power button events triggering recording
**Why it happens:** Multiple /dev/input/event* devices exist (keyboards, mice, power buttons, virtual devices)
**How to avoid:**
- Filter by device capabilities: check for `EV_KEY` capability
- Filter by name: avoid "power button", "sleep button", "lid switch"
- Prefer devices with phys (physical connection) attribute
- Consider allowing user to specify device path in config
**Warning signs:**
- Pressing F13 does nothing
- Random events trigger recording (lid close, power button)
- Multiple keyboards detected, wrong one chosen

### Pitfall 7: Daemon Cannot Access Audio in systemd User Service
**What goes wrong:** sounddevice fails to find audio devices or returns empty list
**Why it happens:** systemd user service not connected to PulseAudio/PipeWire user session
**How to avoid:**
- Ensure daemon runs in user session context (not system daemon)
- Use `systemctl --user` for daemon service
- Verify `PULSE_SERVER` or `PIPEWIRE_RUNTIME_DIR` environment variables set
**Warning signs:**
- `sd.query_devices()` returns empty list
- PulseAudio connection refused errors
- Daemon works when run manually, fails under systemd

### Pitfall 8: Race Condition Between Recording Stop and Transcription Start
**What goes wrong:** Transcription starts before all audio chunks written to queue
**Why it happens:** Stream.stop() returns before callback finishes processing final chunks
**How to avoid:**
- Add small delay after stop (e.g., 100ms) before draining queue
- Use stream.close() which blocks until callback finishes
- Check queue empty before proceeding: `while not queue.empty(): time.sleep(0.01)`
**Warning signs:**
- Transcription missing last word or two
- Intermittent short transcriptions
- Audio file size varies for same recording length

## Code Examples

Verified patterns from official sources:

### Selecting Keyboard Device with evdev
```python
# Source: https://python-evdev.readthedocs.io/en/latest/tutorial.html
import evdev
from evdev import ecodes

def find_keyboard_devices():
    """Find all keyboard input devices"""
    keyboards = []

    for path in evdev.list_devices():
        device = evdev.InputDevice(path)

        # Check if device has key event capability
        caps = device.capabilities()
        if ecodes.EV_KEY not in caps:
            continue

        # Filter out non-keyboard devices
        name_lower = device.name.lower()
        if any(x in name_lower for x in ['power', 'sleep', 'lid', 'video']):
            continue

        keyboards.append({
            'path': device.path,
            'name': device.name,
            'phys': device.phys
        })

    return keyboards

# Usage
keyboards = find_keyboard_devices()
if not keyboards:
    raise RuntimeError("No keyboard devices found")

# Use first keyboard (or let user choose)
device = evdev.InputDevice(keyboards[0]['path'])
print(f"Monitoring: {device.name}")
```

### Monitoring Hotkey Press/Release with evdev
```python
# Source: https://python-evdev.readthedocs.io/en/latest/tutorial.html
import evdev
from evdev import ecodes, categorize

device = evdev.InputDevice('/dev/input/event3')

# Map F13 key
HOTKEY = ecodes.KEY_F13

for event in device.read_loop():
    if event.type == ecodes.EV_KEY:
        key_event = categorize(event)

        if event.code == HOTKEY:
            if event.value == 1:  # Key down
                print("Hotkey pressed - start recording")
                # Trigger state machine: start_recording()
            elif event.value == 0:  # Key up
                print("Hotkey released - stop recording")
                # Trigger state machine: stop_recording()
```

### Recording Audio with sounddevice Queue Pattern
```python
# Source: https://python-sounddevice.readthedocs.io/
import sounddevice as sd
import numpy as np
import queue

# Constants for faster-whisper compatibility
SAMPLE_RATE = 16000
CHANNELS = 1  # Mono

audio_queue = queue.Queue()

def audio_callback(indata, frames, time, status):
    """Called from audio thread - MUST NOT BLOCK"""
    if status:
        print(f"Audio callback status: {status}", flush=True)
    # Copy data to queue (copy required, indata is reused)
    audio_queue.put(indata.copy())

# Start recording
stream = sd.InputStream(
    samplerate=SAMPLE_RATE,
    channels=CHANNELS,
    callback=audio_callback
)
stream.start()

# ... wait for hotkey release ...

# Stop recording
stream.stop()
stream.close()

# Collect all chunks
chunks = []
while not audio_queue.empty():
    chunks.append(audio_queue.get())

audio_data = np.concatenate(chunks, axis=0) if chunks else np.array([])
print(f"Recorded {len(audio_data)} samples ({len(audio_data)/SAMPLE_RATE:.2f}s)")
```

### Saving Audio for faster-whisper
```python
# Source: https://docs.scipy.org/doc/scipy/reference/generated/scipy.io.wavfile.write.html
from scipy.io import wavfile
import numpy as np
import tempfile

def save_audio_for_whisper(audio_data, sample_rate=16000):
    """
    Save NumPy array as WAV file for faster-whisper
    Returns: path to temporary WAV file
    """
    # Ensure mono
    if audio_data.ndim > 1:
        audio_data = audio_data.mean(axis=1)

    # Convert float to int16 for WAV
    if audio_data.dtype in (np.float32, np.float64):
        # Normalize to [-1, 1] then scale to int16 range
        audio_data = np.clip(audio_data, -1.0, 1.0)
        audio_data = (audio_data * 32767).astype(np.int16)

    # Save to temp file
    fd, path = tempfile.mkstemp(suffix='.wav')
    wavfile.write(path, sample_rate, audio_data)

    return path

# Usage
audio_file = save_audio_for_whisper(audio_data, SAMPLE_RATE)
# Now ready for faster-whisper transcription
```

### Transcribing with faster-whisper (INT8, VAD)
```python
# Source: https://github.com/SYSTRAN/faster-whisper
from faster_whisper import WhisperModel

# Initialize model (do this once at startup)
model = WhisperModel(
    "base",  # Options: tiny, base, small, medium, large-v3
    device="cpu",
    compute_type="int8",  # INT8 quantization for speed
)

# Transcribe audio file
segments, info = model.transcribe(
    "audio.wav",
    language=None,  # Auto-detect language
    beam_size=5,
    vad_filter=True,  # Enable voice activity detection
    vad_parameters={
        "threshold": 0.5,
        "min_speech_duration_ms": 250,
        "min_silence_duration_ms": 2000,
    }
)

# Collect transcription
text = "".join(segment.text for segment in segments).strip()
print(f"Detected language: {info.language} (probability: {info.language_probability:.2f})")
print(f"Transcription: {text}")
```

### Text Injection with ydotool (Wayland)
```python
# Source: https://github.com/ReimuNotMoe/ydotool
import subprocess
import os

class YdotoolInjector:
    def __init__(self):
        # Verify daemon is running
        socket_path = os.environ.get('YDOTOOL_SOCKET', '/tmp/.ydotool_socket')
        if not os.path.exists(socket_path):
            raise RuntimeError(
                f"ydotoold socket not found at {socket_path}. "
                "Ensure daemon is running: systemctl --user status ydotoold"
            )

    def type_text(self, text, delay_ms=12):
        """
        Type text using ydotool

        WARNING: Only supports basic Latin characters.
        Non-ASCII (café, emoji) will be missing from output.
        """
        try:
            subprocess.run(
                ['ydotool', 'type', '--key-delay', str(delay_ms), '--', text],
                check=True,
                timeout=10
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("ydotool type command timed out")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"ydotool failed: {e}")

# Usage
injector = YdotoolInjector()
injector.type_text("Hello from LinuxWhisper!")
```

### Text Injection with xdotool (X11 fallback)
```python
# Source: https://www.semicomplete.com/projects/xdotool/
import subprocess
import os

class XdotoolInjector:
    def __init__(self):
        # Verify running on X11
        if not os.environ.get('DISPLAY'):
            raise RuntimeError("DISPLAY not set - not running on X11")

    def type_text(self, text, delay_ms=12):
        """
        Type text using xdotool

        Better Unicode support than ydotool, but requires X11.
        """
        try:
            subprocess.run(
                ['xdotool', 'type', '--delay', str(delay_ms), '--', text],
                check=True,
                timeout=10,
                env={**os.environ, 'LANG': 'en_US.UTF-8'}  # Ensure UTF-8 locale
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("xdotool type command timed out")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"xdotool failed: {e}")

# Usage
injector = XdotoolInjector()
injector.type_text("Café ☕")  # Unicode works better than ydotool
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| PyAudio for recording | sounddevice | 2020+ | NumPy arrays, simpler API, better maintained |
| openai-whisper | faster-whisper | 2023+ | 4x speed improvement, INT8 quantization |
| Manual Wayland input | ydotool daemon | 2021+ (v1.0) | Persistent device avoids timing issues |
| xdotool on Wayland | Doesn't work | Wayland architecture | Must use ydotool or kernel-level tools |
| X11-only hotkeys | evdev | Ongoing | Works on both X11 and Wayland |
| Manual state tracking | State machine libraries | Modern best practice | Clearer code, validates transitions |

**Deprecated/outdated:**
- **PyAudio**: Still works but sounddevice is more Pythonic and actively maintained
- **python-xlib for hotkeys**: X11-only, doesn't work on Wayland
- **Whisper API calls**: Project requirements specify local-only (privacy)
- **Running audio daemons as system services**: PulseAudio/PipeWire require user session context

## Open Questions

1. **evdev device selection algorithm**
   - What we know: Filter by EV_KEY capability, exclude power/sleep buttons
   - What's unclear: Best heuristic for multiple physical keyboards, handling hot-plug
   - Recommendation: Start with first valid keyboard, add config option for manual override in Phase 1

2. **Non-ASCII text handling**
   - What we know: ydotool has limited Unicode support (Latin-only), xdotool better but not perfect
   - What's unclear: How often users dictate emoji/accented characters, acceptable fallback UX
   - Recommendation: Implement basic ASCII-only for Phase 2, document limitation, consider clipboard paste workaround in future phase

3. **Model size selection**
   - What we know: faster-whisper models range from tiny (39MB) to large-v3 (1.5GB)
   - What's unclear: User hardware specs, acceptable transcription latency
   - Recommendation: Default to "base" model (good accuracy/speed balance), make configurable

4. **VAD parameter tuning**
   - What we know: Default min_silence_duration_ms=2000 (2s), threshold=0.5
   - What's unclear: Optimal settings for dictation (vs. long-form transcription)
   - Recommendation: Use defaults initially, collect user feedback on "cut off" issues

5. **Audio cleanup on daemon shutdown**
   - What we know: Save temporary WAV files during transcription
   - What's unclear: When to delete temp files (immediately, on next recording, on shutdown?)
   - Recommendation: Delete after successful transcription, keep on error for debugging

## Sources

### Primary (HIGH confidence)
- [python-evdev tutorial](https://python-evdev.readthedocs.io/en/latest/tutorial.html) - Device selection, key event monitoring
- [python-evdev API reference](https://python-evdev.readthedocs.io/en/latest/apidoc.html) - Device capabilities, event codes
- [faster-whisper README](https://github.com/SYSTRAN/faster-whisper) - INT8 quantization, model loading, VAD
- [faster-whisper VAD documentation](https://deepwiki.com/SYSTRAN/faster-whisper/5.2-voice-activity-detection) - VAD parameters, Silero VAD integration
- [python-sounddevice documentation](https://python-sounddevice.readthedocs.io/) - Recording with callbacks, device selection
- [scipy.io.wavfile.write](https://docs.scipy.org/doc/scipy/reference/generated/scipy.io.wavfile.write.html) - WAV file format, NumPy array conversion
- [ydotool README](https://github.com/ReimuNotMoe/ydotool) - Daemon setup, text typing, uinput permissions

### Secondary (MEDIUM confidence)
- [Session detection methods](https://www.cyberciti.biz/faq/howto-check-for-wayland-or-x11-with-my-linux-desktop/) - XDG_SESSION_TYPE, WAYLAND_DISPLAY, loginctl
- [evdev permissions setup](https://bbs.archlinux.org/viewtopic.php?id=273094) - udev rules, input group configuration
- [ydotool systemd user service](https://gist.github.com/danielrosehill/330230022d964c5fb44799240ed63b97) - Service file example, socket permissions
- [python-statemachine](https://github.com/fgmacedo/python-statemachine) - State machine pattern implementation
- [PipeWire user session](https://wiki.archlinux.org/title/PipeWire) - D-Bus integration, systemd user services
- [sounddevice threading](https://github.com/spatialaudio/python-sounddevice/issues/187) - Thread safety, queue-based callbacks
- [faster-whisper audio requirements](https://github.com/openai/whisper/discussions/870) - 16kHz sample rate, mono channel

### Tertiary (LOW confidence - community reports)
- [ydotool Unicode limitation](https://github.com/ReimuNotMoe/ydotool/issues/249) - Latin-only support, emoji not working
- [xdotool UTF-8 support](https://github.com/jordansissel/xdotool/issues/154) - Unicode handling, locale requirements
- [PyAudio vs sounddevice discussion](https://forums.raspberrypi.com/viewtopic.php?t=269420) - API complexity comparison
- [TalkType example project](https://github.com/lmacan1/talktype) - Similar push-to-talk implementation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries verified from official docs, widely used for these use cases
- Architecture: HIGH - Patterns verified from official documentation and real-world projects
- Pitfalls: MEDIUM-HIGH - Based on official docs, GitHub issues, and community reports (some need hands-on validation)
- Non-ASCII handling: MEDIUM - Confirmed limitation but workaround strategies need testing
- Device selection algorithm: MEDIUM - General approach verified, edge cases need hands-on testing

**Research date:** 2026-02-15
**Valid until:** ~30 days (stable domain - libraries mature, no fast-moving changes expected)
