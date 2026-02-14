# Pitfalls Research

**Domain:** Linux voice dictation
**Researched:** 2026-02-15
**Confidence:** MEDIUM

## Critical Pitfalls

### Pitfall 1: Wayland Input Injection Architecture Mismatch

**What goes wrong:**
Voice dictation tools fail silently on Wayland compositors because they rely on X11-era input injection methods (xdotool). On GNOME Wayland, wtype doesn't work because the virtual-keyboard-unstable-v1 protocol isn't implemented. Text appears to be typed but never reaches native Wayland applications like browsers or GTK4 apps - only XWayland windows receive input.

**Why it happens:**
Developers assume wtype is a drop-in replacement for xdotool on Wayland, but Wayland's security model deliberately prevents input injection across application boundaries. Each compositor has discretion over which protocols to implement. GNOME blocks virtual-keyboard-unstable-v1, KDE Plasma doesn't implement zwp_virtual_keyboard_v1, and compositors vary wildly in what they support.

**How to avoid:**
- Phase 1: Test input injection on actual Wayland (not XWayland) applications during initial development
- Use ydotool via /dev/uinput as the Wayland path, not wtype - it bypasses Wayland restrictions at kernel level
- Maintain X11 path (xdotool) separately - don't attempt unified abstraction
- Document per-compositor limitations upfront (GNOME vs KDE vs Hyprland have different restrictions)

**Warning signs:**
- Works in terminal but not in browser
- Works on X11 session but fails on Wayland session
- wtype returns success but no text appears
- Text appears only in XWayland windows (check with `xprop` - no response means native Wayland)

**Phase to address:**
Phase 1 (Core Hotkey + Text Injection) - architectural decision must be correct from day one. Refactoring later requires complete rewrite of input layer.

---

### Pitfall 2: Whisper Model Cold Start Latency

**What goes wrong:**
Users press hotkey, speak, release hotkey, and wait 5-10 seconds before text appears. First-time users think the application is broken. The CLI approach loads Whisper from disk on every invocation, including SHA256 hash checking and CUDA runtime initialization, making sub-second response impossible.

**Why it happens:**
OpenAI's Whisper is designed for batch processing, not real-time dictation. Developers treat Whisper as a CLI tool rather than a long-running service, reloading the model on every transcription request. The model (especially larger ones) takes gigabytes of RAM and several seconds to load into memory.

**How to avoid:**
- Keep Whisper model loaded in memory as a background service/daemon
- Use faster-whisper (CTranslate2-based) instead of vanilla OpenAI Whisper - 4x faster with same accuracy
- Apply INT8 quantization on CPU - reduces memory 50% and inference time to 1/4 with minimal accuracy loss
- Phase 1: Implement daemon architecture with model pre-loaded, not subprocess per request
- Phase 2: Add lazy loading option for users who prefer memory savings over speed

**Warning signs:**
- Loading message appears every time user dictates
- First word takes >3 seconds to appear after releasing hotkey
- Memory usage spikes during transcription then drops (model unloading)
- Users report "is it working?" on first use

**Phase to address:**
Phase 1 (Whisper Integration) - daemon architecture required from start. Subprocess approach creates unfixable UX problem.

---

### Pitfall 3: evdev Permissions and Exclusive Grab Conflicts

**What goes wrong:**
Hotkey detection requires root permissions or udev rules, but even with correct permissions, grabbing /dev/input/eventX exclusively breaks existing tools. Users can't use hotkeys in their compositor, the keyboard stops responding normally, or the wrong event device is grabbed (some keyboards expose multiple /dev/input nodes but only one provides actual keystrokes).

**Why it happens:**
evdev requires reading /dev/input/event* devices which are root-only by default. Modern systems use logind/ACLs with uaccess tags for dynamic permissions, but exclusive grab (required to prevent hotkey from typing in active window) conflicts with compositor hotkey handlers. Developers grab first available event device without verifying it's the keyboard they want.

