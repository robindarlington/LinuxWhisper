"""Spacing tracker for consecutive dictations."""

import logging

logger = logging.getLogger(__name__)


class SpacingTracker:
    """Tracks spacing state between consecutive dictations.

    Prepends a space before text when a previous dictation has already
    been injected. Resets on newlines or explicit reset.
    """

    def __init__(self):
        self._has_prior_text = False

    def prepare_text(self, text: str) -> str:
        """Prepend space if needed for consecutive dictation.

        Args:
            text: Formatted transcription text.

        Returns:
            Text with leading space if following a previous dictation.
        """
        if not text or not text.strip():
            return text

        result = text
        if self._has_prior_text and not text[0].isspace():
            result = " " + text

        # Update state: text ending with newline resets spacing
        if text[-1] in ("\n", "\r"):
            self._has_prior_text = False
        else:
            self._has_prior_text = True

        return result

    def reset(self) -> None:
        """Reset spacing state (e.g., on cancel, stop, or error)."""
        self._has_prior_text = False
