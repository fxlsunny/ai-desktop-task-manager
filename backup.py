"""
数据备份 / 导入 / 邮件发送模块
======================================
能力：
    export_backup(dest_zip, cfg, include_config=True)
        把 tasks.json + chat_history/ + 可选 config.json 打包成单个 zip
    import_backup(src_zip, cfg, merge=True)
        从 zip 还原数据（默认合并，保留现有任务/对话；覆盖模式会清空旧数据）
    send_backup_email(zip_path, smtp_cfg)
        通过 SMTP/SSL 把备份文件作为附件发送到指定邮箱

设计要点：
- zip 内根目录：tasks.json / chat_history/*.json / config.json / MANIFEST.json
- MANIFEST 记录版本、导出时间、机器名，便于后期兼容
- 合并导入：tasks 按 task_id 去重（导入数据优先级低，不覆盖本地同 id 任务）
            chat_history 按 session_id 去重（同 id 保留 updated_at 较新的一份）
- SMTP 默认用 SSL 465 端口；常用邮箱预设在 COMMON_SMTP 里
- 纯标准库实现（zipfile / json / smtplib / email），无额外依赖
"""
from __future__ import annotations
import json
import os
import platform
import smtplib
import socket
import ssl
import zipfile
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Callable, Optional

BACKUP_VERSION = 1

# 常见邮箱 SMTP 预设（端口均采用 SSL）
COMMON_SMTP = {
    "QQ邮箱":        ("smtp.qq.com",         465),
    "163邮箱":       ("smtp.163.com",        465),
    "126邮箱":       ("smtp.126.com",        465),
    "Gmail":         ("smtp.gmail.com",      465),
    "Outlook/Hotmail": ("smtp-mail.outlook.com", 465),
    "新浪邮箱":       ("smtp.sina.com",       465),
    "Yahoo":         ("smtp.mail.yahoo.com", 465),
}

_BASE_DIR = Path(__file__).resolve().parent
_CFG_FILE = _BASE_DIR / "config.json"


# ─── 路径解析：把数据目录统一从 cfg 里取 ─────────────────────────
def _resolve_data_paths(cfg: dict) -> tuple[Path, Path]:
    """返回 (tasks_json_path, chat_history_dir)

    统一通过 config.ensure_data_dir 解析 cfg['data_dir']，支持相对路径与绝对路径。
    chat_history 随 data_dir 走。
    """
    try:
        import config as _cfg_mod
        data_dir = _cfg_mod.ensure_data_dir(cfg)
    except Exception:
        # 兜底：直接用原值 + 脚本目录
        raw = cfg.get("data_dir") or (_BASE_DIR / "data")
        data_dir = Path(raw)
        if not data_dir.is_absolute():
            data_dir = _BASE_DIR / data_dir
    tasks_path = data_dir / "tasks.json"
    chat_dir   = data_dir / "chat_history"
    return tasks_path, chat_dir


