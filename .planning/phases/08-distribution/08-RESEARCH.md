# Phase 8: Distribution - Research

**Researched:** 2026-02-19
**Domain:** AUR packaging, PKGBUILD, Arch Linux Python package distribution
**Confidence:** HIGH

## Summary

LinuxWhisper needs to be packaged as an AUR package for Arch-based distros. The project uses `pyproject.toml` with setuptools as its build backend, which maps cleanly to the modern Arch Python packaging workflow using `python-build` and `python-installer`. The main challenges are: (1) mapping all Python and system dependencies to their correct Arch package names, (2) creating a proper `.install` file with post-install instructions for input group, udev rules, uinput module, and ydotool setup, (3) deciding between a release package (`linuxwhisper`) and a VCS package (`linuxwhisper-git`), and (4) handling the systemd service file difference between venv-based development installs and system-wide package installs.

The project has significant system-level setup requirements beyond just installing the package: the user must be in the `input` group, the `uinput` kernel module must be loaded, a udev rule must exist for `/dev/uinput`, and ydotool must be running. These cannot be automated in `post_install()` (which runs as root, not as the target user, and should not modify user accounts), so they must be clearly communicated via a post-install message.

A critical finding: the project currently has no LICENSE file on disk (README says MIT), and no `license` field in `pyproject.toml`. Both are required for proper AUR packaging. The systemd service template currently hardcodes the venv Python path via `sys.executable`; for the AUR package, the service file should use `/usr/bin/python -m linuxwhisper` instead, since the package installs to the system Python site-packages.

**Primary recommendation:** Create a `-git` AUR package initially (since there are no releases/tags yet). Include a `.install` file with clear post-install messages. Ship udev rules, modules-load.d config, and a system-wide systemd user service file as part of the package. Add a LICENSE file to the repo.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PKG-01 | AUR package with PKGBUILD for Arch-based distros | Full PKGBUILD template with all dependencies mapped, build/package functions documented, namcap requirements identified |
| PKG-02 | Post-install instructions for input group and ydotool setup | .install file format documented, complete post-install message covering all setup steps (input group, uinput module, udev rule, ydotool service) |
</phase_requirements>

## Standard Stack

### Core (PKGBUILD Build Tools)

| Package | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| python-build | 1.4.0 | PEP 517 build frontend | Official Arch Python packaging guideline |
| python-installer | 0.7.0 | Wheel installer | Official Arch Python packaging guideline |
| python-wheel | 0.46.3 | Wheel format support | Required by python-build |
| python-setuptools | 80.9.0 | Build backend (setuptools) | Matches pyproject.toml build-system |
| python-setuptools-scm | 9.2.2 | SCM-based versioning | Listed in pyproject.toml build-system.requires |
| namcap | latest | Package validation tool | Required for AUR quality assurance |

### Runtime Dependencies (Arch Package Names)

| Arch Package | PyPI Name / Source | Repo | Notes |
|-------------|-------------------|------|-------|
| python | python | extra (official) | >=3.11 |
| python-click | click | extra (official) | CLI framework |
| python-scipy | scipy | extra (official) | Audio processing |
| python-evdev | evdev | extra (official) | Hotkey detection via /dev/input |
| python-tomli-w | tomli-w | extra (official) | TOML config writing |
| python-xdg-base-dirs | xdg-base-dirs | extra (official) | XDG path resolution |
| python-sounddevice | sounddevice | **AUR** | Audio recording |
| python-faster-whisper | faster-whisper | **AUR** | Whisper transcription engine |
| python-gobject | pygobject | extra (official) | GTK4 Python bindings (overlay) |
| gtk4 | - | extra (official) | Overlay widget toolkit |
| gtk4-layer-shell | - | extra (official) | Wayland layer-shell for overlay |
| portaudio | - | extra (official) | sounddevice runtime dependency |

### Optional Runtime Dependencies

