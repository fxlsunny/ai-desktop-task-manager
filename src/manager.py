"""
任务管理主界面 - 增删改查 + 回收站 + 设置
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import re
from datetime import datetime
from pathlib import Path

import config as cfg_mod
import i18n
from i18n import t as _t
from models import Store, Task, priority_label, PRIORITY_COLORS

# 优先级元数据（值, 颜色, i18n key 标签, i18n key 说明）
PRI_META_RAW = [
    (4, "#ef5350", "pri.urgent", "pri.urgent.tip"),
    (3, "#ffb74d", "pri.high",   "pri.high.tip"),
    (2, "#4fc3f7", "pri.mid",    "pri.mid.tip"),
    (1, "#78909c", "pri.low",    "pri.low.tip"),
]


def _pri_meta():
    """返回 [(val, lang_label, color, lang_tip), ...]，每次调用按当前语言渲染"""
    return [(v, _t(lk), c, _t(tk)) for v, c, lk, tk in PRI_META_RAW]

BG      = "#1e1e2e"
BG2     = "#2a2a3e"
BG3     = "#0f3460"
ACC     = "#4fc3f7"
FG      = "#e0e0e0"
FG_DIM  = "#9e9e9e"
RED     = "#ef5350"
GREEN   = "#66bb6a"
YELLOW  = "#ffd54f"
PURPLE  = "#7c4dff"


def _btn(parent, text, command, danger=False, **kw):
    """统一风格按钮"""
    defaults = dict(
        bg=BG3 if not danger else "#3e1a1a",
        fg=ACC if not danger else RED,
        relief="flat", cursor="hand2",
        font=("Microsoft YaHei UI", 10),
        activebackground=ACC if not danger else RED,
        activeforeground="#000" if not danger else "#fff",
        padx=8, pady=3,
    )
    defaults.update(kw)
    return tk.Button(parent, text=text, command=command, **defaults)


class ManagerWin:
    """任务管理窗口（可多次打开/关闭）"""

    def __init__(self, root: tk.Tk, cfg: dict, store: Store, on_save_cfg):
        self.root       = root
        self.cfg        = cfg
        self.store      = store
        self.on_save_cfg = on_save_cfg
        self._edit_task: Task | None = None

        self.win = tk.Toplevel(root)
        self.win.title(_t("manager.title"))
        # ★ 加大默认窗口尺寸，保证右列内容完整显示
        self.win.geometry("980x640")
        self.win.minsize(860, 560)
        self.win.configure(bg=BG)
        self.win.protocol("WM_DELETE_WINDOW", self._close)
        self._apply_theme()
        self._build()
        self._load_list()

    # ─── 主题 ─────────────────────────────────────────────────
    def _apply_theme(self):
        s = ttk.Style(self.win)
        s.theme_use("clam")
        s.configure("TNotebook",      background=BG,  borderwidth=0)
        s.configure("TNotebook.Tab",  background=BG2, foreground="#ccc",
                    padding=[12, 5],  font=("Microsoft YaHei UI", 10))
        s.map("TNotebook.Tab",
              background=[("selected", ACC)],
              foreground=[("selected", "#0a0a1a")])
        s.configure("Treeview",       background="#16213e", foreground=FG,
                    fieldbackground="#16213e", rowheight=26,
                    font=("Microsoft YaHei UI", 10))
        s.configure("Treeview.Heading", background=BG3, foreground=ACC,
                    font=("Microsoft YaHei UI", 10, "bold"))
        s.map("Treeview", background=[("selected", BG3)])
        s.configure("TScrollbar", background=BG2, troughcolor=BG)
        s.configure("TCombobox",  fieldbackground=BG2, background=BG2,
                    foreground=FG, selectbackground=BG3)

    # ─── 主布局 ───────────────────────────────────────────────
    def _build(self):
        self.nb = ttk.Notebook(self.win)
        self.nb.pack(fill="both", expand=True, padx=8, pady=8)

        self.tab_list  = tk.Frame(self.nb, bg=BG)
        self.tab_edit  = tk.Frame(self.nb, bg=BG)
        self.tab_trash = tk.Frame(self.nb, bg=BG)
        self.tab_cfg   = tk.Frame(self.nb, bg=BG)
        self.tab_bkp   = tk.Frame(self.nb, bg=BG)

        self.nb.add(self.tab_list,  text=_t("manager.tab.list"))
        self.nb.add(self.tab_edit,  text=_t("manager.tab.edit"))
        self.nb.add(self.tab_trash, text=_t("manager.tab.trash"))
        self.nb.add(self.tab_cfg,   text=_t("manager.tab.cfg"))
        self.nb.add(self.tab_bkp,   text=_t("manager.tab.bkp"))

        self._build_list_tab()
        self._build_edit_tab()
        self._build_trash_tab()
        self._build_cfg_tab()
        self._build_backup_tab()

    # ══════════════════════════════════════════════════════════
    # Tab 1 – 任务列表
    # ══════════════════════════════════════════════════════════
    def _build_list_tab(self):
        bar = tk.Frame(self.tab_list, bg=BG)
        bar.pack(fill="x", padx=6, pady=(6, 2))

        _btn(bar, _t("manager.btn.new"),    self._new_task).pack(side="left", padx=2)
        _btn(bar, _t("manager.btn.edit"),   self._edit_sel).pack(side="left", padx=2)
        _btn(bar, _t("manager.btn.toggle"), self._toggle_sel).pack(side="left", padx=2)
        _btn(bar, _t("manager.btn.delete"), self._delete_sel, danger=True).pack(side="left", padx=2)

        tk.Label(bar, text="🔍", bg=BG, fg=FG_DIM).pack(side="right")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self._load_list())
        tk.Entry(bar, textvariable=self.search_var, bg=BG2, fg=FG,
                 insertbackground="#fff", relief="flat", width=14,
                 font=("Microsoft YaHei UI", 10)).pack(side="right", padx=4)

        tk.Label(bar, text=_t("manager.filter.label"), bg=BG, fg=FG_DIM,
                 font=("Microsoft YaHei UI", 10)).pack(side="left", padx=(12, 2))

        # 筛选下拉的实际值用 id（all/todo/done/p4/p3/p2/p1）；显示用 i18n 标签
        self._filter_options = [
            ("all",  _t("manager.filter.all")),
            ("todo", _t("manager.filter.todo")),
            ("done", _t("manager.filter.done")),
            ("p4",   _t("pri.urgent")),
            ("p3",   _t("pri.high")),
            ("p2",   _t("pri.mid")),
            ("p1",   _t("pri.low")),
        ]
        self._filter_label_to_id = {lbl: fid for fid, lbl in self._filter_options}
        # 默认显示"待办"
        default_label = _t("manager.filter.todo")
        self.filter_var = tk.StringVar(value=default_label)
        flt = ttk.Combobox(bar, textvariable=self.filter_var, width=10,
                           values=[lbl for _, lbl in self._filter_options],
                           state="readonly", font=("Microsoft YaHei UI", 10))
        flt.pack(side="left")
        flt.bind("<<ComboboxSelected>>", lambda e: self._load_list())

        # Treeview
        cols = ("title","priority","progress","status","elapsed","alarm","tags","created","updated")
        self.tree = ttk.Treeview(self.tab_list, columns=cols,
                                 show="headings", selectmode="browse")
        headers = {
            "title":    (_t("manager.col.title"),    160),
            "priority": (_t("manager.col.priority"),  62),
            "progress": (_t("manager.col.progress"),  58),
            "status":   (_t("manager.col.status"),    64),
            "elapsed":  (_t("manager.col.elapsed"),   62),
            "alarm":    (_t("manager.col.alarm"),    108),
            "tags":     (_t("manager.col.tags"),      80),
            "created":  (_t("manager.col.created"),  110),
            "updated":  (_t("manager.col.updated"),  110),
        }
        for col,(hdr,w) in headers.items():
            self.tree.heading(col, text=hdr, command=lambda c=col: self._sort_by(c))
            anchor = "center" if col in ("priority","progress","status","elapsed") else "w"
            self.tree.column(col, width=w, anchor=anchor, minwidth=40)

        vsb = ttk.Scrollbar(self.tab_list, orient="vertical",   command=self.tree.yview)
        hsb = ttk.Scrollbar(self.tab_list, orient="horizontal",  command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="right",  fill="y")
        hsb.pack(side="bottom", fill="x")
        self.tree.pack(fill="both", expand=True, padx=6, pady=4)

        self.tree.bind("<Double-Button-1>", lambda e: self._edit_sel())
        self.tree.bind("<Button-3>",        self._ctx_menu)

        self.tree.tag_configure("done",   foreground="#4a4a6a")
        self.tree.tag_configure("urgent", foreground=RED,     font=("Microsoft YaHei UI",10,"bold"))
        self.tree.tag_configure("high",   foreground="#ffb74d")
        self.tree.tag_configure("mid",    foreground=ACC)
        self.tree.tag_configure("low",    foreground="#78909c")

        self._sort_col = "priority"
        self._sort_rev = True

    def _sort_by(self, col: str):
        self._sort_rev = (not self._sort_rev) if self._sort_col == col else False
        self._sort_col = col
        self._load_list()

    def _load_list(self):
        self.tree.delete(*self.tree.get_children())
        flt_label = self.filter_var.get()
        flt = self._filter_label_to_id.get(flt_label, "todo")
        kw  = self.search_var.get().strip().lower()
        tasks = self.store.all()   # 不含软删除

        def _match(t: Task) -> bool:
            if flt == "todo" and t.completed:     return False
            if flt == "done" and not t.completed: return False
            if flt == "p4"   and t.priority != 4: return False
            if flt == "p3"   and t.priority != 3: return False
            if flt == "p2"   and t.priority != 2: return False
            if flt == "p1"   and t.priority != 1: return False
            if kw and kw not in (t.title+t.content+t.tags).lower(): return False
            return True

        tasks = [t for t in tasks if _match(t)]
        key_map = {
            "title":   lambda t: t.title,
            "priority":lambda t: t.priority,
            "progress":lambda t: t.progress,
            "status":  lambda t: t.completed,
            "elapsed": lambda t: t.elapsed_days,
            "alarm":   lambda t: t.alarm_time,
            "created": lambda t: t.created_at,
            "updated": lambda t: t.updated_at,
        }
        tasks.sort(key=key_map.get(self._sort_col, lambda t: t.priority),
                   reverse=self._sort_rev)

        for t in tasks:
            alarm_str   = (f"{t.alarm_date} {t.alarm_time}".strip()
                           if t.alarm_date else t.alarm_time)
            status_str  = _t("manager.status.done") if t.completed else _t("manager.status.todo")
            prog_str    = f"{t.progress}%" if t.progress else "—"
            elapsed_str = (_t("overlay.today") if t.elapsed_days == 0
                           else _t("overlay.days", n=t.elapsed_days))
            pri_icon    = {4:"⚠",3:"●",2:"◑",1:"○"}.get(t.priority,"◑")
            pri_str     = f"{pri_icon} {priority_label(t.priority)}"
            tag = ("done" if t.completed
                   else {4:"urgent",3:"high",2:"mid",1:"low"}.get(t.priority,"mid"))
            self.tree.insert("","end", iid=t.task_id, tags=(tag,),
                             values=(t.title, pri_str, prog_str, status_str,
                                     elapsed_str, alarm_str, t.tags,
                                     t.created_at, t.updated_at))

    # 右键菜单
    def _ctx_menu(self, event):
        sel = self.tree.identify_row(event.y)
        if not sel: return
        self.tree.selection_set(sel)
        t = self.store.get(sel)
        if not t: return

        menu = tk.Menu(self.win, tearoff=0, bg=BG, fg=FG,
                       activebackground=BG3, activeforeground=ACC,
                       font=("Microsoft YaHei UI", 10))
        # 进度子菜单
        pm = tk.Menu(menu, tearoff=0, bg=BG, fg=FG,
                     activebackground=BG3, activeforeground=ACC,
                     font=("Microsoft YaHei UI", 10))
        for pct in (0,10,25,50,75,90,100):
            pm.add_command(
                label=f"{'✔ ' if t.progress==pct else '   '}{pct}%",
                command=lambda p=pct,tid=sel: self._quick_progress(tid,p))
        menu.add_cascade(label=_t("manager.ctx.set_progress", pct=t.progress), menu=pm)
        qm = tk.Menu(menu, tearoff=0, bg=BG, fg=FG,
                     activebackground=BG3, activeforeground=ACC,
                     font=("Microsoft YaHei UI", 10))
        for val,lbl,color,tip in _pri_meta():
            qm.add_command(
                label=f"{'✔ ' if t.priority==val else '   '}{lbl} {tip}",
                foreground=color,
                command=lambda v=val,tid=sel: self._quick_priority(tid,v))
        menu.add_cascade(
            label=_t("manager.ctx.set_priority", label=priority_label(t.priority)),
            menu=qm)
        menu.add_separator()
        toggle_lbl = _t("manager.ctx.mark_todo") if t.completed else _t("manager.ctx.mark_done")
        menu.add_command(label=toggle_lbl, command=self._toggle_sel)
        menu.add_separator()
        menu.add_command(label=_t("manager.ctx.edit"),  command=self._edit_sel)
        menu.add_command(label=_t("manager.ctx.trash"), command=self._delete_sel,
                         foreground=RED)
        menu.post(event.x_root, event.y_root)

    def _quick_progress(self, tid, pct):
        t = self.store.get(tid)
        if not t: return
        t.progress = pct
        if pct == 100: t.completed = True
        t.touch(); self.store.update(t)
        self._load_list(); self.on_save_cfg(self.cfg)

    def _quick_priority(self, tid, val):
        t = self.store.get(tid)
        if not t: return
        t.priority = val
        t.touch(); self.store.update(t)
        self._load_list(); self.on_save_cfg(self.cfg)

    # ══════════════════════════════════════════════════════════
    # Tab 2 – 编辑/新建表单
    # ══════════════════════════════════════════════════════════
    def _build_edit_tab(self):
        lbl_s   = dict(bg=BG, fg=FG_DIM, font=("Microsoft YaHei UI", 10), anchor="w")
        entry_s = dict(bg=BG2, fg=FG, insertbackground="#fff",
                       relief="flat", font=("Microsoft YaHei UI", 11))
        pad = dict(padx=10, pady=3)

        # ── ★ 底部按钮行必须最先 pack ─────────────────────────
        btn_row = tk.Frame(self.tab_edit, bg=BG)
        btn_row.pack(side="bottom", fill="x", padx=10, pady=6)

        _btn(btn_row, _t("edit.btn.save"), self._save_task,
             font=("Microsoft YaHei UI",11,"bold"), padx=16, pady=6,
             bg="#0d7377", fg="#fff", activebackground="#14a085",
             activeforeground="#fff").pack(side="left", padx=4)
        _btn(btn_row, _t("edit.btn.clear"), self._clear_form,
             padx=12, pady=6).pack(side="left", padx=4)
        self.lbl_save_msg = tk.Label(btn_row, text="", bg=BG, fg=ACC,
                                     font=("Microsoft YaHei UI", 10))
        self.lbl_save_msg.pack(side="left", padx=8)
        tk.Label(btn_row, text=_t("edit.hint.shortcut"), bg=BG, fg="#555",
                 font=("Microsoft YaHei UI", 9)).pack(side="right", padx=8)

        # ── 编辑状态提示条 ─────────────────────────────────────
        self.lbl_edit_hint = tk.Label(self.tab_edit, text="",
                                      bg=BG3, fg=ACC,
                                      font=("Microsoft YaHei UI", 9),
                                      anchor="w", padx=10, pady=2)
        self.lbl_edit_hint.pack(side="bottom", fill="x")

        # ── 分隔线 ────────────────────────────────────────────
        tk.Frame(self.tab_edit, bg="#333355", height=1).pack(fill="x", padx=8, pady=(4,0))

        # ═══════════════════════════════════════════════════════
        # 左列：文本字段（可扩展）
        # ═══════════════════════════════════════════════════════
        left = tk.Frame(self.tab_edit, bg=BG)
        left.pack(side="left", fill="both", expand=True, padx=(8,4), pady=8)

        tk.Label(left, text=_t("edit.title.label"), **lbl_s).pack(fill="x")
        self.e_title = tk.Entry(left, **entry_s)
        self.e_title.pack(fill="x", **pad)

        content_head = tk.Frame(left, bg=BG)
        content_head.pack(fill="x", pady=(2, 0))
        tk.Label(content_head, text=_t("edit.content.label"), **lbl_s
                 ).pack(side="left")
        tk.Button(content_head, text=_t("edit.btn.expand"),
                  command=self._open_content_editor,
                  bg=BG3, fg=ACC, relief="flat",
                  font=("Microsoft YaHei UI", 9),
                  padx=10, pady=1, cursor="hand2",
                  activebackground=ACC, activeforeground="#fff"
                  ).pack(side="right", padx=4)
        tk.Button(content_head, text=_t("edit.btn.shot"),
                  command=self._quick_screenshot_to_content,
                  bg=PURPLE, fg="#fff", relief="flat",
                  font=("Microsoft YaHei UI", 9, "bold"),
                  padx=10, pady=1, cursor="hand2",
                  activebackground=ACC, activeforeground="#fff"
                  ).pack(side="right", padx=4)
        self.e_content = tk.Text(left, height=5, wrap="word", **entry_s)
        self.e_content.pack(fill="x", **pad)
        self.e_content.bind("<Double-Button-1>",
                            lambda _e: self._open_content_editor())

        tk.Label(left, text=_t("edit.goal.label"), **lbl_s).pack(fill="x")
        self.e_goal = tk.Entry(left, **entry_s)
        self.e_goal.pack(fill="x", **pad)

        tk.Label(left, text=_t("edit.problem.label"), **lbl_s).pack(fill="x")
        self.e_problem = tk.Entry(left, **entry_s)
        self.e_problem.pack(fill="x", **pad)

        tk.Label(left, text=_t("edit.tags.label"), **lbl_s).pack(fill="x")
        self.e_tags = tk.Entry(left, **entry_s)
        self.e_tags.pack(fill="x", **pad)

        # 时间摘要（编辑时显示）
        self.lbl_times = tk.Label(left, text="", bg=BG, fg="#555",
                                  font=("Microsoft YaHei UI", 8), anchor="w")
        self.lbl_times.pack(fill="x", padx=10, pady=(4,0))

        # ═══════════════════════════════════════════════════════
        # 右列：结构化字段 —— 用 Canvas+Scrollbar 保证内容完整显示
        # ═══════════════════════════════════════════════════════
        right_outer = tk.Frame(self.tab_edit, bg=BG, width=260)
        right_outer.pack(side="right", fill="y", padx=(4,8), pady=8)
        right_outer.pack_propagate(False)

        r_canvas = tk.Canvas(right_outer, bg=BG, bd=0,
                             highlightthickness=0, width=244)
        r_vsb = tk.Scrollbar(right_outer, orient="vertical",
                             command=r_canvas.yview, width=5,
                             troughcolor=BG, bg="#444", relief="flat")
        r_canvas.configure(yscrollcommand=r_vsb.set)
        r_vsb.pack(side="right", fill="y")
        r_canvas.pack(side="left", fill="both", expand=True)

        right = tk.Frame(r_canvas, bg=BG)
        _rwin = r_canvas.create_window((0,0), window=right, anchor="nw")
        right.bind("<Configure>", lambda e: r_canvas.configure(
            scrollregion=r_canvas.bbox("all")))
        r_canvas.bind("<Configure>", lambda e:
                      r_canvas.itemconfig(_rwin, width=e.width))
        r_canvas.bind("<MouseWheel>",
                      lambda e: r_canvas.yview_scroll(-1*(e.delta//120),"units"))
        right.bind("<MouseWheel>",
                   lambda e: r_canvas.yview_scroll(-1*(e.delta//120),"units"))

        sep = dict(bg="#333355", height=1)

        tk.Label(right, text=_t("edit.priority.section"), bg=BG, fg=ACC,
                 font=("Microsoft YaHei UI", 10, "bold"), anchor="w").pack(fill="x", padx=6, pady=(8,2))
        self.pri_var = tk.IntVar(value=2)
        for val, lbl_text, color, tip in _pri_meta():
            row_f = tk.Frame(right, bg=BG)
            row_f.pack(fill="x", padx=4, pady=1)
            tk.Radiobutton(
                row_f, text=f"  {lbl_text}",
                variable=self.pri_var, value=val,
                bg=BG, fg=color, selectcolor=BG3,
                activebackground=BG, activeforeground=color,
                font=("Microsoft YaHei UI", 10, "bold"),
                indicatoron=True,
            ).pack(side="left")
            tk.Label(row_f, text=tip, bg=BG, fg="#666",
                     font=("Microsoft YaHei UI", 8)).pack(side="left", padx=4)

        tk.Frame(right, **sep).pack(fill="x", padx=6, pady=(8,4))
        tk.Label(right, text=_t("edit.completed.section"), bg=BG, fg=ACC,
                 font=("Microsoft YaHei UI", 10, "bold"), anchor="w").pack(fill="x", padx=6, pady=(0,2))
        self.completed_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            right, text=_t("edit.completed.checkbox"),
            variable=self.completed_var,
            bg=BG, fg=GREEN, selectcolor=BG3,
            activebackground=BG, activeforeground=GREEN,
            font=("Microsoft YaHei UI", 10),
        ).pack(anchor="w", padx=10)

        tk.Frame(right, **sep).pack(fill="x", padx=6, pady=(8,4))
        prog_hdr = tk.Frame(right, bg=BG)
        prog_hdr.pack(fill="x", padx=6)
        tk.Label(prog_hdr, text=_t("edit.progress.section"), bg=BG, fg=ACC,
                 font=("Microsoft YaHei UI", 10, "bold")).pack(side="left")
        self.lbl_progress = tk.Label(prog_hdr, text="0%", bg=BG,
                                     fg=ACC, font=("Microsoft YaHei UI", 10, "bold"))
        self.lbl_progress.pack(side="right", padx=6)

        # 进度条预览
        self.progress_var = tk.IntVar(value=0)
        prog_track = tk.Frame(right, bg=BG2, height=8)
        prog_track.pack(fill="x", padx=10, pady=(4,0))
        prog_track.pack_propagate(False)
        self.prog_bar = tk.Frame(prog_track, bg=ACC, height=8)
        self.prog_bar.place(x=0, y=0, relheight=1.0, relwidth=0.0)

        self.progress_scale = tk.Scale(
            right, from_=0, to=100, orient="horizontal",
            variable=self.progress_var, bg=BG, fg=FG,
            troughcolor=BG2, highlightthickness=0,
            showvalue=False, sliderlength=14, length=220,
            command=self._update_progress_label,
        )
        self.progress_scale.pack(padx=6, pady=(2,0))

        quick_row = tk.Frame(right, bg=BG)
        quick_row.pack(fill="x", padx=8, pady=(0,2))
        for pct in (0, 25, 50, 75, 100):
            tk.Button(quick_row, text=f"{pct}%",
                      command=lambda p=pct: self._set_progress(p),
                      bg="#1a1a3a", fg=FG_DIM, relief="flat",
                      font=("Microsoft YaHei UI", 8), padx=4, pady=1,
                      cursor="hand2", activebackground=ACC,
                      activeforeground="#000").pack(side="left", padx=1)

        tk.Frame(right, **sep).pack(fill="x", padx=6, pady=(8,4))
        tk.Label(right, text=_t("edit.alarm.section"), bg=BG, fg=ACC,
                 font=("Microsoft YaHei UI", 10, "bold"), anchor="w").pack(fill="x", padx=6, pady=(0,2))

        tk.Label(right, text=_t("edit.alarm.date_label"), bg=BG, fg=FG_DIM,
                 font=("Microsoft YaHei UI", 9), anchor="w").pack(fill="x", padx=10)
        self.e_alarm_date = tk.Entry(right, bg=BG2, fg=FG,
                                     insertbackground="#fff", relief="flat",
                                     font=("Microsoft YaHei UI", 10))
        self.e_alarm_date.insert(0, _t("edit.placeholder.date"))
        self.e_alarm_date.pack(fill="x", padx=10, pady=(2,4))

        tk.Label(right, text=_t("edit.alarm.time_label"), bg=BG, fg=FG_DIM,
                 font=("Microsoft YaHei UI", 9), anchor="w").pack(fill="x", padx=10)
        self.e_alarm_time = tk.Entry(right, bg=BG2, fg=FG,
                                     insertbackground="#fff", relief="flat",
                                     font=("Microsoft YaHei UI", 10))
        self.e_alarm_time.pack(fill="x", padx=10, pady=(2,4))
        tk.Label(right, text=_t("edit.alarm.example"), bg=BG, fg="#555",
                 font=("Microsoft YaHei UI", 8)).pack(anchor="w", padx=12)

        def _cp(entry, ph):
            entry.bind("<FocusIn>",
                       lambda e: entry.delete(0,"end") if entry.get()==ph else None)
            entry.bind("<FocusOut>",
                       lambda e: (entry.delete(0,"end") or entry.insert(0,ph))
                       if not entry.get().strip() else None)
        _cp(self.e_alarm_date, _t("edit.placeholder.date"))

        # 底部留白
        tk.Frame(right, bg=BG, height=12).pack()

        # 全局快捷键
        self.win.bind_all("<Control-s>", lambda e: self._save_task())

    def _update_progress_label(self, val):
        pct = int(float(val))
        color = ("#ef5350" if pct<=30 else "#ffb74d" if pct<=69
                 else "#4fc3f7" if pct<100 else GREEN)
        self.prog_bar.config(bg=color)
        self.prog_bar.place(relwidth=pct/100)
        self.lbl_progress.config(text=f"{pct}%", fg=color)
        if pct == 100:
            self.completed_var.set(True)

    def _set_progress(self, pct: int):
        self.progress_var.set(pct)
        self._update_progress_label(pct)

    # ══════════════════════════════════════════════════════════
    # Tab 3 – 回收站
    # ══════════════════════════════════════════════════════════
    def _build_trash_tab(self):
        bar = tk.Frame(self.tab_trash, bg=BG)
        bar.pack(fill="x", padx=6, pady=(6,2))

        _btn(bar, _t("trash.btn.restore"),    self._restore_sel).pack(side="left", padx=2)
        _btn(bar, _t("trash.btn.purge"),       self._purge_sel,   danger=True).pack(side="left", padx=2)
        _btn(bar, _t("trash.btn.purge_all"),   self._purge_all,   danger=True).pack(side="left", padx=8)
        self.lbl_trash_count = tk.Label(bar, text="", bg=BG, fg=FG_DIM,
                                        font=("Microsoft YaHei UI", 9))
        self.lbl_trash_count.pack(side="right", padx=8)

        cols = ("title","priority","status","elapsed","deleted_at","created")
        self.trash_tree = ttk.Treeview(self.tab_trash, columns=cols,
                                       show="headings", selectmode="browse")
        th = {
            "title":      (_t("manager.col.title"),     200),
            "priority":   (_t("manager.col.priority"),   62),
            "status":     (_t("trash.col.original"),     70),
            "elapsed":    (_t("trash.col.elapsed"),      70),
            "deleted_at": (_t("trash.col.deleted_at"),  120),
            "created":    (_t("manager.col.created"),  120),
        }
        for col,(hdr,w) in th.items():
            self.trash_tree.heading(col, text=hdr)
            self.trash_tree.column(col, width=w, minwidth=40,
                                   anchor="w" if col in ("title","deleted_at","created") else "center")

        vsb2 = ttk.Scrollbar(self.tab_trash, orient="vertical",
                              command=self.trash_tree.yview)
        vsb2.pack(side="right", fill="y")
        self.trash_tree.configure(yscrollcommand=vsb2.set)
        self.trash_tree.pack(fill="both", expand=True, padx=6, pady=4)
        self.trash_tree.tag_configure("deleted", foreground="#666")

        # 切换到回收站 tab 时自动刷新
        self.nb.bind("<<NotebookTabChanged>>", self._on_tab_change)

    def _on_tab_change(self, event):
        if self.nb.select() == str(self.tab_trash):
            self._load_trash()

    def _load_trash(self):
        self.trash_tree.delete(*self.trash_tree.get_children())
        tasks = self.store.deleted()
        tasks.sort(key=lambda t: t.deleted_at, reverse=True)
        for t in tasks:
            status_str = _t("manager.status.done") if t.completed else _t("manager.status.todo")
            elapsed_str = (_t("overlay.today") if t.elapsed_days == 0
                           else _t("overlay.days", n=t.elapsed_days))
            pri_str = priority_label(t.priority)
            self.trash_tree.insert("","end", iid=t.task_id, tags=("deleted",),
                                   values=(t.title, pri_str, status_str,
                                           elapsed_str, t.deleted_at, t.created_at))
        n = len(tasks)
        self.lbl_trash_count.config(
            text=_t("trash.count", n=n) if n > 0 else _t("trash.empty"))

    def _restore_sel(self):
        sel = self.trash_tree.selection()
        if not sel:
            messagebox.showinfo(_t("common.tip"),
                                _t("trash.msg.select_restore"), parent=self.win)
            return
        t = self.store.get(sel[0])
        if t:
            self.store.restore(sel[0])
            self._load_trash()
            self._load_list()
            self.on_save_cfg(self.cfg)
            messagebox.showinfo(_t("trash.msg.restored"),
                                _t("trash.msg.restored_body", title=t.title),
                                parent=self.win)

    def _purge_sel(self):
        sel = self.trash_tree.selection()
        if not sel: return
        t = self.store.get(sel[0])
        if t and messagebox.askyesno(
                _t("trash.msg.purge_title"),
                _t("trash.msg.purge_body", title=t.title),
                parent=self.win):
            self.store.purge(sel[0])
            self._load_trash()

    def _purge_all(self):
        n = len(self.store.deleted())
        if n == 0:
            messagebox.showinfo(_t("common.tip"),
                                _t("trash.msg.empty"), parent=self.win)
            return
        if messagebox.askyesno(
                _t("trash.msg.purge_all"),
                _t("trash.msg.purge_all_body", n=n),
                parent=self.win):
            self.store.purge_all_deleted()
            self._load_trash()

    # ══════════════════════════════════════════════════════════
    # Tab 4 – 设置
    # ══════════════════════════════════════════════════════════
    def _build_cfg_tab(self):
        lbl_s   = dict(bg=BG, fg=FG_DIM, font=("Microsoft YaHei UI", 10))
        entry_s = dict(bg=BG2, fg=FG, insertbackground="#fff",
                       relief="flat", font=("Microsoft YaHei UI", 11))

        # ── 外层左右分栏 ──────────────────────────────────────
        outer = tk.Frame(self.tab_cfg, bg=BG)
        outer.pack(fill="both", expand=True, padx=12, pady=10)

        left = tk.LabelFrame(outer, text=_t("cfg.section.general"), bg=BG, fg=ACC,
                             font=("Microsoft YaHei UI", 10, "bold"),
                             relief="groove", bd=1, labelanchor="n")
        left.pack(side="left", fill="both", expand=True, padx=(0, 8), pady=0)

        frm = tk.Frame(left, bg=BG)
        frm.pack(fill="both", expand=True, padx=16, pady=10)

        lbl_kw = dict(bg=BG, fg=FG_DIM, font=("Microsoft YaHei UI", 10),
                      anchor="w")
        e_kw   = dict(bg=BG2, fg=FG, insertbackground="#fff",
                      relief="flat", font=("Microsoft YaHei UI", 11), width=26)

        tk.Label(frm, text=_t("cfg.data_dir"), **lbl_kw).grid(
            row=0, column=0, sticky="w", pady=5, padx=(0, 12))
        dir_f = tk.Frame(frm, bg=BG)
        dir_f.grid(row=0, column=1, sticky="w")
        self.e_datadir = tk.Entry(dir_f, **e_kw)
        self.e_datadir.insert(0, self.cfg.get("data_dir", "data"))
        self.e_datadir.pack(side="left")
        _btn(dir_f, _t("common.browse"), self._browse_dir,
             font=("Microsoft YaHei UI", 9), padx=6).pack(side="left", padx=4)
        import config as _cfg_mod
        _abs = _cfg_mod.ensure_data_dir(self.cfg)
        tk.Label(frm, text=_t("cfg.data_dir.hint", path=_abs),
                 bg=BG, fg="#666",
                 font=("Microsoft YaHei UI", 8)
                 ).grid(row=1, column=1, sticky="w", pady=(0, 4))

        # 界面语言
        tk.Label(frm, text=_t("cfg.language"), **lbl_kw).grid(
            row=2, column=0, sticky="w", pady=5, padx=(0, 12))
        lang_f = tk.Frame(frm, bg=BG)
        lang_f.grid(row=2, column=1, sticky="w")
        self._lang_options = i18n.lang_options()
        self._lang_label_to_code = {label: code for code, label in self._lang_options}
        cur_code = self.cfg.get("language", "zh_CN")
        cur_label = next((lbl for code, lbl in self._lang_options if code == cur_code),
                         self._lang_options[0][1])
        self.lang_var = tk.StringVar(value=cur_label)
        ttk.Combobox(lang_f, textvariable=self.lang_var,
                     values=[lbl for _, lbl in self._lang_options],
                     state="readonly", width=18,
                     font=("Microsoft YaHei UI", 10)).pack(side="left")
        tk.Label(lang_f, text=" " + _t("cfg.language.note"),
                 bg=BG, fg="#666",
                 font=("Microsoft YaHei UI", 8)).pack(side="left", padx=4)

        self.opacity_var = tk.DoubleVar(value=self.cfg.get("overlay_opacity", 0.90))
        tk.Label(frm, text=_t("cfg.opacity"), **lbl_kw).grid(
            row=3, column=0, sticky="w", pady=5, padx=(0, 12))
        tk.Scale(frm, from_=0.3, to=1.0, resolution=0.05, orient="horizontal",
                 variable=self.opacity_var, bg=BG, fg=FG, troughcolor=BG2,
                 highlightthickness=0, length=180).grid(row=3, column=1, sticky="w")

        self.fontsize_var = tk.IntVar(value=self.cfg.get("font_size", 11))
        tk.Label(frm, text=_t("cfg.font_size"), **lbl_kw).grid(
            row=4, column=0, sticky="w", pady=5, padx=(0, 12))
        ttk.Spinbox(frm, from_=9, to=16, textvariable=self.fontsize_var,
                    width=5, font=("Microsoft YaHei UI", 10)
                    ).grid(row=4, column=1, sticky="w")

        self.maxshow_var = tk.IntVar(value=self.cfg.get("max_display_tasks", 10))
        tk.Label(frm, text=_t("cfg.max_show"), **lbl_kw).grid(
            row=5, column=0, sticky="w", pady=5, padx=(0, 12))
        ttk.Spinbox(frm, from_=3, to=30, textvariable=self.maxshow_var,
                    width=5, font=("Microsoft YaHei UI", 10)
                    ).grid(row=5, column=1, sticky="w")

        self.topmost_var = tk.BooleanVar(value=self.cfg.get("overlay_always_top", True))
        tk.Label(frm, text=_t("cfg.always_top"), **lbl_kw).grid(
            row=6, column=0, sticky="w", pady=5, padx=(0, 12))
        tk.Checkbutton(frm, variable=self.topmost_var, bg=BG, fg=ACC,
                       selectcolor=BG, activebackground=BG
                       ).grid(row=6, column=1, sticky="w")

        self.showdone_var = tk.BooleanVar(value=self.cfg.get("show_completed", False))
        tk.Label(frm, text=_t("cfg.show_done"), **lbl_kw).grid(
            row=7, column=0, sticky="w", pady=5, padx=(0, 12))
        tk.Checkbutton(frm, variable=self.showdone_var, bg=BG, fg=ACC,
                       selectcolor=BG, activebackground=BG
                       ).grid(row=7, column=1, sticky="w")

        self.autostart_var = tk.BooleanVar(value=self.cfg.get("autostart", False))
        tk.Label(frm, text=_t("cfg.autostart"), **lbl_kw).grid(
            row=8, column=0, sticky="w", pady=5, padx=(0, 12))
        tk.Checkbutton(frm, variable=self.autostart_var, bg=BG, fg=ACC,
                       selectcolor=BG, activebackground=BG
                       ).grid(row=8, column=1, sticky="w")

        right = tk.LabelFrame(outer, text=_t("cfg.section.ai"), bg=BG, fg="#7c4dff",
                              font=("Microsoft YaHei UI", 10, "bold"),
                              relief="groove", bd=1, labelanchor="n")
        right.pack(side="right", fill="both", expand=True, padx=(8, 0), pady=0)

        ai_frm = tk.Frame(right, bg=BG)
        ai_frm.pack(fill="both", expand=True, padx=16, pady=10)

        ai_cfg = self.cfg.get("ai", {})

        # 免费注册说明
        tip_f = tk.Frame(ai_frm, bg="#1a1a3e", bd=0)
        tip_f.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        tk.Label(tip_f,
                 text=_t("cfg.ai.tip"),
                 bg="#1a1a3e", fg="#ffd54f",
                 font=("Microsoft YaHei UI", 9), justify="left",
                 wraplength=340).pack(padx=8, pady=6, anchor="w")

        a_lbl = dict(bg=BG, fg=FG_DIM, font=("Microsoft YaHei UI", 10), anchor="w")
        a_ent = dict(bg=BG2, fg=FG, insertbackground="#fff",
                     relief="flat", font=("Microsoft YaHei UI", 10))

        self.ai_ollama_var = tk.BooleanVar(
            value=ai_cfg.get("prefer_ollama", True))
        tk.Label(ai_frm, text=_t("cfg.ai.prefer_ollama"), **a_lbl).grid(
            row=1, column=0, sticky="w", pady=4)
        tk.Checkbutton(ai_frm, variable=self.ai_ollama_var, bg=BG, fg="#7c4dff",
                       selectcolor=BG, activebackground=BG
                       ).grid(row=1, column=1, sticky="w")

        tk.Label(ai_frm, text=_t("cfg.ai.ollama_base"), **a_lbl).grid(
            row=2, column=0, sticky="w", pady=4)
        self.e_ollama_base = tk.Entry(ai_frm, width=28, **a_ent)
        self.e_ollama_base.insert(0, ai_cfg.get("ollama_base", "http://localhost:11434"))
        self.e_ollama_base.grid(row=2, column=1, sticky="w", pady=4)

        tk.Label(ai_frm, text=_t("cfg.ai.ollama_model"), **a_lbl).grid(
            row=3, column=0, sticky="w", pady=4)
        ollama_model_f = tk.Frame(ai_frm, bg=BG)
        ollama_model_f.grid(row=3, column=1, sticky="w", pady=4)
        self.e_ollama_model = tk.Entry(ollama_model_f, width=18, **a_ent)
        self.e_ollama_model.insert(0, ai_cfg.get("ollama_model", "qwen2:7b"))
        self.e_ollama_model.pack(side="left")
        _btn(ollama_model_f, _t("common.detect"), self._detect_ollama,
             font=("Microsoft YaHei UI", 9), padx=6).pack(side="left", padx=4)

        # 分隔线
        tk.Frame(ai_frm, bg="#333355", height=1).grid(
            row=4, column=0, columnspan=2, sticky="ew", pady=8)

        # ── 云端 AI 服务商下拉（每个服务商独立 Key） ──────────
        # Provider 列表 & 当前 active_provider（供下方表单回填）
        # provider 内部 id 与展示名称（展示名称会跟随语言变化）
        _custom_label = "Custom" if i18n.current_lang() == "en_US" else "自定义"
        _hunyuan_label = "Tencent Hunyuan" if i18n.current_lang() == "en_US" else "腾讯混元"
        _groq_label = "Groq Free" if i18n.current_lang() == "en_US" else "Groq 免费"
        self._PROVIDERS = [
            ("hunyuan",  _hunyuan_label, "https://api.hunyuan.cloud.tencent.com/v1", "hunyuan-turbos-latest"),
            ("groq",     _groq_label,    "https://api.groq.com/openai/v1",           "llama3-8b-8192"),
            ("deepseek", "DeepSeek",     "https://api.deepseek.com/v1",               "deepseek-chat"),
            ("moonshot", "Moonshot",     "https://api.moonshot.cn/v1",                "moonshot-v1-8k"),
            ("openai",   "OpenAI",       "https://api.openai.com/v1",                 "gpt-4o-mini"),
            ("custom",   _custom_label,  "",                                           ""),
        ]
        # 本地内存中的各 provider 配置副本（即时编辑，点"保存"才写盘）
        self._provider_state: dict = {}
        existing_providers = ai_cfg.get("providers", {}) or {}
        for pid, label, def_base, def_model in self._PROVIDERS:
            src = existing_providers.get(pid, {})
            self._provider_state[pid] = {
                "label":    label,
                "api_key":  src.get("api_key",  ""),
                "base_url": src.get("base_url", def_base),
                "model":    src.get("model",    def_model),
            }

        self._active_provider = ai_cfg.get("active_provider", "hunyuan")
        if self._active_provider not in self._provider_state:
            self._active_provider = "hunyuan"

        tk.Label(ai_frm, text=_t("cfg.ai.provider"), **a_lbl).grid(
            row=5, column=0, sticky="w", pady=4)
        self.ai_provider_var = tk.StringVar(
            value=self._provider_state[self._active_provider]["label"])
        provider_labels = [p[1] for p in self._PROVIDERS]
        self.cmb_provider = ttk.Combobox(
            ai_frm, textvariable=self.ai_provider_var,
            values=provider_labels, state="readonly", width=25,
            font=("Microsoft YaHei UI", 10))
        self.cmb_provider.grid(row=5, column=1, sticky="w", pady=4)
        self.cmb_provider.bind("<<ComboboxSelected>>", self._on_provider_change)

        tk.Label(ai_frm, text=_t("cfg.ai.api_key"), **a_lbl).grid(
            row=6, column=0, sticky="w", pady=4)
        self.e_ai_key = tk.Entry(ai_frm, width=28, show="*", **a_ent)
        self.e_ai_key.grid(row=6, column=1, sticky="w", pady=4)
        # 显示/隐藏 Key
        self._show_key = False
        def _toggle_show_key():
            self._show_key = not self._show_key
            self.e_ai_key.config(show="" if self._show_key else "*")
        tk.Button(ai_frm, text="👁", command=_toggle_show_key,
                  bg=BG2, fg=FG_DIM, relief="flat", padx=4, cursor="hand2",
                  font=("Segoe UI Emoji", 9), activebackground=BG
                  ).grid(row=6, column=2, padx=4)
        # Key 输入变化时实时写回内存副本（不落盘）
        self.e_ai_key.bind("<KeyRelease>", lambda _e: self._sync_form_to_state())

        tk.Label(ai_frm, text=_t("cfg.ai.base_url"), **a_lbl).grid(
            row=7, column=0, sticky="w", pady=4)
        self.e_ai_base = tk.Entry(ai_frm, width=28, **a_ent)
        self.e_ai_base.grid(row=7, column=1, sticky="w", pady=4)
        self.e_ai_base.bind("<KeyRelease>", lambda _e: self._sync_form_to_state())

        tk.Label(ai_frm, text=_t("cfg.ai.model"), **a_lbl).grid(
            row=8, column=0, sticky="w", pady=4)
        self.e_ai_model = tk.Entry(ai_frm, width=28, **a_ent)
        self.e_ai_model.grid(row=8, column=1, sticky="w", pady=4)
        self.e_ai_model.bind("<KeyRelease>", lambda _e: self._sync_form_to_state())

        link_f = tk.Frame(ai_frm, bg=BG)
        link_f.grid(row=9, column=0, columnspan=3, sticky="w", pady=(4, 2))
        tk.Label(link_f, text=_t("cfg.ai.note"),
                 bg=BG, fg="#ffd54f",
                 font=("Microsoft YaHei UI", 8), justify="left"
                 ).pack(anchor="w")

        # 首次载入，回填当前 active provider 到表单
        self._load_provider_to_form(self._active_provider)

        # AI 状态反馈标签
        self.lbl_ai_status = tk.Label(ai_frm, text="", bg=BG, fg="#7c4dff",
                                      font=("Microsoft YaHei UI", 9))
        self.lbl_ai_status.grid(row=10, column=0, columnspan=3, sticky="w", pady=4)

        # ════════════════════════════════
        # 底部保存按钮（跨越左右）
        # ════════════════════════════════
        btn_row = tk.Frame(self.tab_cfg, bg=BG)
        btn_row.pack(fill="x", padx=16, pady=(0, 12))

        _btn(btn_row, _t("cfg.btn.save"), self._save_cfg,
             font=("Microsoft YaHei UI", 11, "bold"), padx=16, pady=6,
             bg="#0d7377", fg="#fff",
             activebackground="#14a085",
             activeforeground="#fff").pack(side="left")

        self.lbl_cfg_msg = tk.Label(btn_row, text="", bg=BG, fg=ACC,
                                    font=("Microsoft YaHei UI", 10))
        self.lbl_cfg_msg.pack(side="left", padx=12)

    def _detect_ollama(self):
        import threading
        from ai_chat import OllamaBackend
        base = self.e_ollama_base.get().strip()
        self.lbl_ai_status.config(text=_t("cfg.ai.detect_pending"), fg=YELLOW)
        self.win.update()

        def _check():
            ok = OllamaBackend.available(base)
            models = OllamaBackend.list_models(base) if ok else []
            def _show():
                if ok:
                    models_str = ", ".join(models[:6]) or _t("cfg.ai.detect_no_models")
                    self.lbl_ai_status.config(
                        text=_t("cfg.ai.detect_ok", models=models_str), fg=GREEN)
                    if models and not self.e_ollama_model.get().strip():
                        self.e_ollama_model.delete(0, "end")
                        self.e_ollama_model.insert(0, models[0])
                else:
                    self.lbl_ai_status.config(
                        text=_t("cfg.ai.detect_fail", base=base), fg=RED)
            self.win.after(0, _show)
        threading.Thread(target=_check, daemon=True).start()

    # ─── AI 服务商下拉切换 ────────────────────────────────────
    def _provider_id_by_label(self, label: str) -> str:
        for pid, lbl, *_ in self._PROVIDERS:
            if lbl == label:
                return pid
        return "hunyuan"

    def _load_provider_to_form(self, pid: str):
        """把某 provider 的配置回填到表单"""
        p = self._provider_state.get(pid, {})
        self.e_ai_key.delete(0, "end")
        self.e_ai_key.insert(0, p.get("api_key", ""))
        self.e_ai_base.delete(0, "end")
        self.e_ai_base.insert(0, p.get("base_url", ""))
        self.e_ai_model.delete(0, "end")
        self.e_ai_model.insert(0, p.get("model", ""))

    def _sync_form_to_state(self):
        """实时把表单输入写回当前选中 provider 的内存副本"""
        pid = self._active_provider
        if pid not in self._provider_state:
            return
        self._provider_state[pid]["api_key"]  = self.e_ai_key.get().strip()
        self._provider_state[pid]["base_url"] = self.e_ai_base.get().strip()
        self._provider_state[pid]["model"]    = self.e_ai_model.get().strip()

    def _on_provider_change(self, _evt=None):
        """下拉切换服务商时：先把表单写回旧 provider，再把新 provider 的配置载入表单"""
        # 先 flush 当前表单到旧 provider
        self._sync_form_to_state()
        # 切到新 provider
        new_pid = self._provider_id_by_label(self.ai_provider_var.get())
        self._active_provider = new_pid
        self._load_provider_to_form(new_pid)
        # 重置显隐状态
        self._show_key = False
        self.e_ai_key.config(show="*")

    # ─── 操作：列表 ───────────────────────────────────────────
    def _new_task(self):
        self._edit_task = None
        self._clear_form()
        self.nb.select(self.tab_edit)

    def _edit_sel(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo(_t("common.tip"),
                                _t("manager.msg.select_first"), parent=self.win)
            return
        t = self.store.get(sel[0])
        if not t: return
        self._edit_task = t
        self._fill_form(t)
        self.nb.select(self.tab_edit)

    def _toggle_sel(self):
        sel = self.tree.selection()
        if not sel: return
        self.store.toggle(sel[0])
        self._load_list()
        self.on_save_cfg(self.cfg)

    def _delete_sel(self):
        """软删除：移入回收站"""
        sel = self.tree.selection()
        if not sel: return
        t = self.store.get(sel[0])
        if t and messagebox.askyesno(
                _t("manager.msg.trash_title"),
                _t("manager.msg.trash_confirm", title=t.title),
                parent=self.win):
            self.store.soft_delete(sel[0])
            self._load_list()
            self.on_save_cfg(self.cfg)

    # ─── 操作：表单 ───────────────────────────────────────────
    def _save_task(self):
        title = self.e_title.get().strip()
        if not title:
            messagebox.showwarning(_t("common.tip"),
                                   _t("edit.msg.empty_title"), parent=self.win)
            return
        alarm_t = self.e_alarm_time.get().strip()
        if alarm_t and not re.match(r"^\d{2}:\d{2}$", alarm_t):
            messagebox.showwarning(_t("common.tip"),
                                   _t("edit.msg.bad_time"), parent=self.win)
            return
        alarm_d = self.e_alarm_date.get().strip()
        if alarm_d in (_t("edit.placeholder.date"), "YYYY-MM-DD", ""): alarm_d = ""
        if alarm_d and not re.match(r"^\d{4}-\d{2}-\d{2}$", alarm_d):
            messagebox.showwarning(_t("common.tip"),
                                   _t("edit.msg.bad_date"), parent=self.win)
            return

        content = self.e_content.get("1.0","end-1c").strip()
        prog    = int(self.progress_var.get())
        pri     = self.pri_var.get()
        done    = self.completed_var.get() or (prog == 100)

        if self._edit_task:
            t = self._edit_task
            t.title      = title
            t.content    = content
            t.goal       = self.e_goal.get().strip()
            t.problem    = self.e_problem.get().strip()
            t.alarm_time = alarm_t
            t.alarm_date = alarm_d
            t.priority   = pri
            t.tags       = self.e_tags.get().strip()
            t.progress   = prog
            t.completed  = done
            self.store.update(t)
        else:
            t = Task(
                title=title, content=content,
                goal=self.e_goal.get().strip(),
                problem=self.e_problem.get().strip(),
                alarm_time=alarm_t, alarm_date=alarm_d,
                priority=pri, tags=self.e_tags.get().strip(),
                progress=prog, completed=done,
            )
            self.store.add(t)

        self._edit_task = None
        self._load_list()
        self.on_save_cfg(self.cfg)
        self.lbl_save_msg.config(text=_t("edit.msg.saved"))
        self.win.after(2000, lambda: self.lbl_save_msg.config(text=""))
        self._clear_form()
        self.nb.select(self.tab_list)

    # ─── 任务内容：放大编辑 + Markdown 预览 ──────────────────
    def _open_content_editor(self):
        """打开独立大窗编辑任务内容，关闭时把文本写回 e_content"""
        try:
            from markdown_editor import MarkdownEditor
        except Exception as e:
            messagebox.showerror(_t("common.error"),
                                 _t("edit.msg.md_failed", e=e),
                                 parent=self.win)
            return

        cur = self.e_content.get("1.0", "end-1c")
        title_hint = self.e_title.get().strip() or _t("edit.title.hint")

        def _on_save(new_text: str):
            self.e_content.delete("1.0", "end")
            self.e_content.insert("1.0", new_text)
            self.lbl_edit_hint.config(
                text=_t("edit.msg.from_editor", n=len(new_text)),
                fg=GREEN)
            self.win.after(2500,
                           lambda: self.lbl_edit_hint.config(fg=ACC))

        def _on_screenshot(cb_insert):
            """编辑器点截图 → 启动截图流程 → 返回路径给编辑器插入"""
            self._start_screenshot(cb_insert, hide_windows=[
                MarkdownEditor._instance.win
                if MarkdownEditor._instance else None,
                self.win,
            ])

        MarkdownEditor.open(
            self.win,
            initial_text=cur,
            title=_t("edit.window.title", hint=title_hint),
            on_save=_on_save,
            image_base_dir=self._image_base_dir(),
            on_screenshot=_on_screenshot,
        )

    def _quick_screenshot_to_content(self):
        """主窗直接点「📷 截图」：截完直接把 Markdown 插入 e_content"""
        def _cb(path):
            if not path:
                return
            base = self._image_base_dir()
            try:
                rel = Path(path).resolve().relative_to(base.resolve()).as_posix()
            except Exception:
                rel = Path(path).as_posix()
            snippet = f"\n![{_t('shot.alt_prefix')}{Path(path).stem}]({rel})\n"
            try:
                self.e_content.insert("insert", snippet)
            except Exception:
                self.e_content.insert("end", snippet)
            self.lbl_edit_hint.config(
                text=_t("edit.msg.shot_inserted", name=Path(path).name), fg=GREEN)
            self.win.after(3000,
                           lambda: self.lbl_edit_hint.config(fg=ACC))

        self._start_screenshot(_cb, hide_windows=[self.win])

    def _image_base_dir(self) -> Path:
        """获取图片存放根目录 data_dir/img，按需创建"""
        base = cfg_mod.ensure_data_dir(self.cfg) / "img"
        base.mkdir(parents=True, exist_ok=True)
        return base

    def _start_screenshot(self, cb_insert, hide_windows=None):
        """启动截图流程的统一入口"""
        try:
            from screenshot import capture_and_edit
        except Exception as e:
            messagebox.showerror(
                _t("edit.msg.shot_unavail"),
                _t("edit.msg.shot_failed", e=e),
                parent=self.win)
            if cb_insert:
                cb_insert(None)
            return

        save_root = self._image_base_dir()

        def _done(path):
            if cb_insert:
                cb_insert(path)

        # parent 用 Tk 全局 root（self.root）而不是管理窗自己，
        # 避免主窗被 withdraw 后 child Toplevel 行为异常
        capture_and_edit(self.root, save_root, _done,
                         hide_windows=hide_windows)

    def _clear_form(self):
        """清空表单 + 清除编辑状态"""
        self._edit_task = None
        self._reset_fields()
        self.lbl_edit_hint.config(text="")

    def _reset_fields(self):
        """只清控件，不动 _edit_task"""
        self.e_title.delete(0,"end")
        self.e_content.delete("1.0","end")
        self.e_goal.delete(0,"end")
        self.e_problem.delete(0,"end")
        self.e_tags.delete(0,"end")
        self.e_alarm_time.delete(0,"end")
        self.e_alarm_date.delete(0,"end")
        self.e_alarm_date.insert(0, _t("edit.placeholder.date"))
        self.pri_var.set(2)
        self.completed_var.set(False)
        self.progress_var.set(0)
        self._update_progress_label(0)
        self.lbl_times.config(text="")

    def _fill_form(self, t: Task):
        """回填任务数据（调 _reset_fields，不调 _clear_form）"""
        self._reset_fields()
        self.e_title.insert(0, t.title)
        self.e_content.insert("1.0", t.content)
        self.e_goal.insert(0, t.goal)
        self.e_problem.insert(0, t.problem)
        self.e_tags.insert(0, t.tags)
        self.e_alarm_time.insert(0, t.alarm_time)
        if t.alarm_date:
            self.e_alarm_date.delete(0,"end")
            self.e_alarm_date.insert(0, t.alarm_date)
        self.pri_var.set(t.priority)
        self.progress_var.set(t.progress)
        self._update_progress_label(t.progress)
        self.completed_var.set(t.completed)
        elapsed = t.elapsed_days
        elapsed_str = (_t("edit.msg.created_today") if elapsed == 0
                       else _t("edit.msg.created_days", n=elapsed))
        self.lbl_times.config(
            text=_t("edit.msg.times_summary",
                    c=t.created_at, u=t.updated_at, elapsed=elapsed_str))
        self.lbl_edit_hint.config(
            text=_t("edit.msg.editing", title=t.title, id=t.task_id))

    # ─── 设置 ─────────────────────────────────────────────────
    def _browse_dir(self):
        d = filedialog.askdirectory(parent=self.win,
                                    initialdir=self.e_datadir.get(),
                                    title=_t("cfg.dialog.choose_dir"))
        if d:
            self.e_datadir.delete(0,"end")
            self.e_datadir.insert(0, d)

    def _save_cfg(self):
        self.cfg["data_dir"]           = self.e_datadir.get().strip()
        self.cfg["overlay_opacity"]    = self.opacity_var.get()
        self.cfg["font_size"]          = self.fontsize_var.get()
        self.cfg["max_display_tasks"]  = self.maxshow_var.get()
        self.cfg["overlay_always_top"] = self.topmost_var.get()
        self.cfg["show_completed"]     = self.showdone_var.get()
        self.cfg["autostart"]          = self.autostart_var.get()
        # 界面语言
        new_lang = self._lang_label_to_code.get(
            self.lang_var.get(), self.cfg.get("language", "zh_CN"))
        self.cfg["language"]           = new_lang
        # AI 配置
        # 先把当前表单刷回内存副本，确保切换过但未切回的内容不丢
        self._sync_form_to_state()
        self.cfg["ai"] = {
            "prefer_ollama":    self.ai_ollama_var.get(),
            "ollama_base":      self.e_ollama_base.get().strip(),
            "ollama_model":     self.e_ollama_model.get().strip(),
            "active_provider":  self._active_provider,
            "providers":        {
                pid: {
                    "label":    data.get("label", pid),
                    "api_key":  data.get("api_key", ""),
                    "base_url": data.get("base_url", ""),
                    "model":    data.get("model", ""),
                }
                for pid, data in self._provider_state.items()
            },
            "system_prompt":  self.cfg.get("ai", {}).get("system_prompt", ""),
            # 兼容保留：清空旧字段避免再次被迁移
            "api_key":  "",
            "base_url": "",
            "model":    "",
        }
        cfg_mod.save(self.cfg)
        self.lbl_cfg_msg.config(text=_t("cfg.msg.saved"))
        # 把回调放在最后调用，因为它可能销毁本窗口（语言切换）
        self.win.after(50, lambda: self.on_save_cfg(self.cfg))
        # 仅在窗口仍然存在的情况下调度清空提示文字
        try:
            self.win.after(2000,
                           lambda: self.lbl_cfg_msg.winfo_exists()
                           and self.lbl_cfg_msg.config(text=""))
        except Exception:
            pass

    def _close(self):
        self.win.destroy()

    # ══════════════════════════════════════════════════════════
    # Tab 5 – 备份 / 恢复 / 邮件发送
    # ══════════════════════════════════════════════════════════
    def _build_backup_tab(self):
        outer = tk.Frame(self.tab_bkp, bg=BG)
        outer.pack(fill="both", expand=True, padx=12, pady=10)

        # ── 顶部说明 ────────────────────────────────────────
        tip = tk.Frame(outer, bg="#1a1a3e", bd=0)
        tip.pack(fill="x", pady=(0, 10))
        tk.Label(
            tip,
            text=_t("bkp.tip"),
            bg="#1a1a3e", fg=YELLOW, justify="left",
            font=("Microsoft YaHei UI", 9), wraplength=900,
        ).pack(padx=10, pady=8, anchor="w")

        # ── 上部：左（本地备份）+ 右（邮件配置） ────────────
        top = tk.Frame(outer, bg=BG)
        top.pack(fill="x")

        left = tk.LabelFrame(
            top, text=_t("bkp.section.local"), bg=BG, fg=ACC,
            font=("Microsoft YaHei UI", 10, "bold"),
            relief="groove", bd=1, labelanchor="n",
        )
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))

        lfrm = tk.Frame(left, bg=BG)
        lfrm.pack(fill="x", padx=14, pady=12)

        bkp = self.cfg.get("backup", {})

        self.bkp_inc_cfg_var = tk.BooleanVar(
            value=bkp.get("include_config", True))
        tk.Checkbutton(
            lfrm, variable=self.bkp_inc_cfg_var,
            text=_t("bkp.include_cfg"),
            bg=BG, fg=FG, selectcolor=BG, activebackground=BG,
            font=("Microsoft YaHei UI", 10), anchor="w",
        ).pack(fill="x", pady=(0, 10))

        btn_row = tk.Frame(lfrm, bg=BG)
        btn_row.pack(fill="x")
        _btn(btn_row, _t("bkp.btn.export"), self._do_export_local,
             font=("Microsoft YaHei UI", 10, "bold"),
             bg="#0d7377", fg="#fff",
             activebackground="#14a085", activeforeground="#fff",
             padx=14, pady=6).pack(side="left")
        _btn(btn_row, _t("bkp.btn.import"), self._do_import_local,
             font=("Microsoft YaHei UI", 10), padx=12, pady=6
             ).pack(side="left", padx=8)

        tk.Label(
            lfrm,
            text=_t("bkp.import_hint"),
            bg=BG, fg=FG_DIM, justify="left",
            font=("Microsoft YaHei UI", 9), wraplength=360,
        ).pack(fill="x", pady=(10, 0), anchor="w")

        right = tk.LabelFrame(
            top, text=_t("bkp.section.email"), bg=BG, fg=PURPLE,
            font=("Microsoft YaHei UI", 10, "bold"),
            relief="groove", bd=1, labelanchor="n",
        )
        right.pack(side="right", fill="both", expand=True, padx=(8, 0))

        rfrm = tk.Frame(right, bg=BG)
        rfrm.pack(fill="x", padx=14, pady=12)

        a_lbl = dict(bg=BG, fg=FG_DIM, font=("Microsoft YaHei UI", 10),
                     anchor="w")
        a_ent = dict(bg=BG2, fg=FG, insertbackground="#fff",
                     relief="flat", font=("Microsoft YaHei UI", 10))

        # SMTP 服务器预设按钮
        preset_f = tk.Frame(rfrm, bg=BG)
        preset_f.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))
        tk.Label(preset_f, text=_t("bkp.preset_label"), bg=BG, fg=FG_DIM,
                 font=("Microsoft YaHei UI", 9)).pack(side="left")

        try:
            from backup import COMMON_SMTP
        except Exception:
            COMMON_SMTP = {"QQ邮箱": ("smtp.qq.com", 465)}

        for name, (host, port) in COMMON_SMTP.items():
            def _fill(h=host, p=port):
                self.e_bkp_host.delete(0, "end"); self.e_bkp_host.insert(0, h)
                self.e_bkp_port.delete(0, "end"); self.e_bkp_port.insert(0, str(p))
            tk.Button(
                preset_f, text=name, command=_fill,
                bg="#1a1a3e", fg=ACC, relief="flat",
                font=("Microsoft YaHei UI", 8), padx=5, pady=2,
                cursor="hand2", activebackground=BG2,
            ).pack(side="left", padx=2)

        tk.Label(rfrm, text=_t("bkp.smtp_host"), **a_lbl).grid(
            row=1, column=0, sticky="w", pady=4)
        self.e_bkp_host = tk.Entry(rfrm, width=22, **a_ent)
        self.e_bkp_host.insert(0, bkp.get("smtp_host", "smtp.qq.com"))
        self.e_bkp_host.grid(row=1, column=1, sticky="w", pady=4)
        tk.Label(rfrm, text=_t("bkp.smtp_port"), **a_lbl).grid(
            row=1, column=2, sticky="e", padx=(8, 2))
        self.e_bkp_port = tk.Entry(rfrm, width=6, **a_ent)
        self.e_bkp_port.insert(0, str(bkp.get("smtp_port", 465)))
        self.e_bkp_port.grid(row=1, column=3, sticky="w", pady=4)

        tk.Label(rfrm, text=_t("bkp.sender"), **a_lbl).grid(
            row=2, column=0, sticky="w", pady=4)
        self.e_bkp_sender = tk.Entry(rfrm, width=30, **a_ent)
        self.e_bkp_sender.insert(0, bkp.get("sender", ""))
        self.e_bkp_sender.grid(row=2, column=1, columnspan=3,
                               sticky="we", pady=4)

        tk.Label(rfrm, text=_t("bkp.auth_code"), **a_lbl).grid(
            row=3, column=0, sticky="w", pady=4)
        self.e_bkp_auth = tk.Entry(rfrm, width=30, show="*", **a_ent)
        self.e_bkp_auth.insert(0, bkp.get("auth_code", ""))
        self.e_bkp_auth.grid(row=3, column=1, columnspan=2,
                             sticky="we", pady=4)
        self._show_auth = False
        def _toggle_auth():
            self._show_auth = not self._show_auth
            self.e_bkp_auth.config(show="" if self._show_auth else "*")
        tk.Button(
            rfrm, text="👁", command=_toggle_auth,
            bg=BG2, fg=FG_DIM, relief="flat", padx=4, cursor="hand2",
            font=("Segoe UI Emoji", 9), activebackground=BG,
        ).grid(row=3, column=3, padx=4)

        tk.Label(rfrm, text=_t("bkp.recipient"), **a_lbl).grid(
            row=4, column=0, sticky="w", pady=4)
        self.e_bkp_to = tk.Entry(rfrm, width=30, **a_ent)
        self.e_bkp_to.insert(0, bkp.get("recipient", ""))
        self.e_bkp_to.grid(row=4, column=1, columnspan=3,
                           sticky="we", pady=4)
        tk.Label(rfrm, text=_t("bkp.recipient.hint"),
                 bg=BG, fg=FG_DIM,
                 font=("Microsoft YaHei UI", 8)).grid(
            row=5, column=1, columnspan=3, sticky="w")

        rfrm.columnconfigure(1, weight=1)

        # 按钮行
        rbtn = tk.Frame(right, bg=BG)
        rbtn.pack(fill="x", padx=14, pady=(0, 12))
        _btn(rbtn, _t("bkp.btn.save_email"), self._save_backup_cfg,
             font=("Microsoft YaHei UI", 10),
             padx=10, pady=5).pack(side="left")
        _btn(rbtn, _t("bkp.btn.export_send"), self._do_export_and_send,
             font=("Microsoft YaHei UI", 10, "bold"),
             bg=PURPLE, fg="#fff",
             activebackground="#9575ff", activeforeground="#fff",
             padx=12, pady=5).pack(side="left", padx=8)

        # ── 下部：日志输出 ───────────────────────────────────
        log_frm = tk.LabelFrame(
            outer, text=_t("bkp.log.section"), bg=BG, fg=FG_DIM,
            font=("Microsoft YaHei UI", 9), relief="groove", bd=1,
        )
        log_frm.pack(fill="both", expand=True, pady=(12, 0))

        log_inner = tk.Frame(log_frm, bg=BG)
        log_inner.pack(fill="both", expand=True, padx=6, pady=6)
        self.txt_bkp_log = tk.Text(
            log_inner, bg="#0f0f1e", fg="#c5e6ff",
            insertbackground="#fff", relief="flat",
            font=("Consolas", 9), height=10, wrap="word",
        )
        self.txt_bkp_log.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(log_inner, orient="vertical",
                           command=self.txt_bkp_log.yview)
        sb.pack(side="right", fill="y")
        self.txt_bkp_log.config(yscrollcommand=sb.set, state="disabled")
        self._bkp_log(_t("bkp.log.ready"))

    # ─── 备份 Tab 内部工具 ───────────────────────────────────
    def _bkp_log(self, msg: str):
        try:
            self.txt_bkp_log.config(state="normal")
            ts = datetime.now().strftime("%H:%M:%S")
            self.txt_bkp_log.insert("end", f"[{ts}] {msg}\n")
            self.txt_bkp_log.see("end")
            self.txt_bkp_log.config(state="disabled")
            self.win.update_idletasks()
        except Exception:
            pass

    def _collect_backup_cfg(self) -> dict:
        """从界面控件收集当前 backup 配置（不落盘）"""
        try:
            port = int(self.e_bkp_port.get().strip() or "465")
        except ValueError:
            port = 465
        return {
            "smtp_host":      self.e_bkp_host.get().strip(),
            "smtp_port":      port,
            "sender":         self.e_bkp_sender.get().strip(),
            "auth_code":      self.e_bkp_auth.get().strip(),
            "recipient":      self.e_bkp_to.get().strip(),
            "include_config": self.bkp_inc_cfg_var.get(),
            "last_export_dir": self.cfg.get("backup", {}).get("last_export_dir", ""),
        }

    def _save_backup_cfg(self):
        self.cfg["backup"] = self._collect_backup_cfg()
        cfg_mod.save(self.cfg)
        self.on_save_cfg(self.cfg)
        self._bkp_log(_t("bkp.log.saved"))

    # ─── 导出到本地 ──────────────────────────────────────────
    def _do_export_local(self):
        from backup import export_backup, default_zip_name

        init_dir = self.cfg.get("backup", {}).get("last_export_dir") \
            or str(Path.home() / "Desktop") \
            or str(Path.home())

        dest = filedialog.asksaveasfilename(
            parent=self.win,
            title=_t("bkp.dialog.export"),
            defaultextension=".zip",
            initialdir=init_dir,
            initialfile=default_zip_name(),
            filetypes=[(_t("bkp.dialog.zip_filter"), "*.zip"),
                       (_t("bkp.dialog.all"), "*.*")],
        )
        if not dest:
            return

        include_cfg = self.bkp_inc_cfg_var.get()
        try:
            stat = export_backup(dest, self.cfg,
                                 include_config=include_cfg,
                                 on_log=self._bkp_log)
        except Exception as e:
            self._bkp_log(f"❌ {_t('bkp.msg.export_failed')}：{e}")
            messagebox.showerror(_t("bkp.msg.export_failed"),
                                 str(e), parent=self.win)
            return

        self.cfg.setdefault("backup", {})["last_export_dir"] = str(
            Path(dest).parent)
        cfg_mod.save(self.cfg)

        messagebox.showinfo(
            _t("bkp.msg.export_ok_title"),
            _t("bkp.msg.export_ok",
               path=dest, tasks=stat['tasks'], chats=stat['chats']),
            parent=self.win,
        )

    # ─── 从本地文件恢复 ──────────────────────────────────────
    def _do_import_local(self):
        src = filedialog.askopenfilename(
            parent=self.win,
            title=_t("bkp.dialog.import"),
            filetypes=[(_t("bkp.dialog.zip_filter"), "*.zip"),
                       (_t("bkp.dialog.all"), "*.*")],
        )
        if not src:
            return

        import tkinter.messagebox as mb
        res = mb.askyesnocancel(
            _t("bkp.msg.choose_mode"),
            _t("bkp.msg.choose_mode_body"),
            parent=self.win,
        )
        if res is None:
            return
        merge = bool(res)

        if not merge:
            if not mb.askyesno(
                    _t("bkp.msg.confirm_overwrite"),
                    _t("bkp.msg.confirm_overwrite_body"),
                    parent=self.win):
                return

        from backup import import_backup
        try:
            stat = import_backup(src, self.cfg, merge=merge,
                                 on_log=self._bkp_log)
        except Exception as e:
            self._bkp_log(f"❌ {_t('bkp.msg.import_failed')}：{e}")
            messagebox.showerror(_t("bkp.msg.import_failed"), str(e),
                                 parent=self.win)
            return

        try:
            self.store.reload() if hasattr(self.store, "reload") else None
        except Exception:
            pass
        self._load_list()

        messagebox.showinfo(
            _t("bkp.msg.import_ok_title"),
            _t("bkp.msg.import_ok_body",
               ti=stat['tasks_imported'], ts=stat['tasks_skipped'],
               ci=stat['chats_imported'], cs=stat['chats_skipped']),
            parent=self.win,
        )

    # ─── 一键：导出 + 发邮件 ─────────────────────────────────
    def _do_export_and_send(self):
        import threading, tempfile
        from backup import export_backup, send_backup_email, default_zip_name

        smtp = self._collect_backup_cfg()
        # 先存一份到 cfg
        self.cfg["backup"] = smtp
        cfg_mod.save(self.cfg)

        missing = [k for k in ("smtp_host", "sender", "auth_code") if not smtp.get(k)]
        if missing:
            messagebox.showwarning(
                _t("bkp.msg.cfg_missing"),
                _t("bkp.msg.cfg_missing_body", fields="、".join(missing)),
                parent=self.win,
            )
            return

        self._bkp_log(_t("bkp.msg.send_started"))

        def _worker():
            try:
                tmp_dir = Path(tempfile.gettempdir())
                zip_path = tmp_dir / default_zip_name()
                export_backup(zip_path, self.cfg,
                              include_config=smtp["include_config"],
                              on_log=lambda m: self.win.after(
                                  0, self._bkp_log, m))
                send_backup_email(
                    zip_path,
                    {
                        "host":      smtp["smtp_host"],
                        "port":      smtp["smtp_port"],
                        "sender":    smtp["sender"],
                        "auth_code": smtp["auth_code"],
                        "recipient": smtp["recipient"] or smtp["sender"],
                    },
                    on_log=lambda m: self.win.after(0, self._bkp_log, m),
                )
                _to = smtp['recipient'] or smtp['sender']
                self.win.after(0, lambda to=_to: messagebox.showinfo(
                    _t("bkp.msg.send_ok_title"),
                    _t("bkp.msg.send_ok_body", to=to),
                    parent=self.win))
            except Exception as e:
                err = str(e)
                self.win.after(0, self._bkp_log,
                               f"❌ {_t('bkp.msg.send_failed')}：{err}")
                self.win.after(0, lambda: messagebox.showerror(
                    _t("bkp.msg.send_failed"), err, parent=self.win))

        threading.Thread(target=_worker, daemon=True).start()
