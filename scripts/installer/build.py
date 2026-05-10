"""Build the CowAgent desktop installer for Windows or macOS.

Usage:
    python scripts/installer/build.py --platform windows
    python scripts/installer/build.py --platform macos
    python scripts/installer/build.py --platform all

Steps:
1. Download Python Embedded for target platform
2. Download ffmpeg binary
3. Download all pip packages as .whl files
4. Copy project source to payload
5. Run PyInstaller
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path


# ── config ────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PAYLOAD_DIR = Path(__file__).resolve().parent / "payload"
DIST_DIR = Path(__file__).resolve().parent / "dist"

PYTHON_VERSION = "3.12.8"

PYTHON_EMBED_URLS = {
    "windows": f"https://www.python.org/ftp/python/{PYTHON_VERSION}/python-{PYTHON_VERSION}-embed-amd64.zip",
    "macos": f"https://www.python.org/ftp/python/{PYTHON_VERSION}/python-{PYTHON_VERSION}-macos11.pkg",
}

FFMPEG_URLS = {
    "windows": "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip",
    "macos": "https://evermeet.cx/ffmpeg/ffmpeg-7.1.1.zip",  # static build
}

# Files/dirs to exclude when copying project source
PROJECT_EXCLUDE = {
    "venv", ".git", "__pycache__", ".pytest_cache",
    "run.log", "nohup.out", "user_datas.pkl",
    ".claude", "node_modules",
}


# ── download helpers ──────────────────────────────────────────────────────

def download(url, dest):
    print(f"  Downloading: {url}")
    dest.parent.mkdir(parents=True, exist_ok=True)

    def _report(block_num, block_size, total_size):
        downloaded = block_num * block_size
        if total_size > 0:
            pct = min(100, downloaded * 100 // total_size)
            print(f"\r  {pct}%", end="", flush=True)

    urllib.request.urlretrieve(url, str(dest), reporthook=_report)
    print("")


def extract_zip(zip_path, dest_dir):
    print(f"  Extracting to: {dest_dir}")
    dest_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        # Strip top-level directory if present
        members = zf.namelist()
        common_prefix = os.path.commonpath(members) if members else ""
        if common_prefix and common_prefix != "." and common_prefix != "/":
            # All files under common_prefix; extract to temp first, then move
            tmp = tempfile.mkdtemp()
            zf.extractall(tmp)
            src_dir = Path(tmp) / common_prefix
            for item in src_dir.iterdir():
                dest = dest_dir / item.name
                if dest.exists():
                    if dest.is_dir():
                        shutil.rmtree(dest)
                    else:
                        dest.unlink()
                shutil.move(str(item), str(dest_dir / item.name))
            shutil.rmtree(tmp)
        else:
            zf.extractall(dest_dir)


# ── payload assembly ──────────────────────────────────────────────────────

def copy_project_source():
    print("Copying project source...")
    dst = PAYLOAD_DIR / "cowagent"
    if dst.exists():
        shutil.rmtree(dst)

    for item in PROJECT_ROOT.iterdir():
        if item.name in PROJECT_EXCLUDE or item.name.startswith("."):
            continue
        target = dst / item.name
        if item.is_dir():
            shutil.copytree(item, target, ignore=lambda d, f: [x for x in f if x in PROJECT_EXCLUDE or x.startswith(".") and x != ".env.example"])
        else:
            dst.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)
    print(f"  Done: {dst}")


def download_python(platform):
    print("Downloading Python Embedded...")
    url = PYTHON_EMBED_URLS[platform]
    if platform == "windows":
        tmp = Path(tempfile.mkdtemp()) / "python.zip"
        download(url, tmp)
        extract_zip(tmp, PAYLOAD_DIR / "python")
        # Windows embed needs python3._pth modified to enable imports
        pth_file = PAYLOAD_DIR / "python" / "python312._pth"
        if pth_file.exists():
            content = pth_file.read_text()
            # Uncomment 'import site' to enable pip packages
            content = content.replace("#import site", "import site")
            # Add Lib path
            content += "\nLib\nLib/site-packages\n"
            pth_file.write_text(content)
        # Create empty Lib/site-packages dirs
        (PAYLOAD_DIR / "python" / "Lib" / "site-packages").mkdir(parents=True, exist_ok=True)
        tmp.unlink(missing_ok=True)
    else:
        # macOS: download pkg, extract to payload/python/
        tmp = Path(tempfile.mkdtemp()) / "python.pkg"
        download(url, tmp)
        # For macOS, we use xar + cpio or just rely on system Python for the packaged app
        # PyInstaller handles Python on macOS differently
        print("  (macOS: Python handled by PyInstaller)")
    print(f"  Done: {PAYLOAD_DIR / 'python'}")


def download_ffmpeg(platform):
    print("Downloading ffmpeg...")
    url = FFMPEG_URLS[platform]
    tmp = Path(tempfile.mkdtemp()) / "ffmpeg.zip"
    download(url, tmp)
    ffmpeg_dst = PAYLOAD_DIR / "ffmpeg"
    extract_zip(tmp, ffmpeg_dst)
    # Find the actual ffmpeg binary and flatten the structure
    for root, dirs, files in os.walk(ffmpeg_dst):
        if "ffmpeg.exe" in files or "ffmpeg" in files:
            # Move binaries to ffmpeg root
            for f in files:
                src = Path(root) / f
                dst = ffmpeg_dst / f
                if src != dst and not dst.exists():
                    shutil.move(str(src), str(dst))
            break
    tmp.unlink(missing_ok=True)
    print(f"  Done: {PAYLOAD_DIR / 'ffmpeg'}")


def download_wheels():
    print("Downloading pip packages (.whl)...")
    wheels_dir = PAYLOAD_DIR / "wheels"
    wheels_dir.mkdir(parents=True, exist_ok=True)
    req_files = [
        str(PROJECT_ROOT / "requirements.txt"),
        str(PROJECT_ROOT / "requirements-optional.txt"),
    ]
    for req_file in req_files:
        if Path(req_file).exists():
            subprocess.run(
                [sys.executable, "-m", "pip", "download", "-r", req_file, "--dest", str(wheels_dir),
                 "--only-binary", ":all:"],
                check=True,
            )
    print(f"  Done: {wheels_dir}")


def copy_scripts():
    print("Copying start/uninstall scripts...")
    dst = PAYLOAD_DIR / "scripts"
    src = PROJECT_ROOT / "scripts" / "installer" / "payload" / "scripts"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    # Ensure executable permissions on macOS scripts
    if sys.platform != "win32":
        for script in dst.glob("*.command"):
            os.chmod(script, 0o755)
    print(f"  Done: {dst}")


# ── PyInstaller ───────────────────────────────────────────────────────────

def run_pyinstaller():
    print("Running PyInstaller...")
    spec_file = Path(__file__).resolve().parent / "installer.spec"
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", str(spec_file), "--distpath", str(DIST_DIR), "--workpath", str(Path(tempfile.mkdtemp()) / "pyinstaller"), "--noconfirm"],
        check=True,
        cwd=str(PROJECT_ROOT),
    )
    print(f"  Done. Output: {DIST_DIR}")


# ── main ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Build CowAgent installer")
    parser.add_argument("--platform", choices=("windows", "macos", "all"), default="windows")
    parser.add_argument("--skip-download", action="store_true", help="Skip downloading (payload already assembled)")
    args = parser.parse_args()

    platforms = ["windows", "macos"] if args.platform == "all" else [args.platform]

    for platform in platforms:
        print(f"\n{'='*60}\n  Building for: {platform}\n{'='*60}")

        if not args.skip_download:
            download_python(platform)
            download_ffmpeg(platform)
            download_wheels()
            copy_project_source()
            copy_scripts()

        try:
            run_pyinstaller()
        except subprocess.CalledProcessError:
            print("PyInstaller not installed. Install with: pip install pyinstaller")
            print("Then re-run: python scripts/installer/build.py")
            sys.exit(1)

    print(f"\nBuild complete. Installer(s) in: {DIST_DIR}")


if __name__ == "__main__":
    main()
