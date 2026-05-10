"""Install engine — step-by-step installation logic for CowAgent."""

import os
import queue
import re
import shutil
import sys
from pathlib import Path


class InstallEngine:
    """Orchestrates the 10-step installation process.

    Communicates progress via callback_queue: (percent, message) tuples.
    """

    def __init__(self, install_dir: str, callback_queue: queue.Queue):
        self.install_dir = install_dir
        self.callback_queue = callback_queue
        self._payload_dir = None
        self._python_bin = None

    def run(self):
        """Execute all installation steps in order."""
        self._discover_payload_path()

        self._step("正在检查磁盘空间...", 5)
        self._check_disk_space()

        self._step("正在创建安装目录...", 10)
        self._create_dirs()

        self._step("正在安装 Python 运行环境...", 25)
        self._install_python()

        self._step("正在复制项目文件...", 35)
        self._install_project()

        self._step("正在安装依赖包...", 55)
        self._install_wheels()

        self._step("正在安装 ffmpeg...", 75)
        self._install_ffmpeg()

        self._step("正在创建配置文件...", 85)
        self._install_config()

        self._step("正在创建快捷方式...", 90)
        self._create_shortcuts()

        self._step("正在写入卸载脚本...", 95)
        self._write_uninstall_script()

        self._step("安装完成", 100)

    # ── public helpers ──────────────────────────────────────────────────

    @staticmethod
    def get_default_install_dir():
        """Return the default installation directory for this platform."""
        if sys.platform == "win32":
            return os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "CowAgent")
        else:
            return os.path.join(str(Path.home()), "Applications", "CowAgent")

    def validate_path(self, path_str: str):
        """Validate an install path. Returns (is_valid, error_message)."""
        if not path_str or not path_str.strip():
            return False, "Installer path is empty"
        if sys.platform == "win32":
            # Allow colon only at position 1 (drive letter separator e.g. C:)
            drive, rest = os.path.splitdrive(path_str)
            check_part = rest if drive else path_str
            if re.search(r'[<>"|?*]', check_part) or ":" in check_part:
                return False, "Path contains invalid characters: < > \" | ? * :"
        drive = os.path.splitdrive(path_str)[0]
        if drive and sys.platform == "win32":
            if not os.path.exists(drive + "\\"):
                return False, f"drive {drive} doesn't exist"
        return True, ""

    # ── payload discovery ───────────────────────────────────────────────

    def _discover_payload_path(self):
        """Find the payload directory.

        When running from PyInstaller, payload is in sys._MEIPASS.
        In dev mode, use scripts/installer/payload relative to project root.
        """
        # PyInstaller bundle path
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidate = os.path.join(meipass, "payload")
            if os.path.isdir(candidate):
                self._payload_dir = candidate
                return candidate

        # Dev mode: find payload relative to this file
        this_dir = Path(__file__).resolve().parent
        candidate = this_dir / "payload"
        if candidate.is_dir():
            self._payload_dir = str(candidate)
            return str(candidate)

        # Fallback: search up from cwd
        for parent in Path.cwd().parents:
            candidate = parent / "scripts" / "installer" / "payload"
            if candidate.is_dir():
                self._payload_dir = str(candidate)
                return str(candidate)

        raise FileNotFoundError("Cannot locate payload directory")

    # ── install steps ───────────────────────────────────────────────────

    def _check_disk_space(self):
        required = int(1.5 * 1024**3)  # 1.5 GB
        try:
            free = shutil.disk_usage(os.path.splitdrive(self.install_dir)[0] or "/").free
        except Exception:
            free = shutil.disk_usage(self.install_dir).free
        if free < required:
            raise OSError(f"磁盘空间不足，需要至少 1.5 GB（当前可用: {free / 1024**3:.1f} GB）")

    def _create_dirs(self):
        Path(self.install_dir).mkdir(parents=True, exist_ok=True)

    def _install_python(self):
        src = os.path.join(self._payload_dir, "python")
        dst = os.path.join(self.install_dir, "python")
        self._copy_or_skip(src, dst)

        if sys.platform == "win32":
            self._python_bin = os.path.join(dst, "python.exe")
        else:
            self._python_bin = os.path.join(dst, "bin", "python3")

    def _install_project(self):
        src = os.path.join(self._payload_dir, "cowagent")
        dst = os.path.join(self.install_dir, "cowagent")
        self._copy_or_skip(src, dst)

    def _install_wheels(self):
        wheels_dir = os.path.join(self._payload_dir, "wheels")
        if not os.path.isdir(wheels_dir):
            return  # no wheels in payload (dev mode)
        python_bin = self._python_bin or sys.executable
        import subprocess
        subprocess.run(
            [python_bin, "-m", "pip", "install", "--no-index", "--find-links", wheels_dir,
             "-r", os.path.join(self.install_dir, "cowagent", "requirements.txt")],
            check=True, capture_output=True
        )
        subprocess.run(
            [python_bin, "-m", "pip", "install", "--no-index", "--find-links", wheels_dir,
             "-r", os.path.join(self.install_dir, "cowagent", "requirements-optional.txt")],
            check=False, capture_output=True
        )
        # Install cow CLI
        subprocess.run(
            [python_bin, "-m", "pip", "install", "-e",
             os.path.join(self.install_dir, "cowagent")],
            check=False, capture_output=True
        )

    def _install_ffmpeg(self):
        src = os.path.join(self._payload_dir, "ffmpeg")
        dst = os.path.join(self.install_dir, "tools", "ffmpeg")
        self._copy_or_skip(src, dst)

    def _install_config(self):
        config_template = os.path.join(self.install_dir, "cowagent", "config-template.json")
        config_file = os.path.join(self.install_dir, "cowagent", "config.json")
        if os.path.isfile(config_template) and not os.path.isfile(config_file):
            shutil.copy(config_template, config_file)

    def _create_shortcuts(self):
        self._create_desktop_shortcut()
        if sys.platform == "win32":
            self._create_start_menu_entry()

    def _create_desktop_shortcut(self):
        if sys.platform == "win32":
            import pythoncom
            pythoncom.CoInitialize()
            try:
                from win32com.client import Dispatch
                desktop = Path.home() / "Desktop"
                shortcut_path = desktop / "CowAgent.lnk"
                shell = Dispatch("WScript.Shell")
                shortcut = shell.CreateShortcut(str(shortcut_path))
                shortcut.TargetPath = str(Path(self.install_dir) / "scripts" / "start.bat")
                shortcut.WorkingDirectory = str(Path(self.install_dir) / "cowagent")
                shortcut.Description = "CowAgent AI 角色陪伴"
                shortcut.Save()
            except ImportError:
                self._create_bat_shortcut_fallback()
            finally:
                pythoncom.CoUninitialize()
        else:
            # macOS: create .command file on Desktop
            desktop = Path.home() / "Desktop"
            launcher = desktop / "CowAgent.command"
            launcher.write_text(
                '#!/bin/bash\n'
                f'cd "{self.install_dir}/cowagent"\n'
                f'"{self._python_bin or "python3"}" app.py &\n'
                'sleep 3\n'
                'open http://localhost:9899/chat\n'
            )
            os.chmod(launcher, 0o755)

    def _create_bat_shortcut_fallback(self):
        desktop = Path.home() / "Desktop"
        bat = desktop / "CowAgent.bat"
        bat.write_text(
            f'@echo off\n'
            f'cd /d "{self.install_dir}\\cowagent"\n'
            f'start "" /b "{self._python_bin or "python"}" app.py\n'
            f'start http://localhost:9899/chat\n'
        )

    def _create_start_menu_entry(self):
        try:
            start_menu = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
            cow_dir = start_menu / "CowAgent"
            cow_dir.mkdir(parents=True, exist_ok=True)
            import pythoncom
            pythoncom.CoInitialize()
            try:
                from win32com.client import Dispatch
                shortcut_path = cow_dir / "CowAgent.lnk"
                shell = Dispatch("WScript.Shell")
                shortcut = shell.CreateShortcut(str(shortcut_path))
                shortcut.TargetPath = str(Path(self.install_dir) / "scripts" / "start.bat")
                shortcut.WorkingDirectory = str(Path(self.install_dir) / "cowagent")
                shortcut.Description = "CowAgent AI 角色陪伴"
                shortcut.Save()
            finally:
                pythoncom.CoUninitialize()
        except Exception:
            pass  # start menu is optional, non-critical

    def _write_uninstall_script(self):
        if sys.platform == "win32":
            uninstall = Path(self.install_dir) / "scripts" / "uninstall.bat"
            uninstall.write_text(
                '@echo off\n'
                'echo Uninstalling CowAgent...\n'
                f'del /q "%USERPROFILE%\\Desktop\\CowAgent.lnk" 2>nul\n'
                f'del /q "%USERPROFILE%\\Desktop\\CowAgent.bat" 2>nul\n'
                f'rmdir /s /q "{self.install_dir}"\n'
                'echo CowAgent has been uninstalled.\n'
                'pause\n'
            )
        else:
            uninstall = Path(self.install_dir) / "scripts" / "uninstall.command"
            uninstall.write_text(
                '#!/bin/bash\n'
                'echo "Uninstalling CowAgent..."\n'
                f'rm -f ~/Desktop/CowAgent.command\n'
                f'rm -rf "{self.install_dir}"\n'
                'echo "CowAgent has been uninstalled."\n'
            )
            os.chmod(uninstall, 0o755)

    # ── helpers ──────────────────────────────────────────────────────────

    def _step(self, text: str, percent: int):
        if self.callback_queue:
            self.callback_queue.put((percent, text))

    @staticmethod
    def _copy_or_skip(src, dst):
        if os.path.isdir(dst):
            return  # already installed, skip
        if os.path.isdir(src):
            shutil.copytree(src, dst)
        elif os.path.isfile(src):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