**How to avoid:**
- Use udev rules to add user to input group (avoid asking for root at runtime)
- Document uaccess/logind approach for systemd-based distros (Arch default)
- Implement non-exclusive grab first, test for conflicts, only grab exclusively if needed
- Validate event device provides KEY events before grabbing (check capabilities via evdev API)
- Provide device selection if multiple keyboards detected
- Use InputDevice.grab_context() context manager to ensure ungrab on crash
- Sync device state on ungrab to prevent phantom modifier key states

**Warning signs:**
- Permission denied on /dev/input/event*
- Keyboard stops working when app runs
- Compositor hotkeys stop working
- Keys appear "stuck" after ungrabbing
- Hotkey works on some keyboards but not others (USB vs built-in)

**Phase to address:**
Phase 1 (Core Hotkey) - must be robust before any other features. Bad input handling breaks entire system usability.

---

### Pitfall 4: Unicode and Special Character Text Injection Failures

**What goes wrong:**
Dictated text containing emoji, accented characters (é, ñ, ç), or non-Latin scripts (中文, العربية) fails to appear, shows as "?" or garbage characters, or causes xdotool/wtype to crash with "Invalid multi-byte sequence" errors. Worse: xdotool assumes US keyboard layout, so punctuation like "/" types as "q" on non-US layouts.

**Why it happens:**
xdotool was designed for ASCII and doesn't handle UTF-8 correctly. It simulates keypresses assuming a US keyboard layout, so special characters that aren't on US keyboards fail. wtype on Wayland has better Unicode support but still struggles with complex grapheme clusters and RTL text. Developers test with English ASCII text and don't discover the problem until users report it.

**How to avoid:**
- Phase 1: Test with non-ASCII test suite (emoji, accented chars, CJK, Arabic, Hebrew)
- Use wtype on Wayland (better Unicode), but fallback to clipboard paste for problematic characters
- On X11, use XTestFakeInput with Unicode-to-keysym mapping, not xdotool CLI
- Query active keyboard layout before injection (Hyprland: hyprctl getoption input:kb_layout)
- Document keyboard layout limitations upfront
- Implement clipboard paste fallback for characters that fail direct injection

**Warning signs:**
- Works with "hello world" but fails with "café"
- Emoji dictation shows boxes or crashes
- French/German users report missing accented characters
- "/" becomes "q" or other wrong character
- RTL languages (Arabic, Hebrew) appear reversed or broken

**Phase to address:**
Phase 1 (Text Injection) - discovered too late requires rewriting text injection layer. Test non-ASCII early.

---

### Pitfall 5: Audio Capture Reliability Across PipeWire/PulseAudio

**What goes wrong:**
Audio capture works on developer's machine (PulseAudio) but fails for users on PipeWire or vice versa. Microphone device enumeration returns empty list, recording captures silence, or device names change after reboot. Systemd user services fail to access audio because XDG_RUNTIME_DIR isn't set or session isn't properly recognized.

**Why it happens:**
Linux audio is fragmented: PulseAudio, PipeWire-as-PulseAudio, pure PipeWire, ALSA. PyAudio only recognizes sub-device 0 and may miss the actual microphone. sounddevice requires PortAudio backend configuration. PipeWire uses Polkit-like permissions asking Wayland/Flatpak for access. Systemd user services inherit minimal environment without audio session variables.

**How to avoid:**
- Use sounddevice over PyAudio (better Linux compatibility, active maintenance)
- Test on both PipeWire and PulseAudio systems (Arch defaults to PipeWire in 2026)
- Set CHUNK to integer fraction of RATE for PyAudio stability
- For systemd services: require XDG_RUNTIME_DIR in environment, verify session context
- Implement device selection UI, don't assume default device is correct
- Query PipeWire/PulseAudio directly via their APIs, don't rely solely on Python libraries

**Warning signs:**
- Works when launched from terminal, fails as systemd service
- Device list empty on PipeWire systems
- Records only silence despite mic working in other apps
- "Connection refused" errors with pipewire-pulse
- Different behavior on Arch vs Ubuntu (PipeWire vs PulseAudio)

