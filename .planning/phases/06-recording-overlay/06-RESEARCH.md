# Phase 6: Recording Overlay - Research

**Researched:** 2026-02-18
**Domain:** Wayland/X11 overlay windows, real-time audio waveform rendering, GTK4 layer-shell
**Confidence:** HIGH

## Summary

The recording overlay requires a small, non-focus-stealing window that appears during dictation showing a live audio waveform. The recommended approach uses **GTK4 + gtk4-layer-shell** for Wayland (supporting wlr-layer-shell protocol on Hyprland/Sway) with an X11 fallback path using standard GTK4 window hints. The waveform is drawn with **Cairo on a GTK4 DrawingArea** using `set_draw_func`, refreshed at 30fps via `GLib.timeout_add`.

The critical architectural decision is **subprocess isolation**: the overlay runs as a separate Python process spawned by the daemon, communicating via stdin pipe. This avoids GTK main loop blocking the daemon, avoids multiprocessing+GLib incompatibility, and provides clean lifecycle management (kill the process to hide the overlay). Audio amplitude data is sent from the daemon to the overlay process as simple text lines.

**Primary recommendation:** Run the overlay as a subprocess (`python -m linuxwhisper.overlay`), use gtk4-layer-shell for Wayland with keyboard_mode NONE, draw waveform with Cairo on DrawingArea at 30fps, send RMS amplitude values over stdin pipe from the audio recorder callback.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| UI-01 | Live waveform visualization during recording | GTK4 DrawingArea + Cairo for waveform rendering; GLib.timeout_add for 30fps refresh; sounddevice callback feeds amplitude data via pipe to overlay subprocess |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyGObject (gi) | 3.54.5 | Python bindings for GTK4/GLib/Cairo | Official GNOME Python bindings, available as `python-gobject` on Arch |
| GTK4 | 4.20.3 | Widget toolkit for overlay window | Modern toolkit with DrawingArea, CSS styling, GLib event loop |
| gtk4-layer-shell | 1.3.0 | Wayland layer-shell protocol for GTK4 | Only viable way to create non-focus-stealing overlays on wlr-based Wayland compositors |
| pycairo | 1.29.0 | Cairo drawing bindings for Python | Required by PyGObject for DrawingArea drawing; draws the waveform |
| numpy | (existing) | Audio data processing | Already a project dependency via sounddevice/scipy |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| GLib (via gi) | (bundled) | Event loop, timeout_add, idle_add | Animation timer, thread-safe GUI updates |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| GTK4 + Cairo | SDL2/pygame | Lighter weight but no layer-shell integration; would need raw Wayland client code |
| GTK4 + Cairo | Qt6 + wlr-layer-shell-qt | More C++-oriented ecosystem; PyQt6 licensing concerns; less native on GTK-based desktops |
| GTK4 + Cairo | Raw Wayland client | Maximum control but enormous implementation effort for a small overlay |
| GTK4 + Cairo | Matplotlib | Far too heavy for a real-time overlay; designed for static plots, not 30fps animation |
| Subprocess | In-process threading | GTK main loop blocks or must run on main thread; multiprocessing+GLib is explicitly broken; subprocess provides clean isolation |

**System packages (Arch Linux):**
```bash
sudo pacman -S python-gobject python-cairo gtk4-layer-shell
```

**No pip packages needed.** All dependencies are system packages accessed via GObject introspection. The project's `pyproject.toml` should NOT list these as pip dependencies -- they are system-level GI bindings.

## Architecture Patterns

### Recommended Project Structure
```
src/linuxwhisper/
  overlay/
    __init__.py          # Public API: show_overlay(), hide_overlay()
    __main__.py          # Entry point: python -m linuxwhisper.overlay
    window.py            # GTK4 Application + LayerShell window setup
    waveform.py          # Cairo DrawingArea waveform renderer
    reader.py            # Stdin pipe reader (reads amplitude data)
    x11_fallback.py      # X11-specific window configuration
```

