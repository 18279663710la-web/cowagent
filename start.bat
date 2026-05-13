@echo off
cd /d "%~dp0"

echo ========================================
echo   CowAgent Startup
echo ========================================
echo.

:: Use venv Python if available
set PYTHON=python
if exist "venv\Scripts\python.exe" (
    set PYTHON=venv\Scripts\python.exe
    echo [OK] Using venv Python
) else (
    echo [WARN] venv not found, using system Python
)

%PYTHON% --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found
    pause
    exit /b 1
)

:: --- check if deps already installed ---
if exist ".deps_installed" (
    echo [OK] Dependencies already installed, skipping...
    goto :start_app
)

:: --- install deps ---
echo [1/2] Installing core dependencies...
%PYTHON% -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
if %errorlevel% neq 0 (
    echo [WARN] Tsinghua mirror failed, trying default...
    %PYTHON% -m pip install -r requirements.txt
)

echo [2/2] Installing optional dependencies...
if exist "requirements-optional.txt" (
    %PYTHON% -m pip install tiktoken pydub gTTS edge-tts elevenlabs==1.0.3 dulwich google-generativeai pypdf python-docx openpyxl python-pptx -i https://pypi.tuna.tsinghua.edu.cn/simple 2>nul
    if %errorlevel% neq 0 (
        %PYTHON% -m pip install tiktoken pydub gTTS edge-tts elevenlabs==1.0.3 dulwich google-generativeai pypdf python-docx openpyxl python-pptx 2>nul
    )
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
%PYTHON% app.py

pause
