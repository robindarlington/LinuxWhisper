"""evdev-based hotkey detection for Linux."""
import logging
from typing import Callable

import evdev
from evdev import InputDevice, ecodes

logger = logging.getLogger(__name__)


class HotkeyDetector:
    """Detects and monitors hotkey press/release events using evdev."""

    def __init__(self, hotkey: str = "KEY_F13", device_path: str | None = None):
        """Initialize hotkey detector.

        Args:
            hotkey: Key name (e.g., "KEY_F13" or "F13")
            device_path: Optional specific device path. If None, auto-detect.
        """
        self.hotkey_name = hotkey
        self.keycode = self._resolve_keycode(hotkey)
        self.device_path = device_path if device_path else self._find_keyboard()
        self.device: InputDevice | None = None
        self._running = False

    def _resolve_keycode(self, hotkey_name: str) -> int:
        """Convert hotkey name to evdev keycode.

        Args:
            hotkey_name: Key name like "KEY_F13" or "F13"

        Returns:
            Integer keycode for evdev

        Raises:
            ValueError: If keycode not found
        """
        # Ensure KEY_ prefix
        if not hotkey_name.startswith("KEY_"):
            hotkey_name = f"KEY_{hotkey_name}"

        try:
            return getattr(ecodes, hotkey_name)
        except AttributeError:
            raise ValueError(f"Unknown keycode: {hotkey_name}")

    def _find_keyboard(self) -> str:
        """Find a suitable keyboard device.

        Returns:
            Device path

        Raises:
            RuntimeError: If no keyboard found
        """
        devices = evdev.list_devices()
        candidates = []

        for path in devices:
            try:
                device = InputDevice(path)
                caps = device.capabilities(verbose=False)

                # Must support key events
                if ecodes.EV_KEY not in caps:
                    continue

                # Skip non-keyboard devices (power buttons, etc.)
                name_lower = device.name.lower()
                skip_keywords = ['power', 'sleep', 'lid', 'video', 'consumer']
                if any(kw in name_lower for kw in skip_keywords):
                    continue

                # Must be a physical device
                if not device.phys:
                    continue

                # Prefer USB keyboards
                score = 0
                if 'usb' in device.phys.lower():
                    score += 2
                if 'input' in device.phys.lower():
                    score += 1

                candidates.append((path, device.name, device.phys, score))
                device.close()

            except (OSError, PermissionError):
                # Can't access this device, skip it
                continue

        if not candidates:
            raise RuntimeError(
                "No keyboard device found. Check input group membership."
            )

        # Sort by score (highest first) and return best candidate
        candidates.sort(key=lambda x: x[3], reverse=True)
        best_path = candidates[0][0]
        logger.info(f"Selected keyboard: {candidates[0][1]} at {best_path}")
        return best_path

    def start(self, on_press: Callable[[], None], on_release: Callable[[], None]) -> None:
        """Start monitoring hotkey events.

        This method blocks until stop() is called.

        Args:
            on_press: Callback for key press (value=1)
            on_release: Callback for key release (value=0)
        """
        self.device = InputDevice(self.device_path)
        self.device.grab()  # Exclusively grab device to prevent propagation
        self._running = True

        logger.info(f"Monitoring hotkey {self.hotkey_name} on {self.device.name}")

        try:
            for event in self.device.read_loop():
                if not self._running:
                    break

                # Only care about key events for our specific key
                if event.type == ecodes.EV_KEY and event.code == self.keycode:
                    if event.value == 1:  # Key down
                        on_press()
                    elif event.value == 0:  # Key up
                        on_release()
                    # value == 2 is key repeat, ignore it

        finally:
            if self.device:
                try:
                    self.device.ungrab()
                except OSError:
                    pass  # Device may already be closed
                self.device.close()
                self.device = None

    def stop(self) -> None:
        """Stop monitoring hotkey events."""
        self._running = False
        logger.info("Stopping hotkey detection")

    @property
    def devices(self) -> list[dict]:
        """Get list of all detected keyboard devices for diagnostics.

        Returns:
            List of dicts with 'path', 'name', 'phys' keys
        """
        result = []
        for path in evdev.list_devices():
            try:
                device = InputDevice(path)
                caps = device.capabilities(verbose=False)
                if ecodes.EV_KEY in caps:
                    result.append({
                        'path': path,
                        'name': device.name,
                        'phys': device.phys or ''
                    })
                device.close()
            except (OSError, PermissionError):
                continue
        return result