### Pattern 1: Subprocess Overlay Architecture
**What:** The daemon spawns the overlay as a separate Python process; audio data flows via stdin pipe.
**When to use:** Always. GTK4 requires owning the main loop, which conflicts with the daemon's event loop.
**Why subprocess, not multiprocessing:** Python's `multiprocessing` module uses `fork()` without `exec()`, which is explicitly incompatible with GLib/GTK (documented at https://jameswestby.net/tech/14-caution-python-multiprocessing-and-glib-dont-mix.html). `subprocess.Popen` runs a clean new process.

```python
# In the daemon (coordinator or overlay manager):
import subprocess
import sys

class OverlayManager:
    def __init__(self):
        self._process = None

    def show(self):
        """Spawn overlay subprocess."""
        if self._process is not None:
            return
        self._process = subprocess.Popen(
            [sys.executable, "-m", "linuxwhisper.overlay"],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def hide(self):
        """Kill overlay subprocess."""
        if self._process is not None:
            self._process.terminate()
            self._process.wait(timeout=2)
            self._process = None

    def send_amplitude(self, rms: float):
        """Send RMS amplitude value to overlay via stdin pipe."""
        if self._process and self._process.stdin:
            try:
                self._process.stdin.write(f"{rms:.4f}\n".encode())
                self._process.stdin.flush()
            except (BrokenPipeError, OSError):
                pass  # Overlay died, will be cleaned up
```

### Pattern 2: GTK4 Layer-Shell Window (Wayland)
**What:** Configure a GTK4 window as a layer-shell surface anchored to bottom-right corner with no keyboard focus.
**When to use:** When running on Wayland with a wlr-layer-shell compatible compositor (Hyprland, Sway).

```python
# Source: https://github.com/wmww/gtk4-layer-shell/blob/main/examples/simple-example.py
# CRITICAL: Must load the shared library before gi imports
from ctypes import CDLL
CDLL('libgtk4-layer-shell.so')

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gtk4LayerShell', '1.0')
from gi.repository import Gtk, GLib
from gi.repository import Gtk4LayerShell as LayerShell

def setup_layer_shell(window):
    """Configure window as a Wayland layer-shell surface."""
    LayerShell.init_for_window(window)
    LayerShell.set_layer(window, LayerShell.Layer.TOP)

    # Anchor to bottom-right corner
    LayerShell.set_anchor(window, LayerShell.Edge.BOTTOM, True)
    LayerShell.set_anchor(window, LayerShell.Edge.RIGHT, True)

    # Margins from screen edges
    LayerShell.set_margin(window, LayerShell.Edge.BOTTOM, 20)
    LayerShell.set_margin(window, LayerShell.Edge.RIGHT, 20)

    # CRITICAL: No keyboard focus — overlay must never steal focus
    LayerShell.set_keyboard_mode(
        window,
        LayerShell.KeyboardMode.NONE
    )

    # Namespace helps compositors identify the surface type
    LayerShell.set_namespace(window, "linuxwhisper-overlay")

    # No exclusive zone — don't push other windows around
    LayerShell.set_exclusive_zone(window, -1)
```

### Pattern 3: Cairo Waveform Drawing on GTK4 DrawingArea
**What:** Custom DrawingArea with set_draw_func that renders the waveform using Cairo line drawing.
**When to use:** For the waveform visualization widget.