| Arch Package | Purpose | Repo |
|-------------|---------|------|
| ydotool | Wayland text injection (primary) | extra (official) |
| wtype | Wayland text injection (wlroots-only, Unicode) | extra (official) |
| xdotool | X11 text injection | extra (official) |
| wl-clipboard | Clipboard-based injection (Wayland) | extra (official) |
| xclip | Clipboard-based injection (X11) | extra (official) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| linuxwhisper-git (VCS) | linuxwhisper (release) | Release package requires tagged versions and source tarballs; -git is simpler to start with, switch to release package when v1.0 is tagged |
| System Python install | pip/venv install | System install via PKGBUILD is the Arch way; venv approach stays for development |

## Architecture Patterns

### Recommended Package File Structure

```
aur/
  PKGBUILD              # Package build script
  linuxwhisper.install   # Post-install/upgrade/remove messages
  .SRCINFO              # Generated metadata (makepkg --printsrcinfo)
```

### System Files Installed by Package

```
/usr/lib/systemd/user/linuxwhisper.service    # systemd user service (system-wide path)
/usr/lib/udev/rules.d/80-linuxwhisper-uinput.rules  # udev rule for /dev/uinput
/usr/lib/modules-load.d/linuxwhisper-uinput.conf     # Auto-load uinput kernel module
```

### Pattern 1: Modern Python PKGBUILD (PEP 517)

