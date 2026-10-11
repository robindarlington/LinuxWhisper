import json
import subprocess
import unittest
from unittest.mock import Mock, patch

from linuxwhisper.injection.fallback import FallbackInjector
from linuxwhisper.injection.focus import focused_window_is_chromium


def backend(name, unicode=True, fail=False):
    item = Mock()
    item.name.return_value = name
    item.is_available.return_value = True
    item.supports_unicode.return_value = unicode
    if fail:
        item.type_text.side_effect = RuntimeError("unavailable")
    return item


class RoutingTests(unittest.TestCase):
    @patch("linuxwhisper.injection.fallback.focused_window_is_chromium", return_value=True)
    def test_chromium_pastes_ascii_and_unicode(self, focus):
        for text in (" Hello world.", " Hello café."):
            wtype = backend("wtype")
            keys = backend("ydotool", unicode=False)
            clipboard = backend("clipboard-wayland")
            FallbackInjector([wtype, keys, clipboard]).type_text(text)
            clipboard.type_text.assert_called_once_with(text)
            wtype.type_text.assert_not_called()
            keys.type_text.assert_not_called()

    @patch("linuxwhisper.injection.fallback.focused_window_is_chromium", return_value=False)
    def test_other_apps_keep_wtype(self, focus):
        wtype = backend("wtype")
        clipboard = backend("clipboard-wayland")
        FallbackInjector([wtype, clipboard]).type_text("hello")
        wtype.type_text.assert_called_once_with("hello")
        clipboard.type_text.assert_not_called()

    @patch("linuxwhisper.injection.fallback.focused_window_is_chromium", return_value=True)
    def test_clipboard_failure_never_retries_wtype(self, focus):
        wtype = backend("wtype")
        clipboard = backend("clipboard-wayland", fail=True)
        keys = backend("ydotool", unicode=False)
        FallbackInjector([wtype, keys, clipboard]).type_text("hello")
        keys.type_text.assert_called_once_with("hello")
        wtype.type_text.assert_not_called()

    @patch("linuxwhisper.injection.fallback.focused_window_is_chromium", return_value=True)
    def test_no_safe_backend_reports_failure(self, focus):
        wtype = backend("wtype")
        with self.assertRaises(RuntimeError):
            FallbackInjector([wtype]).type_text("hello")
        wtype.type_text.assert_not_called()


class FocusTests(unittest.TestCase):
    @patch.dict("os.environ", {"HYPRLAND_INSTANCE_SIGNATURE": "test"}, clear=True)
    @patch("linuxwhisper.injection.focus.subprocess.run")
    def test_hyprland_class(self, run):
        run.return_value.stdout = json.dumps({"class": "chromium"})
        self.assertTrue(focused_window_is_chromium())
        run.return_value.stdout = json.dumps({"class": "org.example.Editor"})
        self.assertFalse(focused_window_is_chromium())

    @patch.dict("os.environ", {"HYPRLAND_INSTANCE_SIGNATURE": "test"}, clear=True)
    @patch("linuxwhisper.injection.focus.os.readlink", return_value="/usr/lib/chromium/chromium")
    @patch("linuxwhisper.injection.focus.subprocess.run")
    def test_installed_web_app_process(self, run, readlink):
        run.return_value.stdout = json.dumps({"class": "chrome-app-id", "pid": 123})
        self.assertTrue(focused_window_is_chromium())

    @patch.dict("os.environ", {"SWAYSOCK": "test"}, clear=True)
    @patch("linuxwhisper.injection.focus.subprocess.run")
    def test_sway_floating_window(self, run):
        run.return_value.stdout = json.dumps({"nodes": [], "floating_nodes": [
            {"focused": True, "app_id": "chromium"}]})
        self.assertTrue(focused_window_is_chromium())

    @patch.dict("os.environ", {"HYPRLAND_INSTANCE_SIGNATURE": "test"}, clear=True)
    @patch("linuxwhisper.injection.focus.subprocess.run")
    def test_failed_query(self, run):
        for response in ("not json", "[]"):
            run.return_value.stdout = response
            self.assertFalse(focused_window_is_chromium())
        run.side_effect = subprocess.TimeoutExpired("hyprctl", 1)
        self.assertFalse(focused_window_is_chromium())


if __name__ == "__main__":
    unittest.main()