```python
# Source: https://pygobject.gnome.org/guide/cairo_integration.html
import cairo
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib
import collections

class WaveformWidget(Gtk.DrawingArea):
    """Live audio waveform display using Cairo."""

    def __init__(self, history_size=100):
        super().__init__()
        self._amplitudes = collections.deque(maxlen=history_size)
        self.set_draw_func(self._draw)
        # Start 30fps refresh timer
        self._timer_id = GLib.timeout_add(33, self._tick)  # ~30fps

    def push_amplitude(self, rms: float):
        """Add a new amplitude value (called from stdin reader)."""
        self._amplitudes.append(rms)

    def _tick(self):
        """Timer callback — trigger redraw."""
        self.queue_draw()
        return True  # Keep timer running

    def _draw(self, area, ctx, width, height):
        """Cairo draw function for waveform."""
        # Blue background
        ctx.set_source_rgb(0.13, 0.39, 0.68)  # #2164AD
        ctx.rectangle(0, 0, width, height)
        ctx.fill()

        if not self._amplitudes:
            return

        # White waveform
        ctx.set_source_rgb(1.0, 1.0, 1.0)
        ctx.set_line_width(2.0)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)

        amps = list(self._amplitudes)
        n = len(amps)
        mid_y = height / 2.0

        # Draw waveform as mirrored amplitude bars
        for i, amp in enumerate(amps):
            x = (i / max(n - 1, 1)) * width
            # Scale amplitude to half-height
            bar_h = amp * mid_y * 5.0  # Scale factor for visibility
            bar_h = min(bar_h, mid_y - 2)  # Clamp

            if i == 0:
                ctx.move_to(x, mid_y - bar_h)
            else:
                ctx.line_to(x, mid_y - bar_h)

        # Mirror bottom half
        for i in range(n - 1, -1, -1):
            x = (i / max(n - 1, 1)) * width
            amp = amps[i]
            bar_h = amp * mid_y * 5.0
            bar_h = min(bar_h, mid_y - 2)
            ctx.line_to(x, mid_y + bar_h)

        ctx.close_path()
        ctx.fill()

        ctx.stroke()

    def stop(self):
        """Stop the refresh timer."""
        if self._timer_id:
            GLib.source_remove(self._timer_id)
            self._timer_id = None
```

### Pattern 4: Stdin Pipe Reader with GLib Integration
**What:** Read amplitude values from stdin in the overlay process using GLib.io_add_watch or a daemon thread with GLib.idle_add.
**When to use:** In the overlay subprocess to receive data from the daemon.

```python
import sys
import threading
from gi.repository import GLib

class StdinReader:
    """Read amplitude values from stdin pipe, push to waveform widget."""

    def __init__(self, waveform_widget):
        self._widget = waveform_widget
        self._thread = None
        self._running = False

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def _read_loop(self):
        """Read lines from stdin in background thread."""
        for line in sys.stdin:
            if not self._running:
                break
            line = line.strip()
            if not line:
                continue
            try:
                rms = float(line)
                # Schedule GUI update on main thread
                GLib.idle_add(self._widget.push_amplitude, rms)
            except ValueError:
                pass  # Ignore malformed lines

    def stop(self):
        self._running = False
```

### Pattern 5: Audio Amplitude Extraction from Existing Recorder
**What:** Extract RMS amplitude from the audio callback and send it to the overlay.
**When to use:** In the daemon, hooking into the existing AudioRecorder._callback.

```python
import numpy as np

def compute_rms(audio_chunk: np.ndarray) -> float:
    """Compute RMS amplitude from an audio chunk (float32 numpy array)."""
    if audio_chunk.size == 0:
        return 0.0
    # Flatten multi-channel to mono if needed
    if audio_chunk.ndim > 1:
        audio_chunk = audio_chunk.mean(axis=1)
    return float(np.sqrt(np.mean(audio_chunk ** 2)))
```

The existing `AudioRecorder._callback` already copies `indata` and puts it in a queue. The amplitude extraction should happen either:
- (a) In the callback itself (compute RMS on the copy, send to overlay) -- fast, ~microseconds for 1024 samples
- (b) Via a secondary observer/callback on the recorder that the overlay manager subscribes to

Option (a) is simpler. The callback is non-blocking (numpy RMS on ~1024 float32 samples is trivial).

### Pattern 6: X11 Fallback
**What:** On X11, create a regular GTK4 window with window manager hints to avoid focus stealing.
**When to use:** When layer-shell is not available (X11 sessions, GNOME Wayland).

