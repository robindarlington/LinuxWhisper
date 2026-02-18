# Phase 5: Output Refinement — Research

## Research Summary

Phase 5 hardens the existing text injection infrastructure to handle Unicode, work universally across compositors, auto-space between dictations, and work in native Wayland apps (Firefox, Chrome). The critical discovery is that **ydotool cannot type Unicode characters at all** -- it simulates a physical keyboard which has no concept of Unicode code points. This requires a multi-backend fallback strategy with clipboard-based injection as the Unicode-capable path.

---

## Standard Stack

### Primary Tools (ordered by preference)

| Tool | Protocol | Unicode | Compositors | Daemon | Package (Arch) |
|------|----------|---------|-------------|--------|-----------------|
| **wtype** | zwp_virtual_keyboard_v1 | Full (generates keymap on-the-fly) | wlroots-based only (Hyprland, Sway) | No | `wtype` |
| **ydotool** | /dev/uinput (kernel) | ASCII only | All (kernel-level bypass) | Yes (ydotoold) | `ydotool` |
| **xdotool** | X11 events | Partial (locale-dependent) | X11 only | No | `xdotool` |
| **wl-clipboard** | Wayland clipboard | Full (any MIME type) | All Wayland | No | `wl-clipboard` |
| **xclip** | X11 CLIPBOARD selection | Full | X11 only | No | `xclip` |

### Fallback Chain (use this order)

For **Wayland (wlroots: Hyprland, Sway)**:
1. **wtype** -- best option, native Unicode/CJK, no daemon, direct virtual keyboard protocol
2. **Clipboard fallback** (`wl-copy` + `ydotool key ctrl+v`) -- for when wtype unavailable
3. **ydotool type** -- ASCII-only path, works everywhere but no Unicode

For **Wayland (GNOME, KDE)** -- wtype does NOT work on these:
1. **Clipboard fallback** (`wl-copy` + `ydotool key ctrl+v`) -- primary path
2. **ydotool type** -- ASCII-only path

For **X11**:
1. **xdotool type** -- with `LANG=en_US.UTF-8` and `--clearmodifiers`
2. **Clipboard fallback** (`xclip` + `xdotool key ctrl+v`) -- Unicode fallback

### Decision: Use wtype as primary on wlroots, clipboard fallback for Unicode everywhere else

**Confidence: HIGH** -- This matches the Voxtype fallback chain (the most mature Linux dictation tool), confirmed by multiple independent sources.

---

## Architecture Patterns

### 1. Multi-Backend Injector with Fallback Chain

The injector should try backends in order and fall through on failure. This is the established pattern used by Voxtype and other mature tools.

```
InjectorBackend (ABC)
  +-- WtypeBackend        # wlroots Wayland (Hyprland, Sway)
  +-- ClipboardBackend    # Universal fallback (wl-copy/xclip + paste keystroke)
  +-- YdotoolBackend      # Existing, ASCII-only Wayland
  +-- XdotoolBackend      # Existing, X11

FallbackInjector
  - backends: list[InjectorBackend]  # ordered by preference
  - _detect_available() -> list[InjectorBackend]
  - type_text(text) -> tries each backend until one succeeds
```

### 2. ASCII vs Unicode Path Split

Since ydotool handles ASCII fine but fails on Unicode, the injector should detect whether text contains non-ASCII characters and choose the optimal path:

- **ASCII-only text**: Use ydotool/xdotool directly (fastest, no clipboard clobber)
- **Contains Unicode**: Use wtype (wlroots) or clipboard fallback (everywhere else)

This avoids the clipboard save/restore overhead for the common case (English dictation produces ASCII).

### 3. Clipboard Save/Restore Pattern

When using the clipboard fallback path, preserve the user's clipboard:

```
1. Save current clipboard: old = wl-paste (or xclip -o)
2. Copy text to clipboard: echo text | wl-copy (or echo text | xclip -selection clipboard)
3. Simulate Ctrl+V: ydotool key 29:1 47:1 47:0 29:0 (or xdotool key ctrl+v)
4. Wait for paste to complete (50-100ms minimum)
5. Restore clipboard: echo old | wl-copy (or echo old | xclip -selection clipboard)
```

