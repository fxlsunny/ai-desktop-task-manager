"""
开机自启动管理 - 通过 Windows 注册表 Run 键实现
"""
import sys
import os
import winreg

APP_NAME = "DesktopTaskManager"
RUN_KEY = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"


def _get_exe_path() -> str:
    """返回当前可执行文件路径（支持 .exe 和 .py）"""
    if getattr(sys, "frozen", False):
        # PyInstaller 打包后
        return sys.executable
    else:
        # 直接运行 .py 脚本
        main_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
        return f'"{sys.executable}" "{main_py}"'


def enable():
    """写入注册表，开机自启动"""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY,
                             0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _get_exe_path())
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"[autostart] 写入失败: {e}")
        return False


def disable():
    """删除注册表条目"""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY,
                             0, winreg.KEY_SET_VALUE)
        try:
            winreg.DeleteValue(key, APP_NAME)
        except FileNotFoundError:
            pass
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"[autostart] 删除失败: {e}")
        return False


def is_enabled() -> bool:
    """检查当前是否已设置自启动"""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY,
                             0, winreg.KEY_READ)
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False


def sync(enabled: bool):
    """根据 cfg['autostart'] 同步注册表状态"""
    if enabled:
        enable()
    else:
        disable()
