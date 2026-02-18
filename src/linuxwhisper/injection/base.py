"""Abstract base class for text injection backends."""

from abc import ABC, abstractmethod


class InjectorBackend(ABC):
    """Abstract base class for text injection backends."""

    @abstractmethod
    def name(self) -> str:
        """Human-readable backend name."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this backend can be used in the current environment."""
        ...

    @abstractmethod
    def type_text(self, text: str) -> None:
        """Inject text into the active window.

        Raises:
            RuntimeError: On failure.
        """
        ...

    def supports_unicode(self) -> bool:
        """Whether this backend handles non-ASCII characters."""
        return False
