"""
AI 聊天历史持久化模块
======================================
- 每个会话 = 一个独立 JSON 文件，保存在 data/chat_history/ 目录下
- 文件名：chat_YYYYMMDD_HHMMSS_<随机4位>.json
- 内容结构：
    {
        "session_id":   "chat_20260417_213200_a8f3",
        "created_at":   "2026-04-17 21:32:00",
        "updated_at":   "2026-04-17 21:35:11",
        "title":        "（由首条用户消息截取前 24 字）",
        "backend":      "OpenAICompatBackend",
        "model":        "hunyuan-turbos-latest",
        "label":        "腾讯混元",
        "messages": [
            {
                "time":   "2026-04-17 21:32:05",
                "role":   "user" | "assistant",
                "model":  "hunyuan-turbos-latest",   # assistant 才填
                "content":"…"
            },
            ...
        ]
    }
- 对外能力：
    HistoryStore.list_sessions()       → 按更新时间倒序
    HistoryStore.load(session_id)      → 读取指定会话
    HistoryStore.delete(session_id)
    HistoryStore.new_session(backend)  → 返回空会话字典并预分配 id
    HistoryStore.append(session, role, content, backend)  → 追加消息并落盘
    HistoryStore.rename(session_id, new_title)
"""
from __future__ import annotations
import json
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

# 目录：与 tasks.json 同级的 data/chat_history/（相对仓库根）
_BASE_DIR = Path(__file__).resolve().parent.parent
_DATA_DIR = _BASE_DIR / "data" / "chat_history"


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _safe_title(text: str, limit: int = 24) -> str:
    """从用户首条消息截取会话标题"""
    text = (text or "").strip().replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text[:limit] if text else "新对话"


def _describe_backend(backend) -> tuple[str, str, str]:
    """返回 (backend_cls, model, label)"""
    if backend is None:
        return ("None", "", "离线")
    cls = type(backend).__name__
    model = getattr(backend, "model", "") or ""
    label = getattr(backend, "label", None) or ""
    if not label:
        if cls == "OllamaBackend":
            label = "Ollama 本地"
        elif cls == "OpenAICompatBackend":
            base = getattr(backend, "base", "") or ""
            label = base.replace("https://", "").replace("http://", "").split("/")[0]
        else:
            label = cls
    return (cls, model, label)


class HistoryStore:
    """聊天历史文件管理器"""

    def __init__(self, base_dir: Optional[Path] = None):
        self.dir = Path(base_dir) if base_dir else _DATA_DIR
        self.dir.mkdir(parents=True, exist_ok=True)

    # ─── 基础 IO ────────────────────────────────────────────
    def _path(self, session_id: str) -> Path:
        return self.dir / f"{session_id}.json"

    def _save(self, session: dict):
        session["updated_at"] = _now_str()
        p = self._path(session["session_id"])
        tmp = p.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(session, f, ensure_ascii=False, indent=2)
        os.replace(tmp, p)

    def load(self, session_id: str) -> Optional[dict]:
        p = self._path(session_id)
        if not p.exists():
            return None
        try:
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def delete(self, session_id: str) -> bool:
        p = self._path(session_id)
        if p.exists():
            try:
                p.unlink()
                return True
            except Exception:
                return False
        return False

    # ─── 列表 ───────────────────────────────────────────────
    def list_sessions(self) -> list[dict]:
        """按 updated_at 倒序返回摘要列表：
            [{session_id, title, updated_at, created_at, msg_count, label, model}, ...]
        """
        out = []
        for p in self.dir.glob("chat_*.json"):
            try:
                with open(p, encoding="utf-8") as f:
                    d = json.load(f)
            except Exception:
                continue
            out.append({
                "session_id": d.get("session_id") or p.stem,
                "title":      d.get("title") or "新对话",
                "created_at": d.get("created_at", ""),
                "updated_at": d.get("updated_at", ""),
                "msg_count":  len(d.get("messages", [])),
                "label":      d.get("label", ""),
                "model":      d.get("model", ""),
            })
        out.sort(key=lambda x: x["updated_at"] or x["created_at"], reverse=True)
        return out

    # ─── 新建 ───────────────────────────────────────────────
    def new_session(self, backend=None) -> dict:
        cls, model, label = _describe_backend(backend)
        now = datetime.now()
        sid = "chat_" + now.strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:4]
        session = {
            "session_id": sid,
            "created_at": _now_str(),
            "updated_at": _now_str(),
            "title":      "新对话",
            "backend":    cls,
            "model":      model,
            "label":      label,
            "messages":   [],
        }
        # 空会话不立即落盘，等首条消息后 append 时再写
        return session

    # ─── 追加消息 ───────────────────────────────────────────
    def append(self, session: dict, role: str, content: str, backend=None) -> dict:
        """向会话追加一条消息并落盘。role: 'user' | 'assistant' """
        cls, model, label = _describe_backend(backend)
        entry = {
            "time":    _now_str(),
            "role":    role,
            "content": content,
        }
        if role == "assistant":
            entry["model"] = model
            entry["label"] = label
        session.setdefault("messages", []).append(entry)

        # 首条用户消息 → 自动生成标题
        if role == "user" and (not session.get("title") or session["title"] == "新对话"):
            session["title"] = _safe_title(content)

        # 同步当前后端
        if backend is not None:
            session["backend"] = cls
            session["model"]   = model
            session["label"]   = label

        self._save(session)
        return session

    def rename(self, session_id: str, new_title: str) -> bool:
        s = self.load(session_id)
        if not s:
            return False
        s["title"] = _safe_title(new_title, limit=40)
        self._save(s)
        return True