```python
# X11 fallback: use GDK X11 backend properties
# GTK4 removed set_accept_focus and set_type_hint, but on X11 we can use
# GdkX11 to set window properties after realization.

def setup_x11_fallback(window):
    """Configure window for X11: always-on-top, no focus, no decoration."""
    # In GTK4, use CSS to remove decoration and set transparency
    css_provider = Gtk.CssProvider()
    css_provider.load_from_string("""
        window {
            background-color: transparent;
        }
    """)
    display = window.get_display()
    Gtk.StyleContext.add_provider_for_display(
        display, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )

    # After window is realized, set X11 properties
    def on_realize(widget):
        surface = widget.get_native().get_surface()
        # GdkX11.X11Surface provides access to X11 window properties
        # Set window type to UTILITY or NOTIFICATION to avoid taskbar and focus
        try:
            gi.require_version('GdkX11', '4.0')
            from gi.repository import GdkX11
            if isinstance(surface, GdkX11.X11Surface):
                # X11 surfaces in GTK4 are limited, but override-redirect
                # can be set via the surface
                pass
        except (ValueError, ImportError):
            pass

    window.connect('realize', on_realize)
```

**Note on X11 fallback complexity:** GTK4 removed many X11-specific window management functions. The cleanest X11 approach is to position the window and rely on compositor behavior (most X11 WMs respect EWMH hints). The window should be set as `always_on_top` via the window manager, be undecorated (via CSS), and be small enough that accidental focus is unlikely. For Hyprland/Sway (the primary targets), layer-shell handles everything properly.

### Anti-Patterns to Avoid
- **Running GTK main loop in a thread:** GTK4 explicitly requires the main loop on the main thread. Running it in a daemon thread causes crashes and undefined behavior.
- **Using Python multiprocessing with GTK:** `fork()` without `exec()` breaks GLib. Always use `subprocess.Popen` for clean process isolation.
- **Using matplotlib for real-time waveform:** matplotlib is designed for static plots, not 30fps animation in a small overlay. Cairo + DrawingArea is the correct choice.
- **Sending raw audio samples over the pipe:** Sending 16000 float32 samples/second over a pipe is wasteful. Send computed RMS values (one float per callback, ~30-60 per second).
- **Using `GLib.timeout_add` for amplitude reading:** This polls and wastes CPU. Use a daemon thread reading stdin + `GLib.idle_add` for push-based updates.
- **Exclusive zone on overlay:** Setting auto_exclusive_zone would push other windows away from the overlay. Use `set_exclusive_zone(-1)` to overlay without displacing anything.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Wayland overlay positioning | Custom Wayland client with wl_surface/wl_subsurface | gtk4-layer-shell | Layer-shell protocol is the standard; raw Wayland requires hundreds of lines of C-level protocol handling |
| Non-focus-stealing windows | Custom focus management logic | LayerShell.KeyboardMode.NONE | Protocol-level guarantee; no compositor-specific hacks needed |
| Real-time 2D drawing | OpenGL/Vulkan renderer | Cairo on DrawingArea | For a small waveform widget, Cairo is more than fast enough and infinitely simpler |
| Cross-display-server detection | Custom env var parsing | Existing `detect_session_type()` in detector.py | Already implemented and tested in Phase 5 |
| IPC protocol | Custom socket/protocol | stdin pipe with text lines | For unidirectional float values, stdin pipe is trivially simple and reliable |

**Key insight:** The overlay is a small, short-lived visual widget. Every technology choice should optimize for simplicity and reliability, not flexibility. gtk4-layer-shell + Cairo is the simplest stack that meets all requirements.

## Common Pitfalls

### Pitfall 1: GTK4-Layer-Shell Library Loading Order
**What goes wrong:** ImportError or segfault when importing Gtk4LayerShell via gi.
**Why it happens:** `libgtk4-layer-shell.so` must be loaded before `libwayland-client` to intercept Wayland calls. If GTK4 loads first, the interception fails.
**How to avoid:** Always load the shared library explicitly before any gi imports:
```python
from ctypes import CDLL
CDLL('libgtk4-layer-shell.so')
```
**Warning signs:** Segfault on window.present(), or LayerShell functions silently doing nothing.

