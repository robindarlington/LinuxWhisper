"""evdev-based hotkey detection for Linux."""
import logging
from typing import Callable

import evdev
from evdev import InputDevice, UInput, ecodes

logger = logging.getLogger(__name__)


class HotkeyDetector:
    """Detects and monitors hotkey press/release events using evdev."""

    def __init__(
        self,
        hotkey: str = "KEY_F13",
        device_path: str | None = None,
        escape_keycode: int | None = None,
    ):
        """Initialize hotkey detector.

        Args:
            hotkey: Key name (e.g., "KEY_F13" or "F13")
            device_path: Optional specific device path. If None, auto-detect.
            escape_keycode: Keycode for the Escape key. Defaults to ecodes.KEY_ESC.
                Only used when on_escape callback is passed to start().
        """
        self.hotkey_name = hotkey
        self.keycode = self._resolve_keycode(hotkey)
        self.escape_keycode = escape_keycode if escape_keycode is not None else ecodes.KEY_ESC
        self.device_path = device_path if device_path else self._find_keyboard()
        self.device: InputDevice | None = None
        self._running = False
        self._key_pressed = False  # Track key state for missed press events

    def _resolve_keycode(self, hotkey_name: str) -> int:
        """Convert hotkey name to evdev keycode.

        Args:
            hotkey_name: Key name like "KEY_F13" or "F13"

        Returns:
            Integer keycode for evdev

        Raises:
            ValueError: If keycode not found
        """
        # Normalize to uppercase and ensure KEY_ prefix
        hotkey_name = hotkey_name.upper()
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
                skip_keywords = ['power', 'sleep', 'lid', 'video', 'consumer', 'mouse', 'trackpad', 'touchpad']
                if any(kw in name_lower for kw in skip_keywords):
                    continue

                # Must be a physical device
                if not device.phys:
                    continue

                # Score based on how likely this is a real keyboard
                score = 0
                key_caps = caps.get(ecodes.EV_KEY, [])
                # Real keyboards support alphabetic keys
                has_alpha = any(ecodes.KEY_A <= k <= ecodes.KEY_Z for k in key_caps)
                if has_alpha:
                    score += 10
                if 'keyboard' in name_lower:
                    score += 5
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

    def start(
        self,
        on_press: Callable[[], None],
        on_release: Callable[[], None],
        on_escape: Callable[[], None] | None = None,
    ) -> None:
        """Start monitoring hotkey events.

        This method blocks until stop() is called.

        Args:
            on_press: Callback for key press (value=1)
            on_release: Callback for key release (value=0)
            on_escape: Optional callback for Escape key press. When provided,
                Escape events are intercepted (swallowed) and on_escape is called.
                When None, Escape events pass through to the system normally.
        """
        self.device = InputDevice(self.device_path)
        self.device.grab()  # Grab device to intercept hotkey
        self._running = True

        # Create virtual device to re-inject non-hotkey events
        self._uinput = UInput.from_device(self.device, name="LinuxWhisper passthrough")

        logger.info(f"Monitoring hotkey {self.hotkey_name} on {self.device.name}")

        try:
            for event in self.device.read_loop():
                if not self._running:
                    break

                # Intercept our hotkey — swallow it, invoke callbacks
                if event.type == ecodes.EV_KEY and event.code == self.keycode:
                    if event.value == 1:  # Key down
                        self._key_pressed = True
                        on_press()
                    elif event.value == 0:  # Key up
                        self._key_pressed = False
                        on_release()
                    elif event.value == 2 and not self._key_pressed:
                        # First repeat without seeing initial press (grab race condition)
                        self._key_pressed = True
                        logger.debug("Hotkey repeat treated as press (missed initial press event)")
                        on_press()

                # Intercept Escape only when on_escape callback is registered
                elif (
                    on_escape is not None
                    and event.type == ecodes.EV_KEY
                    and event.code == self.escape_keycode
                    and event.value == 1  # Key down only
                ):
                    on_escape()

                else:
                    # Re-inject all other events so keyboard works normally
                    self._uinput.write_event(event)

        finally:
            if self._uinput:
                self._uinput.close()
                self._uinput = None
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
