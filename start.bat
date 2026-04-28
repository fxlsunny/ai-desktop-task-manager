@echo off
REM Convenience launcher — forwards to scripts\start.bat
REM 便捷入口：双击此文件即可启动，等价于运行 scripts\start.bat
cd /d "%~dp0"
call "scripts\start.bat" %*
