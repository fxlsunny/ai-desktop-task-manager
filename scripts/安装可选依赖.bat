@echo off
chcp 65001 >nul
title 安装可选依赖
cd /d "%~dp0\.."
echo 正在安装可选依赖...
echo.
echo [1/3] pystray - 系统托盘图标
echo [2/3] pillow  - 截图 / 图片预览
echo [3/3] keyboard - 全局热键 Ctrl+Alt+A 发起截图
echo.
python -m pip install pystray pillow keyboard --quiet
echo.
echo 完成！可运行 scripts\桌面任务管理.bat 启动程序。
pause
