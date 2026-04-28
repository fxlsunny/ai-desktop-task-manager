@echo off
chcp 65001 >nul
title AI Desktop Task Manager

REM ----------------------------------------------------------------------
REM  scripts/start.bat   (chdir to project root = scripts/..)
REM ----------------------------------------------------------------------
cd /d "%~dp0\.."

REM ----------------------------------------------------------------------
REM  Parse args:  --console / -c   keep terminal open and show real logs
REM ----------------------------------------------------------------------
set CONSOLE=0
for %%A in (%*) do (
    if /I "%%~A"=="--console" set CONSOLE=1
    if /I "%%~A"=="-c"        set CONSOLE=1
)

REM ----------------------------------------------------------------------
REM  Pick interpreter:  pythonw (silent) by default; python in console mode
REM ----------------------------------------------------------------------
set PY=python
if "%CONSOLE%"=="0" (
    where pythonw >nul 2>&1
    if %errorlevel% equ 0 set PY=pythonw
)

REM ----------------------------------------------------------------------
REM  Sanity checks
REM ----------------------------------------------------------------------
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python 3.8+ is required but not found in PATH.
    echo         Please install Python 3.8 or newer:
    echo         https://www.python.org/downloads/
    echo         Remember to check "Add Python to PATH" during install.
    pause
    exit /b 1
)

python -c "import tkinter" >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Tkinter is missing. Reinstall Python and check the
    echo         "tcl/tk and IDLE" component in the installer.
    pause
    exit /b 1
)

REM ----------------------------------------------------------------------
REM  Launch
REM    - silent  : 'start ""' detaches pythonw so cmd exits immediately and
REM                pythonw becomes an independent GUI process. This is also
REM                required to dodge the Microsoft-Store Python sandbox bug
REM                that kills child pythonw when its launching cmd exits.
REM    - console : block on python so logs stream live in this window.
REM ----------------------------------------------------------------------
if "%CONSOLE%"=="1" (
    echo ============================================================
    echo  AI Desktop Task Manager  -  Console Mode
    echo  Logs will be printed here. Close window to terminate.
    echo ============================================================
    %PY% scripts\run.py --console
    echo.
    echo ============================================================
    echo  Program exited. Press any key to close this window.
    pause >nul
) else (
    REM PowerShell Start-Process -WindowStyle Hidden 是最彻底的 detach 启动方式：
    REM   - 子进程获得全新 console，不再继承父 cmd
    REM   - 设 WindowStyle Hidden 让它无任何窗口闪现
    REM   - 这是绕过 Microsoft Store Python 沙盒杀进程 bug 的最稳路径
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%PY%' -ArgumentList 'scripts\run.py' -WindowStyle Hidden -WorkingDirectory '%CD%'"
)
