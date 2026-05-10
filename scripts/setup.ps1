#Requires -Version 5.1
<#
.SYNOPSIS
    CowAgent one-click environment setup for Windows.
.DESCRIPTION
    Installs all system dependencies (Python, Git, ffmpeg),
    clones the project (if not already in it), creates a virtual
    environment, installs Python packages, and registers the cow CLI.

    Web download & run (PowerShell as Administrator recommended):
      irm https://raw.githubusercontent.com/18279663710la-web/cowagent/master/scripts/setup.ps1 | iex

    Local run:
      .\scripts\setup.ps1
      .\scripts\setup.ps1 -WithBrowser      # also install Playwright + Chromium
      .\scripts\setup.ps1 -SkipSystem        # skip system deps, only Python setup
      .\scripts\setup.ps1 -Dev               # install dev/test dependencies too
#>

param(
    [switch]$WithBrowser,  # Also install browser automation tools
    [switch]$SkipSystem,   # Skip system dependency installation
    [switch]$Dev           # Install dev/test dependencies
)

$ErrorActionPreference = "Stop"

# ── UTF-8 console ───────────────────────────────────────────────────
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
chcp 65001 | Out-Null

# ── helpers ────────────────────────────────────────────────────────
function Write-Step  { param([string]$M) Write-Host "=> $M" -ForegroundColor Cyan }
function Write-Good  { param([string]$M) Write-Host "   [OK] $M" -ForegroundColor Green }
function Write-Warn  { param([string]$M) Write-Host "   [!!] $M" -ForegroundColor Yellow }
function Write-Fail  { param([string]$M) Write-Host "   [FAIL] $M" -ForegroundColor Red }