**What:** Standard PKGBUILD for Python packages using pyproject.toml
**When to use:** Any Python package with a pyproject.toml build-system definition
**Source:** [ArchWiki Python Package Guidelines](https://wiki.archlinux.org/title/Python_package_guidelines)

```bash
# Maintainer: Your Name <your.email@example.com>
pkgname=linuxwhisper-git
pkgver=0.1.0.r42.gabcdef0
pkgrel=1
pkgdesc="Linux desktop voice dictation tool using local Whisper"
arch=('x86_64')
url="https://github.com/robindarlington/linuxwhisper"
license=('MIT')
depends=(
    'python>=3.11'
    'python-click'
    'python-tomli-w'
    'python-xdg-base-dirs'
    'python-evdev'
    'python-sounddevice'
    'python-faster-whisper'
    'python-scipy'
    'python-gobject'
    'gtk4'
    'gtk4-layer-shell'
    'portaudio'
)
makedepends=(
    'git'
    'python-build'
    'python-installer'
    'python-wheel'
    'python-setuptools'
    'python-setuptools-scm'
)
optdepends=(
    'ydotool: Wayland text injection (recommended)'
    'wtype: Wayland text injection for wlroots compositors (Unicode support)'
    'xdotool: X11 text injection'
    'wl-clipboard: clipboard-based injection on Wayland'
    'xclip: clipboard-based injection on X11'
)
provides=('linuxwhisper')
conflicts=('linuxwhisper')
install=linuxwhisper.install
source=("${pkgname}::git+https://github.com/robindarlington/linuxwhisper.git")
sha256sums=('SKIP')

pkgver() {
    cd "$pkgname"
    git describe --long --abbrev=7 2>/dev/null | sed 's/\([^-]*-g\)/r\1/;s/-/./g' \
        || printf "0.1.0.r%s.%s" "$(git rev-list --count HEAD)" "$(git rev-parse --short=7 HEAD)"
}

build() {
    cd "$pkgname"
    python -m build --wheel --no-isolation
}

package() {
    cd "$pkgname"
    python -m installer --destdir="$pkgdir" dist/*.whl

    # Install license
    install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"

    # Install systemd user service
    install -Dm644 /dev/stdin "$pkgdir/usr/lib/systemd/user/linuxwhisper.service" <<'EOF'
[Unit]
Description=LinuxWhisper voice dictation daemon
After=graphical-session.target
PartOf=graphical-session.target
Wants=ydotool.service
StartLimitIntervalSec=300
StartLimitBurst=5

[Service]
Type=simple
ExecStart=/usr/bin/python -m linuxwhisper
ExecReload=/bin/kill -HUP $MAINPID
Restart=on-failure
RestartSec=5
Environment=PYTHONUNBUFFERED=1
TimeoutStopSec=10

[Install]
WantedBy=graphical-session.target
EOF

    # Install udev rule for /dev/uinput access
    install -Dm644 /dev/stdin "$pkgdir/usr/lib/udev/rules.d/80-linuxwhisper-uinput.rules" <<'EOF'
KERNEL=="uinput", GROUP="input", MODE="0660"
EOF

    # Install modules-load.d config for uinput
    install -Dm644 /dev/stdin "$pkgdir/usr/lib/modules-load.d/linuxwhisper-uinput.conf" <<'EOF'
uinput
EOF
}
```

### Pattern 2: .install File with Post-Install Messages

**What:** Shell script with post_install/post_upgrade functions for user instructions
**When to use:** When the package requires manual user configuration steps
**Source:** [ArchWiki PKGBUILD](https://wiki.archlinux.org/title/PKGBUILD)

```bash
post_install() {
    cat <<EOF

==========================================================
  LinuxWhisper - Post-Installation Setup
==========================================================

  1. ADD YOUR USER TO THE INPUT GROUP (required for hotkey detection):

     sudo usermod -aG input \$USER

  2. LOAD THE UINPUT KERNEL MODULE (required for ydotool):

     sudo modprobe uinput

     This will persist across reboots via /usr/lib/modules-load.d/linuxwhisper-uinput.conf

  3. INSTALL AND ENABLE YDOTOOL (required for Wayland text injection):

     systemctl --user enable --now ydotool

  4. LOG OUT AND LOG BACK IN for group changes to take effect.

  5. START LINUXWHISPER:

     # Option A: One-time start
     linuxwhisper start

     # Option B: Enable as systemd service (auto-start on login)
     systemctl --user enable --now linuxwhisper

  For troubleshooting, see:
     journalctl --user -u linuxwhisper -f

==========================================================

EOF
}

post_upgrade() {
    post_install
}
```

### Pattern 3: System-Wide Service File vs Venv Service File

**What:** The AUR package installs to system Python, so the service file path changes
**When to use:** When transitioning from development (venv) to packaged install

For the AUR package, the systemd service file uses a different ExecStart:

| Context | ExecStart Path | Service File Location |
|---------|---------------|----------------------|
| Development (venv) | `{venv}/bin/python -m linuxwhisper` | `~/.config/systemd/user/` |
| AUR package (system) | `/usr/bin/python -m linuxwhisper` | `/usr/lib/systemd/user/` |

The `linuxwhisper service install` command (from Phase 7) should detect whether the package is installed system-wide and skip if a system service file already exists at `/usr/lib/systemd/user/linuxwhisper.service`.

### Anti-Patterns to Avoid

- **Running usermod in post_install():** post_install runs as root and should NOT automatically modify user accounts. Only print instructions.
- **Using pip inside PKGBUILD:** Never call pip in build() or package(). Use python-build + python-installer.
- **Installing to /etc/ for package-provided files:** Package-provided udev rules go in `/usr/lib/udev/rules.d/`, not `/etc/udev/rules.d/`. The `/etc/` path is for local admin overrides.
- **Auto-enabling systemd services in post_install:** Arch policy is to install service files but NOT enable them automatically. Let the user decide.
- **Bundling Python dependencies:** Never vendor/bundle Python libraries. Declare them as `depends` and let pacman resolve them.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Python package building | Custom setup.py install scripts | `python -m build --wheel` + `python -m installer` | Official Arch guideline, handles entry points and metadata |
| Dependency tracking | Manual dependency lists | `namcap` validation on built package | namcap auto-detects missing deps via ldd and Python imports |
| Package validation | Manual review of file permissions | `namcap PKGBUILD && namcap *.pkg.tar.zst` | Catches permission errors, missing deps, license issues |
| .SRCINFO generation | Hand-written .SRCINFO | `makepkg --printsrcinfo > .SRCINFO` | Required format, auto-generated from PKGBUILD |
| udev rule reload | Custom reload scripts | pacman hooks (automatic since systemd ships the hook) | Installing to `/usr/lib/udev/rules.d/` triggers automatic reload |

**Key insight:** Arch packaging is highly standardized. Deviating from the documented patterns causes namcap failures and user confusion. Follow the ArchWiki templates exactly.

## Common Pitfalls

### Pitfall 1: Missing AUR Dependencies

**What goes wrong:** Package installs but fails to run because `python-sounddevice` or `python-faster-whisper` are AUR packages, not official repo packages. Users installing with `pacman -S` (instead of an AUR helper like yay/paru) won't get these automatically.
**Why it happens:** AUR packages can only depend on other AUR packages or official packages, but `pacman` itself doesn't resolve AUR dependencies.
**How to avoid:** Document in the AUR package description that an AUR helper (yay/paru) is recommended. List ALL AUR dependencies in the PKGBUILD `depends` array -- AUR helpers DO resolve AUR-to-AUR dependencies.
**Warning signs:** `ImportError: No module named 'faster_whisper'` or `No module named 'sounddevice'` at runtime.

### Pitfall 2: setuptools-scm Version Detection Fails

**What goes wrong:** Build fails because `setuptools-scm` can't determine the version from git metadata.
**Why it happens:** The PKGBUILD `build()` runs in a source directory that may lack git history (for release packages) or where `setuptools-scm` can't find tags.
**How to avoid:** For the `-git` package, git history is present. But `setuptools-scm` looks for annotated tags. If there are no tags (current state), it falls back. Ensure `pyproject.toml` has a fallback version: `version = "0.1.0"` and use `setuptools-scm` only in `build-system.requires`, not as the sole version source. The current `pyproject.toml` already hardcodes `version = "0.1.0"`, so this is safe.
**Warning signs:** `LookupError: setuptools-scm was unable to detect version`

### Pitfall 3: Service File Conflict Between Venv and System Install

**What goes wrong:** User has both a venv-based `linuxwhisper service install` (from development) and the AUR package's system service file. Two service files compete.
**Why it happens:** The venv service installs to `~/.config/systemd/user/linuxwhisper.service` while the package installs to `/usr/lib/systemd/user/linuxwhisper.service`. The user-local file takes precedence in systemd's resolution order.
**How to avoid:** The `linuxwhisper service install` command should check for a system-installed service file and warn if one already exists. Document that users should NOT use `linuxwhisper service install` when the AUR package is installed (the package already ships the service file).
**Warning signs:** Service runs the venv Python instead of the system Python, or vice versa.

### Pitfall 4: Missing LICENSE File

**What goes wrong:** namcap reports error: `missing-license`. Package cannot be promoted to official repos.
**Why it happens:** The project currently has no LICENSE file in the repository. README says MIT but there's no actual license file.
**How to avoid:** Add a LICENSE file containing the MIT license text to the project root. Add `license=('MIT')` to PKGBUILD. Install the license to `/usr/share/licenses/$pkgname/LICENSE`.
**Warning signs:** namcap error `E: missing-license`.

### Pitfall 5: Forgetting pyproject.toml License Field

**What goes wrong:** Built wheel metadata lacks license information, causing namcap warnings.
**Why it happens:** `pyproject.toml` has no `license` field under `[project]`.
**How to avoid:** Add `license = {text = "MIT"}` or `license = "MIT"` (SPDX identifier) to `pyproject.toml` `[project]` table.
**Warning signs:** namcap warnings about missing license metadata in the installed package.

### Pitfall 6: Incorrect Python Source Layout in Wheel

**What goes wrong:** After installing the wheel, `python -m linuxwhisper` fails with `ModuleNotFoundError`.
**Why it happens:** The `pyproject.toml` specifies `[tool.setuptools.packages.find] where = ["src"]`. If the build runs from the wrong directory or the src layout isn't properly detected, the wheel may be empty.
**How to avoid:** Verify the wheel contains the correct files: `python -m zipfile -l dist/*.whl`. The build function must `cd "$pkgname"` before running `python -m build`.
**Warning signs:** Empty or suspiciously small wheel file, missing `linuxwhisper/__main__.py` from the wheel.

### Pitfall 7: uinput Module Not Loaded

**What goes wrong:** ydotool fails with "Permission denied" because `/dev/uinput` doesn't exist.
**Why it happens:** The `uinput` kernel module isn't loaded. Without it, `/dev/uinput` never appears, the udev rule never fires.
**How to avoid:** Ship `/usr/lib/modules-load.d/linuxwhisper-uinput.conf` with content `uinput`. The post-install message must also instruct users to run `sudo modprobe uinput` for immediate effect (the modules-load.d config only takes effect on next boot).
**Warning signs:** `/dev/uinput` doesn't exist, ydotool crashes.

## Code Examples

### Verified PKGBUILD Build/Package Functions

Source: [ArchWiki Python Package Guidelines](https://wiki.archlinux.org/title/Python_package_guidelines)

```bash
build() {
    cd "$pkgname"
    python -m build --wheel --no-isolation
}

package() {
    cd "$pkgname"
    python -m installer --destdir="$pkgdir" dist/*.whl

    # Install license
    install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
}
```

### pkgver() for Git Package Without Tags

Source: [ArchWiki VCS Package Guidelines](https://wiki.archlinux.org/title/VCS_package_guidelines)

```bash
pkgver() {
    cd "$pkgname"
    # Try tag-based versioning first, fall back to commit count
    git describe --long --abbrev=7 2>/dev/null \
        | sed 's/\([^-]*-g\)/r\1/;s/-/./g' \
        || printf "0.1.0.r%s.%s" "$(git rev-list --count HEAD)" "$(git rev-parse --short=7 HEAD)"
}
```

Output example: `0.1.0.r42.gabcdef0` (version 0.1.0, 42 commits, at hash abcdef0)

### System-Wide Service File for AUR Package

The AUR package ships a service file with a generic ExecStart (no venv path):

```ini
[Unit]
Description=LinuxWhisper voice dictation daemon
After=graphical-session.target
PartOf=graphical-session.target
Wants=ydotool.service
StartLimitIntervalSec=300
StartLimitBurst=5

[Service]
Type=simple
ExecStart=/usr/bin/python -m linuxwhisper
ExecReload=/bin/kill -HUP $MAINPID
Restart=on-failure
RestartSec=5
Environment=PYTHONUNBUFFERED=1
TimeoutStopSec=10

[Install]
WantedBy=graphical-session.target
```

**Key difference from venv version:** `ExecStart=/usr/bin/python -m linuxwhisper` instead of `ExecStart={venv_python} -m linuxwhisper`. The package installs linuxwhisper to the system Python site-packages, so `/usr/bin/python` can find it.

### Building and Validating the Package

```bash
# In the AUR package directory:

# Build the package
makepkg -s    # -s installs missing dependencies

# Validate PKGBUILD
namcap PKGBUILD

# Validate built package
namcap linuxwhisper-git-*.pkg.tar.zst

# Install locally for testing
makepkg -si   # -i installs after building

# Generate .SRCINFO for AUR submission
makepkg --printsrcinfo > .SRCINFO
```

### Testing on a Clean System (Optional)

```bash
# Create a clean chroot for testing (ensures no host pollution)
# Requires devtools package
extra-x86_64-build

# Or test in a container/VM:
# 1. Install base Arch
# 2. Install yay/paru
# 3. yay -S linuxwhisper-git
# 4. Follow post-install instructions
# 5. Run linuxwhisper start
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `python setup.py install` | `python -m build` + `python -m installer` | ~2022 (PEP 517 adoption) | PKGBUILD must use new build workflow |
| setup.py-only packages | pyproject.toml with build-system | ~2021 (PEP 621) | LinuxWhisper already uses pyproject.toml (good) |
| udev rules in /etc/ | udev rules in /usr/lib/ for packages | Standard practice | Pacman hook auto-reloads rules from /usr/lib/ |
| .install file with systemctl enable | Just install, never auto-enable | Arch policy | post_install prints instructions only |

**Deprecated/outdated:**
- `python setup.py install --root="$pkgdir"`: Still works but the ArchWiki now recommends `python -m build` + `python -m installer`
- `pip install` inside PKGBUILD: Explicitly discouraged; use python-build/python-installer

## Open Questions

1. **GitHub Repository URL**
   - What we know: README references `https://github.com/robindarlington/linuxwhisper.git` but no git remote is currently configured and no releases/tags exist
   - What's unclear: Is this the final URL? Will the repo be public before AUR submission?
   - Recommendation: The PKGBUILD needs a valid source URL. For local testing, use a local `file://` source or the placeholder URL. Before AUR submission, ensure the GitHub repo exists and is public. Create an initial git tag (e.g., `v0.1.0`) if switching to a release-based package.

2. **ydotool as depends vs optdepends**
   - What we know: ydotool is the primary text injection method on Wayland. Without it, LinuxWhisper has fallbacks (wtype, clipboard) but the primary use case requires it.
   - What's unclear: Should ydotool be a hard dependency or optional?
   - Recommendation: Keep as `optdepends` since LinuxWhisper has multiple injection backends and can work with just wtype on wlroots compositors. The post-install message strongly recommends it.

3. **Service file: ship in package vs generate via `linuxwhisper service install`?**
   - What we know: Phase 7 implemented `linuxwhisper service install` which generates a service file with the venv Python path. The AUR package should ship a system-wide service file.
   - What's unclear: Should we modify the service module to detect system-wide installation and skip/warn?
   - Recommendation: Ship the system-wide service file in the package at `/usr/lib/systemd/user/linuxwhisper.service`. Modify `linuxwhisper service install` to check for an existing system service file and warn that it's not needed when installed via the AUR package.

4. **python-sounddevice and python-faster-whisper are AUR dependencies**
   - What we know: Both are in the AUR (not official repos). AUR-to-AUR dependencies work with AUR helpers (yay/paru) but not plain pacman.
   - What's unclear: Will this cause issues for users?
   - Recommendation: This is standard for AUR packages. Document that an AUR helper is needed. Most Arch users already have one.

## Sources

### Primary (HIGH confidence)
- [ArchWiki Python Package Guidelines](https://wiki.archlinux.org/title/Python_package_guidelines) - Modern PKGBUILD patterns for Python packages
- [ArchWiki PKGBUILD](https://wiki.archlinux.org/title/PKGBUILD) - .install file functions, backup array, all PKGBUILD variables
- [ArchWiki VCS Package Guidelines](https://wiki.archlinux.org/title/VCS_package_guidelines) - -git package naming, pkgver() function, source format
- [ArchWiki AUR Submission Guidelines](https://wiki.archlinux.org/title/AUR_submission_guidelines) - Required files, .SRCINFO generation, naming rules
- [ArchWiki Namcap](https://wiki.archlinux.org/title/Namcap) - Package validation tool, error/warning categories
- Local `pacman -Si` verification of all package names and versions (verified on live Arch system)

### Secondary (MEDIUM confidence)
- [AUR python-faster-whisper](https://aur.archlinux.org/packages/python-faster-whisper) - Dependency chain for faster-whisper (python-ctranslate2, etc.)
- [AUR python-sounddevice](https://aur.archlinux.org/packages/python-sounddevice) - Confirmed AUR status, portaudio dependency
- [ArchWiki udev](https://wiki.archlinux.org/title/Udev) - Rules directory hierarchy (/usr/lib/ vs /etc/)
- Phase 7 Research (this project) - systemd service file template, verified working on this system

### Tertiary (LOW confidence)
- Various Arch Linux forum threads on PKGBUILD review and Python packaging edge cases

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All package names verified against live Arch system via `pacman -Ss` / `pacman -Si`. AUR packages verified via aur.archlinux.org.
- Architecture: HIGH - PKGBUILD patterns taken directly from ArchWiki official guidelines. .install file format verified from ArchWiki and real-world examples.
- Pitfalls: HIGH - Based on actual project state (missing LICENSE file, setuptools-scm in build-system.requires, venv vs system service conflict), not hypothetical issues.
- Post-install requirements: HIGH - input group, uinput module, udev rule, ydotool all documented in project memory as real setup pain points encountered during development.

**Research date:** 2026-02-19
**Valid until:** 2026-04-19 (Arch packaging guidelines are stable; Python package names rarely change)