**Phase to address:**
Phase 1 (Audio Capture) - audio is prerequisite for everything. Fragility here breaks core functionality.

---

### Pitfall 6: AUR PKGBUILD Missing Transitive Dependencies

**What goes wrong:**
Package installs successfully on developer's system (already has dependencies from other packages) but fails on clean Arch install with "module not found" or missing libraries. Common culprits: forgot python-sounddevice in depends, listed evdev in makedepends instead of depends, assumed systemd without declaring dependency.

**Why it happens:**
Developers test on their own systems which already have transitive dependencies installed. pacman only installs direct dependencies listed in PKGBUILD. The most common packaging error is missing dependencies. Projects change from Vosk to Whisper but PKGBUILD still lists python-vosk.

**How to avoid:**
- List all direct first-level dependencies even if they're transitive (if package depends on A and B, and A depends on B, list both)
- Use namcap to analyze PKGBUILD and built package - it catches missing dependencies
- Test in clean chroot (systemd-nspawn container) not just local system
- Distinguish depends (runtime), makedepends (build only), optdepends (optional features)
- Use ldd/readelf on binaries to verify shared library dependencies
- Version pin critical dependencies if API breaks between versions (depends=('faster-whisper>=1.0.0' 'faster-whisper<2.0.0'))

**Warning signs:**
- Works on dev system, "No module named X" on fresh install
- namcap warnings about missing dependencies
- Users report missing libraries in AUR comments
- Build succeeds but runtime fails
- Different behavior between pacman -S install and makepkg local build

**Phase to address:**
Phase 4 (AUR Packaging) - but validate dependency list in Phase 1-3. Fixing post-release annoys early adopters.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Subprocess Whisper calls instead of daemon | Simple implementation, no process management | 5-10 second latency per request, terrible UX | Never - users will abandon |
| xdotool CLI instead of native Xlib/evdev | Easy 2-line implementation | Unicode breaks, keyboard layout issues, no Wayland | Never - basic functionality requirement |
| Hard-code default audio device | Skip device selection UI | Breaks for users with multiple mics, USB headsets | Only in Phase 1 MVP with documented limitation |
| Root permissions for evdev | Skip udev rule installation | Security risk, users reject root requirement | Never - Arch users expect proper packaging |
| Global pip install Whisper | Avoid venv complexity | Conflicts with user's Python environment | Never - AUR must use system Python properly |
| Assume US keyboard layout | Works for developer | Breaks for 90% of world, wrong punctuation | Never - international users are not edge case |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Hyprland hotkeys | Using xdotool or assuming GNOME keybind API | Use hyprctl for config queries, evdev for capture |
| Wayland text injection | Assuming wtype works everywhere | ydotool via uinput for GNOME/KDE, wtype for compositors with virtual-keyboard protocol |
| PipeWire audio | Using PyAudio's PulseAudio backend | Use sounddevice with explicit backend detection, test both PipeWire and PulseAudio |
| systemd user services | Running as system service | User service in ~/.config/systemd/user/ with session environment |
| faster-whisper | Using default model path | Specify explicit model cache dir to avoid permission issues |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Loading Whisper model per request | 5-10 sec delay on every dictation | Keep model in memory as daemon | Immediately - first use |
| Using large Whisper model on CPU | 30+ second transcription for 5 sec audio | Start with base model + INT8 quantization | >5 second audio clips |
| Synchronous audio recording blocking event loop | UI freezes during recording | Async audio capture in separate thread | Any real usage |
| No audio chunk buffering | Missed speech at start/end | Buffer 0.5s before/after hotkey events | Fast speakers, short phrases |
| Keeping keyboard grabbed during transcription | Keyboard unusable for 5+ seconds | Ungrab immediately after hotkey release, only grab for hotkey detection | User tries to type during transcription |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Requesting root for evdev access | Users reject app, security red flag | Use udev rules + input group, never ask for root at runtime |
| Storing transcribed text in /tmp with predictable names | Local users can read dictated text (passwords, private data) | Use secure temp files with 0600 permissions, XDG_RUNTIME_DIR |
| Exclusive keyboard grab without timeout | Malicious app can lock keyboard | Implement grab timeout, ungrab on any error, use grab_context() |
| Loading Whisper model from user-provided path | Model file can be replaced with malicious code | Validate model hashes, use hardcoded cache dir, warn on custom models |
| Running systemd service as root for audio+evdev | Full system compromise if exploited | User service with udev rules, logind ACLs |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No feedback during Whisper processing | Users think app crashed, press hotkey repeatedly | Show notification/indicator during transcription |
| Capitalizing first letter of sentence mid-paragraph | Breaks text flow, requires manual editing | Only capitalize after .!? followed by space |
| No space between consecutive dictations | "hello" "world" becomes "helloworld" | Always append space after transcription (except before punctuation) |
| Dictated punctuation appears as words | "hello comma world" not "hello, world" | Command mode for punctuation (say "comma" → insert ",") |
| Hotkey conflicts with existing compositor bindings | User's workflow broken, has to reconfigure | Auto-detect common hotkey conflicts, suggest alternatives |
| Failing silently on Wayland | Users think it's broken, leave negative reviews | Detect compositor, warn if input injection will fail, offer workarounds |

