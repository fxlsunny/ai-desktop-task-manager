#!/usr/bin/env python3
"""跨平台启动器 — Windows / macOS / Linux 通用

位置：scripts/run.py
项目根：scripts 的上一级目录

功能：
  * 自动定位项目根目录、把 src 加入 sys.path
  * 首次运行：从 config/config.example.json 复制出 config/config.json
  * 在 Windows 上自动转用 pythonw.exe（无终端窗口），可用 --console 强制留控制台
  * 在 macOS / Linux 上直接运行（双击 .command / .sh 时已是 GUI 模式）
  * 自动检测 Python 版本（>= 3.8）
  * 提示安装可选依赖（pillow / pystray / keyboard）
  * 捕获主程序异常并写入 logs/runtime.log（pythonw 静默崩溃必备）
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import traceback
from datetime import datetime
from pathlib import Path

# scripts/run.py → 项目根 = parent.parent
ROOT = Path(__file__).resolve().parent.parent
SRC  = ROOT / "src"
CFG_DIR     = ROOT / "config"
CFG_FILE    = CFG_DIR / "config.json"
CFG_EXAMPLE = CFG_DIR / "config.example.json"
LOG_DIR     = ROOT / "logs"
LOG_FILE    = LOG_DIR / "runtime.log"


# ════════════════════════════════════════════════════════════
#  Pythonw fix — Windows 下用 pythonw.exe 启动时 sys.stdout / sys.stderr
#  都是 None，任何 print() 或 sys.stdout.write() 都会抛
#  AttributeError: 'NoneType' object has no attribute 'write'。
#  这里用一个静默吞掉所有写入的 _NullWriter 兜底。
# ════════════════════════════════════════════════════════════
class _NullWriter:
    def write(self, _s): pass
    def flush(self): pass
    def isatty(self): return False
    def __getattr__(self, _name): return lambda *a, **kw: None


if sys.stdout is None:
    sys.stdout = _NullWriter()
if sys.stderr is None:
    sys.stderr = _NullWriter()


def _check_python() -> None:
    if sys.version_info < (3, 8):
        sys.stderr.write(
            f"[ERROR] Python 3.8+ required, current = {sys.version.split()[0]}\n"
        )
        sys.exit(1)


def _ensure_config() -> None:
    """首次启动：拷贝 config.example.json -> config.json"""
    if CFG_FILE.exists():
        return
    if not CFG_EXAMPLE.exists():
        return
    CFG_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(CFG_EXAMPLE, CFG_FILE)
    sys.stdout.write(
        f"[INFO] 已生成默认配置: {CFG_FILE}\n"
        f"[INFO] Default config created at {CFG_FILE}\n"
    )


def _hint_optional_deps() -> None:
    """检测可选依赖；缺失只提示，不强制安装"""
    miss = []
    for mod, pkg in (("PIL", "pillow"), ("pystray", "pystray")):
        try:
            __import__(mod)
        except ImportError:
            miss.append(pkg)
    if miss:
        sys.stdout.write(
            "[INFO] 可选依赖未安装（不影响启动）: "
            + " ".join(miss) + "\n"
            "        安装命令: python -m pip install " + " ".join(miss) + "\n"
        )


def _windows_relaunch_with_pythonw() -> None:
    """Windows 下，如果用 python.exe 启动，自动转 pythonw.exe（隐藏控制台）"""
    if not sys.platform.startswith("win"):
        return
    if "--console" in sys.argv:
        sys.argv.remove("--console")
        return
    exe = Path(sys.executable)
    if exe.name.lower() == "pythonw.exe":
        return
    candidate = exe.with_name("pythonw.exe")
    if not candidate.exists():
        return
    args = [str(candidate), str(Path(__file__).resolve()), *sys.argv[1:]]
    subprocess.Popen(args, close_fds=True)
    sys.exit(0)


def _setup_crash_log() -> None:
    """把未捕获异常写入 logs/runtime.log，pythonw 静默崩溃也能定位"""
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        return

    def _hook(exc_type, exc_value, exc_tb):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(f"\n[{ts}] ────────── Uncaught Exception ──────────\n")
                f.write(f"Python   : {sys.version}\n")
                f.write(f"Platform : {sys.platform}\n")
                f.write(f"Argv     : {sys.argv}\n")
                traceback.print_exception(exc_type, exc_value, exc_tb, file=f)
                f.write("\n")
        except Exception:
            pass
        traceback.print_exception(exc_type, exc_value, exc_tb)

    sys.excepthook = _hook


def main() -> None:
    _check_python()
    _ensure_config()
    _setup_crash_log()
    _hint_optional_deps()
    _windows_relaunch_with_pythonw()

    sys.path.insert(0, str(SRC))

    os.chdir(ROOT)

    try:
        import main as app_main
        app_main.main()
    except Exception:
        traceback.print_exc()
        if sys.platform.startswith("win"):
            try:
                import tkinter as tk
                from tkinter import messagebox
                rt = tk.Tk(); rt.withdraw()
                messagebox.showerror(
                    "AI Desktop Task Manager - 启动失败",
                    f"程序启动时崩溃。\n\n详情请查看日志:\n{LOG_FILE}\n\n"
                    "或在终端运行 `scripts\\start.bat --console` 查看实时输出。"
                )
                rt.destroy()
            except Exception:
                pass
        sys.exit(1)


if __name__ == "__main__":
    main()
