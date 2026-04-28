"""
开机自启动管理 - 兼容入口
====================================
本文件保留旧 API（enable / disable / is_enabled / sync）以维持向下兼容；
真正的跨平台实现已经迁移到 ``platform_utils``。

平台支持：
- Windows: HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run
- macOS:   ~/Library/LaunchAgents/com.fxlsunny.DesktopTaskManager.plist
- Linux:   ~/.config/autostart/DesktopTaskManager.desktop
"""
from platform_utils import (
    autostart_enable,
    autostart_disable,
    autostart_is_enabled,
    autostart_sync,
    APP_ID as APP_NAME,
)

# ── 旧 API 透传 ───────────────────────────────────────────────
def enable() -> bool:     return autostart_enable()
def disable() -> bool:    return autostart_disable()
def is_enabled() -> bool: return autostart_is_enabled()
def sync(enabled: bool) -> None: autostart_sync(enabled)

__all__ = ["APP_NAME", "enable", "disable", "is_enabled", "sync"]
