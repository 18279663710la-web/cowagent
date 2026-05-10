#!/bin/bash
set -e
# ═════════════════════════════════════════════════════════════════════
# CowAgent one-click environment setup for macOS / Linux
# ═════════════════════════════════════════════════════════════════════
#
# Web download & run:
#   bash <(curl -fsSL https://raw.githubusercontent.com/18279663710la-web/cowagent/master/scripts/setup.sh)
#
# Local run:
#   bash scripts/setup.sh
#   bash scripts/setup.sh --with-browser       # also install Playwright + Chromium
#   bash scripts/setup.sh --skip-system         # skip system deps, only Python setup
#   bash scripts/setup.sh --dev                 # install dev/test dependencies too
# ═════════════════════════════════════════════════════════════════════

WITH_BROWSER=false
SKIP_SYSTEM=false
DEV=false

for arg in "$@"; do
    case $arg in
        --with-browser|-b) WITH_BROWSER=true ;;
        --skip-system|-s)  SKIP_SYSTEM=true ;;
        --dev|-d)          DEV=true ;;
        --help|-h)
            echo "Usage: bash setup.sh [--with-browser] [--skip-system] [--dev]"
            exit 0
            ;;
    esac
done

# ── colours ────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

step()  { echo -e "${CYAN}=> $*${NC}"; }
good()  { echo -e "   ${GREEN}[OK]${NC} $*"; }
warn()  { echo -e "   ${YELLOW}[!!]${NC} $*"; }
fail()  { echo -e "   ${RED}[FAIL]${NC} $*"; }

# ── OS detection ────────────────────────────────────────────────────
OS_TYPE=$(uname -s)
IS_MACOS=false
if [[ "$OS_TYPE" == "Darwin" ]]; then IS_MACOS=true; fi

# ── system dependencies ─────────────────────────────────────────────
has_cmd() { command -v "$1" &>/dev/null; }

install_homebrew() {
    if has_cmd brew; then good "Homebrew already installed"; return; fi
    if ! $IS_MACOS; then warn "Not macOS — skipping Homebrew"; return; fi
    step "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" || {
        warn "Homebrew install failed. Please install manually: https://brew.sh"
        return
    }
    # Add brew to PATH for current session
    if [ -f /opt/homebrew/bin/brew ]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [ -f /usr/local/bin/brew ]; then
        eval "$(/usr/local/bin/brew shellenv)"
    fi
    good "Homebrew installed"
}

