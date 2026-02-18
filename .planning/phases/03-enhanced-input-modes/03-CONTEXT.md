# Phase 3 Context: Enhanced Input Modes

## Toggle Mode Safety

**Decisions:**
- Toggle mode has a **configurable max recording duration** with a **2-minute default**
- Config key: `toggle_timeout` under a `[dictation]` or top-level section
- Timeout is a **safety net**, not the primary stop mechanism — users press the hotkey to stop when done
- When timeout fires: **silently transcribe whatever was captured** (no beep, no notification — text appearing is the cue)
- After timeout: system returns to **idle** (requires new toggle press to start again, no continuous listening)
- Timeout applies to **toggle mode only** — hold-to-talk has the key release as its natural stop signal
- **Escape key cancels** a toggle recording without transcribing — discards the audio

**Rationale:** Hold-to-talk has natural safety (release = stop). Toggle mode needs a safety net for forgotten toggles. 2-minute timeout is long enough for any dictation burst while catching "walked away" scenarios.

## Hotkey Configuration

**Decisions:**
- **Single key only** — no modifier combos (Ctrl+Shift+R, etc.)
- Default hotkey: **HOME** (changed from F13 — most users don't have F13)
- Invalid key name in config: **refuse to start** with a clear error listing valid keys
- **Friendly aliases** for common keys: `scroll_lock` -> `KEY_SCROLLLOCK`, `pause` -> `KEY_PAUSE`, `home` -> `KEY_HOME`, etc.
- Key resolution is **case-insensitive** (already implemented in Phase 2)
- Both `KEY_HOME` and `HOME` formats accepted (already implemented)

**Rationale:** Single keys are simpler to implement with evdev grab, less likely to conflict with compositor bindings (since uncommon keys like HOME/Scroll Lock are rarely bound), and cover the primary use case. Modifier combos add significant evdev state-tracking complexity for marginal benefit.

## Compositor Conflict Detection

**Decisions:**
- **Query compositor runtime** for active bindings (most accurate approach)
  - Hyprland: `hyprctl binds`
  - Sway: `swaymsg -t get_binding_modes` / config parsing
  - GNOME: `gsettings` for keybinding schemas
  - KDE: `kreadconfig5` or dbus
  - X11: `xmodmap` / `xdotool`
- Cover **all major compositors**: Hyprland, Sway, GNOME Wayland, KDE Wayland, and X11
- On conflict: **warn with suggestion** — log a warning naming the conflicting binding and suggest an alternative key, but still start the daemon
- Daemon starts regardless of conflicts (evdev grab takes priority anyway), but user is clearly informed

**Rationale:** Runtime querying is most accurate since users may set bindings dynamically (not just in config files). Warning without blocking is appropriate because evdev grab means LinuxWhisper captures the key first regardless — the conflict is informational, not fatal.

## Recording Feedback UX

**Decisions:**
- **No recording feedback in Phase 3** — skip interim solutions
- The real solution is a **MacWhisper-style waveform overlay**: floating bubble at top-left of the active window, white waveform animation on blue background, visible while recording, disappears on stop
- This overlay feature is deferred to a **new phase after Phase 6** (depends on audio pipeline + display server detection)
- Feedback behavior should be **the same for both hold and toggle modes**

**Rationale:** User doesn't want throwaway interim UX. The waveform overlay is the intended experience and requires GUI framework + Wayland layer-shell + real-time audio visualization — too substantial for Phase 3's scope.

## Audio & Microphone Selection

**Decisions:**
- **System default mic is sufficient** — no device selection UI or config needed beyond existing `audio.device` field
- `audio.device = None` (default) uses whatever the OS default input is — users manage their default in system settings (pavucontrol, PipeWire config)
- If a user explicitly configures a device and it's unavailable: **fall back to system default** with a log warning (don't refuse to start)
- **Audio backend (PipeWire/PulseAudio/ALSA) is handled by sounddevice/PortAudio** — no custom backend detection or replacement needed
- sounddevice already works on PipeWire (validated in Phase 2 testing) — no audio quality issues observed
- No need to log or expose which backend is active — implementation detail users don't care about

**Rationale:** sounddevice via PortAudio abstracts audio backends cleanly. Phase 2 testing confirmed it works on PipeWire without issues. Adding explicit backend management would be unnecessary complexity. *(These decisions led to Phase 4 removal — see below.)*

## Phase 4 Removal

**Decision:** Phase 4 (Audio Optimization) is **removed from the roadmap** and its useful content folded into Phase 3.

**Why:** Phase 4's success criteria were:
1. PipeWire audio capture — already works (sounddevice/PortAudio)
2. PulseAudio fallback — already works (PortAudio auto-detects)
3. 16kHz mono WAV format — done in Phase 2
4. Toggle timeout safety for toggle mode — folded into Phase 3 (above)
5. Audio quality sufficient — validated in Phase 2

All 5 criteria are either already met or folded into Phase 3. Phases 5-8 renumber to 4-7.

## Deferred Ideas

- **Waveform overlay phase** — Insert after Phase 6 as Phase 6.1 or new Phase 7. MacWhisper-style floating waveform bubble. Dependencies: display server detection (Phase 6), GUI framework selection (GTK/Qt + layer-shell).
- **Modifier key combos** — If single-key proves too limiting in practice, revisit combo support in a future phase.

---
*Created: 2026-02-18*
*Updated: 2026-02-18 — Added audio/mic decisions from Phase 4 discussion; Phase 4 folded in and removed*
*Discussed areas: Toggle safety, Hotkey config, Conflict detection, Recording feedback UX, Audio backend, Mic selection*
