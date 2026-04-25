@echo off
chcp 65001 >nul
title 桌面任务管家
cd /d "%~dp0\.."

::: 检测 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

::: 首次启动：若 config/config.json 不存在，自动从 config.example.json 拷贝
if not exist "config\config.json" (
    if exist "config\config.example.json" (
        echo 首次启动，正在从 config.example.json 生成 config.json...
        copy /Y "config\config.example.json" "config\config.json" >nul
        echo 已生成 config\config.json，请用记事本填入你的 API Key 后再次启动。
        echo 路径：%cd%\config\config.json
        pause
        exit /b 0
    )
)

echo 正在启动桌面任务管家...
pythonw src\main.py
