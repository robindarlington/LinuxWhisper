---
status: complete
phase: 03-enhanced-input-modes
source: [03-01-SUMMARY.md, 03-02-SUMMARY.md]
started: 2026-02-18T13:15:00Z
updated: 2026-02-18T15:07:00Z
---

## Tests

### 1. Hold mode with HOME key default
expected: Start daemon with default config. Hold HOME key, speak, release. Text appears in active window.
result: pass

### 2. Toggle mode: press-to-start, press-to-stop
expected: Set mode="toggle" in config, reload daemon. Press HOME once — recording starts. Press HOME again — recording stops and text appears in active window.
result: pass

### 3. Toggle timeout transcribes captured audio
expected: In toggle mode, set toggle_timeout=10 in config (short for testing). Press HOME to start recording, speak, then wait 10 seconds without pressing again. Text appears after timeout fires (not discarded).
result: pass

### 4. Escape cancels toggle recording
expected: In toggle mode, press HOME to start recording, speak, then press Escape. Recording stops but NO text appears (audio discarded). Daemon returns to idle.
result: pass

### 5. Friendly hotkey alias in config
expected: Set hotkey="end" in config.toml (lowercase friendly alias), restart daemon. Daemon starts successfully using the aliased key.
result: pass

### 6. Config reload via SIGHUP
expected: While daemon is running and idle, edit config.toml (e.g. change mode from "hold" to "toggle"), then send SIGHUP. Logs show "Configuration reloaded successfully" and new mode applies without restart.
result: pass

### 7. Invalid config rejected at startup
expected: Set hotkey="NONEXISTENT_KEY" in config.toml, try to start daemon. Daemon refuses to start with clear error message listing available keys.
result: pass
notes: Error message correctly lists all available friendly aliases and F-keys.

### 8. Compositor conflict warnings in logs
expected: Start daemon with hotkey=HOME. Logs show warning about compositor binding conflicts for HOME key.
result: pass
notes: GNOME compositor conflicts detected and logged as warnings. Daemon starts regardless (non-blocking).

## Summary

total: 8
passed: 8
issues: 0
pending: 0
skipped: 0

## Gaps

### GAP-01: Default hotkey is NONEXISTENT_KEY in defaults.py
severity: bug
file: src/linuxwhisper/config/defaults.py:7
description: Default hotkey is "NONEXISTENT_KEY" instead of "HOME". Anyone starting without a config file gets an immediate startup failure. Plan 03-02 specified HOME as the default.