install_python() {
    if has_cmd python3; then
        local ver
        ver=$(python3 -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')" 2>/dev/null || echo "0")
        local major minor
        major=$(echo "$ver" | cut -d. -f1)
        minor=$(echo "$ver" | cut -d. -f2)
        if [ "$major" = "3" ] && [ "$minor" -ge 9 ] && [ "$minor" -le 13 ]; then
            good "Python $ver already installed ($(which python3))"
            return
        fi
        warn "Python $ver found but not in 3.9-3.13 range."
    fi

    step "Installing Python 3.12..."
    if $IS_MACOS && has_cmd brew; then
        brew install python@3.12
        good "Python 3.12 installed via Homebrew"
    elif has_cmd apt-get; then
        sudo apt-get update -qq && sudo apt-get install -y -qq python3 python3-pip python3-venv
        good "Python installed via apt"
    elif has_cmd yum; then
        sudo yum install -y python3 python3-pip
        good "Python installed via yum"
    else
        fail "Cannot install Python automatically. Please install Python 3.9-3.13 from: https://www.python.org/downloads/"
        exit 1
    fi
}

install_git() {
    if has_cmd git; then good "Git already installed ($(git --version 2>&1))"; return; fi
    step "Installing Git..."
    if $IS_MACOS && has_cmd brew; then
        brew install git
    elif has_cmd apt-get; then
        sudo apt-get update -qq && sudo apt-get install -y -qq git
    elif has_cmd yum; then
        sudo yum install -y git
    else
        fail "Cannot install Git. Please install from: https://git-scm.com"
        exit 1
    fi
    good "Git installed"
}

install_ffmpeg() {
    if has_cmd ffmpeg; then good "ffmpeg already installed ($(ffmpeg -version 2>&1 | head -1))"; return; fi
    step "Installing ffmpeg..."
    if $IS_MACOS && has_cmd brew; then
        brew install ffmpeg
    elif has_cmd apt-get; then
        sudo apt-get update -qq && sudo apt-get install -y -qq ffmpeg
    elif has_cmd yum; then
        sudo yum install -y ffmpeg-free 2>/dev/null || sudo yum install -y ffmpeg
    else
        warn "Cannot install ffmpeg automatically. Voice features won't work."
        return
    fi
    good "ffmpeg installed"
}

# ── Python detection ────────────────────────────────────────────────
PYTHON_CMD=""
PYTHON_VERSION=""

detect_python() {
    for cmd in python3 python python3.12 python3.11 python3.10 python3.9; do
        if has_cmd "$cmd"; then
            local ver
            ver=$($cmd -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')" 2>/dev/null || echo "0")
            local major minor
            major=$(echo "$ver" | cut -d. -f1)
            minor=$(echo "$ver" | cut -d. -f2)
            if [ "$major" = "3" ] && [ "$minor" -ge 9 ] && [ "$minor" -le 13 ]; then
                PYTHON_CMD=$cmd
                PYTHON_VERSION=$ver
                good "Python $ver detected: $(which $PYTHON_CMD)"
                return 0
            fi
        fi
    done
    fail "Python 3.9-3.13 not found. Run without --skip-system to install it."
    exit 1
}

# ── clone project ───────────────────────────────────────────────────
clone_project() {
    if $IS_PROJECT_DIR; then
        good "Already in project directory: $BASE_DIR"
        return
    fi

    local target_dir="$PWD/cowagent"
    if [ -d "$target_dir" ]; then
        warn "Directory '$target_dir' already exists. Using it."
        cd "$target_dir"
        BASE_DIR=$(pwd)
        IS_PROJECT_DIR=true
        return
    fi

    step "Cloning project..."
    local clone_ok=false

    if curl -sI --connect-timeout 5 --max-time 10 https://github.com > /dev/null 2>&1; then
        step "GitHub reachable, cloning..."
        git clone --depth 10 "https://github.com/18279663710la-web/cowagent.git" "$target_dir" 2>&1 && clone_ok=true
    fi

    if ! $clone_ok; then
        step "Trying Gitee mirror..."
        git clone --depth 10 "https://gitee.com/zhayujie/CowAgent.git" "$target_dir" 2>&1 && clone_ok=true
    fi

    if ! $clone_ok; then
        fail "Clone failed. Please check your network."
        exit 1
    fi

    cd "$target_dir"
    BASE_DIR=$(pwd)
    IS_PROJECT_DIR=true
    good "Project cloned to: $BASE_DIR"
}

# ── Python environment ──────────────────────────────────────────────
setup_venv() {
    local venv_dir="$BASE_DIR/venv"
    if [ -d "$venv_dir" ]; then
        good "Virtual environment already exists: $venv_dir"
    else
        step "Creating virtual environment..."
        $PYTHON_CMD -m venv "$venv_dir"
        good "Virtual environment created"
    fi
    source "$venv_dir/bin/activate"
    good "Virtual environment activated"
    pip install --upgrade pip -q 2>&1 | tail -1
}

install_pip_deps() {
    step "Installing core dependencies (requirements.txt)..."
    set +e
    pip install -r "$BASE_DIR/requirements.txt"
    local ec=$?
    set -e
    if [ $ec -ne 0 ]; then
        warn "Retrying with Tsinghua mirror..."
        pip install -r "$BASE_DIR/requirements.txt" -i https://pypi.tuna.tsinghua.edu.cn/simple
    fi
    good "Core dependencies installed"

    step "Installing optional dependencies (requirements-optional.txt)..."
    set +e
    pip install -r "$BASE_DIR/requirements-optional.txt"
    if [ $? -ne 0 ]; then
        warn "Some optional dependencies failed — voice/file features may be limited"
    fi
    set -e
    good "Optional dependencies installed"

    step "Installing Cow CLI (pip install -e .)..."
    pip install -e "$BASE_DIR" -q
    good "Cow CLI installed"

    if $DEV; then
        step "Installing dev dependencies..."
        pip install pytest pytest-asyncio pytest-cov
        good "Dev dependencies installed"
    fi
}

install_browser() {
    step "Installing browser automation tools..."
    pip install playwright
    playwright install chromium
    good "Browser tools installed (Chromium + Playwright)"
}

# ── verify ──────────────────────────────────────────────────────────
verify_setup() {
    step "Verifying installation..."
    echo ""
    echo "  Python:      $(python3 --version 2>&1)"
    echo "  pip:         $(pip --version 2>&1)"
    echo "  Git:         $(git --version 2>&1 || echo 'NOT FOUND')"
    echo "  ffmpeg:      $(ffmpeg -version 2>&1 | head -1 || echo 'NOT FOUND')"
    echo "  cow CLI:     $(which cow 2>/dev/null || echo 'NOT IN PATH')"

    if python3 -c "import requests, yaml, dotenv" 2>/dev/null; then
        echo "  Core libs:   OK"
    else
        warn "  Core libs:   Some imports failed"
    fi
    echo ""
    good "Verification complete"
}

# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════

clear 2>/dev/null || true
echo ""
echo -e "${CYAN}  ╔══════════════════════════════════════════╗"
echo -e "  ║     CowAgent Environment Setup            ║"
echo -e "  ║     macOS / Linux Edition                  ║"
echo -e "  ╚══════════════════════════════════════════╝${NC}"
echo ""

# Detect project directory
BASE_DIR=$(cd "$(dirname "$0")/.." 2>/dev/null && pwd || echo "$PWD")
IS_PROJECT_DIR=false
[ -f "$BASE_DIR/app.py" ] && [ -f "$BASE_DIR/config-template.json" ] && IS_PROJECT_DIR=true
if ! $IS_PROJECT_DIR; then
    BASE_DIR="$PWD"
    [ -f "$BASE_DIR/app.py" ] && [ -f "$BASE_DIR/config-template.json" ] && IS_PROJECT_DIR=true
fi

# Step 1: System
if ! $SKIP_SYSTEM; then
    echo -e "${BOLD}── [1/5] System dependencies ──────────────────────${NC}"
    install_homebrew
    install_git
    install_python
    install_ffmpeg
    echo ""
fi

# Step 2: Project
echo -e "${BOLD}── [2/5] Project source ───────────────────────────${NC}"
detect_python
if ! $IS_PROJECT_DIR; then
    step "Cloning project to ./cowagent ..."
    clone_project
fi
echo ""

# Step 3: venv
echo -e "${BOLD}── [3/5] Python virtual environment ──────────────${NC}"
setup_venv
echo ""

# Step 4: pip deps
echo -e "${BOLD}── [4/5] Python dependencies ──────────────────────${NC}"
install_pip_deps
echo ""

# Step 5: Browser
echo -e "${BOLD}── [5/5] Browser tools ────────────────────────────${NC}"
if $WITH_BROWSER; then
    install_browser
else
    warn "Skipped. Run with --with-browser to install Playwright + Chromium."
fi
echo ""

# Verify
verify_setup

echo ""
echo -e "${GREEN}  ┌────────────────────────────────────────────┐"
echo -e "  │  Setup complete!                           │"
echo -e "  └────────────────────────────────────────────┘${NC}"
echo ""
echo "  Next steps:"
echo "    1. cp config-template.json config.json  # add your API keys"
echo "    2. source venv/bin/activate"
echo "    3. cow start"
echo "    4. Open browser: http://localhost:9899/chat"
echo ""
echo "  Quick start (interactive config wizard):"
echo "    bash run.sh"
echo ""
