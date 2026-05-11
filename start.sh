#!/bin/bash
set -e

cd "$(dirname "$0")"

echo "========================================"
echo "  CowAgent Startup"
echo "========================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 not found. Please install Python 3.10+ first."
    exit 1
fi

# --- check if deps already installed ---
if [ -f ".deps_installed" ]; then
    echo "[OK] Dependencies already installed, skipping..."
else
    # --- install deps ---
    echo "[1/2] Installing core dependencies..."
    pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple 2>/dev/null || \
    pip3 install -r requirements.txt

    if [ -f "requirements-optional.txt" ]; then
        echo "[2/2] Installing optional dependencies..."
        pip3 install -r requirements-optional.txt -i https://pypi.tuna.tsinghua.edu.cn/simple 2>/dev/null || \
        pip3 install -r requirements-optional.txt 2>/dev/null || true
    fi

    if [ -f "setup.py" ]; then
        pip3 install -e . 2>/dev/null || true
    fi

    echo "installed" > .deps_installed
    echo "[OK] All dependencies installed."
    echo ""
fi

# --- start app ---
echo "Starting backend server..."
echo ""

# Open browser after 3 seconds
sleep 3 && open http://localhost:9899 2>/dev/null || \
sleep 3 && xdg-open http://localhost:9899 2>/dev/null || true &

python3 app.py
