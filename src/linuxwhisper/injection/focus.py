"""Identify Chromium windows without reading window titles."""

import json
import os
from pathlib import Path
import subprocess


def focused_window_is_chromium() -> bool:
    """Inspect the focused window on Hyprland or Sway.

    Unsupported desktops and failed queries keep the normal backend order.
    Check the process too, because installed web apps use their own app IDs.
    """
    try:
        if os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"):
            command = ["hyprctl", "activewindow", "-j"]
        elif os.environ.get("SWAYSOCK"):
            command = ["swaymsg", "-t", "get_tree", "-r"]
        else:
            return False
        result = subprocess.run(command, capture_output=True, text=True,
                                check=True, timeout=1)
        window = json.loads(result.stdout)
        if command[0] == "swaymsg":
            pending = [window]
            window = {}
            while pending:
                node = pending.pop()
                if node.get("focused"):
                    window = node
                    break
                pending.extend(node.get("nodes", []))
                pending.extend(node.get("floating_nodes", []))
        names = [window.get("class", ""), window.get("initialClass", ""),
                 window.get("app_id", ""),
                 (window.get("window_properties") or {}).get("class", "")]
        pid = window.get("pid")
        if isinstance(pid, int) and pid > 0:
            try:
                names.append(Path(os.readlink(f"/proc/{pid}/exe")).name)
            except OSError:
                pass
        browsers = {"chromium", "chromium-browser", "google-chrome", "chrome",
                    "google-chrome-stable", "google-chrome-beta",
                    "google-chrome-unstable", "brave", "brave-browser",
                    "vivaldi", "vivaldi-stable", "microsoft-edge"}
        return any(isinstance(name, str) and name.lower() in browsers
                   for name in names)
    except (OSError, subprocess.SubprocessError, ValueError, TypeError, AttributeError):
        return False
