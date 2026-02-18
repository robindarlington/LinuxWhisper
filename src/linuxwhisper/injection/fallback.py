"""Fallback injector that tries multiple backends in order."""

import logging

from .base import InjectorBackend

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

        # If Unicode needed, try Unicode-capable backends first
        if needs_unicode:
            for backend in self._backends:
                if backend.supports_unicode():
                    try:
                        backend.type_text(text)
                        return
                    except RuntimeError as e:
                        errors.append(f"{backend.name()}: {e}")

        # Try all backends in order
        for backend in self._backends:
            try:
                backend.type_text(text)
                return
            except RuntimeError as e:
                errors.append(f"{backend.name()}: {e}")

        raise RuntimeError(
            f"All injection backends failed: {'; '.join(errors)}"
        )
