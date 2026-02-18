---
phase: 04-transcription-features
plan: 01
status: complete
started: 2026-02-18
completed: 2026-02-18
duration: 3 min
commit: 108f206
---

# Summary: Config validation, numpy passthrough, sentence formatting, model hot-reload

## What was done

**Task 1 — Config, engine, formatting:**
- Added `sentence_format: True` default to `DEFAULT_CONFIG`
- Added `VALID_MODEL_SIZES` set (8 models: tiny/base/small/medium + .en variants)
- Added model validation to `validate_config_input()`
- Updated `TranscriptionEngine.transcribe()` to accept `Union[str, np.ndarray]` with 2D squeeze
- Created `formatting.py` with `format_sentence()` — capitalizes first char, adds trailing period
- Updated `transcription/__init__.py` exports

**Task 2 — Pipeline and lifecycle wiring:**
- Replaced WAV file save/transcribe/unlink with direct numpy array passthrough in `_process_recording()`
- Added `format_sentence()` call before text injection (gated by `sentence_format` config)
- Added `reload_model()` method to `DictationPipeline` — checks IDLE state, unloads, gc.collect, reloads
- Added `model_changed` detection to `reload_config_safe()` in lifecycle
- Wired `pipeline.reload_model()` call on model config change via SIGHUP

## Deviations

None.

## Must-haves verification

| # | Truth | Status |
|---|-------|--------|
| 1 | User can set model to valid sizes in config.toml | PASS — VALID_MODEL_SIZES validates 8 sizes |
| 2 | Invalid model value rejected with clear error | PASS — validate_config_input returns error string |
| 3 | Whisper model loads once at startup, stays in memory | PASS — unchanged from Phase 2 |
| 4 | Transcription passes numpy data directly | PASS — no WAV file in _process_recording |
| 5 | Dictated text capitalized with trailing period | PASS — format_sentence verified |
| 6 | sentence_format defaults to true, configurable | PASS — in DEFAULT_CONFIG |
| 7 | SIGHUP hot-reloads model without restart | PASS — lifecycle detects model_changed, calls reload_model |
| 8 | Model hot-reload only when IDLE | PASS — reload_model checks state |
