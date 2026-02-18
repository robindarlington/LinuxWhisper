# Phase 4: Transcription Features - Research

**Researched:** 2026-02-18
**Domain:** Whisper model management, transcription optimization, text post-processing
**Confidence:** HIGH

## Summary

Phase 4 addresses three concerns: configurable model selection, persistent in-memory model loading, and sentence formatting. The good news is that the existing codebase already has most of the infrastructure in place. The `TranscriptionEngine` class already separates `__init__` from `load_model()`, already supports `model_size` as a constructor parameter, and the `DictationPipeline.start()` already pre-loads the model at daemon startup. The config system already has a `model` key in `DEFAULT_CONFIG` (`"base.en"`). What is missing: (1) config validation for the `model` field, (2) model reload on SIGHUP when the model size changes, (3) sentence formatting post-processing, and (4) direct numpy array pass-through to avoid the WAV file intermediary.

The `.en` model variants (tiny.en, base.en, small.en, medium.en) are English-only and slightly faster/more accurate for English than their multilingual counterparts. The current default `"base.en"` is a reasonable default. All model sizes from tiny through medium are appropriate for CPU use with INT8 quantization.

**Primary recommendation:** Add model validation to config, implement model hot-reload on SIGHUP (unload old + load new), add a sentence formatting post-processor, and pass numpy arrays directly to `transcribe()` to eliminate WAV file I/O overhead.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TRANS-02 | User can select Whisper model size (tiny, base, small, medium) via config | Config already has `model` key; needs validation of allowed values and `.en` variants |
| TRANS-03 | Whisper model stays loaded in memory via daemon (sub-500ms response) | Model already pre-loaded at startup; needs numpy passthrough to eliminate WAV I/O overhead, and model hot-reload on config change |
| TRANS-04 | Full sentence mode auto-capitalizes first word and adds period at end | Needs new post-processing step in pipeline between transcription and injection |
</phase_requirements>

## Standard Stack

### Core (already installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| faster-whisper | 1.2.1 | Speech-to-text transcription | Already in project; CTranslate2 backend, 4x faster than openai/whisper |
| numpy | (dep) | Audio data arrays | Already used by AudioRecorder and faster-whisper |

### Supporting (no new dependencies needed)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| gc (stdlib) | - | Garbage collection for model unload | When switching model sizes at runtime |
| re (stdlib) | - | Regex for sentence formatting | For capitalization/punctuation post-processing |

### No New Dependencies
This phase requires zero new pip packages. All work is internal refactoring and post-processing logic using existing libraries.

## Architecture Patterns

### Current Architecture (What Already Exists)

```
config.toml              TranscriptionEngine         DictationPipeline
  model = "base.en"  -->   __init__(model_size)  -->   start() calls engine.load_model()
                           load_model()                _process_recording() calls engine.transcribe(wav_path)
                           transcribe(audio_path)      stop() calls engine.unload_model()
                           unload_model()
```

**Key files and their roles:**
- `src/linuxwhisper/config/defaults.py` -- `DEFAULT_CONFIG["model"] = "base.en"` (already exists)
- `src/linuxwhisper/transcription/engine.py` -- `TranscriptionEngine` with load/unload/transcribe
- `src/linuxwhisper/pipeline/coordinator.py` -- Creates engine, pre-loads model, orchestrates pipeline
- `src/linuxwhisper/daemon/lifecycle.py` -- `reload_config_safe()` detects config changes, updates pipeline
- `src/linuxwhisper/config/validation.py` -- `validate_config_input()` validates hotkey/mode (no model validation yet)

### Pattern 1: Model Validation in Config
**What:** Add model size validation to `validate_config_input()` in `validation.py`
**When to use:** Every config load and reload
**Example:**
```python
# In config/validation.py
VALID_MODEL_SIZES = {
    "tiny", "tiny.en",
    "base", "base.en",
    "small", "small.en",
    "medium", "medium.en",
}

def validate_config_input(config: dict) -> list[str]:
    errors: list[str] = []
    # ... existing hotkey/mode validation ...

    # Validate model size
    model = config.get("model", "base.en")
    if model not in VALID_MODEL_SIZES:
        errors.append(
            f"Invalid model: '{model}'. "
            f"Valid models: {', '.join(sorted(VALID_MODEL_SIZES))}"
        )

    return errors
```