function Test-Admin {
    $current = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    return $current.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Test-Command {
    param([string]$Cmd)
    return [bool](Get-Command $Cmd -ErrorAction SilentlyContinue)
}

function Install-Winget {
    if (Test-Command winget) { return $true }
    Write-Step "Installing winget (App Installer)..."
    try {
        $progressPreference = 'silentlyContinue'
        $releases = Invoke-RestMethod -Uri "https://api.github.com/repos/microsoft/winget-cli/releases/latest" -TimeoutSec 15
        $bundle = ($releases.assets | Where-Object { $_.name -like "*.msixbundle" -and $_.name -notlike "*License*" } | Select-Object -First 1).browser_download_url
        if (-not $bundle) { throw "No msixbundle found" }
        $out = "$env:TEMP\winget.msixbundle"
        Invoke-WebRequest -Uri $bundle -OutFile $out -UseBasicParsing
        Add-AppxPackage -Path $out
        Remove-Item $out -Force -ErrorAction SilentlyContinue
        Write-Good "winget installed"
        return $true
    } catch {
        Write-Warn "winget install failed: $_"
        return $false
    }
}

# ── system dependencies ─────────────────────────────────────────────
function Install-Python {
    if (Test-Command python) {
        try {
            $ver = & python -c "import sys; v=sys.version_info; print(f'{v.major}.{v.minor}')" 2>$null
            $parts = $ver -split '\.'
            $major = [int]$parts[0]; $minor = [int]$parts[1]
            if ($major -eq 3 -and $minor -ge 9 -and $minor -le 13) {
                Write-Good "Python $ver already installed (at $(Get-Command python).Source))"
                return
            }
            Write-Warn "Python $ver found but version not in 3.9-3.13 range."
        } catch {}
    }

    Write-Step "Installing Python 3.12 via winget..."
    if (Test-Command winget) {
        winget install Python.Python.3.12 --accept-source-agreements --accept-package-agreements --silent
        # Refresh PATH for current session
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        Write-Good "Python 3.12 installed. Please restart your terminal if python is not found."
    } else {
        Write-Fail "Cannot install Python automatically. Please download from: https://www.python.org/downloads/"
        Write-Warn "Make sure to check 'Add Python to PATH' during installation."
        throw "Python installation required"
    }
}

function Install-Git {
    if (Test-Command git) {
        Write-Good "Git already installed ($(& git --version))"
        return
    }

    Write-Step "Installing Git via winget..."
    if (Test-Command winget) {
        winget install Git.Git --accept-source-agreements --accept-package-agreements --silent
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        Write-Good "Git installed"
    } else {
        Write-Fail "Cannot install Git automatically. Please download from: https://git-scm.com/download/win"
        throw "Git installation required"
    }
}

function Install-FFmpeg {
    if (Test-Command ffmpeg) {
        Write-Good "ffmpeg already installed ($(& ffmpeg -version | Select-Object -First 1))"
        return
    }

    Write-Step "Installing ffmpeg via winget..."
    if (Test-Command winget) {
        winget install Gyan.FFmpeg --accept-source-agreements --accept-package-agreements --silent
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        if (Test-Command ffmpeg) {
            Write-Good "ffmpeg installed"
        } else {
            Write-Warn "ffmpeg installed but not in current PATH. Restart terminal if needed."
        }
    } else {
        Write-Warn "Cannot install ffmpeg automatically. Voice features won't work."
        Write-Warn "Download from: https://ffmpeg.org/download.html"
    }
}

# ── Python environment ──────────────────────────────────────────────
function Assert-Python {
    # Collect all matching Python binaries, then prefer native Windows Python
    $candidates = @()
    foreach ($cmd in @("python3", "python")) {
        $bin = Get-Command $cmd -ErrorAction SilentlyContinue
        if (-not $bin) { continue }
        try {
            $ver = & $bin.Source -c "import sys; v=sys.version_info; print(f'{v.major}.{v.minor}')" 2>$null
            $parts = $ver -split '\.'
            $major = [int]$parts[0]; $minor = [int]$parts[1]
            if ($major -eq 3 -and $minor -ge 9 -and $minor -le 13) {
                $isWindowsNative = $bin.Source -notmatch '(msys|cygwin|mingw)'
                $candidates += @{ Source = $bin.Source; Version = $ver; Native = $isWindowsNative }
            }
        } catch {}
    }
    if ($candidates.Count -eq 0) {
        Write-Fail "Python 3.9-3.13 not found. Run script without -SkipSystem to install it."
        exit 1
    }
    # Prefer Windows-native Python, fall back to first available
    $pick = ($candidates | Where-Object { $_.Native } | Select-Object -First 1)
    if (-not $pick) { $pick = $candidates[0] }
    $script:PythonCmd = $pick.Source
    $script:PythonVer = $pick.Version
    if (-not $pick.Native) {
        Write-Warn "MSYS2/Cygwin Python detected. For best results, install from python.org."
    }
    Write-Good "Python $script:PythonVer detected: $PythonCmd"
}

function Get-VenvPython {
    param([string]$VenvDir)
    # Windows-style venv (from python.org)
    $winPy = Join-Path $VenvDir "Scripts\python.exe"
    if (Test-Path $winPy) { return $winPy }
    # Unix-style venv (from MSYS2/Git Bash Python)
    $unixPy = Join-Path $VenvDir "bin\python"
    $unixPyExe = Join-Path $VenvDir "bin\python.exe"
    if (Test-Path $unixPyExe) { return $unixPyExe }
    if (Test-Path $unixPy) { return $unixPy }
    return $null
}

function New-Venv {
    $venvDir = Join-Path $BaseDir "venv"
    if (Test-Path $venvDir) {
        Write-Good "Virtual environment already exists: $venvDir"
    } else {
        Write-Step "Creating virtual environment..."
        & $PythonCmd -m venv $venvDir
        Write-Good "Virtual environment created"
    }
    $script:VenvPython = Get-VenvPython $venvDir
    if (-not $VenvPython) {
        Write-Fail "Virtual environment created but cannot find python in it."
        exit 1
    }
    Write-Good "Virtual environment activated (using $VenvPython)"
    # Upgrade pip inside the venv
    & $VenvPython -m pip install --upgrade pip -q 2>&1 | Out-Null
}

function Install-PipDeps {
    Write-Step "Installing core dependencies (requirements.txt)..."
    $prevEAP = $ErrorActionPreference; $ErrorActionPreference = "Continue"
    & $VenvPython -m pip install -r "$BaseDir\requirements.txt"
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "Some dependencies had issues. Trying with Tsinghua mirror..."
        & $VenvPython -m pip install -r "$BaseDir\requirements.txt" -i https://pypi.tuna.tsinghua.edu.cn/simple
    }
    $ErrorActionPreference = $prevEAP
    Write-Good "Core dependencies installed"

    Write-Step "Installing optional dependencies (requirements-optional.txt)..."
    $prevEAP = $ErrorActionPreference; $ErrorActionPreference = "Continue"
    & $VenvPython -m pip install -r "$BaseDir\requirements-optional.txt"
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "Some optional dependencies failed — voice/file features may be limited"
    }
    $ErrorActionPreference = $prevEAP
    Write-Good "Optional dependencies installed"

    Write-Step "Installing Cow CLI (pip install -e .)..."
    $prevEAP = $ErrorActionPreference; $ErrorActionPreference = "Continue"
    & $VenvPython -m pip install -e $BaseDir
    $ErrorActionPreference = $prevEAP
    Write-Good "Cow CLI installed"

    if ($Dev) {
        Write-Step "Installing dev dependencies..."
        & $VenvPython -m pip install pytest pytest-asyncio pytest-cov
        Write-Good "Dev dependencies installed"
    }
}