# ═══════════════════════════════════════════════════════════════════
# 导出
# ═══════════════════════════════════════════════════════════════════
def export_backup(
    dest_zip: str | os.PathLike,
    cfg: dict,
    include_config: bool = True,
    on_log: Optional[Callable[[str], None]] = None,
) -> dict:
    """打包导出。返回统计字典：{zip, size, tasks, chats, bytes}"""
    log = on_log or (lambda _m: None)
    dest = Path(dest_zip)
    dest.parent.mkdir(parents=True, exist_ok=True)

    tasks_path, chat_dir = _resolve_data_paths(cfg)

    tasks_count = 0
    chat_count = 0
    total_bytes = 0

    manifest = {
        "version":     BACKUP_VERSION,
        "exported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "machine":     socket.gethostname(),
        "os":          f"{platform.system()} {platform.release()}",
        "python":      platform.python_version(),
        "includes":    [],
    }

    log(f"📦 开始打包 → {dest}")

    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1) tasks.json
        if tasks_path.exists():
            zf.write(tasks_path, arcname="tasks.json")
            try:
                with open(tasks_path, encoding="utf-8") as f:
                    tasks_count = len(json.load(f))
            except Exception:
                tasks_count = 0
            manifest["includes"].append("tasks.json")
            total_bytes += tasks_path.stat().st_size
            log(f"  ✓ tasks.json（{tasks_count} 条任务）")
        else:
            log("  ⚠ 未找到 tasks.json，跳过")

        # 2) chat_history/*.json
        if chat_dir.exists():
            for p in sorted(chat_dir.glob("chat_*.json")):
                zf.write(p, arcname=f"chat_history/{p.name}")
                chat_count += 1
                total_bytes += p.stat().st_size
            manifest["includes"].append(f"chat_history/ ({chat_count})")
            log(f"  ✓ chat_history/（{chat_count} 个会话）")
        else:
            log("  ⚠ 未找到 chat_history 目录，跳过")

        # 3) 可选 config.json（敏感字段自动脱敏）
        if include_config and _CFG_FILE.exists():
            try:
                with open(_CFG_FILE, encoding="utf-8") as f:
                    raw = json.load(f)
                # 脱敏：API Key / 邮箱授权码清空（避免随备份泄漏）
                safe = dict(raw)
                if isinstance(safe.get("ai"), dict):
                    safe["ai"] = dict(safe["ai"])
                    if safe["ai"].get("api_key"):
                        safe["ai"]["api_key"] = ""  # noqa
                if isinstance(safe.get("backup"), dict):
                    safe["backup"] = dict(safe["backup"])
                    if safe["backup"].get("auth_code"):
                        safe["backup"]["auth_code"] = ""
                zf.writestr("config.json", json.dumps(safe, ensure_ascii=False, indent=2))
                manifest["includes"].append("config.json (sanitized)")
                log("  ✓ config.json（已脱敏 API Key / 授权码）")
            except Exception as e:
                log(f"  ⚠ config.json 打包失败：{e}")

        # 4) 清单
        zf.writestr("MANIFEST.json", json.dumps(manifest, ensure_ascii=False, indent=2))

    size = dest.stat().st_size
    log(f"✅ 完成：{dest.name}  ·  {_fmt_size(size)}")
    return {
        "zip":    str(dest),
        "size":   size,
        "tasks":  tasks_count,
        "chats":  chat_count,
        "bytes":  total_bytes,
    }


# ═══════════════════════════════════════════════════════════════════
# 导入
# ═══════════════════════════════════════════════════════════════════
def import_backup(
    src_zip: str | os.PathLike,
    cfg: dict,
    merge: bool = True,
    on_log: Optional[Callable[[str], None]] = None,
) -> dict:
    """从 zip 恢复数据。
    merge=True  合并（推荐，安全）：
        - tasks：按 task_id 去重，本地已存在的 id 保留本地版本
        - chats：按 session_id 去重，保留 updated_at 较新的那份
    merge=False 覆盖：
        - tasks.json 直接替换
        - chat_history 先清空再写入 zip 里的所有会话
    """
    log = on_log or (lambda _m: None)
    src = Path(src_zip)
    if not src.exists():
        raise FileNotFoundError(src)

    tasks_path, chat_dir = _resolve_data_paths(cfg)
    tasks_path.parent.mkdir(parents=True, exist_ok=True)
    chat_dir.mkdir(parents=True, exist_ok=True)

    stat = {"tasks_imported": 0, "tasks_skipped": 0,
            "chats_imported": 0, "chats_skipped": 0}

    log(f"📂 开始恢复 ← {src.name}  ·  模式：{'合并' if merge else '覆盖'}")

    with zipfile.ZipFile(src, "r") as zf:
        names = zf.namelist()

        # 1) tasks.json
        if "tasks.json" in names:
            incoming_tasks = json.loads(zf.read("tasks.json").decode("utf-8"))
            if merge and tasks_path.exists():
                try:
                    with open(tasks_path, encoding="utf-8") as f:
                        local_tasks = json.load(f)
                except Exception:
                    local_tasks = []
                local_ids = {t.get("task_id") for t in local_tasks if isinstance(t, dict)}
                for t in incoming_tasks:
                    if not isinstance(t, dict):
                        continue
                    tid = t.get("task_id")
                    if tid and tid in local_ids:
                        stat["tasks_skipped"] += 1
                        continue
                    local_tasks.append(t)
                    if tid:
                        local_ids.add(tid)
                    stat["tasks_imported"] += 1
                _atomic_write_json(tasks_path, local_tasks)
            else:
                _atomic_write_json(tasks_path, incoming_tasks)
                stat["tasks_imported"] = len(incoming_tasks)
            log(f"  ✓ 任务：新增 {stat['tasks_imported']}  ·  跳过 {stat['tasks_skipped']}")

        # 2) chat_history
        if not merge:
            # 覆盖模式：清空旧会话文件（只清 chat_*.json，不碰其他东西）
            for p in chat_dir.glob("chat_*.json"):
                try:
                    p.unlink()
                except Exception:
                    pass

        for name in names:
            if not name.startswith("chat_history/") or not name.endswith(".json"):
                continue
            fname = Path(name).name
            dest = chat_dir / fname
            incoming = json.loads(zf.read(name).decode("utf-8"))

            if merge and dest.exists():
                try:
                    with open(dest, encoding="utf-8") as f:
                        local = json.load(f)
                    local_t = local.get("updated_at") or local.get("created_at") or ""
                    inc_t = incoming.get("updated_at") or incoming.get("created_at") or ""
                    if inc_t <= local_t:
                        stat["chats_skipped"] += 1
                        continue
                except Exception:
                    pass

            _atomic_write_json(dest, incoming)
            stat["chats_imported"] += 1

        log(f"  ✓ 对话：新增/更新 {stat['chats_imported']}  ·  跳过 {stat['chats_skipped']}")

    log("✅ 恢复完成")
    return stat


