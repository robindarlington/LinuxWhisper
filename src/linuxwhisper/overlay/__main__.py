"""Overlay subprocess entry point: python -m linuxwhisper.overlay

CRITICAL: libgtk4-layer-shell.so must be loaded via ctypes BEFORE any gi
imports. This allows it to intercept Wayland calls before GTK4 initializes.
"""

import argparse
from ctypes import CDLL

# Load layer-shell shared library before any GObject introspection imports.
# This is required per gtk4-layer-shell documentation.
_layer_shell_available = False
try:
    CDLL("libgtk4-layer-shell.so")
    _layer_shell_available = True
except OSError:
    pass

import gi  # noqa: E402

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402

if _layer_shell_available:
    gi.require_version("Gtk4LayerShell", "1.0")
    from gi.repository import Gtk4LayerShell as LayerShell  # noqa: E402

from linuxwhisper.overlay.reader import StdinReader  # noqa: E402
from linuxwhisper.overlay.waveform import WaveformWidget  # noqa: E402
from linuxwhisper.overlay.window import create_overlay_window  # noqa: E402

# Module-level args, set in main() before GTK runs
_args: argparse.Namespace | None = None


def on_activate(app: Gtk.Application) -> None:
    """Application activate handler — creates window and wires components."""
    use_layer_shell = _layer_shell_available and LayerShell.is_supported()

    width = _args.width if _args else 120
    height = _args.height if _args else 32
    abs_x = _args.x if _args else None
    abs_y = _args.y if _args else None

    window = create_overlay_window(
        app,
        use_layer_shell=use_layer_shell,
        width=width,
        height=height,
        abs_x=abs_x,
        abs_y=abs_y,
    )

    waveform = WaveformWidget(history_size=40)
    window.set_child(waveform)

    reader = StdinReader(waveform)
    reader.set_app(app)
    reader.start()

    window.present()


def main() -> None:
    """Entry point for the overlay subprocess."""
    global _args

    parser = argparse.ArgumentParser()
    parser.add_argument("--width", type=int, default=120)
    parser.add_argument("--height", type=int, default=32)
    parser.add_argument("--x", type=int, default=None)
    parser.add_argument("--y", type=int, default=None)
    parser.add_argument("--position", type=str, default=None)
    _args = parser.parse_args()

    app = Gtk.Application(application_id="com.linuxwhisper.overlay")
    app.connect("activate", on_activate)
    app.run(None)


if __name__ == "__main__":
    main()
