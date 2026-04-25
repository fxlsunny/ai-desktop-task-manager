"""
桌面任务管家 - 主入口
用法: python main.py
"""
import sys
import os
import threading
import tkinter as tk
from tkinter import messagebox

# 确保脚本目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config as cfg_mod
import autostart
from models import Store
from overlay import Overlay
from manager import ManagerWin
from ai_window import AIChatWin
import alarm

# ── 全局状态 ──────────────────────────────────────────────────
_manager_win = None
_overlay = None
_cfg = None
_store = None
_root = None
_tray_icon = None   # pystray 图标（可选）


# ──────────────────────────────────────────────────────────────
#  系统托盘（使用 pystray 可选；不存在时退化为普通隐藏窗口）
# ──────────────────────────────────────────────────────────────
def _start_tray():
    """尝试启动系统托盘图标（pystray 可选依赖）"""
    global _tray_icon
    try:
        import pystray
        from PIL import Image, ImageDraw

        def _icon_img():
            size = 64
            img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            d.ellipse([4, 4, 60, 60], fill="#4fc3f7")
            d.text((18, 18), "T", fill="#0a0a1a")
            return img

        def _show_mgr(icon, item):
            _root.after(0, _open_manager)

        def _toggle_overlay(icon, item):
            _root.after(0, lambda: _overlay.show() if not _overlay.win.winfo_viewable()
                        else _overlay.hide())

        def _open_ai_tray(icon, item):
            _root.after(0, _open_ai)

        def _shot_tray(icon, item):
            _root.after(0, _quick_screenshot)

        def _quit(icon, item):
            icon.stop()
            _root.after(0, _quit_app)

        menu = pystray.Menu(
            pystray.MenuItem("📋 打开管理器", _show_mgr, default=True),
            pystray.MenuItem("🤖 AI 问答",    _open_ai_tray),
            pystray.MenuItem("📷 截图",        _shot_tray),
            pystray.MenuItem("👁 显示/隐藏悬浮窗", _toggle_overlay),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("❌ 退出", _quit),
        )
        _tray_icon = pystray.Icon("TaskManager", _icon_img(),
                                  "桌面任务管家", menu)
        t = threading.Thread(target=_tray_icon.run, daemon=True)
        t.start()
    except ImportError:
        pass    # 没有 pystray / PIL，跳过托盘


# ──────────────────────────────────────────────────────────────
#  主逻辑
# ──────────────────────────────────────────────────────────────
def _open_manager():
    global _manager_win
    if _manager_win and _manager_win.win.winfo_exists():
        _manager_win.win.lift()
        _manager_win.win.focus_force()
        return
    _manager_win = ManagerWin(_root, _cfg, _store, _on_cfg_saved)


def _open_ai():
    """打开 AI 问答窗口（单例）"""
    AIChatWin.open(_root, _cfg, _store)


def _quick_screenshot():
    """全局热键触发截图 → 保存到 data/img/YYYYMMDD/ → 追加到管理器当前编辑的任务内容"""
    try:
        from screenshot import capture_and_edit
    except Exception as e:
        print(f"[screenshot] 模块加载失败: {e}")
        return

    save_root = cfg_mod.ensure_data_dir(_cfg) / "img"
    save_root.mkdir(parents=True, exist_ok=True)

    hide = []
    if _overlay and hasattr(_overlay, "win"):
        hide.append(_overlay.win)
    if _manager_win and _manager_win.win.winfo_exists() and _manager_win.win.winfo_viewable():
        hide.append(_manager_win.win)

    def _on_shot(path):
        if not path:
            return
        # 若管理器打开且有编辑态，插入到 e_content
        if _manager_win and _manager_win.win.winfo_exists():
            try:
                base = save_root
                from pathlib import Path
                rel = Path(path).resolve().relative_to(base.resolve()).as_posix()
                snippet = f"\n![截图_{Path(path).stem}]({rel})\n"
                _manager_win.e_content.insert("insert", snippet)
                _manager_win.win.lift()
                _manager_win.lbl_edit_hint.config(
                    text=f"  📷 已插入截图：{Path(path).name}", fg="#66bb6a")
                return
            except Exception as e:
                print(f"[screenshot] 插入失败，已仅保存到 {path}: {e}")
        # 否则只提示保存位置
        try:
            from tkinter import messagebox
            messagebox.showinfo("截图已保存",
                                f"已保存到：\n{path}",
                                parent=_root)
        except Exception:
            pass

    capture_and_edit(_root, save_root, _on_shot, hide_windows=hide)


