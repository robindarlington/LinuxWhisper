---
phase: 01-foundation
plan: 01
subsystem: core
tags: [packaging, configuration, xdg]
dependency_graph:
  requires: []
  provides: [package-structure, config-system, xdg-paths]
  affects: [all-future-modules]
tech_stack:
  added: [setuptools, click, tomli-w, xdg-base-dirs]
  patterns: [xdg-base-dirs, toml-config, deep-merge]
key_files:
  created:
    - pyproject.toml
    - src/linuxwhisper/__init__.py
    - src/linuxwhisper/config/defaults.py
    - src/linuxwhisper/config/loader.py
    - src/linuxwhisper/cli/commands.py
  modified: []
decisions:
  - "Use stdlib tomllib (Python 3.11+) for reading TOML, tomli-w for writing"
  - "Create virtual environment (.venv) for development isolation"
  - "Implement deep merge for config to allow partial user overrides"
metrics:
  duration: "3 minutes"
  completed: "2026-02-14"
  tasks: 2
  commits: 3
---

# Phase 01 Plan 01: Project Structure and Config System Summary

**One-liner:** Python package structure with XDG-compliant TOML config loading and deep merge for user overrides.

## Overview

Established LinuxWhisper as an installable Python package with proper project structure, CLI entry point, and a robust configuration system that respects XDG Base Directory standards. The config system creates default config files on first run and deep-merges user overrides to preserve unset defaults.

## Tasks Completed

### Task 1: Create project structure and Python packaging
**Commit:** `51f0fbc`

Created the foundational Python package structure with:
- `pyproject.toml` defining project metadata, Python 3.11+ requirement, and dependencies
- Source layout under `src/linuxwhisper/` with subpackages: config, daemon, cli, logging
- CLI entry point using Click framework registered as `linuxwhisper` command
- Package version `0.1.0` in `__init__.py`
- Editable installation via `pip install -e .`

**Files created:**
- `/home/rob/Documents/Projects/LinuxWhisper/pyproject.toml`
- `/home/rob/Documents/Projects/LinuxWhisper/src/linuxwhisper/__init__.py`
- `/home/rob/Documents/Projects/LinuxWhisper/src/linuxwhisper/config/__init__.py`
- `/home/rob/Documents/Projects/LinuxWhisper/src/linuxwhisper/daemon/__init__.py`
- `/home/rob/Documents/Projects/LinuxWhisper/src/linuxwhisper/cli/__init__.py`
- `/home/rob/Documents/Projects/LinuxWhisper/src/linuxwhisper/cli/commands.py`
- `/home/rob/Documents/Projects/LinuxWhisper/src/linuxwhisper/logging/__init__.py`

### Task 2: Implement configuration system with XDG paths and default creation
**Commit:** `7c83c2f`

Built a complete configuration management system with:
- `DEFAULT_CONFIG` dictionary defining hotkey, mode, model, audio, and logging defaults
- `get_config_path()` returning XDG-compliant path `~/.config/linuxwhisper/config.toml`
- `load_config()` creating default config on first run, then loading and merging user config
- `merge_config()` implementing recursive deep merge for nested dictionaries
- `write_default_config()` writing defaults to TOML using tomli-w
- Exported public API from `__init__.py`: `load_config` and `get_config_path`

**Files created:**
- `/home/rob/Documents/Projects/LinuxWhisper/src/linuxwhisper/config/defaults.py`
- `/home/rob/Documents/Projects/LinuxWhisper/src/linuxwhisper/config/loader.py`

**Files modified:**
- `/home/rob/Documents/Projects/LinuxWhisper/src/linuxwhisper/config/__init__.py`

### Additional: Add .gitignore
**Commit:** `db3d4b2`

Added comprehensive `.gitignore` to exclude Python build artifacts, cache files, virtual environments, and IDE files.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Created virtual environment**
- **Found during:** Task 1 execution
- **Issue:** System Python installation did not have pip module available, blocking package installation
- **Fix:** Created `.venv` virtual environment using `python3 -m venv .venv` and activated it for all subsequent operations
- **Files modified:** Created `.venv/` directory (excluded by .gitignore)
- **Commit:** N/A (not committed, infrastructure only)

