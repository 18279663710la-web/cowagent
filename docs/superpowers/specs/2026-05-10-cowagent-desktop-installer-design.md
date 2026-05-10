# CowAgent Desktop Installer — Design Spec

**Date**: 2026-05-10  
**Status**: Draft  

---

## 1. Goal

Turn CowAgent into a desktop application with a GUI-based installer. New users download a single file, double-click, select an install location, and everything is set up automatically. After installation, they access CowAgent through a web browser at `http://localhost:9899/chat`. No terminal, no pip, no git clone.

---

## 2. Approach

**Python self-packaging installer (PyInstaller)**. One codebase produces both Windows (`.exe`) and macOS (`.app`) installers. The GUI is built with tkinter (Python stdlib, zero extra deps). The installer payload bundles Python Embedded + all pip packages + ffmpeg + project source — fully offline capable.

---

## 3. Architecture

```
┌──────────────────────────────────────┐
│  Installer GUI (tkinter)            │  ← user interface
│  Welcome → Progress → Done          │
├──────────────────────────────────────┤
│  Install Engine (Python logic)      │  ← file extraction, shortcuts, config
├──────────────────────────────────────┤
│  Payload (bundled in installer)     │
│  ├─ Python Embedded                 │
│  ├─ project source (cowagent/)      │
│  ├─ pip dependencies (.whl)         │
│  ├─ ffmpeg binary                   │
│  └─ start / uninstall scripts       │
└──────────────────────────────────────┘
```

---

## 4. Installer GUI

Single tkinter window, 500×380 px, non-resizable, centered on screen.

### Page 1: Welcome + Path Selection

- Emoji label (cow)
- Install path: `ttk.Entry` prefilled with OS default (`C:\Program Files\CowAgent` on Windows, `~/Applications/CowAgent` on macOS)
- "Browse..." button → native folder selection dialog
- "Space required: ~1.2 GB" label
- "Install" button (large, primary action)

### Page 2: Progress

- `ttk.Progressbar` (determinate, 0–100%)
- Current step description label (e.g. "Installing dependencies...")
- No buttons — user waits

### Page 3: Done

- Success checkmark + "Installation complete"
- Install location path displayed
- Two buttons: "Launch CowAgent" (starts service + opens browser) and "Close"

### Progress Updates

Install engine runs on a background thread. Sends `(percent, text)` tuples through `queue.Queue` to the main thread. Main thread polls with `widget.after(100)`.

---

## 5. Install Engine

### Step Sequence

| Step | Action | Progress |
|------|--------|----------|
| 1 | Check disk space (≥ 1.5 GB free) | 5% |
| 2 | Create install directory | 10% |
| 3 | Extract Python Embedded → `python/` | 25% |
| 4 | Copy project source → `cowagent/` | 35% |
| 5 | pip install all wheels (offline) | 55% |
| 6 | Extract ffmpeg → `tools/ffmpeg/` | 75% |
| 7 | Copy config-template → config.json | 85% |
| 8 | Create desktop shortcut / launcher | 90% |
| 9 | Write uninstall script | 95% |
| 10 | Done | 100% |

### Error Handling

- Disk space insufficient: show error message, offer to choose a different path
- Install directory exists: offer overwrite or choose different path
- Any file operation failure: show error with details, suggest retry or exit

---

## 6. Installed Directory Layout

```
C:\Program Files\CowAgent\          (or user-chosen path)
├── python/                         # Python Embedded, self-contained
│   ├── python.exe
│   └── Lib/site-packages/          # all pip packages
├── cowagent/                       # project source
│   ├── app.py
│   ├── config.json
│   ├── config-template.json
│   └── ...
├── tools/
│   └── ffmpeg/                     # ffmpeg binaries
├── scripts/
│   ├── start.bat / start.command       # launch script
│   └── uninstall.bat / uninstall.command  # removal script
└── workspace/                      # runtime data (logs, DB, memory)
```

---

## 7. Cross-Platform Differences