### Pattern 2: Model Hot-Reload on SIGHUP
**What:** Detect model change in `reload_config_safe()`, unload old model, load new one
**When to use:** When user changes `model` in config.toml and sends SIGHUP
**Example:**
```python
# In daemon/lifecycle.py -- reload_config_safe()
model_changed = _current_config.get("model") != new_config.get("model")

if model_changed:
    logger.info(
        f"Model changed: {_current_config.get('model')} -> {new_config.get('model')}"
    )

# In pipeline/coordinator.py -- new method
def reload_model(self, new_model_size: str) -> None:
    """Reload whisper model with new size. Only call when IDLE."""
    if self._state != PipelineState.IDLE:
        logger.warning("Cannot reload model: pipeline not idle")
        return

    logger.info(f"Reloading model: {self._engine.model_size} -> {new_model_size}")
    self._engine.unload_model()

    import gc
    gc.collect()

    self._engine = TranscriptionEngine(model_size=new_model_size)
    self._engine.load_model()
    logger.info(f"Model reloaded: {new_model_size}")
```

### Pattern 3: Direct Numpy Array Transcription (Eliminate WAV I/O)
**What:** Pass numpy audio data directly to `transcribe()` instead of saving to WAV first
**When to use:** In `_process_recording()` -- eliminates temp file creation and deletion
**Why:** faster-whisper 1.2.1 accepts `Union[str, BinaryIO, np.ndarray]` for the audio parameter. The current code saves a WAV file then reads it back -- unnecessary disk I/O.
**Example:**
```python
# In pipeline/coordinator.py -- _process_recording()
# CURRENT (wasteful):
wav_path = self._recorder.save_wav(audio_data)
text = self._engine.transcribe(wav_path)
os.unlink(wav_path)

# NEW (direct):
text = self._engine.transcribe(audio_data)
```

**Important caveat:** The audio data from AudioRecorder is float32 with shape `(N, 1)` for mono. faster-whisper expects a 1D float32 array at 16kHz. Need to squeeze the channel dimension:
```python
# Ensure 1D array for faster-whisper
if audio_data.ndim > 1:
    audio_data = audio_data.squeeze()
text = self._engine.transcribe(audio_data)
```

### Pattern 4: Sentence Formatting Post-Processor
**What:** Capitalize first letter and add trailing period for "full sentence" mode
**When to use:** After transcription, before injection
**Example:**
```python
def format_sentence(text: str) -> str:
    """Auto-capitalize first word and add trailing period."""
    text = text.strip()
    if not text:
        return text

    # Capitalize first character
    text = text[0].upper() + text[1:]

    # Add period if no terminal punctuation
    if text[-1] not in ".!?":
        text += "."

    return text
```

### Recommended File Changes Summary

```
src/linuxwhisper/
├── config/
│   ├── defaults.py          # No changes needed (model key already exists)
│   └── validation.py        # ADD: model size validation to validate_config_input()
├── transcription/
│   ├── engine.py            # MODIFY: accept numpy arrays directly in transcribe()
│   └── formatting.py        # NEW: sentence formatting post-processor
├── pipeline/
│   └── coordinator.py       # MODIFY: pass numpy directly, add reload_model(), apply formatting
└── daemon/
    └── lifecycle.py         # MODIFY: detect model changes in reload_config_safe()
```

### Anti-Patterns to Avoid
- **Re-creating the entire pipeline on model change:** The pipeline has many components (hotkey detector, audio recorder, injector). Only the engine needs to change. Do NOT destroy and recreate `DictationPipeline`.
- **Loading model in TranscriptionEngine.__init__:** Model loading is slow (seconds). Keep it separate from construction so the daemon controls timing.
- **Blocking SIGHUP handler with model load:** Model loading takes 1-5 seconds depending on size. The SIGHUP handler runs in the signal handler context. Defer the actual model reload to the main loop or use a flag.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Audio format conversion | Custom WAV encoder/decoder | Pass numpy array directly to `transcribe()` | faster-whisper accepts numpy natively; WAV round-trip is pure overhead |
| Model download/caching | Custom download manager | faster-whisper's built-in HuggingFace Hub download | Models auto-download on first use, cached in `~/.cache/huggingface/hub` |
| Language detection | Custom language detector | faster-whisper's built-in auto-detection | Set `language=None` or `language="en"` -- it handles the rest |
| VAD (Voice Activity Detection) | Custom silence detection | faster-whisper's `vad_filter=True` with Silero VAD | Already configured in current `transcribe()` call with good parameters |

**Key insight:** The transcription engine is already well-built. This phase is about config plumbing, model lifecycle management, and a thin post-processing layer -- not about changing the transcription logic itself.

## Common Pitfalls

### Pitfall 1: SIGHUP Model Reload During Active Transcription
**What goes wrong:** If a SIGHUP arrives while the pipeline is PROCESSING (transcribing), unloading the model mid-transcribe causes a crash or corrupted output.
**Why it happens:** Signal handlers can fire at any point.
**How to avoid:** The existing `reload_config_safe()` already defers when pipeline is not IDLE. Model reload MUST follow the same pattern -- only reload when `pipeline.state == PipelineState.IDLE`.
**Warning signs:** Segfault or `RuntimeError` during transcription after a reload.