def _atomic_write_json(path: Path, data) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


# ═══════════════════════════════════════════════════════════════════
# 邮件发送
# ═══════════════════════════════════════════════════════════════════
def send_backup_email(
    zip_path: str | os.PathLike,
    smtp_cfg: dict,
    on_log: Optional[Callable[[str], None]] = None,
) -> None:
    """通过 SMTP/SSL 发送备份附件到指定邮箱。
    smtp_cfg 必填：host, port, sender, auth_code, recipient
              可选：subject, body, timeout
    """
    log = on_log or (lambda _m: None)
    zp = Path(zip_path)
    if not zp.exists():
        raise FileNotFoundError(zp)

    host     = (smtp_cfg.get("host")      or "").strip()
    port     = int(smtp_cfg.get("port")   or 465)
    sender   = (smtp_cfg.get("sender")    or "").strip()
    auth     = (smtp_cfg.get("auth_code") or "").strip()
    to       = (smtp_cfg.get("recipient") or "").strip() or sender
    subject  = smtp_cfg.get("subject")  or f"[桌面任务管家备份] {zp.name}"
    body     = smtp_cfg.get("body")     or (
        "桌面任务管家数据备份\n"
        f"文件：{zp.name}\n"
        f"大小：{_fmt_size(zp.stat().st_size)}\n"
        f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"来源机器：{socket.gethostname()}\n\n"
        "请妥善保管此附件。在新机器上可通过「管理 → 备份/恢复 → 导入」还原。"
    )
    timeout  = int(smtp_cfg.get("timeout") or 30)

    # 校验
    missing = [k for k, v in [("host", host), ("sender", sender),
                              ("auth_code", auth), ("recipient", to)] if not v]
    if missing:
        raise ValueError(f"SMTP 配置不完整：缺 {', '.join(missing)}")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"]    = sender
    msg["To"]      = to
    msg.set_content(body)
    with open(zp, "rb") as f:
        msg.add_attachment(f.read(),
                           maintype="application",
                           subtype="zip",
                           filename=zp.name)

    log(f"📡 连接 {host}:{port} …")
    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL(host, port, timeout=timeout, context=ctx) as smtp:
        log(f"🔐 登录 {sender}")
        smtp.login(sender, auth)
        log(f"📤 发送到 {to}（附件 {_fmt_size(zp.stat().st_size)}）")
        smtp.send_message(msg)
    log("✅ 邮件发送成功")


# ─── 工具 ─────────────────────────────────────────────────────────
def _fmt_size(n: int) -> str:
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {u}" if u != "B" else f"{n} B"
        n /= 1024
    return f"{n:.1f} TB"


# 默认导出文件名（带时间戳 + 主机名）
def default_zip_name() -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    host = socket.gethostname().replace(" ", "_")
    return f"TaskManager_Backup_{host}_{ts}.zip"
