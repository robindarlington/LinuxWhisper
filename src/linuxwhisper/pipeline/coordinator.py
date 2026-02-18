"""Pipeline coordinator that orchestrates the dictation workflow."""

import logging
import os
import threading

from linuxwhisper.audio import AudioRecorder
from linuxwhisper.hotkey import HotkeyDetector, check_input_permissions, get_permission_instructions
from linuxwhisper.injection import create_injector
from linuxwhisper.transcription import TranscriptionEngine
from .states import PipelineState, VALID_TRANSITIONS

logger = logging.getLogger(__name__)


class DictationPipeline:
    """Coordinates hotkey detection, audio recording, transcription, and text injection."""

    def __init__(self, config: dict):
        """Initialize pipeline components from config.

        Args:
            config: Configuration dictionary with keys:
                - hotkey: Key to trigger dictation (default: "F13")
                - model: Whisper model size (default: "base.en")
                - audio.sample_rate: Audio sample rate (default: 16000)
                - audio.channels: Audio channels (default: 1)
        """
        # Extract config values with defaults
        hotkey = config.get("hotkey", "F13")
        model = config.get("model", "base.en")
        audio_config = config.get("audio", {})
        sample_rate = audio_config.get("sample_rate", 16000)
        channels = audio_config.get("channels", 1)

        # Create component instances
        self._detector = HotkeyDetector(hotkey=hotkey)
        self._recorder = AudioRecorder(sample_rate=sample_rate, channels=channels)
        self._engine = TranscriptionEngine(model_size=model)
        self._injector = create_injector()

        # State machine
        self._state = PipelineState.IDLE
        self._running = False
        self._hotkey_thread = None

        logger.info(f"DictationPipeline initialized (hotkey={hotkey}, model={model})")

    def _validate_transition(self, new_state: PipelineState) -> bool:
        """Validate if transition from current state to new state is allowed.

        Args:
            new_state: Target state

        Returns:
            True if transition is valid, False otherwise
        """
        if new_state in VALID_TRANSITIONS.get(self._state, set()):
            return True

        logger.warning(f"Invalid state transition: {self._state.name} -> {new_state.name}")
        return False

    def _transition(self, new_state: PipelineState) -> None:
        """Transition to a new state if valid.

        Args:
            new_state: Target state
        """
        if self._validate_transition(new_state):
            old_state = self._state
            self._state = new_state
            logger.info(f"Pipeline: {old_state.name} -> {new_state.name}")

    def _on_hotkey_press(self) -> None:
        """Handle hotkey press event - start recording."""
        if self._state == PipelineState.IDLE:
            self._transition(PipelineState.RECORDING)
            self._recorder.start()
            logger.info("Recording started")

    def _on_hotkey_release(self) -> None:
        """Handle hotkey release event - stop recording and process audio."""
        if self._state != PipelineState.RECORDING:
            return

        try:
            # Stop recording and get audio data
            self._transition(PipelineState.PROCESSING)
            audio_data = self._recorder.stop()

            # Check if recording is too short
            min_samples = int(self._recorder.sample_rate * 0.1)  # 0.1 seconds
            if audio_data is None or len(audio_data) < min_samples:
                logger.info("Recording too short, discarding")
                self._transition(PipelineState.IDLE)
                return

            # Save as temporary WAV file
            wav_path = self._recorder.save_wav(audio_data)
            logger.debug(f"Audio saved to {wav_path}")

            # Transcribe audio
            text = self._engine.transcribe(wav_path)

            # Clean up temporary file
            try:
                os.unlink(wav_path)
            except OSError as e:
                logger.warning(f"Failed to delete temp WAV file {wav_path}: {e}")

            # Check if transcription is empty
            if not text or not text.strip():
                logger.info("Empty transcription, skipping injection")
                self._transition(PipelineState.IDLE)
                return

            # Inject transcribed text
            self._transition(PipelineState.INJECTING)
            self._injector.type_text(text)
            logger.info(f"Dictation complete: '{text}'")

            # Return to idle
            self._transition(PipelineState.IDLE)

        except Exception as e:
            logger.error(f"Error during dictation processing: {e}", exc_info=True)
            self._transition(PipelineState.IDLE)

    def _run_hotkey_loop(self) -> None:
        """Run the hotkey detector loop in a thread."""
        try:
            self._detector.start(
                on_press=self._on_hotkey_press,
                on_release=self._on_hotkey_release
            )
        except Exception as e:
            logger.error(f"Hotkey detector error: {e}", exc_info=True)
            if self._running:
                logger.error("Hotkey detector stopped unexpectedly")

    def start(self) -> None:
        """Start the dictation pipeline.

        Raises:
            RuntimeError: If input permissions are not available
        """
        # Check input permissions
        if not check_input_permissions():
            error_msg = f"Input permissions not available.\n{get_permission_instructions()}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        # Pre-load Whisper model (do this at start so first dictation is fast)
        logger.info("Loading Whisper model...")
        self._engine.load_model()

        logger.info("Dictation pipeline started")
        self._running = True

        # Start hotkey detector in daemon thread
        self._hotkey_thread = threading.Thread(
            target=self._run_hotkey_loop,
            daemon=True
        )
        self._hotkey_thread.start()

    def stop(self) -> None:
        """Stop the dictation pipeline."""
        self._running = False

        # Stop hotkey detector
        self._detector.stop()

        # Stop recording if in progress
        if self._recorder.is_recording:
            self._recorder.stop()

        # Unload model
        self._engine.unload_model()

        logger.info("Dictation pipeline stopped")

    @property
    def state(self) -> PipelineState:
        """Get current pipeline state.

        Returns:
            Current PipelineState
        """
        return self._state
