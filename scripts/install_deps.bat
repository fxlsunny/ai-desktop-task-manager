@echo off
chcp 65001 >nul
title Install optional dependencies
cd /d "%~dp0\.."

echo [1/2] Upgrading pip ...
python -m pip install --upgrade pip
if %errorlevel% neq 0 (
    echo [ERROR] Please install Python 3.8+ first:
    echo         https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [2/2] Installing optional deps (pillow / pystray / keyboard) ...
python -m pip install -r requirements.txt

echo.
echo [OK] Optional deps installed. Now you can run scripts\start.bat
pause
