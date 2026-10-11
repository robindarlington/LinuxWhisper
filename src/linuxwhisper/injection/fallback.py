"""Fallback injector that tries multiple backends in order."""

import logging

from .base import InjectorBackend
from .focus import focused_window_is_chromium

logger = logging.getLogger(__name__)


class FallbackInjector:
    """Tries multiple injection backends in order.

    For Unicode text, prefers Unicode-capable backends first.
    Falls back through the chain on failure.
    """

    def __init__(self, backends: list[InjectorBackend]):
        self._backends = [b for b in backends if b.is_available()]
        if not self._backends:
            raise RuntimeError("No text injection backends available")
        logger.info(
            f"Available injection backends: {[b.name() for b in self._backends]}"
        )

    def type_text(self, text: str) -> None:
        """Inject text using the first working backend.

        For non-ASCII text, tries Unicode-capable backends first.
        Falls back through the chain on failure.

        Raises:
            RuntimeError: If all backends fail.
        """
        needs_unicode = not text.isascii()
        errors = []
        backends = self._backends

        # wtype can map spaces to control keys in Chromium. Prefer a single
        # clipboard paste and never retry wtype for this target.
        if any(b.name() == "wtype" for b in backends) and focused_window_is_chromium():
            backends = sorted(
                (b for b in backends if b.name() != "wtype"),
                key=lambda b: not b.name().startswith("clipboard-"),
            )
            logger.info("Chromium window: prefer clipboard paste; skip wtype")

        # If Unicode needed, try Unicode-capable backends first
        if needs_unicode:
            for backend in backends:
                if backend.supports_unicode():
                    try:
                        backend.type_text(text)
                        return
                    except RuntimeError as e:
                        errors.append(f"{backend.name()}: {e}")

        # Try all backends in order
        for backend in backends:
            try:
                backend.type_text(text)
                return
            except RuntimeError as e:
                errors.append(f"{backend.name()}: {e}")

        raise RuntimeError(
            f"All injection backends failed: {'; '.join(errors)}"
        )
