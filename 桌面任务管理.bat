@echo off
chcp 65001 >nul
title 桌面任务管家
cd /d "%~dp0"

:: 检测 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

:: 可选：安装 pystray（系统托盘）
:: python -m pip install pystray pillow -q

echo 正在启动桌面任务管家...
pythonw main.py
