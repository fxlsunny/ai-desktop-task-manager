#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────
# 一键安装可选依赖 — Linux / macOS
# Install optional dependencies — Linux / macOS
# ──────────────────────────────────────────────────────────
# 位置 / Location: scripts/install_deps.sh
# ──────────────────────────────────────────────────────────
set -e
cd "$(dirname "$0")/.."

if command -v python3 >/dev/null 2>&1; then
    PY=python3
else
    PY=python
fi

echo "[1/3] 升级 pip ..."
"$PY" -m pip install --upgrade pip

echo "[2/3] 安装可选依赖（pillow / pystray / keyboard）..."
"$PY" -m pip install -r requirements.txt

echo "[3/3] 检查 Tkinter ..."
if ! "$PY" -c "import tkinter" >/dev/null 2>&1; then
    echo
    echo "[WARN] Tkinter 未检测到，请按系统包管理器安装："
    echo "       Ubuntu/Debian : sudo apt install python3-tk"
    echo "       Fedora        : sudo dnf install python3-tkinter"
    echo "       Arch / Manjaro: sudo pacman -S tk"
    echo "       macOS         : brew install python-tk"
fi

echo
echo "[OK] 可选依赖安装完成。现在可以运行 ./scripts/start.sh 启动了。"
