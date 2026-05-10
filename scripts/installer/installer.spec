# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for CowAgent Desktop Installer."""

import sys
from pathlib import Path

_payload = Path(SPECPATH) / "payload"

a = Analysis(
    [str(Path(SPECPATH) / "installer_gui.py")],
    pathex=[str(Path(SPECPATH)), str(Path(SPECPATH).parent)],
    binaries=[],
    datas=[
        (str(_payload), "payload"),
    ],
    hiddenimports=[
        "queue", "shutil", "pathlib", "json", "subprocess",
        "sysconfig", "tkinter", "tkinter.ttk", "tkinter.filedialog",
        "tkinter.messagebox", "threading", "urllib.request",
        "zipfile", "tempfile", "argparse", "re", "webbrowser",
        "scripts.installer.install_engine",
        "scripts.installer.installer_gui",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "numpy", "pandas", "scipy", "PIL", "cv2"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="CowAgent-Installer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # TODO: add icon file
)
