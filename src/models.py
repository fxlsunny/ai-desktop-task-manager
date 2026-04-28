"""
数据模型与持久化 - 任务 CRUD，JSON 文件存储
支持软删除：deleted=True 保留记录，deleted_at 记录删除时间
"""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import config as cfg_mod

TASKS_FILE = "tasks.json"

PRIORITY_COLORS = {1: "#78909c", 2: "#4fc3f7", 3: "#ffb74d", 4: "#ef5350"}

# 优先级标签 - 兼容旧调用：保留 dict 形态，但也提供 priority_label() 函数
# 旧代码 PRIORITY_LABELS[p] 仍然可用（取中文）；新代码请用 priority_label(p)
PRIORITY_LABELS = {1: "低", 2: "中", 3: "高", 4: "紧急"}

_PRI_KEYS = {1: "pri.low", 2: "pri.mid", 3: "pri.high", 4: "pri.urgent"}


def priority_label(p: int) -> str:
    """根据当前 i18n 语言返回优先级标签"""
    try:
        from i18n import t as _t
        return _t(_PRI_KEYS.get(int(p), "pri.mid"))
    except Exception:
        return PRIORITY_LABELS.get(int(p), "中")


class Task:
    __slots__ = (
        "task_id", "title", "content", "goal", "problem",
        "alarm_time", "alarm_date", "priority", "tags",
        "completed", "progress", "created_at", "updated_at",
        "deleted", "deleted_at",          # 软删除字段
    )

    def __init__(self, title="", content="", goal="", problem="",
                 alarm_time="", alarm_date="", priority=2, tags="",
                 completed=False, progress=0,
                 created_at=None, updated_at=None,
                 task_id=None,
                 deleted=False, deleted_at=""):
        self.task_id    = task_id or uuid.uuid4().hex[:8]
        self.title      = title
        self.content    = content
        self.goal       = goal
        self.problem    = problem
        self.alarm_time = alarm_time    # HH:MM
        self.alarm_date = alarm_date    # YYYY-MM-DD, 空=每天
        self.priority   = priority
        self.tags       = tags
        self.completed  = completed
        self.progress   = max(0, min(100, int(progress)))
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.created_at = created_at or now
        self.updated_at = updated_at or now
        self.deleted    = bool(deleted)
        self.deleted_at = deleted_at or ""

    def to_dict(self) -> dict:
        return {s: getattr(self, s) for s in self.__slots__}

    @classmethod
    def from_dict(cls, d: dict) -> "Task":
        allowed = set(cls.__init__.__code__.co_varnames)
        return cls(**{k: v for k, v in d.items() if k in allowed})

    def touch(self):
        self.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    @property
    def elapsed_days(self) -> int:
        """从创建到今天的天数"""
        try:
            created = datetime.strptime(self.created_at[:10], "%Y-%m-%d")
            return (datetime.now() - created).days
        except Exception:
            return 0

    @property
    def deleted_days(self) -> int:
        """从删除到今天的天数（未删除返回 -1）"""
        if not self.deleted or not self.deleted_at:
            return -1
        try:
            dt = datetime.strptime(self.deleted_at[:10], "%Y-%m-%d")
            return (datetime.now() - dt).days
        except Exception:
            return -1


class Store:
    """任务存储（单例），cfg 字典由外部传入并可热更新"""
    _inst = None

    def __new__(cls, cfg: dict = None):
        if cls._inst is None:
            cls._inst = super().__new__(cls)
            cls._inst._tasks: List[Task] = []
            cls._inst._cfg = cfg or cfg_mod.load()
            cls._inst._load()
        elif cfg is not None:
            cls._inst._cfg = cfg
        return cls._inst

    # ── 内部 ──────────────────────────────────────────────────
    def _fp(self) -> Path:
        return cfg_mod.ensure_data_dir(self._cfg) / TASKS_FILE

    def _load(self):
        fp = self._fp()
        if fp.exists():
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    self._tasks = [Task.from_dict(d) for d in json.load(f)]
            except Exception as e:
                print(f"[Store] 加载失败: {e}")

    def _save(self):
        try:
            with open(self._fp(), "w", encoding="utf-8") as f:
                json.dump([t.to_dict() for t in self._tasks], f,
                          ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Store] 保存失败: {e}")

    # ── 公开 API ─────────────────────────────────────────────
    def reload(self, new_cfg: dict):
        """数据目录变更后重新加载"""
        self._cfg = new_cfg
        self._tasks.clear()
        self._load()

    def all(self) -> List[Task]:
        """返回所有未软删除的任务"""
        return [t for t in self._tasks if not t.deleted]

    def active(self) -> List[Task]:
        """返回未完成且未删除的任务"""
        return [t for t in self._tasks if not t.completed and not t.deleted]

    def deleted(self) -> List[Task]:
        """返回所有已软删除的任务（回收站）"""
        return [t for t in self._tasks if t.deleted]

    def get(self, tid: str) -> Optional[Task]:
        return next((t for t in self._tasks if t.task_id == tid), None)

    def add(self, task: Task):
        self._tasks.append(task)
        self._save()

    def update(self, task: Task):
        for i, t in enumerate(self._tasks):
            if t.task_id == task.task_id:
                task.touch()
                self._tasks[i] = task
                break
        self._save()

    def soft_delete(self, tid: str):
        """软删除：保留记录，标记 deleted=True + 记录删除时间"""
        t = self.get(tid)
        if t:
            t.deleted    = True
            t.deleted_at = datetime.now().strftime("%Y-%m-%d %H:%M")
            t.touch()
            self._save()

    def restore(self, tid: str):
        """从回收站恢复任务"""
        t = self.get(tid)
        if t:
            t.deleted    = False
            t.deleted_at = ""
            t.touch()
            self._save()

    def purge(self, tid: str):
        """永久删除（仅在回收站中使用）"""
        self._tasks = [t for t in self._tasks if t.task_id != tid]
        self._save()

    def purge_all_deleted(self):
        """清空整个回收站"""
        self._tasks = [t for t in self._tasks if not t.deleted]
        self._save()

    def toggle(self, tid: str):
        t = self.get(tid)
        if t:
            t.completed = not t.completed
            t.touch()
            self._save()

    def pending_alarms(self) -> List[Task]:
        """返回当前分钟需要触发的任务"""
        hm  = datetime.now().strftime("%H:%M")
        ymd = datetime.now().strftime("%Y-%m-%d")
        return [
            t for t in self._tasks
            if not t.completed and not t.deleted
            and t.alarm_time == hm
            and (not t.alarm_date or t.alarm_date == ymd)
        ]
