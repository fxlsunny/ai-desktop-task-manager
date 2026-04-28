"""
跨平台工具模块
======================================
- beep()             : 系统提示音（Windows winsound / macOS afplay / Linux paplay/aplay 兜底）
- enable_dpi_awareness(): 仅 Windows 生效，其它平台空操作
- IS_WIN / IS_MAC / IS_LINUX: 平台判断常量
- run_at_startup(enable, name, cmd) : Windows 注册表 / macOS LaunchAgents / Linux .desktop
"""
from __future__ import annotations
import os
import sys
import platform
import shutil
import subprocess
from pathlib import Path

# ── 平台判断 ──────────────────────────────────────────────────
IS_WIN   = sys.platform.startswith("win")
IS_MAC   = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")


# ══════════════════════════════════════════════════════════════
# DPI 感知（仅 Windows 有意义）
# ══════════════════════════════════════════════════════════════
def enable_dpi_awareness() -> None:
    if not IS_WIN:
        return
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PER_MONITOR_AWARE
    except Exception:
        try:
            import ctypes
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════
# 提示音 / Bell
# ══════════════════════════════════════════════════════════════
def beep(times: int = 3) -> None:
    """跨平台播放短提示音；任何平台失败都安静兜底，不抛异常。"""
    if IS_WIN:
        try:
            import winsound
            for _ in range(times):
                winsound.Beep(880, 200)
                winsound.Beep(660, 180)
            return
        except Exception:
            pass
    if IS_MAC:
        for _ in range(times):
            try:
                subprocess.run(
                    ["afplay", "/System/Library/Sounds/Glass.aiff"],
                    check=False, timeout=2,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
            except Exception:
                break
        return
    if IS_LINUX:
        # 优先 paplay，再 aplay，再 ASCII bell
        for cand in ("paplay", "aplay"):
            if shutil.which(cand):
                try:
                    subprocess.run(
                        [cand, "/usr/share/sounds/freedesktop/stereo/bell.oga"]
                        if cand == "paplay" else
                        [cand, "/usr/share/sounds/alsa/Front_Center.wav"],
                        check=False, timeout=2,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    )
                    return
                except Exception:
                    continue
    # 最终兜底：ASCII bell
    try:
        for _ in range(times):
            sys.stdout.write("\a")
            sys.stdout.flush()
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════
# 开机自启动：跨平台
# ══════════════════════════════════════════════════════════════
APP_ID    = "DesktopTaskManager"
APP_LABEL = "AI Desktop Task Manager"

# Linux .desktop 路径
_LINUX_AUTOSTART_DIR = Path.home() / ".config" / "autostart"
_LINUX_DESKTOP_FILE  = _LINUX_AUTOSTART_DIR / f"{APP_ID}.desktop"

# macOS LaunchAgent 路径
_MAC_AGENT_DIR  = Path.home() / "Library" / "LaunchAgents"
_MAC_PLIST_FILE = _MAC_AGENT_DIR / f"com.fxlsunny.{APP_ID}.plist"


def _resolve_command() -> tuple[str, list[str]]:
    """返回 (可执行, 参数列表)；优先 pythonw（无控制台窗口）"""
    if getattr(sys, "frozen", False):
        return sys.executable, []
    main_py = str(Path(__file__).resolve().parent / "main.py")
    py = sys.executable
    if IS_WIN:
        # 把 python.exe 替换成 pythonw.exe 以避免控制台
        candidate = py.replace("python.exe", "pythonw.exe")
        if Path(candidate).exists():
            py = candidate
    return py, [main_py]


# ── Windows 注册表 ───────────────────────────────────────────
def _win_enable() -> bool:
    try:
        import winreg
        py, args = _resolve_command()
        cmd = f'"{py}" ' + " ".join(f'"{a}"' for a in args) if args else f'"{py}"'
        with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, APP_ID, 0, winreg.REG_SZ, cmd)
        return True
    except Exception as e:
        print(f"[autostart] win enable failed: {e}")
        return False


def _win_disable() -> bool:
    try:
        import winreg
        with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE) as key:
            try:
                winreg.DeleteValue(key, APP_ID)
            except FileNotFoundError:
                pass
        return True
    except Exception as e:
        print(f"[autostart] win disable failed: {e}")
        return False