**Critical timing**: The OpenWhispr project discovered that 200ms clipboard restore delay is too fast -- the app hasn't finished processing the paste event. Use 300-500ms minimum.

### 4. Dictation Spacing State Machine

Track spacing state between consecutive dictations:

```
States:
  EMPTY    -- No text injected yet (or after newline)
  HAS_TEXT -- Text was injected, next dictation needs leading space

Transitions:
  inject(text):
    if state == HAS_TEXT:
      prepend " " to text
    inject text
    if text ends with newline:
      state = EMPTY
    else:
      state = HAS_TEXT

  reset():
    state = EMPTY
```

**Prepend a space, don't append.** Appending leaves a trailing space visible to the user; prepending is invisible because the cursor is at the end.

### 5. Compositor Detection (enhance existing detector.py)

Extend the existing session detection to identify the specific compositor for backend selection:

```
Session Type Detection (existing):
  XDG_SESSION_TYPE -> "wayland" | "x11"
  WAYLAND_DISPLAY -> "wayland"
  DISPLAY -> "x11"
  loginctl fallback

Compositor Detection (new, Wayland only):
  XDG_CURRENT_DESKTOP -> "Hyprland" | "sway" | "GNOME" | "KDE"
  HYPRLAND_INSTANCE_SIGNATURE -> Hyprland
  SWAYSOCK -> Sway
  Process check: pgrep -x "hyprland|sway|gnome-shell|kwin_wayland"
```

This determines whether wtype is viable (wlroots compositors) or clipboard fallback is needed (GNOME/KDE).

---

## Don't Hand-Roll

1. **Virtual keyboard protocol interaction** -- Use `wtype` binary, do not implement zwp_virtual_keyboard_v1 directly. The protocol requires generating a keymap on-the-fly for Unicode; wtype already does this correctly.

2. **Clipboard operations** -- Use `wl-copy`/`wl-paste` (Wayland) and `xclip` (X11). Do not implement Wayland clipboard protocol or X11 selections directly.

3. **uinput device management** -- Use `ydotool` via subprocess. The ydotoold daemon handles virtual device lifecycle, recognition timing, and persistence. Do not create uinput devices directly.

4. **Key code mapping** -- ydotool and xdotool handle scancode-to-character mapping for ASCII. wtype handles Unicode-to-keymap generation. Do not build character-to-keycode lookup tables.

5. **Keyboard layout detection** -- wtype uses libxkbcommon for layout resolution. ydotool uses the system keyboard layout. Do not detect or compensate for keyboard layouts manually.

6. **X11 modifier state management** -- xdotool's `--clearmodifiers` flag handles this. Do not manually track or clear modifier state.

---

## Common Pitfalls

