"""Pipeline coordinator that orchestrates the dictation workflow."""

import logging
import os
import threading

from linuxwhisper.audio import AudioRecorder
from linuxwhisper.hotkey import HotkeyDetector, check_input_permissions, get_permission_instructions
from linuxwhisper.injection import create_injector
from linuxwhisper.transcription import TranscriptionEngine
from linuxwhisper.input.modes import InputMode, get_mode_from_config, DEFAULT_TOGGLE_TIMEOUT
from linuxwhisper.config.validation import validate_hotkey, check_compositor_conflicts, validate_config_input
from .states import PipelineState, VALID_TRANSITIONS

logger = logging.getLogger(__name__)


class DictationPipeline:
    """Coordinates hotkey detection, audio recording, transcription, and text injection."""

    def __init__(self, config: dict):
        """Initialize pipeline components from config.

        Args:
            config: Configuration dictionary with keys:
                - hotkey: Key to trigger dictation (default: "HOME")
                - mode: Input mode "hold" or "toggle" (default: "hold")
                - toggle_timeout: Seconds before toggle auto-transcribes (default: 120)
                - model: Whisper model size (default: "base.en")
                - audio.sample_rate: Audio sample rate (default: 16000)
                - audio.channels: Audio channels (default: 1)

        Raises:
            ValueError: If configuration is invalid (bad hotkey, unknown mode, etc.)
        """
        # Store full config for later use (e.g., restart_hotkey_detector)
        self._config = config

        # Validate input config before initializing anything
        errors = validate_config_input(config)
        if errors:
            raise ValueError(f"Invalid configuration: {'; '.join(errors)}")

        # Extract config values with defaults
        hotkey = config.get("hotkey", "HOME")
        model = config.get("model", "base.en")
        audio_config = config.get("audio", {})
        sample_rate = audio_config.get("sample_rate", 16000)
        channels = audio_config.get("channels", 1)

        # Parse input mode and toggle timeout
        self._mode = get_mode_from_config(config)
        self._toggle_timeout = config.get("toggle_timeout", DEFAULT_TOGGLE_TIMEOUT)
        logger.info(f"Input mode: {self._mode.value}")

        # Check for compositor conflicts (warnings only, don't block startup)
        conflicts = check_compositor_conflicts(hotkey)
        for conflict in conflicts:
            logger.warning(f"Compositor conflict: {conflict}")

        # Create component instances
        self._detector = HotkeyDetector(hotkey=hotkey)
        self._recorder = AudioRecorder(sample_rate=sample_rate, channels=channels)
        self._engine = TranscriptionEngine(model_size=model)
        self._injector = create_injector()

        # State machine
        self._state = PipelineState.IDLE
        self._running = False
        self._hotkey_thread: threading.Thread | None = None

        # Toggle timeout timer
        self._timeout_timer: threading.Timer | None = None

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

    def _process_recording(self) -> None:
        """Stop recording and process the captured audio (transcribe + inject).

        Shared between hold-release, toggle-stop, and timeout paths.
        Cancels any active timeout timer, stops recording, transcribes, and
        injects the resulting text. Always returns to IDLE.
        """
        try:
            # Cancel any active timeout timer first
            self._cancel_timeout()

            # Stop recording and get audio data
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

    def _cancel_toggle_recording(self) -> None:
        """Cancel an active toggle recording via Escape key.

        Discards captured audio without transcribing. Does nothing if not recording.
        """
        if self._state != PipelineState.RECORDING:
            logger.debug(f"Escape cancel ignored: not recording (state={self._state.name})")
            return

        try:
            logger.info("Toggle recording cancelled via Escape")
            self._transition(PipelineState.CANCELLING)

            # Cancel any active timeout timer
            self._cancel_timeout()

            # Stop recording but discard audio (do not transcribe)
            self._recorder.stop()

            # Return to idle
            self._transition(PipelineState.IDLE)

        except Exception as e:
            logger.error(f"Error during toggle cancel: {e}", exc_info=True)
            self._transition(PipelineState.IDLE)

    def _start_timeout(self) -> None:
        """Start the toggle mode timeout timer."""
        # Cancel any existing timer first
        self._cancel_timeout()

        self._timeout_timer = threading.Timer(self._toggle_timeout, self._on_timeout)
        self._timeout_timer.daemon = True
        self._timeout_timer.start()
        logger.debug(f"Toggle timeout started: {self._toggle_timeout}s")

    def _cancel_timeout(self) -> None:
        """Cancel the toggle timeout timer if active."""
        if self._timeout_timer is not None:
            self._timeout_timer.cancel()
            self._timeout_timer = None

    def _on_timeout(self) -> None:
        """Handle toggle timeout — transcribe whatever was captured (do not discard)."""
        if self._state != PipelineState.RECORDING:
            # Recording already stopped by other means
            return

        logger.warning(
            f"Toggle recording timeout ({self._toggle_timeout}s) "
            "— transcribing captured audio"
        )
        self._transition(PipelineState.PROCESSING)
        self._process_recording()

    def _on_hotkey_press(self) -> None:
        """Handle hotkey press event — behavior depends on input mode."""
        if self._mode == InputMode.HOLD:
            # Hold mode: press starts recording
            if self._state == PipelineState.IDLE:
                self._transition(PipelineState.RECORDING)
                self._recorder.start()
                logger.info("Recording started")

        elif self._mode == InputMode.TOGGLE:
            # Toggle mode: press toggles between recording and processing
            if self._state == PipelineState.IDLE:
                self._transition(PipelineState.RECORDING)
                self._recorder.start()
                self._start_timeout()
                logger.info("Toggle: recording started")

            elif self._state == PipelineState.RECORDING:
                self._transition(PipelineState.PROCESSING)
                logger.info("Toggle: recording stopped")
                self._process_recording()

            else:
                # Pipeline is busy (PROCESSING, INJECTING) — ignore press
                logger.debug(f"Toggle press ignored: pipeline busy ({self._state.name})")

    def _on_hotkey_release(self) -> None:
        """Handle hotkey release event — behavior depends on input mode."""
        if self._mode == InputMode.HOLD:
            # Hold mode: release stops recording and triggers processing
            if self._state == PipelineState.RECORDING:
                self._transition(PipelineState.PROCESSING)
                self._process_recording()

        elif self._mode == InputMode.TOGGLE:
            # Toggle mode: release is irrelevant (toggle, not hold)
            pass

    def _run_hotkey_loop(self) -> None:
        """Run the hotkey detector loop in a thread."""
        try:
            # Provide escape callback only in toggle mode
            escape_cb = self._cancel_toggle_recording if self._mode == InputMode.TOGGLE else None
            self._detector.start(
                on_press=self._on_hotkey_press,
                on_release=self._on_hotkey_release,
                on_escape=escape_cb,
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
        # Cancel any active toggle timeout timer
        self._cancel_timeout()

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

    @property
    def mode(self) -> InputMode:
        """Get current input mode.

        Returns:
            Current InputMode
        """
        return self._mode

    def update_config(self, new_config: dict) -> None:
        """Update pipeline configuration at runtime.

        Updates mode and toggle_timeout. Use restart_hotkey_detector() to
        apply hotkey changes.

        Args:
            new_config: New configuration dictionary.
        """
        self._config = new_config
        self._mode = get_mode_from_config(new_config)
        self._toggle_timeout = new_config.get("toggle_timeout", DEFAULT_TOGGLE_TIMEOUT)
        logger.info(
            f"Pipeline config updated: mode={self._mode.value}, "
            f"toggle_timeout={self._toggle_timeout}s"
        )

    def restart_hotkey_detector(self) -> None:
        """Restart the hotkey detector with the current config hotkey.

        Can only be called when the pipeline is idle.
        """
        if self._state != PipelineState.IDLE:
            logger.warning(
                f"Cannot restart hotkey detector: pipeline not idle (state={self._state.name})"
            )
            return

        # Stop current detector
        self._detector.stop()

        # Wait for hotkey thread to exit
        if self._hotkey_thread is not None:
            self._hotkey_thread.join(timeout=2)

        # Create new detector with updated hotkey
        hotkey = self._config.get("hotkey", "HOME")
        self._detector = HotkeyDetector(hotkey=hotkey)

        # Start a new hotkey thread
        self._hotkey_thread = threading.Thread(
            target=self._run_hotkey_loop,
            daemon=True
        )
        self._hotkey_thread.start()
        logger.info(f"Hotkey detector restarted with key={hotkey}")
