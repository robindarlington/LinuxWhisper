"""GTK4 overlay window creation with Wayland layer-shell positioning.

On Wayland compositors that support wlr-layer-shell (Hyprland, Sway), the
window is anchored to the bottom-right corner at the TOP layer with no
keyboard focus. On X11 or unsupported compositors, falls back to a small
undecorated window.
"""

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

# Conditional layer-shell import — only available if __main__ preloaded the lib
try:
    gi.require_version("Gtk4LayerShell", "1.0")
    from gi.repository import Gtk4LayerShell as LayerShell
except (ValueError, ImportError):
    LayerShell = None


def create_overlay_window(
    app: Gtk.Application,
    *,
    use_layer_shell: bool = False,
    width: int = 120,
    height: int = 32,
    abs_x: int | None = None,
    abs_y: int | None = None,
) -> Gtk.Window:
    """Create and configure the overlay window.

    Args:
        app: The GTK Application instance.
        use_layer_shell: Whether to use layer-shell positioning (Wayland).
        width: Window width in pixels.
        height: Window height in pixels.
        abs_x: Absolute X position (from left edge of screen). If None, falls
               back to bottom-right corner.
        abs_y: Absolute Y position (from top edge of screen). If None, falls
               back to bottom-right corner.

    Returns:
        Configured Gtk.Window (not yet presented).
    """
    window = Gtk.Window(application=app)
    window.set_default_size(width, height)
    window.set_decorated(False)
    window.set_resizable(False)

    if use_layer_shell and LayerShell is not None:
        if abs_x is not None and abs_y is not None:
            _setup_layer_shell_absolute(window, abs_x, abs_y)
        else:
            _setup_layer_shell_corner(window, margin=20)

    _apply_css(window)
    return window


def _setup_layer_shell_absolute(
    window: Gtk.Window, x: int, y: int
) -> None:
    """Position overlay at absolute screen coordinates via layer-shell.

    Uses TOP+LEFT anchors with margins to place the window at (x, y).
    """
    LayerShell.init_for_window(window)
    LayerShell.set_layer(window, LayerShell.Layer.TOP)

    # Anchor to top-left, use margins for absolute positioning
    LayerShell.set_anchor(window, LayerShell.Edge.TOP, True)
    LayerShell.set_anchor(window, LayerShell.Edge.LEFT, True)
    LayerShell.set_margin(window, LayerShell.Edge.TOP, y)
    LayerShell.set_margin(window, LayerShell.Edge.LEFT, x)

    LayerShell.set_keyboard_mode(window, LayerShell.KeyboardMode.NONE)
    LayerShell.set_namespace(window, "linuxwhisper-overlay")
    LayerShell.set_exclusive_zone(window, -1)


def _setup_layer_shell_corner(window: Gtk.Window, margin: int) -> None:
    """Fallback: anchor overlay to bottom-right corner via layer-shell."""
    LayerShell.init_for_window(window)
    LayerShell.set_layer(window, LayerShell.Layer.TOP)

    LayerShell.set_anchor(window, LayerShell.Edge.BOTTOM, True)
    LayerShell.set_anchor(window, LayerShell.Edge.RIGHT, True)
    LayerShell.set_margin(window, LayerShell.Edge.BOTTOM, margin)
    LayerShell.set_margin(window, LayerShell.Edge.RIGHT, margin)

    LayerShell.set_keyboard_mode(window, LayerShell.KeyboardMode.NONE)
    LayerShell.set_namespace(window, "linuxwhisper-overlay")
    LayerShell.set_exclusive_zone(window, -1)


def _apply_css(window: Gtk.Window) -> None:
    """Apply CSS styling for rounded corners and background color."""
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