**2. [Rule 3 - Blocking] Added .gitignore file**
- **Found during:** Task 2 commit
- **Issue:** Build artifacts (`__pycache__`, `*.egg-info`) appeared as untracked files that should not be committed
- **Fix:** Created comprehensive `.gitignore` file covering Python artifacts, virtual environments, IDE files, and OS files
- **Files created:** `.gitignore`
- **Commit:** `db3d4b2`

**3. [Rule 2 - Critical functionality] Fixed pyproject.toml build backend**
- **Found during:** Task 1 implementation
- **Issue:** Plan specified `build-backend = "setuptools.backends._legacy:_Backend"` which is incorrect and deprecated
- **Fix:** Changed to `build-backend = "setuptools.build_meta"` which is the correct modern setuptools backend
- **Files modified:** `pyproject.toml`
- **Commit:** `51f0fbc` (included in Task 1)

## Verification Results

All verification criteria passed:

1. **Package installation:** `pip install -e .` succeeded without errors
2. **Import test:** `import linuxwhisper` works, `__version__` is "0.1.0"
3. **Config file creation:** First `load_config()` call creates `~/.config/linuxwhisper/config.toml` at XDG path
4. **Default values:** Config matches `DEFAULT_CONFIG` when no user overrides present
5. **User overrides:** Partial user config correctly overrides specific keys while preserving unset defaults (deep merge validated)

## Key Technical Decisions

1. **Python 3.11+ requirement**: Enables use of stdlib `tomllib` (no backport dependency needed), keeps tomli-w only for writing config files

2. **Virtual environment approach**: Created `.venv` for development isolation rather than relying on system Python packages

3. **Deep merge implementation**: Recursive merge allows users to override nested config keys (e.g., `audio.sample_rate`) without specifying entire sections, preserving other defaults in that section

4. **XDG compliance**: Using `xdg-base-dirs` library ensures proper respect for `XDG_CONFIG_HOME` environment variable

## Dependencies Added

- `click>=8.1` - CLI framework
- `tomli-w>=1.0` - TOML writing (reading via stdlib tomllib)
- `xdg-base-dirs>=6.0` - XDG Base Directory specification support

## Impact on Future Work

This plan establishes foundational infrastructure that all future modules depend on:

- **Package structure** provides organization for daemon, CLI, and logging modules (Phase 1-2)
- **Config system** will be used by daemon startup, hotkey binding, audio settings, and model selection (Phase 2-4)
- **CLI entry point** ready for subcommands to be added in next plan (start, stop, config, etc.)
- **XDG paths** pattern can be extended for data directory, cache directory, and runtime directory as needed

## Next Steps

With package structure and config system in place, the next plan should:

1. Implement daemon lifecycle management (start, stop, status commands)
2. Add logging configuration based on config system
3. Create systemd user service or process management approach
4. Build remaining CLI commands to control the daemon

## Self-Check: PASSED

Verifying all claimed artifacts exist:

```bash
# Files created
FOUND: /home/rob/Documents/Projects/LinuxWhisper/pyproject.toml
FOUND: /home/rob/Documents/Projects/LinuxWhisper/src/linuxwhisper/__init__.py
FOUND: /home/rob/Documents/Projects/LinuxWhisper/src/linuxwhisper/config/defaults.py
FOUND: /home/rob/Documents/Projects/LinuxWhisper/src/linuxwhisper/config/loader.py
FOUND: /home/rob/Documents/Projects/LinuxWhisper/src/linuxwhisper/cli/commands.py
FOUND: /home/rob/Documents/Projects/LinuxWhisper/.gitignore

# Commits exist
FOUND: 51f0fbc
FOUND: 7c83c2f
FOUND: db3d4b2
```

All files and commits verified successfully.