function Install-Browser {
    Write-Step "Installing browser automation tools..."
    & $VenvPython -m pip install playwright
    & $VenvPython -m playwright install chromium
    Write-Good "Browser tools installed (Chromium + Playwright)"
}

# ── clone project ───────────────────────────────────────────────────
function Clone-Project {
    if ($IsProjectDir) {
        Write-Good "Already in project directory: $BaseDir"
        return
    }

    $targetDir = Join-Path (Get-Location) "cowagent"
    if (Test-Path $targetDir) {
        Write-Warn "Directory '$targetDir' already exists. Using it."
        Set-Location $targetDir
        $script:BaseDir = $targetDir
        $script:IsProjectDir = $true
        return
    }

    Write-Step "Cloning project..."
    $cloneOk = $false

    # Try GitHub first
    try {
        Invoke-WebRequest -Uri "https://github.com" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop | Out-Null
        Write-Step "GitHub reachable, cloning..."
        $prevEAP = $ErrorActionPreference; $ErrorActionPreference = "Continue"
        git clone --depth 10 "https://github.com/18279663710la-web/cowagent.git" $targetDir
        if ($LASTEXITCODE -eq 0) { $cloneOk = $true }
        $ErrorActionPreference = $prevEAP
    } catch {
        Write-Warn "GitHub not reachable, trying Gitee mirror..."
    }

    if (-not $cloneOk) {
        Write-Step "Cloning from Gitee mirror..."
        $prevEAP = $ErrorActionPreference; $ErrorActionPreference = "Continue"
        git clone --depth 10 "https://gitee.com/zhayujie/CowAgent.git" $targetDir
        if ($LASTEXITCODE -eq 0) { $cloneOk = $true }
        $ErrorActionPreference = $prevEAP
    }

    if (-not $cloneOk) {
        Write-Fail "Clone failed. Please check network and try again."
        exit 1
    }

    Set-Location $targetDir
    $script:BaseDir = $targetDir
    $script:IsProjectDir = $true
    Write-Good "Project cloned to: $BaseDir"
}