| Item | Windows | macOS |
|------|---------|-------|
| Default install path | `C:\Program Files\CowAgent` | `~/Applications/CowAgent` |
| Shortcut | `.lnk` via PowerShell | `.command` file, double-clickable |
| Start script | `.bat` file | `.command` file (chmod +x) |
| ffmpeg source | gyan.dev Windows build | evermeet.cx macOS build |
| Python Embedded | python.org embeddable .zip | python.org macOS .pkg or PyInstaller handled |
| Desktop shortcut location | `%USERPROFILE%\Desktop` | `~/Desktop` |
| Start menu entry | `%APPDATA%\Microsoft\Windows\Start Menu` | N/A (macOS uses .command on desktop) |

---

## 8. User Flow After Install

1. Double-click desktop shortcut
2. Script starts CowAgent Web service (background) on port 9899
3. Script waits 3s for service to become ready
4. Default browser opens → `http://localhost:9899/chat`
5. User configures API keys, model, character, channels via Web UI
6. Chat immediately

### Service Management

All management through the Web UI:
- Configure API keys → `/config`
- Manage characters → `/api/characters`
- Manage channels → `/api/channels`
- View logs → `/api/logs`
- Stop service → from Web UI or close terminal

No terminal required for day-to-day use.

---

## 9. Uninstall

User runs `uninstall.bat` (Win) or `uninstall.command` (macOS) from the install directory, or manually deletes:
1. The install directory (`C:\Program Files\CowAgent`)
2. The desktop shortcut

Nothing else — no registry entries, no system PATH changes, no system-level modifications.

---

## 10. Environment Isolation

- Does NOT modify system PATH
- Does NOT touch system Python installation
- Does NOT write to Windows registry
- Python Embedded runs within install directory only
- All pip packages contained in `python/Lib/site-packages/`
- Runtime data (logs, DB, memory) contained in `workspace/`

Complete uninstall = delete the install directory + desktop shortcut.

---

## 11. Installer Project Structure

```
scripts/installer/
├── build.py                  # build script — one command, two platform packages
├── installer_gui.py           # tkinter GUI (3 pages)
├── install_engine.py          # step-by-step install logic
├── installer.spec             # PyInstaller spec
├── payload/
│   ├── (python-embedded/)     # downloaded at build time
│   ├── (cowagent/)            # copied from project root at build time
│   ├── (wheels/)              # downloaded at build time
│   ├── (ffmpeg/)              # downloaded at build time
│   └── scripts/
│       ├── start.bat
│       ├── start.command
│       ├── uninstall.bat
│       └── uninstall.command
└── README.md                  # build instructions for developers
```

---

## 12. Size Estimates

| Component | Size |
|-----------|------|
| Python Embedded | ~35 MB |
| pip packages (installed) | ~370 MB |
| ffmpeg binary | ~100 MB |
| Project source | ~13 MB |
| **Total unpacked** | **~520 MB** |
| **Installer download (compressed)** | **~200-250 MB** |
| **Installed footprint** | **~1.2 GB** (includes workspace reserve) |

---

## 13. Build Process

```
python scripts/installer/build.py --platform windows
python scripts/installer/build.py --platform macos
python scripts/installer/build.py --platform all
```

Build steps:
1. Download Python Embedded from python.org for target platform
2. Download ffmpeg binary for target platform
3. Download all pip packages as .whl files (`pip download -r requirements.txt -r requirements-optional.txt`)
4. Copy project source to payload
5. Copy start/uninstall scripts to payload
6. Run PyInstaller with spec file

Output: `dist/CowAgent-Installer-Windows.exe` or `dist/CowAgent-Installer-macOS.app`

---

## 14. GUI Mockup (ASCII)

```
┌──────────────────────────────────────┐
│  CowAgent 安装向导              [_][X]│
│                                      │
│              🐄                       │
│                                      │
│  安装路径：                           │
│  ┌──────────────────────────────┐    │
│  │ C:\Program Files\CowAgent    │    │
│  └──────────────────────────────┘    │
│  [浏览...]                           │
│                                      │
│  所需空间：约 500 MB                   │
│                                      │
│  ┌──────────────────────────────┐    │
│  │        开 始 安 装           │    │
│  └──────────────────────────────┘    │
└──────────────────────────────────────┘
```
