"""Stdin pipe reader for the overlay subprocess.

Reads RMS amplitude values (one float per line) from stdin in a daemon
thread and pushes them to the waveform widget via GLib.idle_add for
thread-safe GUI updates.

When stdin closes (EOF — daemon terminated or hid the overlay), the
reader requests the GTK application to quit.
"""

import sys
import threading

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk


class StdinReader:
    """Reads float amplitude values from stdin and feeds them to a widget."""

    def __init__(self, waveform_widget):
        self._widget = waveform_widget
        self._app: Gtk.Application | None = None
        self._thread: threading.Thread | None = None
        self._running = False

    def set_app(self, app: Gtk.Application) -> None:
        """Store a reference to the GTK application for quit-on-EOF."""
        self._app = app

    def start(self) -> None:
        """Spawn the background reader thread."""
        self._running = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Signal the reader to stop (best-effort — stdin may block)."""
        self._running = False

    def _read_loop(self) -> None:
        """Read float lines from stdin, push to waveform via GLib.idle_add."""
        try:
            for line in sys.stdin:
                if not self._running:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    rms = float(line)
                    GLib.idle_add(self._widget.push_amplitude, rms)
                except ValueError:
                    pass  # Malformed line — skip silently
        except (IOError, OSError):
            pass  # Pipe broken

        # Stdin closed (EOF) or stopped — request application quit
        GLib.idle_add(self._request_quit)

    def _request_quit(self) -> bool:
        """Ask the GTK application to quit. Returns False for GLib.idle_add."""
        if self._app is not None:
            self._app.quit()
        return False
