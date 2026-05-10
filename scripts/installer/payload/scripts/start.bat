@echo off
cd /d "%~dp0..\cowagent"
start "" /b "%~dp0..\python\python.exe" app.py
timeout /t 3 /nobreak >nul
start http://localhost:9899/chat