## "Looks Done But Isn't" Checklist

- [ ] **Text Injection:** Often missing Unicode/emoji support - verify with café, 中文, 🎉
- [ ] **Wayland Support:** Often missing native Wayland app testing - verify in Firefox (native Wayland), not terminal (XWayland)
- [ ] **Hotkey Detection:** Often missing multi-keyboard support - verify with USB keyboard plugged in
- [ ] **Audio Capture:** Often missing PipeWire testing - verify on Arch (PipeWire default), not Ubuntu (PulseAudio)
- [ ] **Keyboard Layouts:** Often missing non-US layout testing - verify with French/German/Dvorak layout active
- [ ] **Systemd Service:** Often missing environment variables - verify XDG_RUNTIME_DIR, DBUS_SESSION_BUS_ADDRESS in service
- [ ] **Model Loading:** Often missing cold start optimization - verify first-run latency, not just subsequent runs
- [ ] **AUR Package:** Often missing transitive dependencies - verify in clean chroot, not dev environment
- [ ] **Error Messages:** Often missing helpful diagnostics - verify fails gracefully with clear message, not Python traceback
- [ ] **Sentence Spacing:** Often missing space between dictations - verify consecutive hotkey presses produce separated text

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Subprocess Whisper (not daemon) | HIGH | Rewrite entire Whisper integration, add daemon process management, IPC between hotkey and transcription |
| xdotool-only (no ydotool) | MEDIUM | Add ydotool code path, detect compositor type, abstract text injection interface |
| PyAudio hard-coded | MEDIUM | Switch to sounddevice, rewrite audio capture layer, test across distros |
| Missing udev rules | LOW | Add udev rules to package, document manual installation in README |
| US layout assumption | MEDIUM | Query active keyboard layout, map characters to layout-specific keysyms |
| PulseAudio-only | MEDIUM | Add PipeWire detection, abstract audio backend, test on Arch |
| Root requirement | HIGH | Requires udev rules, package restructuring, user education on proper install |
| No Unicode support | HIGH | Rewrite text injection to use keysym mapping or clipboard fallback |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Wayland input injection fails | Phase 1 | Test in Firefox (native Wayland), not just terminal |
| Whisper cold start latency | Phase 1 | First-run transcription <2sec from hotkey release |
| evdev permission errors | Phase 1 | Install on fresh Arch without root, hotkey works |
| Unicode text injection broken | Phase 1 | Dictate "café 🎉 中文" and verify exact output |
| Audio capture PipeWire fails | Phase 1 | Test on Arch (PipeWire) and Ubuntu (PulseAudio) |
| Non-US keyboard layout issues | Phase 2 | Test with French/German layout active, "/" types correctly |
| systemd service environment | Phase 3 | Service starts on boot, audio works, no manual env vars |
| AUR missing dependencies | Phase 4 | Clean chroot install succeeds, runtime works without manual deps |
| No transcription progress feedback | Phase 2 | User sees indicator during 5sec+ transcriptions |
| Hotkey conflicts with compositor | Phase 2 | Detect conflicts with Hyprland/GNOME common bindings |