def _win_is_enabled() -> bool:
    try:
        import winreg
        with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, APP_ID)
            return True
    except FileNotFoundError:
        return False
    except Exception:
        return False


# ── Linux .desktop ───────────────────────────────────────────
def _linux_enable() -> bool:
    try:
        _LINUX_AUTOSTART_DIR.mkdir(parents=True, exist_ok=True)
        py, args = _resolve_command()
        exec_line = " ".join([py, *args])
        content = (
            "[Desktop Entry]\n"
            "Type=Application\n"
            f"Name={APP_LABEL}\n"
            "Comment=AI Desktop Task Manager\n"
            f"Exec={exec_line}\n"
            "Terminal=false\n"
            "X-GNOME-Autostart-enabled=true\n"
            "Categories=Utility;Office;\n"
        )
        _LINUX_DESKTOP_FILE.write_text(content, encoding="utf-8")
        os.chmod(_LINUX_DESKTOP_FILE, 0o644)
        return True
    except Exception as e:
        print(f"[autostart] linux enable failed: {e}")
        return False


def _linux_disable() -> bool:
    try:
        if _LINUX_DESKTOP_FILE.exists():
            _LINUX_DESKTOP_FILE.unlink()
        return True
    except Exception as e:
        print(f"[autostart] linux disable failed: {e}")
        return False


def _linux_is_enabled() -> bool:
    return _LINUX_DESKTOP_FILE.exists()


# ── macOS LaunchAgents ───────────────────────────────────────
def _mac_enable() -> bool:
    try:
        _MAC_AGENT_DIR.mkdir(parents=True, exist_ok=True)
        py, args = _resolve_command()
        program_args = "".join(
            f"        <string>{x}</string>\n" for x in [py, *args]
        )
        plist = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
            '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
            '<plist version="1.0">\n'
            '  <dict>\n'
            f'    <key>Label</key><string>com.fxlsunny.{APP_ID}</string>\n'
            '    <key>ProgramArguments</key>\n'
            '    <array>\n'
            f'{program_args}'
            '    </array>\n'
            '    <key>RunAtLoad</key><true/>\n'
            '    <key>KeepAlive</key><false/>\n'
            '  </dict>\n'
            '</plist>\n'
        )
        _MAC_PLIST_FILE.write_text(plist, encoding="utf-8")
        # 加载到 launchd（失败也没关系，重启系统后会自动生效）
        try:
            subprocess.run(["launchctl", "unload", str(_MAC_PLIST_FILE)],
                           check=False, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=5)
            subprocess.run(["launchctl", "load", str(_MAC_PLIST_FILE)],
                           check=False, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=5)
        except Exception:
            pass
        return True
    except Exception as e:
        print(f"[autostart] mac enable failed: {e}")
        return False


def _mac_disable() -> bool:
    try:
        if _MAC_PLIST_FILE.exists():
            try:
                subprocess.run(["launchctl", "unload", str(_MAC_PLIST_FILE)],
                               check=False, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, timeout=5)
            except Exception:
                pass
            _MAC_PLIST_FILE.unlink()
        return True
    except Exception as e:
        print(f"[autostart] mac disable failed: {e}")
        return False


def _mac_is_enabled() -> bool:
    return _MAC_PLIST_FILE.exists()


# ── 统一入口 ─────────────────────────────────────────────────
def autostart_enable() -> bool:
    if IS_WIN:   return _win_enable()
    if IS_MAC:   return _mac_enable()
    if IS_LINUX: return _linux_enable()
    return False


def autostart_disable() -> bool:
    if IS_WIN:   return _win_disable()
    if IS_MAC:   return _mac_disable()
    if IS_LINUX: return _linux_disable()
    return False


def autostart_is_enabled() -> bool:
    if IS_WIN:   return _win_is_enabled()
    if IS_MAC:   return _mac_is_enabled()
    if IS_LINUX: return _linux_is_enabled()
    return False


def autostart_sync(enabled: bool) -> None:
    if enabled:
        autostart_enable()
    else:
        autostart_disable()
