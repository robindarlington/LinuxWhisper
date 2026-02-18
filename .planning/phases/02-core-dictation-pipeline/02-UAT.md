---
status: complete
phase: 02-core-dictation-pipeline
source: [02-01-SUMMARY.md, 02-02-SUMMARY.md, 02-03-SUMMARY.md]
started: 2026-02-15T12:00:00Z
updated: 2026-02-18T10:37:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Daemon Starts with Pipeline
expected: Run `linuxwhisper start`. Daemon initializes, loads Whisper model, and logs show pipeline ready. No errors on startup.
result: issue
reported: "fail it says failed to start daemon — ydotoold not running due to /dev/uinput permissions"
severity: blocker
resolution: Fixed by chgrp input + chmod 0660 on /dev/uinput, then restarting ydotool. System config issue, not code bug. Daemon starts successfully after fix.

### 2. Hold-to-Talk Dictation
expected: Open a text editor. Hold hotkey, speak, release. Transcribed text appears in the text editor within a few seconds.
result: pass
notes: Tested with HOME key (PAUSE key doesn't support hold). "Hello, is this working?" transcribed accurately in ~2s. Longer phrase also worked.

### 3. Display Server Detection
expected: Check daemon logs. Session type detection shows "wayland" or "x11" matching your current session. Correct injector (ydotool/xdotool) is selected.
result: pass
notes: Logs show "Detected session type: wayland (via XDG_SESSION_TYPE)" and "Created WaylandInjector"

### 4. Quick Tap Ignored
expected: Quickly tap and release hotkey (less than 0.1 seconds). No text should appear in the active window. Daemon logs may show "recording too short".
result: pass
notes: PAUSE key tap (instant press+release) correctly logged "Recording too short, discarding" and returned to IDLE

### 5. Error Recovery
expected: If any dictation attempt fails (e.g., empty transcription), the pipeline returns to IDLE and the next dictation attempt works normally without restarting the daemon.
result: pass
notes: After short-tap discard (test 4), subsequent hold-to-talk worked without restart. Pipeline correctly returned to IDLE.

### 6. Clean Daemon Shutdown
expected: Daemon shuts down cleanly with no errors or orphaned processes. Pipeline and model are unloaded.
result: pass
notes: Process terminated cleanly, no orphaned processes found via pgrep.

## Summary

total: 6
passed: 5
issues: 1
pending: 0
skipped: 0

## Gaps

- truth: "Daemon starts without manual system configuration"
  status: deferred
  reason: "User reported: ydotoold not running due to /dev/uinput permissions. Required manual chgrp/chmod."
  severity: major
  test: 1
  root_cause: "udev rule exists but doesn't apply on boot for /dev/uinput. Manual permission fix needed."
  artifacts:
    - path: "/etc/udev/rules.d/80-uinput.rules"
      issue: "Rule exists but doesn't take effect automatically"
  missing:
    - "Post-install automation or documentation for uinput permissions"
  deferred_to: "Phase 7 (System Integration) / Phase 8 (Distribution)"
