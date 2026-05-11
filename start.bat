@echo off
cd /d "%~dp0"

echo ========================================
echo   CowAgent Startup
echo ========================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found
    pause
    exit /b 1
)

:: --- check if deps already installed ---
set DEPS_OK=0
if exist ".deps_installed" (
    set DEPS_OK=1
    echo [OK] Dependencies already installed, skipping...
    goto :start_app
)

:: --- install deps ---
echo [1/2] Installing core dependencies...
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
if %errorlevel% neq 0 (
    echo [WARN] Tsinghua mirror failed, trying default...
    pip install -r requirements.txt
)

echo [2/2] Installing optional dependencies...
if exist "requirements-optional.txt" (
    pip install -r requirements-optional.txt -i https://pypi.tuna.tsinghua.edu.cn/simple 2>nul
    if %errorlevel% neq 0 (
        pip install -r requirements-optional.txt 2>nul
    )
)

if exist "setup.py" (
    pip install -e . -i https://pypi.tuna.tsinghua.edu.cn/simple 2>nul
)

echo installed > .deps_installed
echo [OK] All dependencies installed.
echo.

:start_app
:: --- start app ---
echo Starting backend server...
echo.

:: Open browser after 3 seconds
start "" cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:9899"

:: Run
python app.py

pause
