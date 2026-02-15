"""Pipeline state machine for dictation workflow."""

import enum


class PipelineState(enum.Enum):
    """States in the dictation pipeline state machine."""
    IDLE = "idle"
    RECORDING = "recording"
    PROCESSING = "processing"
    INJECTING = "injecting"
    ERROR = "error"


# Valid state transitions map
VALID_TRANSITIONS: dict[PipelineState, set[PipelineState]] = {
    PipelineState.IDLE: {PipelineState.RECORDING},
    PipelineState.RECORDING: {PipelineState.PROCESSING, PipelineState.IDLE},  # IDLE for cancel/error
    PipelineState.PROCESSING: {PipelineState.INJECTING, PipelineState.IDLE},  # IDLE for empty transcription or error
    PipelineState.INJECTING: {PipelineState.IDLE},
    PipelineState.ERROR: {PipelineState.IDLE},
}