def _start_global_hotkey():
    """可选：注册全局热键 Ctrl+Alt+A 触发截图（依赖 keyboard 库）"""
    try:
        import keyboard
    except ImportError:
        print("[hotkey] 未安装 keyboard 库，全局热键跳过（pip install keyboard 可启用）")
        return

    def _trigger():
        # keyboard 回调线程 ≠ Tk 主线程，要走 after
        _root.after(0, _quick_screenshot)

    try:
        keyboard.add_hotkey("ctrl+alt+a", _trigger)
        print("[hotkey] 已注册全局热键 Ctrl+Alt+A → 截图")
    except Exception as e:
        print(f"[hotkey] 注册失败: {e}")


def _on_cfg_saved(new_cfg: dict):
    """配置保存后的回调：同步自启动 + 刷新悬浮窗 + 重建AI后端"""
    global _cfg
    _cfg = new_cfg
    cfg_mod.save(_cfg)
    autostart.sync(_cfg.get("autostart", False))
    if _overlay:
        _overlay.update_cfg(_cfg)
    # 如果数据目录变了，重新加载任务
    _store.reload(_cfg)
    if _overlay:
        _overlay.refresh()
    if _manager_win and _manager_win.win.winfo_exists():
        _manager_win._load_list()
    # 通知 AI 窗口更新后端
    if AIChatWin._instance and AIChatWin._instance.win.winfo_exists():
        AIChatWin._instance._maybe_rebuild_backend(_cfg)


def _check_alarms():
    """每分钟检测一次闹钟（精确到分）"""
    triggered = _store.pending_alarms()
    if triggered:
        alarm.ring(_root, triggered)
    from datetime import datetime
    now = datetime.now()
    wait_ms = (60 - now.second) * 1000 - now.microsecond // 1000
    if wait_ms < 1000:
        wait_ms = 60000
    _root.after(wait_ms, _check_alarms)


def _quit_app():
    if _overlay:
        cfg_mod.save(_cfg)
    _root.destroy()


def main():
    global _root, _cfg, _store, _overlay

    # 在 Tk 初始化前打开 DPI 感知，截图坐标才会正确
    try:
        from screenshot import _enable_dpi_awareness
        _enable_dpi_awareness()
    except Exception:
        pass

    _root = tk.Tk()
    _root.withdraw()
    _root.title("桌面任务管家")

    # 加载配置 & 数据
    _cfg = cfg_mod.load()
    cfg_mod.ensure_data_dir(_cfg)
    _store = Store(_cfg)

    # 同步自启动注册表
    autostart.sync(_cfg.get("autostart", False))

    # 悬浮窗（传入 quit 回调 + AI 回调 + 截图回调）
    _overlay = Overlay(_root, _cfg, _store, _open_manager,
                       quit_cb=_quit_app, open_ai_cb=_open_ai,
                       screenshot_cb=_quick_screenshot)

    # 系统托盘（可选）
    _start_tray()

    # 全局热键 Ctrl+Alt+A → 截图（可选）
    _start_global_hotkey()

    # 绑定主窗口关闭
    _root.protocol("WM_DELETE_WINDOW", _quit_app)

    # 启动闹钟轮询
    _root.after(5000, _check_alarms)

    # 首次启动打开管理器
    _root.after(300, _open_manager)

    _root.mainloop()


if __name__ == "__main__":
    main()