# ── verify ──────────────────────────────────────────────────────────
function Test-Setup {
    Write-Step "Verifying installation..."
    $allOk = $true

    Write-Host ""
    Write-Host "  Python:      $(& $VenvPython --version 2>&1)"
    Write-Host "  pip:         $(& $VenvPython -m pip --version 2>&1)"
    Write-Host "  Git:         $(try { & git --version } catch { 'NOT FOUND' })"
    Write-Host "  ffmpeg:      $(try { (& ffmpeg -version | Select-Object -First 1) } catch { 'NOT FOUND' })"

    if (Test-Command cow) {
        Write-Host "  cow CLI:     $(Get-Command cow).Source"
    } else {
        $scriptsDir = & $VenvPython -c "import sysconfig; print(sysconfig.get_path('scripts'))" 2>$null
        Write-Warn "  cow CLI:     NOT IN PATH (check $scriptsDir)"
    }

    # Quick import test
    try {
        & $VenvPython -c "import requests, yaml, dotenv; print('  Core libs:   OK')"
    } catch {
        Write-Warn "  Core libs:   Some imports failed: $_"
        $allOk = $false
    }

    Write-Host ""
    if ($allOk) { Write-Good "All checks passed!" }
    return $allOk
}

# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════

Clear-Host
Write-Host ""
Write-Host "  ╔══════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "  ║     CowAgent Environment Setup            ║" -ForegroundColor Cyan
Write-Host "  ║     Windows Edition                       ║" -ForegroundColor Cyan
Write-Host "  ╚══════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Detect if we're already in the project
$script:BaseDir = $PWD.Path
$script:IsProjectDir = (Test-Path "$BaseDir\app.py") -and (Test-Path "$BaseDir\config-template.json")

# Step 1: System dependencies
if (-not $SkipSystem) {
    Write-Host "── [1/5] System dependencies ──────────────────────"
    if (-not (Test-Admin)) {
        Write-Warn "Not running as Administrator. Some installs may fail."
        Write-Warn "Tip: Right-click PowerShell → 'Run as Administrator'"
        Write-Host ""
    }
    Install-Winget | Out-Null
    Install-Git
    Install-Python
    Install-FFmpeg
    Write-Host ""
}

# Step 2: Clone project
Write-Host "── [2/5] Project source ───────────────────────────"
if (-not $SkipSystem) {
    # Refresh PATH after system installs
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
}
Assert-Python
if (-not $IsProjectDir) {
    Write-Step "Cloning project to ./cowagent ..."
    Clone-Project
}
Write-Host ""

# Step 3: Virtual environment
Write-Host "── [3/5] Python virtual environment ──────────────"
New-Venv
Write-Host ""

# Step 4: Dependencies
Write-Host "── [4/5] Python dependencies ──────────────────────"
Install-PipDeps
Write-Host ""

# Step 5: Browser (optional)
if ($WithBrowser) {
    Write-Host "── [5/5] Browser tools ────────────────────────────"
    Install-Browser
    Write-Host ""
} else {
    Write-Host "── [5/5] Browser tools ────────────────────────────"
    Write-Warn "Skipped. Run with -WithBrowser to install Playwright + Chromium."
    Write-Host ""
}

# Verify
Test-Setup

Write-Host ""
Write-Host "  ┌────────────────────────────────────────────┐" -ForegroundColor Green
Write-Host "  │  Setup complete!                           │" -ForegroundColor Green
Write-Host "  └────────────────────────────────────────────┘" -ForegroundColor Green
Write-Host ""
Write-Host "  Next steps:"
Write-Host "    1. Copy config-template.json to config.json and add your API keys"
Write-Host "    2. Activate venv:  venv\Scripts\Activate.ps1"
Write-Host "    3. Start:          cow start"
Write-Host "    4. Open browser:   http://localhost:9899/chat"
Write-Host ""
Write-Host "  Quick start (skip config, uses interactive wizard):"
Write-Host "    .\scripts\run.ps1"
Write-Host ""
