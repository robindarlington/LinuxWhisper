"""Cairo waveform widget for the recording overlay.

Renders a live audio waveform as a mirrored white fill on a blue
background. Amplitude history is stored in a fixed-size deque and
refreshed at ~30fps via GLib.timeout_add.
"""

import collections

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk


class WaveformWidget(Gtk.DrawingArea):
    """Live audio waveform display using Cairo on a GTK4 DrawingArea.

    Push amplitude values via push_amplitude(). The widget redraws
    automatically at ~30fps showing a mirrored waveform fill.
    """

    def __init__(self, history_size: int = 100):
        super().__init__()
        self._amplitudes: collections.deque[float] = collections.deque(
            maxlen=history_size
        )
        self.set_draw_func(self._draw)
        self.set_content_width(200)
        self.set_content_height(60)

        # ~30fps refresh timer
        self._timer_id = GLib.timeout_add(33, self._tick)

    def push_amplitude(self, rms: float) -> bool:
        """Add a new amplitude value to the history.

        Returns False so GLib.idle_add does not repeat the call.
        """
        self._amplitudes.append(rms)
        return False

    def stop(self) -> None:
        """Stop the refresh timer."""
        if self._timer_id is not None:
            GLib.source_remove(self._timer_id)
            self._timer_id = None

    def _tick(self) -> bool:
        """Timer callback — trigger a redraw.

        MUST return True explicitly to keep the timer running.
        """
        self.queue_draw()
        return True

    def _draw(self, area: Gtk.DrawingArea, ctx, width: int, height: int) -> None:
        """Cairo draw function for the waveform.

        Draws a blue background with a mirrored white waveform fill.
        When idle (no data), draws a thin white center line.
        """
        mid_y = height / 2.0

        # Blue background
        ctx.set_source_rgb(0.13, 0.39, 0.68)  # #2164AD
        ctx.rectangle(0, 0, width, height)
        ctx.fill()

        if not self._amplitudes:
            # Idle indicator — thin white center line
            ctx.set_source_rgba(1.0, 1.0, 1.0, 0.4)
            ctx.set_line_width(1.0)
            ctx.move_to(0, mid_y)
            ctx.line_to(width, mid_y)
            ctx.stroke()
            return

        # White mirrored waveform fill
        ctx.set_source_rgba(1.0, 1.0, 1.0, 0.9)

        amps = list(self._amplitudes)
        n = len(amps)

        # Forward pass: top edge (left to right)
        for i, amp in enumerate(amps):
            x = (i / max(n - 1, 1)) * width
            bar_h = min(amp * mid_y * 5.0, mid_y - 2)  # Scale and clamp
            y = mid_y - bar_h
            if i == 0:
                ctx.move_to(x, y)
            else:
                ctx.line_to(x, y)

        # Reverse pass: bottom edge (right to left) — mirror
        for i in range(n - 1, -1, -1):
            x = (i / max(n - 1, 1)) * width
            bar_h = min(amps[i] * mid_y * 5.0, mid_y - 2)
            ctx.line_to(x, mid_y + bar_h)

        ctx.close_path()
        ctx.fill()
