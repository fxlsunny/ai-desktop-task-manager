#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────
# AI Desktop Task Manager — Linux / macOS launcher
# ──────────────────────────────────────────────────────────
# 位置 / Location: scripts/start.sh
# 用法 / Usage:
#   ./scripts/start.sh             # 后台静默启动（推荐）
#   ./scripts/start.sh --console   # 前台启动，能看 print 输出
# ──────────────────────────────────────────────────────────
set -e

# 切换到项目根目录（scripts/.. = repo root）
cd "$(dirname "$0")/.."

# 1. 选 Python 解释器
if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    echo "[ERROR] Python 3.8+ is required but not found in PATH"
    echo "        macOS: brew install python@3.12"
    echo "        Ubuntu/Debian: sudo apt install python3 python3-tk"
    echo "        Fedora:        sudo dnf install python3 python3-tkinter"
    exit 1
fi

# 2. 检查 Tkinter
if ! "$PY" -c "import tkinter" >/dev/null 2>&1; then
    echo "[ERROR] Tkinter is missing. Please install:"
    echo "        macOS: brew install python-tk"
    echo "        Ubuntu/Debian: sudo apt install python3-tk"
    echo "        Fedora:        sudo dnf install python3-tkinter"
    exit 1
fi

# 3. 启动
if [[ "$1" == "--console" || "$1" == "-c" ]]; then
    exec "$PY" scripts/run.py --console
else
    nohup "$PY" scripts/run.py >/dev/null 2>&1 &
    disown
    echo "[OK] AI Desktop Task Manager launched (pid=$!)"
fi
