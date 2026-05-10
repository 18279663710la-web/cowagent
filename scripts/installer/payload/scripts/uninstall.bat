@echo off
echo Uninstalling CowAgent...
del /q "%USERPROFILE%\Desktop\CowAgent.lnk" 2>nul
del /q "%USERPROFILE%\Desktop\CowAgent.bat" 2>nul
rmdir /s /q "%~dp0.."
echo CowAgent has been uninstalled.
pause
