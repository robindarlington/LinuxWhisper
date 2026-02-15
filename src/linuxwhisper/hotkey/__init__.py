"""Hotkey detection module."""
from .detector import HotkeyDetector
from .permissions import check_input_permissions, get_permission_instructions

__all__ = ['HotkeyDetector', 'check_input_permissions', 'get_permission_instructions']
