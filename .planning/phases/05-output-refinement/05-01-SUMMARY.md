# Plan 05-01 Summary: Multi-backend Fallback Injector

**Status:** COMPLETE
**Commit:** 8c46818

## What was built

Replaced single-backend injection system with multi-backend FallbackInjector that auto-selects the best text injection method based on compositor detection.

## Key artifacts

| File | Purpose |
|------|---------|
| `injection/detector.py` | Added `detect_compositor()` and `is_wlroots_compositor()` |
| `injection/base.py` | `InjectorBackend` ABC with `name()`, `is_available()`, `type_text()`, `supports_unicode()` |
| `injection/wtype.py` | `WtypeBackend` — full Unicode via wtype on wlroots compositors |
| `injection/clipboard.py` | `ClipboardWaylandBackend` and `ClipboardX11Backend` — Unicode via clipboard paste |
| `injection/wayland.py` | `YdotoolBackend` (refactored from `WaylandInjector`) — ASCII only |
| `injection/x11.py` | `XdotoolBackend` (refactored from `X11Injector`) — ASCII only, --clearmodifiers |
| `injection/fallback.py` | `FallbackInjector` — tries backends in order, Unicode-capable first for non-ASCII |
| `injection/__init__.py` | `create_injector(config)` — builds backend chain per session/compositor |
| `config/defaults.py` | Added `clipboard_restore_delay_ms: 300` |
| `pipeline/coordinator.py` | Passes config to `create_injector(config)` |

## Backend selection

- **Wayland (wlroots):** wtype > clipboard-wayland > ydotool
- **Wayland (GNOME/KDE):** clipboard-wayland > ydotool
- **X11:** xdotool > clipboard-x11
- **Unknown:** all backends in order

## Verification

All 11 success criteria verified via automated checks. Session detected as `wayland`, compositor as `hyprland`.
