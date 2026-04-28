"""
桌面透明悬浮窗口 - 始终置顶，可拖动，卡片内快速操作
"""
import tkinter as tk
from models import Task, Store, PRIORITY_COLORS, priority_label
from i18n import t as _t

CHROMA = "#010101"   # 透明色键（勿在UI中使用）

PROG_COLOR = {
    "low":  "#ef5350",   # 0-30
    "mid":  "#ffb74d",   # 31-69
    "hi":   "#4fc3f7",   # 70-99
    "done": "#66bb6a",   # 100
}


def _prog_color(pct: int) -> str:
    if pct <= 30:   return PROG_COLOR["low"]
    if pct <= 69:   return PROG_COLOR["mid"]
    if pct < 100:   return PROG_COLOR["hi"]
    return PROG_COLOR["done"]


class Overlay:
    def __init__(self, root: tk.Tk, cfg: dict, store: Store,
                 open_manager_cb, quit_cb=None, open_ai_cb=None,
                 screenshot_cb=None):
        self.root          = root
        self.cfg           = cfg
        self.store         = store
        self.open_cb       = open_manager_cb
        self.quit_cb       = quit_cb
        self.open_ai_cb    = open_ai_cb       # AI 问答回调
        self.screenshot_cb = screenshot_cb    # 截图回调
        self._drag_ox      = self._drag_oy = 0
        self._minimized    = False
        # 缩放拖拽起始状态（按下右下角拖手时记录）
        self._rs_x0 = self._rs_y0 = 0
        self._rs_w0 = self._rs_h0 = 0

        self.win = tk.Toplevel(root)
        self._init_win()
        self._build()
        self.refresh()

    # ─── 窗口初始化 ──────────────────────────────────────────
    def _init_win(self):
        w = self.win
        w.overrideredirect(True)
        w.wm_attributes("-topmost",        self.cfg.get("overlay_always_top", True))
        try:
            w.wm_attributes("-transparentcolor", CHROMA)
        except tk.TclError:
            pass  # 非 Windows 平台不支持 -transparentcolor，忽略即可
        w.wm_attributes("-alpha",          self.cfg.get("overlay_opacity", 0.90))
        x  = self.cfg.get("overlay_x", 20)
        y  = self.cfg.get("overlay_y", 100)
        ow = int(self.cfg.get("overlay_width", 300))
        oh = int(self.cfg.get("overlay_height", 600))

        # 尺寸合法性钳制（防止历史配置异常 / 历史最小宽度过小）
        # 与 MIN_W/MIN_H 保持一致，避免下次启动恢复到一个挤掉按钮的窗口
        ow = max(280, min(ow, 1200))
        oh = max(180, min(oh, 2000))

        # 屏幕边界钳制：防止跨屏幕设备拔掉副屏后窗口跑到屏外不可见
        try:
            sw = w.winfo_screenwidth()
            sh = w.winfo_screenheight()
            x = max(0, min(int(x), sw - 80))      # 至少留 80px 在屏内
            y = max(0, min(int(y), sh - 80))
            if x + ow > sw:
                x = max(0, sw - ow)
            if y + oh > sh:
                y = max(0, sh - oh)
        except Exception:
            pass
        # 把钳制后的值写回 cfg，保证持久化的就是合法值
        self.cfg["overlay_x"] = x
        self.cfg["overlay_y"] = y
        self.cfg["overlay_width"]  = ow
        self.cfg["overlay_height"] = oh

        w.geometry(f"{ow}x{oh}+{x}+{y}")
        w.configure(bg=CHROMA)

    # ─── 构建骨架 ─────────────────────────────────────────────
    def _build(self):
        bg  = self.cfg["overlay_bg_color"]
        acc = self.cfg["overlay_accent_color"]
        fs  = self.cfg["font_size"]

        # 外框
        self.outer = tk.Frame(self.win, bg=bg, bd=0,
                              highlightthickness=1, highlightbackground=acc)
        self.outer.pack(fill="both", expand=True, padx=1, pady=1)

        # ── 标题栏 ──────────────────────────────────────────
        bar = tk.Frame(self.outer, bg=acc, height=26)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        lbl_ico = tk.Label(bar, text="📋", bg=acc, fg="#0a0a1a",
                           font=("Segoe UI Emoji", 11), cursor="fleur")
        lbl_ico.pack(side="left", padx=(4, 0))
        lbl_hd = tk.Label(bar, text=_t("overlay.title"), bg=acc,
                          fg="#0a0a1a",
                          font=("Microsoft YaHei UI", fs - 1, "bold"),
                          cursor="fleur")
        lbl_hd.pack(side="left", padx=3)

        for w in (bar, lbl_ico, lbl_hd):
            w.bind("<ButtonPress-1>", self._on_press)
            w.bind("<B1-Motion>",     self._on_drag)

        btn_s = dict(bg=acc, fg="#0a0a1a", bd=0, pady=0, padx=5,
                     activebackground="#81d4fa", activeforeground="#000",
                     font=("Arial", 10, "bold"), cursor="hand2", relief="flat")

        # × 退出
        q_btn = tk.Button(bar, text="×", command=self._on_quit,
                          bg="#c0392b", fg="#fff", bd=0, pady=0, padx=7,
                          activebackground="#e74c3c", activeforeground="#fff",
                          font=("Arial", 12, "bold"), cursor="hand2", relief="flat")
        q_btn.pack(side="right", padx=(0, 1))
        q_btn.bind("<Enter>", lambda e: q_btn.config(bg="#e74c3c"))
        q_btn.bind("<Leave>", lambda e: q_btn.config(bg="#c0392b"))

        # 🤖 AI 问答按钮（蓝紫色）
        ai_btn = tk.Button(bar, text="🤖",
                           command=self._on_open_ai,
                           bg="#5c35cc", fg="#fff", bd=0, pady=0, padx=6,
                           activebackground="#7c4dff", activeforeground="#fff",
                           font=("Segoe UI Emoji", 10), cursor="hand2", relief="flat")
        ai_btn.pack(side="right", padx=1)
        ai_btn.bind("<Enter>", lambda e: ai_btn.config(bg="#7c4dff"))
        ai_btn.bind("<Leave>", lambda e: ai_btn.config(bg="#5c35cc"))
        self._ai_tip = tk.Label(self.win, text=_t("overlay.tip_ai"),
                                bg="#5c35cc", fg="#fff",
                                font=("Microsoft YaHei UI", 8),
                                relief="flat", padx=4, pady=1)
        ai_btn.bind("<Enter>", lambda e, b=ai_btn, t=self._ai_tip: (
            b.config(bg="#7c4dff"),
            t.place(x=b.winfo_x(), y=28)
        ))
        ai_btn.bind("<Leave>", lambda e, b=ai_btn, t=self._ai_tip: (
            b.config(bg="#5c35cc"),
            t.place_forget()
        ))

        tk.Button(bar, text="＋", command=self.open_cb, **btn_s).pack(side="right", padx=1)
        tk.Button(bar, text="－", command=self._toggle_min, **btn_s).pack(side="right")

        # ── 工具栏（待办/全部切换）──────────────────────────
        self.toolbar = tk.Frame(self.outer, bg=bg, height=22)
        self.toolbar.pack(fill="x")
        self.toolbar.pack_propagate(False)

        self._show_all_var = tk.BooleanVar(
            value=self.cfg.get("show_completed", False))
        tk.Label(self.toolbar, text=_t("overlay.show"), bg=bg, fg="#888",
                 font=("Microsoft YaHei UI", 8)).pack(side="left", padx=(6, 2))
        self._btn_todo = tk.Button(
            self.toolbar, text=_t("overlay.todo"),
            command=lambda: self._switch_show(False),
            bg=acc if not self._show_all_var.get() else bg,
            fg="#0a0a1a" if not self._show_all_var.get() else "#888",
            relief="flat", padx=6, pady=0,
            font=("Microsoft YaHei UI", 8, "bold"), cursor="hand2")
        self._btn_todo.pack(side="left")
        self._btn_all = tk.Button(
            self.toolbar, text=_t("overlay.all"),
            command=lambda: self._switch_show(True),
            bg=acc if self._show_all_var.get() else bg,
            fg="#0a0a1a" if self._show_all_var.get() else "#888",
            relief="flat", padx=6, pady=0,
            font=("Microsoft YaHei UI", 8, "bold"), cursor="hand2")
        self._btn_all.pack(side="left")

        # ── 📷 截图按钮（紧跟在显示切换后面）──────────────
        self._btn_shot = tk.Button(
            self.toolbar, text="📷",
            command=self._on_screenshot,
            bg="#7c4dff", fg="#fff",
            relief="flat", padx=6, pady=0,
            font=("Segoe UI Emoji", 9, "bold"),
            cursor="hand2",
            activebackground="#9575ff", activeforeground="#fff")
        self._btn_shot.pack(side="left", padx=(6, 0))
        self._btn_shot.bind("<Enter>",
                            lambda e: self._btn_shot.config(bg="#9575ff"))
        self._btn_shot.bind("<Leave>",
                            lambda e: self._btn_shot.config(bg="#7c4dff"))

        # ── 可折叠内容区 ────────────────────────────────────
        self.body = tk.Frame(self.outer, bg=bg)
        self.body.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(self.body, bg=bg, bd=0, highlightthickness=0)
        self.vsb = tk.Scrollbar(self.body, orient="vertical",
                                command=self.canvas.yview, width=5,
                                troughcolor=bg, bg="#333", relief="flat")
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.inner = tk.Frame(self.canvas, bg=bg)
        self._cwin = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e:
                         self.canvas.itemconfig(self._cwin, width=e.width))
        self.canvas.bind("<MouseWheel>", self._scroll)
        self.inner.bind("<MouseWheel>",  self._scroll)

        # ── 状态栏 ─────────────────────────────────────────
        # 状态栏只放文字；缩放手柄独立用 place() 绑到 self.win 的右下角，
        # 这样无论窗口怎么 resize/relayout，手柄位置都稳定可点。
        self.status_bar = tk.Frame(self.outer, bg=bg)
        self.status_bar.pack(fill="x", padx=0, pady=(0, 0))

        self.status = tk.Label(self.status_bar, text="", bg=bg,
                               fg="#666", anchor="w",
                               font=("Microsoft YaHei UI", 8))
        self.status.pack(side="left", fill="x", expand=True,
                         padx=(4, 18), pady=(0, 3))   # 右侧留 18px 给 grip

        # 缩放拖手：右下角，◢ + size_nw_se 光标；用 place() 锚定到 win 右下角
        self.grip = tk.Label(self.win, text="◢", bg=bg, fg="#888",
                             font=("Arial", 11, "bold"),
                             cursor="size_nw_se",
                             padx=2, pady=0)
        # relx=1.0 / rely=1.0 + anchor="se" → 右下角对齐；用负偏移避开外框 1px 高亮
        self.grip.place(relx=1.0, rely=1.0, anchor="se", x=-2, y=-2)
        self.grip.bind("<ButtonPress-1>",   self._on_resize_press)
        self.grip.bind("<B1-Motion>",       self._on_resize_drag)
        self.grip.bind("<ButtonRelease-1>", self._on_resize_release)
        self.grip.bind("<Enter>", lambda e: self.grip.config(fg=acc))
        self.grip.bind("<Leave>", lambda e: self.grip.config(fg="#888"))
        # 保证 grip 永远在最上层（高于 status_bar 内容）
        self.grip.lift()

    # ─── 显示切换 ─────────────────────────────────────────────
    def _switch_show(self, show_all: bool):
        self._show_all_var.set(show_all)
        self.cfg["show_completed"] = show_all
        acc = self.cfg["overlay_accent_color"]
        bg  = self.cfg["overlay_bg_color"]
        if show_all:
            self._btn_all.config(bg=acc,  fg="#0a0a1a")
            self._btn_todo.config(bg=bg,   fg="#888")
        else:
            self._btn_todo.config(bg=acc,  fg="#0a0a1a")
            self._btn_all.config(bg=bg,    fg="#888")
        self.refresh()

    # ─── 任务刷新 ─────────────────────────────────────────────
    def refresh(self):
        for w in self.inner.winfo_children():
            w.destroy()

        show_all = self._show_all_var.get()
        max_n    = self.cfg.get("max_display_tasks", 10)
        tasks    = self.store.all() if show_all else self.store.active()
        tasks    = sorted(tasks, key=lambda t: (-t.priority, t.created_at))[:max_n]

        bg  = self.cfg["overlay_bg_color"]
        acc = self.cfg["overlay_accent_color"]
        fg  = self.cfg["overlay_text_color"]
        fs  = self.cfg["font_size"]

        if not tasks:
            tk.Label(self.inner, text=_t("overlay.empty"), bg=bg,
                     fg="#555", font=("Microsoft YaHei UI", fs),
                     justify="center").pack(pady=25)
        else:
            for i, t in enumerate(tasks):
                self._card(t, i, bg, acc, fg, fs)

        active = len(self.store.active())
        total  = len(self.store.all())
        self.status.config(
            text=_t("overlay.status", active=active, total=total))

    # ─── 单张任务卡片 ─────────────────────────────────────────
    def _card(self, t: Task, idx: int, bg, acc, fg, fs):
        pc = PRIORITY_COLORS.get(t.priority, acc)
        cb = "#16213e" if idx % 2 == 0 else "#0f3460"

        card = tk.Frame(self.inner, bg=cb, padx=5, pady=3,
                        highlightthickness=1, highlightbackground=pc)
        card.pack(fill="x", padx=3, pady=2)

        # ── 第1行：优先级点 + 标题 + 完成勾选 ──────────────
        row1 = tk.Frame(card, bg=cb)
        row1.pack(fill="x")

        tk.Label(row1, text="●", bg=cb, fg=pc,
                 font=("Arial", 8)).pack(side="left")
        title_s = (t.title[:20] + "…") if len(t.title) > 21 else t.title
        lbl = tk.Label(row1, text=title_s, bg=cb, fg=acc,
                       font=("Microsoft YaHei UI", fs - 1, "bold"), anchor="w")
        lbl.pack(side="left", fill="x", expand=True)

        var = tk.BooleanVar(value=t.completed)
        chk = tk.Checkbutton(row1, variable=var, bg=cb, fg=fg,
                              selectcolor=cb, activebackground=cb, bd=0,
                              command=lambda tid=t.task_id: self._toggle(tid))
        chk.pack(side="right")

        # ── 第2行：内容摘要 ──────────────────────────────────
        if t.content:
            s = (t.content[:36] + "…") if len(t.content) > 36 else t.content
            tk.Label(card, text=s, bg=cb, fg="#9e9e9e",
                     font=("Microsoft YaHei UI", fs - 2),
                     anchor="w", wraplength=260, justify="left").pack(fill="x")

        # ── 第3行：目标 + 闹钟 + 耗时 ───────────────────────
        info = []
        if t.goal:
            g = (t.goal[:16] + "…") if len(t.goal) > 16 else t.goal
            info.append(f"🎯{g}")
        if t.alarm_time:
            s = f"{t.alarm_date} {t.alarm_time}" if t.alarm_date else t.alarm_time
            info.append(f"⏰{s}")
        elapsed = t.elapsed_days
        if elapsed == 0:
            info.append(f"📅{_t('overlay.today')}")
        else:
            info.append(f"📅{_t('overlay.days', n=elapsed)}")
        if info:
            tk.Label(card, text="  ".join(info), bg=cb, fg="#ffd54f",
                     font=("Microsoft YaHei UI", fs - 2), anchor="w").pack(fill="x")

        # ── 标签 ────────────────────────────────────────────
        if t.tags:
            tk.Label(card, text=f"🏷 {t.tags}", bg=cb, fg="#ce93d8",
                     font=("Microsoft YaHei UI", fs - 2), anchor="w").pack(fill="x")

        # ── 进度条 ───────────────────────────────────────────
        prog = t.progress
        pcolor = _prog_color(prog)
        prog_row = tk.Frame(card, bg=cb)
        prog_row.pack(fill="x", pady=(2, 1))

        track = tk.Frame(prog_row, bg="#1a1a3a", height=5)
        track.pack(side="left", fill="x", expand=True, pady=2)
        tk.Frame(track, bg=pcolor, height=5).place(
            x=0, y=0, relheight=1.0, relwidth=prog / 100)

        tk.Label(prog_row, text=f"{prog}%", bg=cb, fg=pcolor,
                 font=("Microsoft YaHei UI", 7, "bold")).pack(side="right", padx=2)

        # ── 快速操作行 ───────────────────────────────────────
        action_row = tk.Frame(card, bg=cb)
        action_row.pack(fill="x", pady=(1, 0))

        # 快速进度按钮
        for pct in (25, 50, 75, 100):
            is_cur = (prog == pct)
            tc = pcolor if is_cur else "#555"
            bk = "#1a1a3a" if not is_cur else "#0f3460"
            tk.Button(action_row, text=f"{pct}%",
                      command=lambda p=pct, tid=t.task_id: self._quick_prog(tid, p),
                      bg=bk, fg=tc, relief="flat",
                      font=("Microsoft YaHei UI", 7), padx=3, pady=0,
                      cursor="hand2",
                      activebackground="#4fc3f7",
                      activeforeground="#000").pack(side="left", padx=1)

        pri_btn = tk.Button(
            action_row,
            text=f"🔥{priority_label(t.priority)}",
            command=lambda tid=t.task_id, p=t.priority: self._next_priority(tid, p),
            bg="#1a1a3a", fg=pc, relief="flat",
            font=("Microsoft YaHei UI", 7), padx=4, pady=0,
            cursor="hand2",
            activebackground=pc, activeforeground="#000")
        pri_btn.pack(side="right", padx=2)

        # 双击打开管理器
        def _dbl(e): self.open_cb()
        for w in [card, lbl] + list(card.winfo_children()):
            w.bind("<Double-Button-1>", _dbl)
            w.bind("<MouseWheel>",      self._scroll)

    # ─── 快速操作回调 ─────────────────────────────────────────
    def _toggle(self, tid: str):
        self.store.toggle(tid)
        self.refresh()

    def _quick_prog(self, tid: str, pct: int):
        t = self.store.get(tid)
        if not t:
            return
        t.progress = pct
        if pct == 100:
            t.completed = True
        t.touch()
        self.store.update(t)
        self.refresh()

    def _next_priority(self, tid: str, cur: int):
        """循环切换优先级：低→中→高→紧急→低"""
        t = self.store.get(tid)
        if not t:
            return
        t.priority = (cur % 4) + 1   # 1→2→3→4→1
        t.touch()
        self.store.update(t)
        self.refresh()

    # ─── 折叠 / 展开 ─────────────────────────────────────────
    def _toggle_min(self):
        ow = int(self.cfg.get("overlay_width", 300))
        oh = int(self.cfg.get("overlay_height", 600))
        if self._minimized:
            self.toolbar.pack(fill="x")
            self.body.pack(fill="both", expand=True)
            self.status_bar.pack(fill="x")
            self.win.geometry(f"{ow}x{oh}")
            try:
                self.grip.place(relx=1.0, rely=1.0, anchor="se", x=-2, y=-2)
                self.grip.lift()
            except Exception:
                pass
            self._minimized = False
        else:
            self.toolbar.pack_forget()
            self.body.pack_forget()
            self.status_bar.pack_forget()
            try:
                self.grip.place_forget()    # 折叠时藏起 grip，避免遮挡标题栏按钮
            except Exception:
                pass
            self.win.geometry(f"{ow}x26")
            self._minimized = True

    # ─── 拖动 ─────────────────────────────────────────────────
    def _on_press(self, e):
        self._drag_ox = e.x_root - self.win.winfo_x()
        self._drag_oy = e.y_root - self.win.winfo_y()

    def _on_drag(self, e):
        x = e.x_root - self._drag_ox
        y = e.y_root - self._drag_oy
        self.win.geometry(f"+{x}+{y}")
        self.cfg["overlay_x"] = x
        self.cfg["overlay_y"] = y

    # ─── 右下角拖手缩放 ──────────────────────────────────────
    # 折叠状态下不允许缩放（避免破坏折叠形态）。
    # 最小宽度 280：保证标题栏 4 个按钮（－ ＋ 🤖 ×）+ 图标 + 标题在中英文下都不被挤掉。
    # 最小高度 180：保证标题栏 + 工具栏 + 至少一行任务可见。
    MIN_W, MIN_H = 280, 180

    def _on_resize_press(self, e):
        if self._minimized:
            return
        self.win.update_idletasks()      # 同步真实尺寸，避免读到上一次拖拽队列中的旧值
        self._rs_x0 = e.x_root
        self._rs_y0 = e.y_root
        self._rs_w0 = self.win.winfo_width()
        self._rs_h0 = self.win.winfo_height()

    def _on_resize_drag(self, e):
        # 注：不再用 _rs_w0==0 做活跃判定，按下后即视为可拖；折叠状态除外。
        if self._minimized:
            return
        if self._rs_w0 <= 0 or self._rs_h0 <= 0:
            # 极端情况下 press 没记录到尺寸，按当前尺寸兜底
            self._rs_w0 = self.win.winfo_width()
            self._rs_h0 = self.win.winfo_height()
            self._rs_x0 = e.x_root
            self._rs_y0 = e.y_root
            return
        dw = e.x_root - self._rs_x0
        dh = e.y_root - self._rs_y0
        try:
            sw = self.win.winfo_screenwidth()
            sh = self.win.winfo_screenheight()
        except Exception:
            sw = sh = 99999
        x = self.win.winfo_x()
        y = self.win.winfo_y()
        new_w = max(self.MIN_W, min(self._rs_w0 + dw, sw - x))
        new_h = max(self.MIN_H, min(self._rs_h0 + dh, sh - y))
        self.win.geometry(f"{new_w}x{new_h}")

    def _on_resize_release(self, _e):
        if self._minimized:
            return
        try:
            self.win.update_idletasks()
            self.cfg["overlay_width"]  = int(self.win.winfo_width())
            self.cfg["overlay_height"] = int(self.win.winfo_height())
        except Exception:
            pass
        # 注意：不要把 _rs_w0/_rs_h0 重置为 0，
        # 否则一旦下次 press 因为 update_idletasks 时序问题没采到值，
        # drag 早返回就会出现"再也拖不动"。下次 press 会自然覆盖。

    def _scroll(self, e):
        self.canvas.yview_scroll(-1 * (e.delta // 120), "units")

    # ─── 公开接口 ─────────────────────────────────────────────
    def show(self):  self.win.deiconify()
    def hide(self):  self.win.withdraw()

    def update_cfg(self, new_cfg: dict):
        self.cfg = new_cfg
        self.win.wm_attributes("-alpha",   new_cfg.get("overlay_opacity", 0.90))
        self.win.wm_attributes("-topmost", new_cfg.get("overlay_always_top", True))
        # 同步待办/全部按钮状态
        show_all = new_cfg.get("show_completed", False)
        self._show_all_var.set(show_all)
        acc = new_cfg["overlay_accent_color"]
        bg  = new_cfg["overlay_bg_color"]
        if show_all:
            self._btn_all.config(bg=acc, fg="#0a0a1a")
            self._btn_todo.config(bg=bg,  fg="#888")
        else:
            self._btn_todo.config(bg=acc, fg="#0a0a1a")
            self._btn_all.config(bg=bg,   fg="#888")
        self.refresh()

    # ─── AI 问答 ──────────────────────────────────────────────
    def _on_open_ai(self):
        if self.open_ai_cb:
            self.open_ai_cb()

    # ─── 截图 ─────────────────────────────────────────────────
    def _on_screenshot(self):
        if self.screenshot_cb:
            self.screenshot_cb()

    # ─── 退出 ─────────────────────────────────────────────────
    def _on_quit(self):
        from tkinter import messagebox
        if messagebox.askokcancel(
                _t("common.exit"),
                _t("common.exit_confirm", app=_t("common.app_name")),
                parent=self.win):
            if self.quit_cb:
                self.quit_cb()
            else:
                self.root.destroy()

    # ─── 语言切换：销毁内部并重建 UI ──────────────────────────
    def rebuild_ui(self):
        try:
            for w in self.outer.winfo_children() + [self.outer]:
                w.destroy()
        except Exception:
            pass
        self._build()
        self.refresh()