### Pitfall 2: Memory Not Freed After Model Unload
**What goes wrong:** After `del model`, CTranslate2 memory may not be immediately freed. Loading a larger model may fail with OOM.
**Why it happens:** Python garbage collector doesn't immediately free native (C++) memory.
**How to avoid:** Call `gc.collect()` after `del model` / `unload_model()`. On CPU (this project's primary target), this is less critical than GPU, but still good practice.
**Warning signs:** Memory usage keeps growing across model switches.

### Pitfall 3: First Model Download Blocks Daemon Startup
**What goes wrong:** On first run with a new model size, faster-whisper downloads the model from HuggingFace Hub (can be hundreds of MB). This blocks startup for minutes.
**Why it happens:** `WhisperModel()` constructor triggers download if model not in cache.
**How to avoid:** This is acceptable behavior -- document it. The download only happens once per model size. Log a clear message like "Downloading model 'small.en' (first use)..." so users know what is happening.
**Warning signs:** Daemon appears to hang on first start after changing model size.

### Pitfall 4: Audio Array Shape Mismatch
**What goes wrong:** Passing a 2D array `(N, 1)` from AudioRecorder to faster-whisper which expects 1D `(N,)`.
**Why it happens:** `sounddevice.InputStream` produces `(frames, channels)` shape even for mono.
**How to avoid:** Squeeze the array: `audio_data.squeeze()` or `audio_data.flatten()` before passing to `transcribe()`.
**Warning signs:** Shape error or silent incorrect transcription.

### Pitfall 5: Sentence Formatting Breaks Multi-Sentence Output
**What goes wrong:** Whisper sometimes returns multiple sentences. Naively capitalizing only the first character and adding one period misses internal sentences.
**Why it happens:** Whisper's output for longer recordings may contain multiple natural sentences.
**How to avoid:** Whisper already handles internal punctuation well. The formatting should only ensure the FIRST character is uppercase and the LAST character has terminal punctuation. Do NOT try to split and reformat internal sentences.
**Warning signs:** Text like "hello world. this is a test" becomes "Hello world. this is a test." (correct -- internal "this" stays lowercase because Whisper put the period there, and we just fix the boundaries).

## Code Examples

### Current Engine (verified from source)
```python
# Source: src/linuxwhisper/transcription/engine.py (lines 14-48)
class TranscriptionEngine:
    def __init__(self, model_size: str = "base.en", device: str = "cpu"):
        self.model_size = model_size
        self.device = device
        self.compute_type = "int8" if device == "cpu" else "int8_float16"
        self._model: Optional[WhisperModel] = None

    def load_model(self) -> None:
        self._model = WhisperModel(
            self.model_size, device=self.device, compute_type=self.compute_type
        )

    def transcribe(self, audio_path: str, language: Optional[str] = None) -> str:
        if self._model is None:
            self.load_model()
        segments, info = self._model.transcribe(
            audio_path, language=language, beam_size=5,
            vad_filter=True, vad_parameters={...},
        )
        text = "".join(seg.text for seg in segments).strip()
        return text
```

### Updated Engine Signature (for numpy passthrough)
```python
# Updated transcribe to accept numpy arrays directly
def transcribe(
    self,
    audio: Union[str, "np.ndarray"],
    language: Optional[str] = None,
) -> str:
    """Transcribe audio to text.

    Args:
        audio: Path to audio file OR numpy array of float32 samples at 16kHz
        language: Language code or None for auto-detection
    """
    if self._model is None:
        self.load_model()

    # Ensure numpy arrays are 1D
    if isinstance(audio, np.ndarray) and audio.ndim > 1:
        audio = audio.squeeze()

    segments, info = self._model.transcribe(
        audio, language=language, beam_size=5,
        vad_filter=True, vad_parameters={...},
    )
    text = "".join(seg.text for seg in segments).strip()
    return text
```

### Config Validation for Model
```python
# Source: pattern derived from existing validate_config_input()
VALID_MODEL_SIZES = {
    "tiny", "tiny.en",
    "base", "base.en",
    "small", "small.en",
    "medium", "medium.en",
}

# In validate_config_input():
model = config.get("model", "base.en")
if model not in VALID_MODEL_SIZES:
    errors.append(
        f"Invalid model: '{model}'. "
        f"Valid models: {', '.join(sorted(VALID_MODEL_SIZES))}"
    )
```

### Pipeline Process Recording (numpy passthrough)
```python
# Updated _process_recording in coordinator.py
def _process_recording(self) -> None:
    try:
        self._cancel_timeout()
        audio_data = self._recorder.stop()

        min_samples = int(self._recorder.sample_rate * 0.1)
        if audio_data is None or len(audio_data) < min_samples:
            logger.info("Recording too short, discarding")
            self._transition(PipelineState.IDLE)
            return

        # Pass numpy array directly -- no WAV file needed
        text = self._engine.transcribe(audio_data)

        if not text or not text.strip():
            logger.info("Empty transcription, skipping injection")
            self._transition(PipelineState.IDLE)
            return

        # Apply sentence formatting
        text = format_sentence(text)

        self._transition(PipelineState.INJECTING)
        self._injector.type_text(text)
        logger.info(f"Dictation complete: '{text}'")
        self._transition(PipelineState.IDLE)
    except Exception as e:
        logger.error(f"Error during dictation processing: {e}", exc_info=True)
        self._transition(PipelineState.IDLE)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Save WAV, pass path to transcribe | Pass numpy array directly | faster-whisper has always supported this | Eliminates disk I/O, saves ~5-10ms per transcription |
| Reload entire daemon for model change | Hot-reload model via SIGHUP | Phase 4 (new) | Users can switch models without restarting daemon |
| Raw Whisper output injected as-is | Sentence-formatted output | Phase 4 (new) | Proper capitalization and punctuation |

## Whisper Model Reference

| Model | Parameters | Disk Size | RAM (INT8) | English-Only Variant | Speed (relative) |
|-------|-----------|-----------|------------|---------------------|-------------------|
| tiny | 39M | ~75MB | ~150MB | tiny.en | Fastest |
| base | 74M | ~150MB | ~250MB | base.en | Fast |
| small | 244M | ~500MB | ~500MB | small.en | Moderate |
| medium | 769M | ~1.5GB | ~1GB | medium.en | Slow |

**Notes:**
- `.en` variants are English-only, slightly more accurate and faster for English
- INT8 quantization (already used by this project) roughly halves memory vs float32
- All sizes download from HuggingFace Hub on first use, cached in `~/.cache/huggingface/hub`
- Model loading time: tiny ~1s, base ~1-2s, small ~2-3s, medium ~3-5s (CPU, varies by hardware)

## Open Questions

1. **Should "large" models be allowed?**
   - What we know: large-v3 is 1.5B params, needs ~3GB RAM with INT8. This is a desktop app, users might have the RAM.
   - What's unclear: Whether the performance hit (10+ second transcription) is acceptable for a dictation tool
   - Recommendation: Exclude for now. The requirement says "tiny, base, small, medium". Add large in a future phase if requested.

2. **Should sentence formatting be opt-in or always-on?**
   - What we know: TRANS-04 says "full sentence mode" -- implies it is a mode, not always-on
   - What's unclear: Whether users want a config toggle or if it should just always apply
   - Recommendation: Make it a config option (`sentence_format = true` default true) so users can disable if they want raw output (e.g., for note-taking where fragments are fine).

3. **Should the transcribe method accept language from config?**
   - What we know: The engine currently passes `language=None` (auto-detect). The `.en` models already imply English.
   - What's unclear: Whether to add a `language` config key
   - Recommendation: Defer. The `.en` model suffix handles English. Multi-language is a v2 feature (ADV-03). For now, `.en` models force English, multilingual models auto-detect.

## Sources

### Primary (HIGH confidence)
- faster-whisper 1.2.1 installed in project venv -- verified via `pip show` and `help()`
- `WhisperModel.__init__` signature -- verified via Python `inspect`
- `WhisperModel.transcribe` signature -- verified via Python `inspect`
- numpy array input support -- verified from source: `if not isinstance(audio, np.ndarray): audio = decode_audio(...)`
- Project source code (all files under `src/linuxwhisper/`) -- read directly

### Secondary (MEDIUM confidence)
- [SYSTRAN/faster-whisper GitHub README](https://github.com/SYSTRAN/faster-whisper) -- model sizes, benchmarks, API overview
- [faster-whisper unload discussion #431](https://github.com/SYSTRAN/faster-whisper/discussions/431) -- model unload pattern (del + gc.collect)
- [Whisper model sizes and parameters](https://whisper-api.com/blog/models/) -- parameter counts, memory usage

### Tertiary (LOW confidence)
- RAM estimates for INT8 models are approximate (derived from float32 sizes / 2, not measured)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new deps, all verified from installed packages
- Architecture: HIGH -- all patterns derived from reading actual source code, not hypothetical
- Pitfalls: HIGH -- signal handling and model lifecycle patterns are well-understood
- Model sizes/memory: MEDIUM -- parameter counts from official docs, RAM estimates are approximate
- Sentence formatting: HIGH -- simple string manipulation, well-defined requirements

**Research date:** 2026-02-18
**Valid until:** 2026-03-18 (stable domain, faster-whisper API unlikely to break)