### Pitfall 2: Overlay Steals Focus During Dictation
**What goes wrong:** When the overlay appears, the user's active window loses focus, and injected text goes to the wrong window.
**Why it happens:** Incorrect keyboard_mode setting, or missing layer-shell initialization.
**How to avoid:** Always set `LayerShell.set_keyboard_mode(window, LayerShell.KeyboardMode.NONE)`. Verify by testing that typing continues in the background window while overlay is visible.
**Warning signs:** Cursor blinking in overlay window; text not appearing in expected window.

### Pitfall 3: Subprocess Zombie Processes
**What goes wrong:** Overlay processes accumulate if not properly cleaned up.
**Why it happens:** `terminate()` without `wait()`, or not handling process death.
**How to avoid:** Always call `process.wait(timeout=2)` after `terminate()`. Use `process.poll()` to check if process is still alive before sending data. Handle `BrokenPipeError` when writing to stdin.
**Warning signs:** Multiple `python -m linuxwhisper.overlay` processes visible in `ps`.

### Pitfall 4: Pipe Buffer Blocking
**What goes wrong:** The daemon blocks when writing amplitude data to the overlay's stdin.
**Why it happens:** If the overlay process stops reading (e.g., it's hanging), the pipe buffer fills up (typically 64KB on Linux) and `write()` blocks.
**How to avoid:** Write amplitude data in a non-blocking manner. Either use `os.write` with `O_NONBLOCK` on the pipe fd, or write from a separate thread, or accept that the data is small enough (a few bytes per write) that blocking is extremely unlikely at 30-60 writes/second.
**Warning signs:** Daemon hangs during recording after overlay crashes.

### Pitfall 5: GLib.timeout_add Return Value
**What goes wrong:** Timer stops firing after first callback.
**Why it happens:** `timeout_add` callback must return `True` to keep running. Returning `None` (implicit Python return) or `False` removes the timer.
**How to avoid:** Always explicitly `return True` from timeout callbacks that should repeat.
**Warning signs:** Waveform freezes after one frame.

### Pitfall 6: Layer-Shell Not Supported (GNOME, X11)
**What goes wrong:** `Gtk4LayerShell.is_supported()` returns False; overlay doesn't appear.
**Why it happens:** GNOME Wayland does not implement wlr-layer-shell. X11 doesn't have it at all.
**How to avoid:** Check `Gtk4LayerShell.is_supported()` before calling layer-shell functions. Fall back to regular GTK4 window positioning on X11/GNOME. The overlay is a nice-to-have visual feature, so graceful degradation is acceptable.
**Warning signs:** Overlay works on Sway/Hyprland but not on GNOME or X11.

### Pitfall 7: Drawing Performance with Large History
**What goes wrong:** Waveform rendering becomes sluggish.
**Why it happens:** Drawing thousands of line segments per frame in Cairo.
**How to avoid:** Limit waveform history to ~100-150 points. At 30fps with ~30-60 amplitude values/second, this represents 2-3 seconds of visible history, which is visually sufficient.
**Warning signs:** CPU usage spikes when overlay is visible; frame drops.

## Code Examples

### Complete Overlay Entry Point
```python
# src/linuxwhisper/overlay/__main__.py
"""Overlay subprocess entry point: python -m linuxwhisper.overlay"""

from ctypes import CDLL

# MUST load before any gi imports
try:
    CDLL('libgtk4-layer-shell.so')
    _layer_shell_available = True
except OSError:
    _layer_shell_available = False

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib

if _layer_shell_available:
    gi.require_version('Gtk4LayerShell', '1.0')
    from gi.repository import Gtk4LayerShell as LayerShell


def main():
    app = Gtk.Application(application_id='com.linuxwhisper.overlay')
    app.connect('activate', on_activate)
    app.run(None)


def on_activate(app):
    window = Gtk.Window(application=app)
    window.set_default_size(200, 60)
    window.set_decorated(False)
    window.set_resizable(False)

    # Try layer-shell for Wayland
    use_layer_shell = _layer_shell_available and LayerShell.is_supported()
    if use_layer_shell:
        LayerShell.init_for_window(window)
        LayerShell.set_layer(window, LayerShell.Layer.TOP)
        LayerShell.set_anchor(window, LayerShell.Edge.BOTTOM, True)
        LayerShell.set_anchor(window, LayerShell.Edge.RIGHT, True)
        LayerShell.set_margin(window, LayerShell.Edge.BOTTOM, 20)
        LayerShell.set_margin(window, LayerShell.Edge.RIGHT, 20)
        LayerShell.set_keyboard_mode(window, LayerShell.KeyboardMode.NONE)
        LayerShell.set_namespace(window, "linuxwhisper-overlay")
        LayerShell.set_exclusive_zone(window, -1)

    # ... add waveform widget, start stdin reader ...
    window.present()


if __name__ == '__main__':
    main()
```

### Computing and Sending Amplitude from AudioRecorder
```python
# Integration point in coordinator or overlay manager
import numpy as np

def _on_audio_chunk(self, chunk: np.ndarray):
    """Called from audio callback with each chunk."""
    if self._overlay_manager and self._overlay_manager.is_running():
        # Flatten to mono if multi-channel
        if chunk.ndim > 1:
            chunk = chunk.mean(axis=1)
        rms = float(np.sqrt(np.mean(chunk ** 2)))
        self._overlay_manager.send_amplitude(rms)
```

### CSS Styling for Polished Appearance
```python
# Apply rounded corners and consistent styling
css = """
window {
    border-radius: 8px;
    background-color: #2164AD;
}
"""
provider = Gtk.CssProvider()
provider.load_from_string(css)
Gtk.StyleContext.add_provider_for_display(
    window.get_display(),
    provider,
    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| GTK3 + gtk-layer-shell | GTK4 + gtk4-layer-shell | gtk4-layer-shell 1.0 (2023) | GTK4 is current; GTK3 entering maintenance mode |
| Gdk.threads_init() + threads_enter/leave | GLib.idle_add() from threads | GTK4 (2020+) | Old threading model fully deprecated; use GLib.idle_add exclusively |
| set_accept_focus(False) for X11 | Layer-shell keyboard_mode NONE for Wayland | Wayland adoption | X11 approach doesn't exist in Wayland; layer-shell is the replacement |
| DrawingArea "draw" signal (GTK3) | DrawingArea.set_draw_func() (GTK4) | GTK4 | Signal-based drawing replaced with function callback |

**Deprecated/outdated:**
- `Gdk.threads_init()`, `Gdk.threads_enter()`, `Gdk.threads_leave()`: Fully removed in GTK4. Use GLib.idle_add instead.
- `Gtk.Window.set_type_hint()`: Gone in GTK4. Layer-shell replaces this for Wayland.
- `Gtk.Window.set_accept_focus()`: Gone in GTK4. Layer-shell keyboard_mode replaces this.
- `Gtk.Window.set_keep_above()`: Gone in GTK4. Layer-shell layer TOP/OVERLAY replaces this.

## Open Questions

1. **X11 no-focus behavior in GTK4**
   - What we know: GTK4 removed set_accept_focus(), set_type_hint(), and set_keep_above(). Layer-shell handles Wayland.
   - What's unclear: The exact mechanism to prevent focus stealing on X11 in GTK4 without those APIs. May need to use GdkX11 backend-specific calls or accept that X11 is a degraded experience.
   - Recommendation: Prioritize Wayland (primary user is on Hyprland). For X11, create the window and position it manually; most X11 WMs won't focus a small undecorated window that never requests focus. Test and iterate.

2. **GNOME Wayland support**
   - What we know: GNOME does not implement wlr-layer-shell. `Gtk4LayerShell.is_supported()` will return False on GNOME.
   - What's unclear: Whether a regular GTK4 window on GNOME Wayland can be made to not steal focus.
   - Recommendation: Use `is_supported()` check. On GNOME Wayland, fall back to regular window. This is acceptable since the primary targets are Hyprland and Sway.

3. **Optimal waveform window size**
   - What we know: Should be "small and discrete" per success criteria.
   - What's unclear: Exact pixel dimensions that look good across different screen resolutions.
   - Recommendation: Start with 200x60 pixels (width x height). This is small enough to be unobtrusive but large enough to see the waveform. Make it configurable later if needed.

## Sources

### Primary (HIGH confidence)
- [gtk4-layer-shell GitHub](https://github.com/wmww/gtk4-layer-shell) - Python example, README, API overview
- [gtk4-layer-shell API docs](https://wmww.github.io/gtk4-layer-shell/gtk4-layer-shell-GTK4-Layer-Shell.html) - Full API: layers, edges, keyboard modes, exclusive zones
- [wlr-layer-shell protocol](https://wayland.app/protocols/wlr-layer-shell-unstable-v1) - Protocol specification: keyboard_interactivity enum, layer enum, anchor flags
- [Arch Linux gtk4-layer-shell 1.3.0-1](https://archlinux.org/packages/extra/x86_64/gtk4-layer-shell/) - Package version, dependencies
- [Arch Linux python-gobject 3.54.5-2](https://archlinux.org/packages/extra/x86_64/python-gobject/) - Package version, dependencies
- [Arch Linux python-cairo 1.29.0-1](https://archlinux.org/packages/extra/x86_64/python-cairo/) - Package version
- [PyGObject Cairo integration](https://pygobject.gnome.org/guide/cairo_integration.html) - DrawingArea + set_draw_func pattern
- [PyGObject threading guide](https://pygobject.gnome.org/guide/threading.html) - GLib.idle_add, thread safety rules
- [GTK4 DrawingArea docs](https://docs.gtk.org/gtk4/class.DrawingArea.html) - set_draw_func signature, queue_draw
- [GTK4 threading docs](https://docs.gtk.org/gtk4/section-threading.html) - GTK4 threading model

### Secondary (MEDIUM confidence)
- [python-multiprocessing + GLib warning](https://jameswestby.net/tech/14-caution-python-multiprocessing-and-glib-dont-mix.html) - Verified: fork() without exec() breaks GLib
- [sounddevice examples](https://python-sounddevice.readthedocs.io/en/0.3.14/examples.html) - Queue-based callback pattern for audio data sharing
- [GLib.timeout_add docs](https://docs.gtk.org/glib/func.timeout_add.html) - Timer API for animation refresh
- [GTK4 CSS properties](https://docs.gtk.org/gtk4/css-properties.html) - CSS styling for windows

### Tertiary (LOW confidence)
- [GNOME Discourse: X11 properties in GTK4](https://discourse.gnome.org/t/setting-x11-properties-in-gtk4/9985) - GTK4 removed X11 window management; exact fallback unclear
- [GNOME Discourse: GTK4 always on top](https://discourse.gnome.org/t/gtk4-set-window-always-on-top-and-on-center-of-current-monitor/9068) - Confirms removal of set_keep_above

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All packages verified in Arch repos with exact versions; gtk4-layer-shell API documented with Python examples
- Architecture (subprocess model): HIGH - multiprocessing+GLib incompatibility well-documented; subprocess is proven pattern used by nwg-shell ecosystem
- Architecture (Wayland layer-shell): HIGH - Protocol spec verified; gtk4-layer-shell Python example tested pattern; keyboard_mode NONE confirmed in protocol
- Waveform rendering: HIGH - Cairo DrawingArea + set_draw_func is standard GTK4 pattern with official docs
- X11 fallback: LOW - GTK4 removed relevant X11 APIs; exact approach needs prototyping
- Pitfalls: HIGH - All sourced from official docs, GitHub issues, or verified community reports

**Research date:** 2026-02-18
**Valid until:** 2026-03-18 (stable ecosystem, no expected breaking changes)