## Sources

### Wayland Input Injection
- [Wayland vs X11: 2026 Comparison - Rost Glukhov](https://www.glukhov.org/post/2026/01/wayland-vs-x11-comparison/)
- [X11 to Wayland: Why Modern Linux Developers Are Making the Switch - Exam-Labs](https://www.exam-labs.com/blog/x11-to-wayland-why-modern-linux-developers-are-making-the-switch)
- [Sending Keyboard Strokes to Wayland Linux Windows](https://medium.com/@python-javascript-php-html-css/sending-keyboard-strokes-to-wayland-linux-windows-solutions-and-challenges-9319cf424d06)
- [wtype GitHub - xdotool type for wayland](https://github.com/atx/wtype)

### Whisper Performance
- [speed up whisper? · openai/whisper · Discussion #716](https://github.com/openai/whisper/discussions/716)
- [CLI initialization takes 8 seconds · openai/whisper · Discussion #669](https://github.com/openai/whisper/discussions/669)
- [faster-whisper GitHub - SYSTRAN](https://github.com/SYSTRAN/faster-whisper)
- [Faster Whisper Transcription - Cerebrium](https://www.cerebrium.ai/articles/faster-whisper-transcription-how-to-maximize-performance-for-real-time-audio-to-text)

### evdev Permissions
- [Proper way to allow access to /dev/input/event* - Arch Forums](https://bbs.archlinux.org/viewtopic.php?id=273094)
- [udev - ArchWiki](https://wiki.archlinux.org/title/Udev)
- [Python evdev Tutorial](https://python-evdev.readthedocs.io/en/latest/tutorial.html)
- [exclusive-keyboard-access GitHub](https://github.com/whizse/exclusive-keyboard-access)

### Unicode Text Injection
- [Using 'type' with unicode? · xdotool Issue #154](https://github.com/jordansissel/xdotool/issues/154)
- [xdotool to generate special characters - Linux Mint Forums](https://forums.linuxmint.com/viewtopic.php?t=442850)
- [Entering unicode characters with xdotool · kitty Issue #1456](https://github.com/kovidgoyal/kitty/issues/1456)

### Audio Capture
- [PipeWire - ArchWiki](https://wiki.archlinux.org/title/PipeWire)
- [Playing and Recording Sound in Python - Real Python](https://realpython.com/playing-and-recording-sound-python/)
- [python-sounddevice GitHub - spatialaudio](https://github.com/spatialaudio/python-rtmixer)

### AUR Packaging
- [PKGBUILD - ArchWiki](https://wiki.archlinux.org/title/PKGBUILD)
- [Creating packages - ArchWiki](https://wiki.archlinux.org/title/Creating_packages)
- [Arch package guidelines - ArchWiki](https://wiki.archlinux.org/title/Arch_package_guidelines)

### nerd-dictation Experience Reports
- [nerd-dictation GitHub Issues](https://github.com/ideasman42/nerd-dictation/issues)
- [Nerd Dictation - Linux Mint Forums](https://forums.linuxmint.com/viewtopic.php?t=452621)
- [Continuous dictation with Whisper AI · openai/whisper Discussion #1282](https://github.com/openai/whisper/discussions/1282)

### Systemd Services
- [Auto-recovery of crashed services with systemd - Singlebrook](https://singlebrook.com/2017/10/23/auto-restart-crashed-service-systemd/)
- [Keep Your Python HTTP Server Running - systemd](https://ponnala.medium.com/never-let-your-python-http-server-die-step-by-step-guide-to-auto-start-on-boot-and-crash-recovery-1f7b0f94401e)

---
*Pitfalls research for: LinuxWhisper - Linux voice dictation*
*Researched: 2026-02-15*
