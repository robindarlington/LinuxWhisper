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
    width: int = 200,
    height: int = 60,
    margin: int = 20,
) -> Gtk.Window:
    """Create and configure the overlay window.

    Args:
        app: The GTK Application instance.
        use_layer_shell: Whether to use layer-shell positioning (Wayland).
        width: Window width in pixels.
        height: Window height in pixels.
        margin: Margin from screen edges in pixels.

    Returns:
        Configured Gtk.Window (not yet presented).
    """
    window = Gtk.Window(application=app)
    window.set_default_size(width, height)
    window.set_decorated(False)
    window.set_resizable(False)

    if use_layer_shell and LayerShell is not None:
        _setup_layer_shell(window, margin)

    _apply_css(window)
    return window


def _setup_layer_shell(window: Gtk.Window, margin: int) -> None:
    """Configure window as a Wayland layer-shell surface.

    Anchored to bottom-right corner, TOP layer, no keyboard focus,
    no exclusive zone (does not push other windows).
    """
    LayerShell.init_for_window(window)
    LayerShell.set_layer(window, LayerShell.Layer.TOP)

    # Anchor to bottom-right corner
    LayerShell.set_anchor(window, LayerShell.Edge.BOTTOM, True)
    LayerShell.set_anchor(window, LayerShell.Edge.RIGHT, True)

    # Margins from screen edges
    LayerShell.set_margin(window, LayerShell.Edge.BOTTOM, margin)
    LayerShell.set_margin(window, LayerShell.Edge.RIGHT, margin)

    # CRITICAL: no keyboard focus — overlay must never steal focus
    LayerShell.set_keyboard_mode(window, LayerShell.KeyboardMode.NONE)

    # Compositor identification namespace
    LayerShell.set_namespace(window, "linuxwhisper-overlay")

    # Don't push other windows around
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
