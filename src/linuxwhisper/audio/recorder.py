"""Queue-based audio recording for voice dictation."""
import logging
import queue
import tempfile
from typing import Optional

import numpy as np
import sounddevice as sd
from scipy.io import wavfile

logger = logging.getLogger(__name__)


class AudioRecorder:
    """Non-blocking audio recorder using callback-based queue."""

    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        """Initialize audio recorder.

        Args:
            sample_rate: Sample rate in Hz (default 16000 for Whisper)
            channels: Number of channels (1=mono, 2=stereo)
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self._queue: queue.Queue = queue.Queue()
        self._stream: Optional[sd.InputStream] = None
        self._recording = False

    def _callback(self, indata, frames, time, status):
        """Audio callback - MUST NOT BLOCK.

        Args:
            indata: Audio data buffer
            frames: Number of frames
            time: Timing info
            status: Stream status
        """
        if status:
            logger.warning(f"Audio status: {status}")

        # CRITICAL: Copy the data because sounddevice reuses the buffer
        self._queue.put(indata.copy())

    def start(self) -> None:
        """Start audio recording."""
        # Clear any leftover data from previous recordings
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

        # Create and start stream
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            callback=self._callback
        )
        self._stream.start()
        self._recording = True
        logger.info("Audio recording started")

    def stop(self) -> np.ndarray:
        """Stop audio recording and return captured audio.

        Returns:
            NumPy array of audio samples (float32)
        """
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        self._recording = False

        # Drain queue into list
        chunks = []
        while not self._queue.empty():
            try:
                chunks.append(self._queue.get_nowait())
            except queue.Empty:
                break

        # Concatenate all chunks
        if chunks:
            audio_data = np.concatenate(chunks, axis=0)
            duration = len(audio_data) / self.sample_rate
            logger.info(f"Audio recording stopped, captured {len(audio_data)} samples ({duration:.2f}s)")
            return audio_data
        else:
            logger.warning("Audio recording stopped with no data captured")
            return np.array([], dtype=np.float32)

    def save_wav(self, audio_data: np.ndarray, output_path: Optional[str] = None) -> str:
        """Save audio data to WAV file.

        Args:
            audio_data: NumPy array of audio samples
            output_path: Output file path. If None, creates a temp file.

        Returns:
            Path to saved WAV file
        """
        # Create temp file if no output path specified
        if output_path is None:
            fd, output_path = tempfile.mkstemp(suffix='.wav')
            # Close the file descriptor, we'll write with scipy
            import os
            os.close(fd)

        # Ensure mono audio
        if audio_data.ndim > 1:
            audio_data = audio_data.mean(axis=1)

        # Convert float32/float64 to int16 for WAV
        # Clip to [-1.0, 1.0] then scale to int16 range
        audio_clipped = np.clip(audio_data, -1.0, 1.0)
        audio_int16 = (audio_clipped * 32767).astype(np.int16)

        # Write WAV file
        wavfile.write(output_path, self.sample_rate, audio_int16)
        logger.info(f"Audio saved to {output_path}")

        return output_path

    @property
    def is_recording(self) -> bool:
        """Check if currently recording.

        Returns:
            True if recording in progress
        """
        return self._recording
