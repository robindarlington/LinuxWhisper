"""Transcription engine using faster-whisper with INT8 quantization."""

import logging
from typing import Optional, Union

import numpy as np

from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)


class TranscriptionEngine:
    """Wraps faster-whisper for audio transcription with INT8 optimization."""

    def __init__(self, model_size: str = "base.en", device: str = "cpu"):
        """Initialize transcription engine without loading model.

        Args:
            model_size: Whisper model size (tiny, base, small, medium, large)
            device: Device to run on (cpu, cuda)
        """
        self.model_size = model_size
        self.device = device

        # INT8 quantization for speed
        if device == "cpu":
            self.compute_type = "int8"
        else:
            # GPU gets int8_float16 for better performance
            self.compute_type = "int8_float16"

        self._model: Optional[WhisperModel] = None

        logger.info(
            f"TranscriptionEngine initialized with model={model_size}, "
            f"device={device}, compute_type={self.compute_type}"
        )

    def load_model(self) -> None:
        """Load the Whisper model into memory.

        This is separated from __init__ so the daemon can control when
        the (slow) model load happens.
        """
        logger.info(f"Loading Whisper model '{self.model_size}'...")
        self._model = WhisperModel(
            self.model_size, device=self.device, compute_type=self.compute_type
        )
        logger.info(f"Whisper model '{self.model_size}' loaded successfully")

    def transcribe(self, audio: Union[str, np.ndarray], language: Optional[str] = None) -> str:
        """Transcribe audio file or numpy array to text.

        Args:
            audio: Path to audio file OR numpy float32 array at 16kHz
            language: Language code (e.g. 'en') or None for auto-detection

        Returns:
            Transcribed text as string
        """
        # Auto-load model on first use
        if self._model is None:
            self.load_model()

        # Squeeze channel dimension for mono audio from AudioRecorder (N,1) -> (N,)
        if isinstance(audio, np.ndarray) and audio.ndim > 1:
            audio = audio.squeeze()

        # Transcribe with VAD filtering for better results
        segments, info = self._model.transcribe(
            audio,
            language=language,
            beam_size=5,
            vad_filter=True,
            vad_parameters={
                "threshold": 0.5,
                "min_speech_duration_ms": 250,
                "min_silence_duration_ms": 2000,
                "speech_pad_ms": 400,
            },
        )

        # Join all segment texts
        text = "".join(seg.text for seg in segments).strip()

        logger.info(
            f"Transcription complete: {len(text)} chars, "
            f"language={info.language} (prob={info.language_probability:.2f})"
        )

        return text

    def unload_model(self) -> None:
        """Unload model from memory to free resources."""
        self._model = None
        logger.info("Whisper model unloaded")

    @property
    def is_loaded(self) -> bool:
        """Check if model is currently loaded in memory."""
        return self._model is not None