### P1: ydotool Cannot Type Unicode (CRITICAL)
- **Problem**: `ydotool type "cafe"` produces `cafe` but `ydotool type "caf\u00e9"` produces nothing after 'f'. ydotool simulates physical keyboard scancodes; there is no scancode for `\u00e9`.
- **Evidence**: GitHub issues [#9](https://github.com/ReimuNotMoe/ydotool/issues/9), [#22](https://github.com/ReimuNotMoe/ydotool/issues/22), [#249](https://github.com/ReimuNotMoe/ydotool/issues/249). Maintainer confirmed: "It's not possible at this moment since we are emulating a physical keyboard."
- **Impact**: All non-ASCII text (accented characters, emoji, CJK) will silently fail or produce garbage.
- **Mitigation**: Use wtype for wlroots compositors. Use clipboard fallback (wl-copy + Ctrl+V) everywhere else.
- **Confidence**: CONFIRMED -- multiple sources, maintainer acknowledged, unfixable by design.

### P2: wtype Does Not Work on GNOME or KDE Wayland
- **Problem**: GNOME (Mutter) and KDE (KWin) do not implement `zwp_virtual_keyboard_v1` protocol. wtype exits with "Compositor does not support the virtual keyboard protocol."
- **Evidence**: wtype issues [#29](https://github.com/atx/wtype/issues/29), [#34](https://github.com/atx/wtype/issues/34), [#45](https://github.com/atx/wtype/issues/45).
- **Impact**: wtype is viable ONLY on wlroots-based compositors (Hyprland, Sway, river, etc.).
- **Mitigation**: Detect compositor. Use wtype on wlroots; use clipboard fallback on GNOME/KDE.
- **Confidence**: CONFIRMED -- protocol support is compositor-specific, GNOME/KDE have explicitly declined to implement it.

### P3: xdotool Silently Fails on Native Wayland Windows
- **Problem**: On a Wayland session, `xdotool type` returns exit code 0 but produces no output in native Wayland windows (Firefox Wayland, Chrome Wayland, GTK4 apps). It only works in XWayland windows.
- **Evidence**: [OpenWhispr #240](https://github.com/OpenWhispr/openwhispr/issues/240) documents this exact failure mode where xdotool appears to succeed but silently fails.
- **Impact**: If the code tries xdotool first on Wayland (because DISPLAY is set for XWayland compatibility), it will appear to work but inject nothing.
- **Mitigation**: On Wayland sessions, never try xdotool. Use session type detection (already implemented) to gate backend selection.
- **Confidence**: CONFIRMED -- multiple sources.

### P4: Clipboard Restore Race Condition
- **Problem**: After clipboard paste (Ctrl+V), restoring the original clipboard too quickly causes the pasted text to flash then disappear. The target app hasn't finished reading the clipboard when it gets overwritten.
- **Evidence**: [OpenWhispr #240](https://github.com/OpenWhispr/openwhispr/issues/240) -- 200ms was too fast, text vanished.
- **Impact**: User loses both the dictated text and their clipboard contents.
- **Mitigation**: Wait at least 300ms after paste before restoring clipboard. Configurable via `clipboard_restore_delay_ms` in config.
- **Confidence**: HIGH -- documented in production.

### P5: ydotool Key Delay Too Low Causes Character Swapping
- **Problem**: With very low `--key-delay` values (0-2ms), ydotool can swap characters (e.g., `]` becomes `}`), drop characters, or produce digits instead of letters.
- **Evidence**: ydotool issues [#5](https://github.com/ReimuNotMoe/ydotool/issues/5), [#132](https://github.com/ReimuNotMoe/ydotool/issues/132), [#292](https://github.com/ReimuNotMoe/ydotool/issues/292).
- **Impact**: Corrupted output text.
- **Mitigation**: Use minimum 3ms key delay. The current default of 12ms is safe. For web apps (Firefox, Chrome), 3ms minimum is recommended by OpenWhispr.
- **Confidence**: HIGH -- multiple reports, version-specific (worse in 1.0.0).

### P6: ydotool Socket Permissions
- **Problem**: ydotoold may create socket at `/tmp/.ydotool_socket` with root-only permissions (`srw-------`), blocking user-level access.
- **Evidence**: [OpenWhispr #240](https://github.com/OpenWhispr/openwhispr/issues/240), Arch Linux packaging [issue #1](https://gitlab.archlinux.org/archlinux/packaging/packages/ydotool/-/issues/1).
- **Impact**: ydotool commands fail silently or with permission errors.
- **Mitigation**: Check socket permissions at init. Support both `/tmp/.ydotool_socket` and `/run/user/$UID/.ydotool_socket`. Check `YDOTOOL_SOCKET` env var. Already partially implemented in existing `wayland.py`.
- **Confidence**: HIGH.

### P7: xdotool Unicode Needs Locale AND Delay
- **Problem**: `xdotool type` with Unicode requires both `LANG=en_US.UTF-8` AND sufficient `--delay` for some apps (Firefox needs 47-700ms for emoji).
- **Evidence**: [xdotool #154](https://github.com/jordansissel/xdotool/issues/154), [Mozilla bug 1657777](https://bugzilla.mozilla.org/show_bug.cgi?id=1657777).
- **Impact**: Unicode characters may produce "Invalid multi-byte sequence encountered" errors.
- **Mitigation**: Set `LANG=en_US.UTF-8` (already done in existing code). For Unicode text, prefer clipboard fallback on X11 rather than relying on xdotool type.
- **Confidence**: HIGH.

---

## Code Examples

### Example 1: wtype Basic Usage (Wayland, wlroots)

```python
import subprocess
import shutil

def type_via_wtype(text: str, delay_ms: int = 0) -> bool:
    """Type text using wtype (wlroots Wayland compositors only).

    Returns True on success, False if wtype unavailable or failed.
    """
    if not shutil.which("wtype"):
        return False
    try:
        cmd = ["wtype"]
        if delay_ms > 0:
            cmd.extend(["-d", str(delay_ms)])
        cmd.extend(["--", text])
        subprocess.run(cmd, check=True, timeout=10)
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False
```

### Example 2: Clipboard Fallback (Wayland)

```python
import subprocess
import shutil
import time

def type_via_clipboard_wayland(text: str, restore_delay_ms: int = 300) -> bool:
    """Type text via clipboard paste on Wayland.

    Saves clipboard, copies text, pastes via Ctrl+V, restores clipboard.
    Returns True on success.
    """
    if not shutil.which("wl-copy") or not shutil.which("wl-paste"):
        return False
    if not shutil.which("ydotool"):
        return False

    # Save current clipboard
    try:
        old_clipboard = subprocess.run(
            ["wl-paste", "--no-newline"],
            capture_output=True, timeout=2
        ).stdout
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        old_clipboard = b""

    try:
        # Copy text to clipboard
        subprocess.run(
            ["wl-copy", "--", text],
            check=True, timeout=2
        )

        # Simulate Ctrl+V via ydotool
        # Key codes: 29=Left Ctrl, 47=V
        subprocess.run(
            ["ydotool", "key", "29:1", "47:1", "47:0", "29:0"],
            check=True, timeout=5
        )

        # Wait for app to process paste
        time.sleep(restore_delay_ms / 1000.0)

        # Restore original clipboard
        if old_clipboard:
            subprocess.run(
                ["wl-copy", "--"],
                input=old_clipboard, timeout=2
            )
        else:
            subprocess.run(["wl-copy", "--clear"], timeout=2)

        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False
```

### Example 3: Clipboard Fallback (X11)

```python
import subprocess
import shutil
import time

def type_via_clipboard_x11(text: str, restore_delay_ms: int = 300) -> bool:
    """Type text via clipboard paste on X11.

    Saves clipboard, copies text, pastes via Ctrl+V, restores clipboard.
    """
    if not shutil.which("xclip") or not shutil.which("xdotool"):
        return False

    # Save current clipboard
    try:
        old_clipboard = subprocess.run(
            ["xclip", "-selection", "clipboard", "-o"],
            capture_output=True, timeout=2
        ).stdout
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        old_clipboard = b""

    try:
        # Copy text to clipboard
        subprocess.run(
            ["xclip", "-selection", "clipboard"],
            input=text.encode("utf-8"),
            check=True, timeout=2
        )

        # Simulate Ctrl+V
        subprocess.run(
            ["xdotool", "key", "--clearmodifiers", "ctrl+v"],
            check=True, timeout=5
        )

        # Wait for app to process paste
        time.sleep(restore_delay_ms / 1000.0)

        # Restore original clipboard
        if old_clipboard:
            subprocess.run(
                ["xclip", "-selection", "clipboard"],
                input=old_clipboard, timeout=2
            )

        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False
```

### Example 4: ASCII Detection for Path Selection

```python
def is_ascii_only(text: str) -> bool:
    """Check if text contains only ASCII characters."""
    try:
        text.encode("ascii")
        return True
    except UnicodeEncodeError:
        return False
```

### Example 5: Compositor Detection

```python
import os
import shutil
import subprocess

def detect_compositor() -> str:
    """Detect the running Wayland compositor.

    Returns one of: 'hyprland', 'sway', 'gnome', 'kde', 'wlroots-other', 'unknown'
    """
    # Check environment variables (fast path)
    if os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"):
        return "hyprland"
    if os.environ.get("SWAYSOCK"):
        return "sway"

    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
    if "hyprland" in desktop:
        return "hyprland"
    if "sway" in desktop:
        return "sway"
    if "gnome" in desktop:
        return "gnome"
    if "kde" in desktop or "plasma" in desktop:
        return "kde"

    # Fallback: check running processes
    for compositor, name in [
        ("hyprland", "hyprland"),
        ("sway", "sway"),
        ("gnome", "gnome-shell"),
        ("kde", "kwin_wayland"),
    ]:
        try:
            result = subprocess.run(
                ["pgrep", "-x", name],
                capture_output=True, timeout=2
            )
            if result.returncode == 0:
                return compositor
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    return "unknown"


def is_wlroots_compositor(compositor: str) -> bool:
    """Check if compositor supports zwp_virtual_keyboard_v1 (wtype works)."""
    return compositor in ("hyprland", "sway", "wlroots-other")
```

### Example 6: Spacing State Machine

```python
class SpacingTracker:
    """Tracks spacing state between consecutive dictations."""

    def __init__(self):
        self._has_prior_text = False

    def prepare_text(self, text: str) -> str:
        """Prepend space if needed for consecutive dictation.

        Args:
            text: Raw transcription text.

        Returns:
            Text with leading space if following a previous dictation.
        """
        if not text or not text.strip():
            return text

        result = text
        if self._has_prior_text and not text[0].isspace():
            result = " " + text

        # Update state: text that ends with newline resets spacing
        stripped = text.rstrip()
        if stripped and stripped[-1] in ("\n", "\r"):
            self._has_prior_text = False
        else:
            self._has_prior_text = True

        return result

    def reset(self):
        """Reset spacing state (e.g., on mode change or error)."""
        self._has_prior_text = False
```

### Example 7: FallbackInjector Skeleton

```python
import logging
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)


class InjectorBackend(ABC):
    """Abstract base class for text injection backends."""

    @abstractmethod
    def name(self) -> str:
        """Human-readable backend name."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this backend can be used in the current environment."""
        ...

    @abstractmethod
    def type_text(self, text: str, delay_ms: int = 0) -> None:
        """Inject text into the active window.

        Raises RuntimeError on failure.
        """
        ...

    def supports_unicode(self) -> bool:
        """Whether this backend handles non-ASCII characters."""
        return False


class FallbackInjector:
    """Tries multiple injection backends in order."""

    def __init__(self, backends: list[InjectorBackend]):
        self._backends = [b for b in backends if b.is_available()]
        if not self._backends:
            raise RuntimeError("No text injection backends available")
        logger.info(
            f"Available backends: {[b.name() for b in self._backends]}"
        )

    def type_text(self, text: str, delay_ms: int = 0) -> None:
        """Inject text using the first working backend.

        For Unicode text, prefers backends that support Unicode.
        Falls back through the chain on failure.
        """
        needs_unicode = not text.isascii()
        errors = []

        # If Unicode needed, try Unicode-capable backends first
        if needs_unicode:
            for backend in self._backends:
                if backend.supports_unicode():
                    try:
                        backend.type_text(text, delay_ms)
                        return
                    except RuntimeError as e:
                        errors.append(f"{backend.name()}: {e}")

        # Try all backends in order
        for backend in self._backends:
            try:
                backend.type_text(text, delay_ms)
                return
            except RuntimeError as e:
                errors.append(f"{backend.name()}: {e}")

        raise RuntimeError(
            f"All injection backends failed: {'; '.join(errors)}"
        )
```

---

## Key Delay Recommendations

| Backend | Default (ms) | Minimum Safe (ms) | Notes |
|---------|-------------|-------------------|-------|
| ydotool | 12 | 3 | <3ms causes character swapping; 12ms is conservative safe default |
| xdotool | 12 | 12 | Firefox needs 47+ for Unicode; use clipboard fallback instead |
| wtype | 0 | 0 | No delay needed; generates keymap, not individual keystrokes |
| Clipboard paste | N/A | N/A | Single paste operation, no per-character delay |

---

## Wayland Compositor Protocol Support Matrix

| Compositor | zwp_virtual_keyboard_v1 (wtype) | uinput (ydotool) | Notes |
|------------|--------------------------------|-------------------|-------|
| Hyprland | YES | YES | wlroots-based, both work |
| Sway | YES | YES | wlroots-based, both work |
| GNOME (Mutter) | NO | YES | Must use ydotool or clipboard |
| KDE (KWin) | NO | YES | Must use ydotool or clipboard |
| river | YES | YES | wlroots-based |
| X11 (any) | N/A | YES | Use xdotool instead |

---

## Decisions for Phase 5

### D1: Implement multi-backend fallback injector
Replace the current single-backend approach with a FallbackInjector that tries backends in order. Backends: WtypeBackend > ClipboardBackend > YdotoolBackend (Wayland) or XdotoolBackend > ClipboardX11Backend (X11).

### D2: Use wtype as primary backend on wlroots compositors
wtype provides full Unicode support with zero daemon overhead. It is available as an Arch package (`wtype`). On wlroots compositors (Hyprland, Sway), it should be tried first.

### D3: Use clipboard fallback for Unicode on all compositors
When text contains non-ASCII characters and wtype is not available (GNOME, KDE, or wtype not installed), use the clipboard save/copy/paste/restore pattern.

### D4: Keep ydotool/xdotool for ASCII-only fast path
For the common case (English dictation producing ASCII text), ydotool and xdotool remain the fastest path because they don't clobber the clipboard.

### D5: Prepend space for consecutive dictations
Track state: after injecting text, set a flag. Before the next injection, prepend a space if the flag is set. Reset flag on newlines or explicit reset.

### D6: Add compositor detection
Extend `detector.py` to identify the specific compositor, not just "wayland" vs "x11". This drives wtype vs clipboard backend selection.

### D7: wl-clipboard and xclip as optional dependencies
Clipboard fallback requires `wl-clipboard` (Wayland) or `xclip` (X11). These are optional -- if not present, the clipboard path is skipped and only direct typing is available (ASCII only for ydotool).

### D8: wtype as optional dependency
wtype is the ideal backend but should be optional. If not installed, fall through to clipboard or ydotool.

---

## Open Questions (Low Risk)

1. **Should clipboard fallback be configurable (enable/disable)?** -- Probably yes, some users may not want their clipboard touched. Default: enabled.

2. **What clipboard restore delay is optimal?** -- 300ms seems safe based on OpenWhispr experience. Make it configurable.

3. **Should we support dotool in addition to ydotool?** -- Not in Phase 5. dotool is simpler but less common. Can be added later without architecture changes since the fallback chain is extensible.

4. **Should we support eitype for GNOME/KDE?** -- Not in Phase 5. libei/eitype is newer and less widely available. The clipboard fallback covers GNOME/KDE adequately. Can be added as a backend later.

---

## RESEARCH COMPLETE

**Key findings:**

1. **ydotool fundamentally cannot handle Unicode** -- it simulates physical keyboard scancodes, which have no concept of Unicode code points. This is unfixable by design. (Confirmed via maintainer statement and 3 GitHub issues.)

2. **wtype is the correct primary backend for wlroots compositors** (Hyprland, Sway) -- it generates a keymap on-the-fly for arbitrary Unicode. Available as `wtype` on Arch.

3. **wtype does NOT work on GNOME or KDE** -- they don't implement `zwp_virtual_keyboard_v1`. Must use clipboard fallback on these compositors.

4. **Clipboard save/copy/paste/restore is the universal Unicode fallback** -- works on all compositors, all apps, all characters. Has clipboard-clobber tradeoff but restore mitigates it.

5. **ydotool DOES work in native Wayland apps** (Firefox, Chrome) -- because it operates at the kernel /dev/uinput level, bypassing Wayland's security model. xdotool does NOT work in native Wayland apps.

6. **ASCII fast path should use ydotool/xdotool directly** -- avoids clipboard overhead for the common English dictation case.

7. **Spacing: prepend space before next dictation, track state** -- simple flag-based state machine, reset on newlines.

8. **Key delay: 12ms default for ydotool is safe** -- minimum 3ms, below that causes character swapping/dropping.
