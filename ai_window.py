"""
AI 问答窗口 — 独立 Toplevel
 * 左侧：历史对话侧边栏（新建 / 切换 / 删除）
 * 右侧：气泡式对话区 + 输入区，每条消息独立容器，可选中复制
 * 每条问答实时落盘到 data/chat_history/chat_*.json
"""
import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime

from ai_chat import ChatSession, build_backend, build_backend_for_provider
from chat_history import HistoryStore

# ─── 配色 ──────────────────────────────────────────────────
BG      = "#0d1117"
BG2     = "#161b22"
BG3     = "#21262d"
BG_SIDE = "#0a0f16"
ACC     = "#58a6ff"
ACC2    = "#3fb950"
FG      = "#e6edf3"
FG_DIM  = "#8b949e"
FG_DIM2 = "#6e7681"
RED     = "#f85149"
YELLOW  = "#d29922"
HOVER   = "#1f2a3a"
SELECT  = "#1f3d5c"

# 气泡色
BUBBLE_USER_BG = "#1f6feb"   # 用户气泡 = 蓝色
BUBBLE_USER_FG = "#ffffff"
BUBBLE_AI_BG   = "#21262d"   # AI 气泡 = 深灰
BUBBLE_AI_FG   = "#e6edf3"
BUBBLE_SYS_BG  = "#0d1117"   # 系统提示
BUBBLE_SYS_FG  = "#8b949e"
BUBBLE_ERR_BG  = "#3d1b1b"
BUBBLE_ERR_FG  = "#ff7b72"

FONT_M    = ("Microsoft YaHei UI", 11)
FONT_S    = ("Microsoft YaHei UI", 9)
FONT_XS   = ("Microsoft YaHei UI", 8)
FONT_B    = ("Microsoft YaHei UI", 11, "bold")
FONT_SIDE = ("Microsoft YaHei UI", 10)


class AIChatWin:
    """AI 问答浮窗（单例）"""
    _instance = None

    @classmethod
    def open(cls, root: tk.Tk, cfg: dict, store=None):
        if cls._instance and cls._instance.win.winfo_exists():
            cls._instance.win.lift()
            cls._instance.win.focus_force()
            cls._instance._maybe_rebuild_backend(cfg)
            return
        cls._instance = cls(root, cfg, store)

    def __init__(self, root: tk.Tk, cfg: dict, store=None):
        self.root     = root
        self.cfg      = cfg
        self.store    = store
        self._thinking = False

        # AI 后端与当前对话 session
        self._backend = build_backend(cfg)
        self._session = ChatSession(self._backend)

        # 历史存储 & 当前会话记录（跟随 cfg['data_dir']，便于跨机器迁移）
        try:
            import config as _cfg_mod
            _chat_dir = _cfg_mod.ensure_data_dir(self.cfg) / "chat_history"
        except Exception:
            _chat_dir = None
        self._history    = HistoryStore(_chat_dir)
        self._cur_record = self._history.new_session(self._backend)

        # 气泡管理：当前流式中的 AI 气泡引用
        self._cur_ai_bubble = None   # {"frame","text","buf"} or None
        # 批量载入历史时，暂时抑制每条气泡触发的滚动/高度测算
        self._bulk_loading = False

        self.win = tk.Toplevel(root)
        self._build_win()
        self._refresh_history_list()
        self._show_welcome()

    # ─── 窗口骨架 ─────────────────────────────────────────────
    def _build_win(self):
        w = self.win
        w.title("🤖 AI 智能助手")
        w.geometry("1060x680")
        w.minsize(860, 540)
        w.configure(bg=BG)
        w.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_topbar(w)

        body = tk.Frame(w, bg=BG)
        body.pack(fill="both", expand=True)

        self._build_sidebar(body)
        self._build_chat_area(body)

    # ─── 顶栏 ─────────────────────────────────────────────────
    def _build_topbar(self, parent):
        top = tk.Frame(parent, bg=BG3, height=40)
        top.pack(fill="x", side="top")
        top.pack_propagate(False)

        tk.Label(top, text="🤖 AI 智能助手", bg=BG3, fg=ACC,
                 font=("Microsoft YaHei UI", 12, "bold")).pack(side="left", padx=12)

        self._lbl_backend = tk.Label(top, text="", bg=BG3, fg=FG_DIM, font=FONT_S)
        self._lbl_backend.pack(side="left", padx=4)
        self._update_backend_label()

        def _btn(txt, cmd, fg=FG_DIM):
            return tk.Button(top, text=txt, command=cmd,
                             bg=BG3, fg=fg, relief="flat", padx=10, pady=0,
                             font=FONT_S, cursor="hand2",
                             activebackground=BG2, activeforeground=FG)

        _btn("🔄 重建连接", self._rebuild_backend, fg=ACC).pack(side="right", padx=4)

        # ── 模型切换下拉 ────────────────────────────────────
        self._MODEL_CHOICES = [
            ("ollama",   "🟢 Ollama 本地"),
            ("hunyuan",  "🐉 腾讯混元"),
            ("groq",     "⚡ Groq 免费"),
            ("deepseek", "🔵 DeepSeek"),
            ("moonshot", "🌙 Moonshot"),
            ("openai",   "🤖 OpenAI"),
            ("custom",   "🔧 自定义"),
        ]
        tk.Label(top, text="模型:", bg=BG3, fg=FG_DIM, font=FONT_S
                 ).pack(side="right", padx=(8, 2))
        self._model_var = tk.StringVar()
        self._cmb_model = ttk.Combobox(
            top, textvariable=self._model_var,
            values=[lbl for _pid, lbl in self._MODEL_CHOICES],
            state="readonly", width=16, font=FONT_S)
        self._cmb_model.pack(side="right", padx=2, pady=6)
        self._cmb_model.bind("<<ComboboxSelected>>", self._on_model_switch)
        # 初始化下拉显示
        self._sync_model_dropdown()

    def _current_provider_id(self) -> str:
        """根据当前 cfg 推断下拉应选中哪个 provider id"""
        ai = self.cfg.get("ai", {}) or {}
        if ai.get("prefer_ollama", False):
            return "ollama"
        pid = ai.get("active_provider", "hunyuan")
        valid = {p for p, _ in self._MODEL_CHOICES}
        return pid if pid in valid else "hunyuan"

    def _sync_model_dropdown(self):
        """把下拉显示与 cfg.active_provider 保持一致"""
        pid = self._current_provider_id()
        for p, lbl in self._MODEL_CHOICES:
            if p == pid:
                self._model_var.set(lbl)
                return
        # 兜底
        self._model_var.set(self._MODEL_CHOICES[1][1])

    def _on_model_switch(self, _evt=None):
        """下拉切换模型 → 更新 cfg.active_provider → 重建后端"""
        label = self._model_var.get()
        pid = next((p for p, lbl in self._MODEL_CHOICES if lbl == label), None)
        if not pid:
            return

        # 更新 cfg 中的 active_provider 与 prefer_ollama
        ai = self.cfg.setdefault("ai", {})
        if pid == "ollama":
            ai["prefer_ollama"] = True
        else:
            ai["prefer_ollama"] = False
            ai["active_provider"] = pid

        # 落盘（复用 config 模块）
        try:
            import config as cfg_mod
            cfg_mod.save(self.cfg)
        except Exception:
            pass

        # 重建后端
        self._backend = build_backend_for_provider(self.cfg, pid)
        self._session.backend = self._backend
        self._update_backend_label()

        # 检查是否配置了 key（custom / 非混元且未配置时提醒）
        name = type(self._backend).__name__
        if name == "OfflineBackend":
            self._add_sys_bubble(
                f"⚠ 已切换到「{label}」，但尚未配置 API Key。请到「任务管家 → 设置 → AI 配置」填入。")
        else:
            self._add_sys_bubble(f"✅ 已切换到「{label}」")

    # ─── 左侧历史侧边栏 ───────────────────────────────────────
    def _build_sidebar(self, parent):
        side = tk.Frame(parent, bg=BG_SIDE, width=240)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)

        head = tk.Frame(side, bg=BG_SIDE)
        head.pack(fill="x", padx=8, pady=(10, 6))

        tk.Label(head, text="历史对话", bg=BG_SIDE, fg=FG,
                 font=("Microsoft YaHei UI", 11, "bold")).pack(side="left")

        tk.Button(head, text="＋ 新建",
                  command=self._new_chat,
                  bg=ACC, fg="#0d1117", relief="flat",
                  font=FONT_S, padx=10, pady=2, cursor="hand2",
                  activebackground="#1f6feb", activeforeground="#fff"
                  ).pack(side="right")

        list_wrap = tk.Frame(side, bg=BG_SIDE)
        list_wrap.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        self._side_canvas = tk.Canvas(list_wrap, bg=BG_SIDE, highlightthickness=0, bd=0)
        vsb = tk.Scrollbar(list_wrap, orient="vertical",
                           command=self._side_canvas.yview,
                           width=6, troughcolor=BG_SIDE, bg="#333", relief="flat")
        self._side_inner = tk.Frame(self._side_canvas, bg=BG_SIDE)

        self._side_inner.bind(
            "<Configure>",
            lambda e: self._side_canvas.configure(
                scrollregion=self._side_canvas.bbox("all"))
        )
        self._side_canvas_window = self._side_canvas.create_window(
            (0, 0), window=self._side_inner, anchor="nw")
        self._side_canvas.bind(
            "<Configure>",
            lambda e: self._side_canvas.itemconfigure(
                self._side_canvas_window, width=e.width)
        )
        self._side_canvas.configure(yscrollcommand=vsb.set)

        self._side_canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        # 鼠标滚轮：只在悬停侧边栏时响应（不再 bind_all，避免与右侧对话区冲突）
        self._bind_wheel(self._side_canvas,
                         lambda e: self._side_canvas.yview_scroll(
                             int(-1 * (e.delta / 120)), "units"))

        # 底部说明
        tk.Label(side,
                 text="对话自动保存至：\ndata/chat_history/",
                 bg=BG_SIDE, fg=FG_DIM2, font=FONT_XS, justify="left"
                 ).pack(side="bottom", padx=8, pady=(0, 8), anchor="w")

    # ─── 右侧：对话 + 输入 ─────────────────────────────────────
    def _build_chat_area(self, parent):
        right = tk.Frame(parent, bg=BG)
        right.pack(side="left", fill="both", expand=True)

        # 底部 -> 顶部顺序 pack，保证输入区永远可见
        status = tk.Frame(right, bg=BG, height=22)
        status.pack(side="bottom", fill="x")
        status.pack_propagate(False)
        self._lbl_status = tk.Label(status, text="就绪", bg=BG, fg=FG_DIM,
                                    font=FONT_S, anchor="w")
        self._lbl_status.pack(fill="x", padx=12)

        # 输入区
        input_frame = tk.Frame(right, bg=BG2, height=110)
        input_frame.pack(side="bottom", fill="x", padx=8, pady=(4, 6))
        input_frame.pack_propagate(False)

        inner = tk.Frame(input_frame, bg=BG2)
        inner.pack(fill="both", expand=True, padx=6, pady=6)

        self.entry = tk.Text(
            inner,
            bg=BG3, fg=FG, font=FONT_M,
            relief="flat", bd=0,
            insertbackground=FG,
            wrap="word",
            height=3,
            highlightthickness=1,
            highlightbackground="#30363d",
            highlightcolor=ACC,
        )
        self.entry.pack(side="left", fill="both", expand=True, padx=(0, 8))
        self.entry.bind("<Return>",         self._on_enter)
        self.entry.bind("<Control-Return>", lambda e: self._send())

        btn_col = tk.Frame(inner, bg=BG2, width=94)
        btn_col.pack(side="right", fill="y")
        btn_col.pack_propagate(False)

        self._btn_send = tk.Button(
            btn_col, text="发送 ⏎",
            command=self._send,
            bg=ACC, fg="#0d1117",
            relief="flat",
            font=("Microsoft YaHei UI", 11, "bold"),
            cursor="hand2",
            activebackground="#1f6feb", activeforeground="#fff",
        )
        self._btn_send.pack(fill="both", expand=True)

        tk.Label(btn_col, text="Shift+Enter 换行",
                 bg=BG2, fg=FG_DIM2, font=FONT_XS).pack(pady=(4, 0))

        # 快捷提示
        hint_frame = tk.Frame(right, bg=BG, height=36)
        hint_frame.pack(side="bottom", fill="x", padx=8)
        hint_frame.pack_propagate(False)

        tk.Label(hint_frame, text="💡 示例提问（可自由输入任何问题）：",
                 bg=BG, fg=FG_DIM, font=FONT_XS).pack(side="left", padx=(4, 6))

        HINTS = [
            ("今日任务建议",  "请帮我分析当前任务的优先级，给出今日工作安排建议"),
            ("时间规划",      "如何合理规划每天的时间，提升工作效率？"),
            ("目标拆解",      "帮我把一个大目标拆解为可执行的小步骤"),
            ("效率技巧",      "推荐几个提升个人效率的实用方法"),
        ]
        for txt, msg in HINTS:
            tk.Button(
                hint_frame, text=txt,
                command=lambda m=msg: self._fill_entry(m),
                bg=BG2, fg=FG_DIM, relief="flat",
                font=FONT_XS, padx=6, pady=2, cursor="hand2",
                activebackground=BG3, activeforeground=ACC,
            ).pack(side="left", padx=2)

        # 对话区（气泡列表）
        chat_frame = tk.Frame(right, bg=BG)
        chat_frame.pack(side="top", fill="both", expand=True, padx=8, pady=(6, 0))

        self._chat_canvas = tk.Canvas(chat_frame, bg=BG,
                                      highlightthickness=0, bd=0)
        chat_vsb = tk.Scrollbar(chat_frame, orient="vertical",
                                command=self._chat_canvas.yview,
                                width=8, troughcolor=BG, bg="#333", relief="flat")
        self._chat_canvas.configure(yscrollcommand=chat_vsb.set)

        chat_vsb.pack(side="right", fill="y")
        self._chat_canvas.pack(side="left", fill="both", expand=True)

        # 气泡容器
        self._chat_inner = tk.Frame(self._chat_canvas, bg=BG)
        self._chat_window = self._chat_canvas.create_window(
            (0, 0), window=self._chat_inner, anchor="nw")

        def _on_inner_configure(_e):
            self._chat_canvas.configure(
                scrollregion=self._chat_canvas.bbox("all"))
        self._chat_inner.bind("<Configure>", _on_inner_configure)

        def _on_canvas_configure(e):
            # 让气泡容器宽度自动跟随 canvas，气泡才能左右对齐
            self._chat_canvas.itemconfigure(self._chat_window, width=e.width)
            # 触发所有气泡重算宽度
            self._reflow_bubbles(e.width)
        self._chat_canvas.bind("<Configure>", _on_canvas_configure)

        # 鼠标滚轮：只在悬停对话区时滚动对话区
        self._bind_wheel(self._chat_canvas,
                         lambda e: self._chat_canvas.yview_scroll(
                             int(-1 * (e.delta / 120)), "units"))

        # 所有已渲染的气泡 [(role, frame, text_widget), ...]，用于窗口缩放时重算宽度
        self._bubbles = []

    # ─── 鼠标滚轮：悬停才绑定 ────────────────────────────────
    def _bind_wheel(self, widget, handler):
        """
        只在鼠标进入该 widget 或其子代时绑定 <MouseWheel>，离开时解绑。
        避免全局 bind_all 导致左右两个滚动区域互相干扰。
        """
        def _enter(_e):
            widget.bind_all("<MouseWheel>", handler)
        def _leave(_e):
            widget.unbind_all("<MouseWheel>")
        widget.bind("<Enter>", _enter)
        widget.bind("<Leave>", _leave)

    # ─── 快捷填入 ─────────────────────────────────────────────
    def _fill_entry(self, text: str):
        self.entry.delete("1.0", "end")
        self.entry.insert("1.0", text)
        self.entry.focus_set()

    # ─── 后端状态 ─────────────────────────────────────────────
    def _update_backend_label(self):
        b = self._backend
        name = type(b).__name__
        if name == "OllamaBackend":
            txt, color = f"🟢 Ollama 本地 · {b.model}", "#3fb950"
        elif name == "OpenAICompatBackend":
            display = getattr(b, "label", None) \
                      or b.base.replace("https://", "").split("/")[0]
            txt, color = f"🔵 {display} · {b.model}", ACC
        else:
            txt, color = "⚫ 离线模式（未配置）", FG_DIM
        self._lbl_backend.config(text=txt, fg=color)

    def _maybe_rebuild_backend(self, new_cfg: dict):
        self.cfg = new_cfg
        self._backend = build_backend(new_cfg)
        self._session.backend = self._backend
        self._update_backend_label()
        # 设置保存后，同步下拉显示到最新 active_provider
        if hasattr(self, "_model_var"):
            self._sync_model_dropdown()

    def _rebuild_backend(self):
        self._backend = build_backend(self.cfg)
        self._session.backend = self._backend
        self._update_backend_label()
        self._add_sys_bubble("✅ 已重建 AI 连接")

    # ─── 气泡渲染 ─────────────────────────────────────────────
    def _text_line_count(self, text_widget, bubble_width_chars):
        """估算 Text 需要的行数（考虑自动换行）"""
        content = text_widget.get("1.0", "end-1c")
        if not content:
            return 1
        lines = content.split("\n")
        total = 0
        for ln in lines:
            # 按字符数估算（中文按 2 宽度近似）
            w = sum(2 if ord(ch) > 127 else 1 for ch in ln)
            total += max(1, (w // bubble_width_chars) + (1 if w % bubble_width_chars else 0))
        return max(1, total)

    def _fit_bubble_height(self, text_widget, bubble_width_chars):
        """根据内容真实高度调整 Text 高度（考虑自动换行）

        优先用 Tk 的 count(..., 'displaylines') 拿真实显示行数；
        若失败（旧版本 Tk 或尚未布局完成），回退到字符宽度估算。
        """
        try:
            text_widget.update_idletasks()
            # Tk 8.5+ 支持 displaylines，考虑自动换行后的实际显示行数
            try:
                dl = text_widget.count("1.0", "end-1c", "displaylines")
                if isinstance(dl, tuple):
                    dl = dl[0] if dl else None
                if dl and dl > 0:
                    text_widget.configure(height=max(1, int(dl)))
                    return
            except (tk.TclError, TypeError, ValueError):
                pass

            # 回退：用字符数 / 每行字符数 估算
            content = text_widget.get("1.0", "end-1c")
            if not content:
                text_widget.configure(height=1)
                return
            total = 0
            per_line = max(1, int(bubble_width_chars))
            for ln in content.split("\n"):
                w = sum(2 if ord(ch) > 127 else 1 for ch in ln)
                # 空行至少 1 行；有内容按宽度折算
                total += max(1, (w + per_line - 1) // per_line)
            text_widget.configure(height=max(1, total))
        except Exception:
            try:
                text_widget.configure(height=3)
            except Exception:
                pass

    def _make_bubble(self, role: str, content: str, time_str: str = "",
                      model_label: str = ""):
        """
        role: 'user' | 'assistant' | 'system' | 'error'
        返回 (frame, text_widget)
        """
        # 配色 & 对齐方向
        if role == "user":
            bg_b, fg_b = BUBBLE_USER_BG, BUBBLE_USER_FG
            anchor, side = "e", "right"
            nick = "👤 你"
            nick_color = ACC
        elif role == "assistant":
            bg_b, fg_b = BUBBLE_AI_BG, BUBBLE_AI_FG
            anchor, side = "w", "left"
            nick = f"🤖 AI{'  ·  ' + model_label if model_label else ''}"
            nick_color = ACC2
        elif role == "error":
            bg_b, fg_b = BUBBLE_ERR_BG, BUBBLE_ERR_FG
            anchor, side = "w", "left"
            nick = "❌ 错误"
            nick_color = RED
        else:   # system
            bg_b, fg_b = BUBBLE_SYS_BG, BUBBLE_SYS_FG
            anchor, side = "center", "top"
            nick = ""
            nick_color = FG_DIM

        # 外层行容器（占满宽度，用于左右/居中定位）
        row = tk.Frame(self._chat_inner, bg=BG)
        row.pack(fill="x", padx=6, pady=4)

        # 气泡本体（限宽，贴边显示）
        bubble = tk.Frame(row, bg=bg_b)

        # 气泡头部（昵称 + 时间）
        if nick or time_str:
            head = tk.Frame(bubble, bg=bg_b)
            head.pack(fill="x", padx=10, pady=(6, 0))
            if nick:
                tk.Label(head, text=nick, bg=bg_b, fg=nick_color,
                         font=FONT_B).pack(side="left")
            if time_str:
                tk.Label(head, text=time_str, bg=bg_b, fg=FG_DIM,
                         font=FONT_XS).pack(side="left", padx=(6, 0))

        # 内容区：Text（支持选中复制）
        txt = tk.Text(
            bubble,
            bg=bg_b, fg=fg_b, font=FONT_M,
            wrap="word", relief="flat", bd=0,
            padx=10, pady=(4 if nick or time_str else 8),
            highlightthickness=0,
            cursor="xterm",
            selectbackground="#4493f8",
            selectforeground="#ffffff",
            height=1,
            width=1,
        )
        txt.insert("1.0", content)
        # 禁用编辑但保留选中/复制
        txt.configure(state="disabled")
        # 允许 Ctrl+C 拷贝（disabled 下 Text 默认也可 Ctrl+C，但 Keypress 可能被吞，保险起见主动绑）
        def _copy_selection(_e=None, w=txt):
            try:
                sel = w.get("sel.first", "sel.last")
                self.win.clipboard_clear()
                self.win.clipboard_append(sel)
            except tk.TclError:
                pass
            return "break"
        txt.bind("<Control-c>", _copy_selection)
        txt.bind("<Control-C>", _copy_selection)

        # 右键菜单（复制 / 复制整条）
        menu = tk.Menu(txt, tearoff=0, bg=BG3, fg=FG,
                       activebackground=ACC, activeforeground="#0d1117")
        menu.add_command(label="复制选中", command=_copy_selection)
        def _copy_all(w=txt):
            self.win.clipboard_clear()
            self.win.clipboard_append(w.get("1.0", "end-1c"))
        menu.add_command(label="复制整条", command=_copy_all)
        def _popup(event, m=menu):
            m.tk_popup(event.x_root, event.y_root)
        txt.bind("<Button-3>", _popup)

        txt.pack(fill="both", padx=0, pady=(0, 6))

        bubble.pack(side=side, anchor=anchor, padx=4)

        # 记录并重算宽度
        self._bubbles.append({"role": role, "row": row, "bubble": bubble,
                              "text": txt})
        cur_w = self._chat_canvas.winfo_width()
        if not cur_w or cur_w < 50:
            cur_w = 780
        self._apply_bubble_width(row, bubble, txt, cur_w)

        # 几何布局稳定后再测一次高度（解决：初次 update_idletasks 拿不到
        # 正确 displaylines，导致长消息被压成一行）
        def _re_fit():
            try:
                w = self._chat_canvas.winfo_width() or cur_w
                max_px = max(200, int(w * 0.70))
                char_w = max(14, int(max_px / 10))
                self._fit_bubble_height(txt, char_w)
                if not self._bulk_loading:
                    self._scroll_to_bottom()
            except Exception:
                pass
        self.win.after_idle(_re_fit)

        # 滚到底（批量载入时抑制，避免反复跳到旧 scrollregion 的底部出现空白）
        if not self._bulk_loading:
            self.win.after_idle(self._scroll_to_bottom)

        return row, bubble, txt

    def _apply_bubble_width(self, row, bubble, text_widget, canvas_w: int):
        """根据 canvas 宽度设定气泡的字符宽度（气泡最大占 canvas 宽度 70%）"""
        # 像素 → 字符：中文约 14px，英文约 8px，取折中 9px 做列宽估计
        max_px = max(200, int(canvas_w * 0.70))
        char_w = max(14, int(max_px / 10))   # Text width 是字符数
        try:
            text_widget.configure(width=char_w)
        except Exception:
            pass
        # 高度自适应
        self._fit_bubble_height(text_widget, char_w)

    def _reflow_bubbles(self, canvas_w: int):
        for b in self._bubbles:
            self._apply_bubble_width(b["row"], b["bubble"], b["text"], canvas_w)

    def _scroll_to_bottom(self):
        try:
            self._chat_canvas.update_idletasks()
            self._chat_canvas.yview_moveto(1.0)
        except Exception:
            pass

    # 系统/欢迎气泡（居中、浅色小字）
    def _add_sys_bubble(self, text: str):
        self._make_bubble("system", text)

    def _clear_chat_area(self):
        for child in self._chat_inner.winfo_children():
            child.destroy()
        self._bubbles = []
        self._cur_ai_bubble = None
        # 主动重置 canvas 滚动区域 & 视图位置，避免切换历史时
        # 残留上一次对话的大 scrollregion 导致视图停在一片空白
        try:
            self._chat_canvas.configure(scrollregion=(0, 0, 0, 0))
            self._chat_canvas.yview_moveto(0)
        except Exception:
            pass

    def _show_welcome(self):
        b = self._backend
        name = type(b).__name__
        if name == "OllamaBackend":
            mode = f"已连接本地 Ollama（{b.model}）"
        elif name == "OpenAICompatBackend":
            display = getattr(b, "label", None) or "云端 API"
            mode = f"已连接 {display}（{b.model}）"
        else:
            mode = "当前为离线模式，请在「设置 → AI 配置」填写 API Key"
        welcome = (
            "欢迎使用 AI 智能助手 🤖\n"
            f"当前模式：{mode}\n"
            "💬 Enter 发送 / Shift+Enter 换行 · 对话自动保存到 data/chat_history/"
        )
        self._add_sys_bubble(welcome)

    # ─── 历史侧边栏 ───────────────────────────────────────────
    def _refresh_history_list(self):
        for child in self._side_inner.winfo_children():
            child.destroy()

        sessions = self._history.list_sessions()
        if not sessions:
            tk.Label(self._side_inner,
                     text="（暂无历史对话）\n开始聊天后会自动保存",
                     bg=BG_SIDE, fg=FG_DIM2, font=FONT_XS, justify="left"
                     ).pack(pady=10, padx=6, anchor="w")
            return

        cur_sid = self._cur_record.get("session_id")
        for s in sessions:
            self._make_history_item(s, is_current=(s["session_id"] == cur_sid))

    def _make_history_item(self, s: dict, is_current: bool):
        bg_item = SELECT if is_current else BG_SIDE
        item = tk.Frame(self._side_inner, bg=bg_item, cursor="hand2")
        item.pack(fill="x", padx=2, pady=2)

        title = s["title"] or "新对话"
        if len(title) > 20:
            title = title[:20] + "…"

        ts = s.get("updated_at", "")[5:16]   # MM-DD HH:MM

        lbl_title = tk.Label(item, text=title, bg=bg_item, fg=FG,
                             font=FONT_SIDE, anchor="w", justify="left")
        lbl_title.pack(fill="x", padx=8, pady=(6, 0), anchor="w")

        meta_txt = f"{ts}  ·  {s.get('msg_count', 0)} 条"
        lbl_meta = tk.Label(item, text=meta_txt, bg=bg_item, fg=FG_DIM2,
                            font=FONT_XS, anchor="w")
        lbl_meta.pack(fill="x", padx=8, pady=(0, 6), anchor="w")

        btn_del = tk.Label(item, text="✕", bg=bg_item, fg=FG_DIM2,
                           font=FONT_S, cursor="hand2")
        btn_del.place(relx=1.0, rely=0.0, anchor="ne", x=-4, y=2)

        def _select(event=None, sid=s["session_id"]):
            self._load_history(sid)

        def _delete(event=None, sid=s["session_id"], title=s["title"]):
            if messagebox.askyesno(
                "删除对话",
                f"确定删除对话「{title[:20]}」？\n此操作不可恢复。",
                parent=self.win,
            ):
                self._history.delete(sid)
                if sid == self._cur_record.get("session_id"):
                    self._new_chat()
                else:
                    self._refresh_history_list()
            return "break"

        def _enter(_e=None):
            if not is_current:
                item.configure(bg=HOVER)
                for c in (lbl_title, lbl_meta, btn_del):
                    c.configure(bg=HOVER)
                btn_del.configure(fg=RED)

        def _leave(_e=None):
            if not is_current:
                item.configure(bg=BG_SIDE)
                for c in (lbl_title, lbl_meta, btn_del):
                    c.configure(bg=BG_SIDE)
                btn_del.configure(fg=FG_DIM2)

        for widget in (item, lbl_title, lbl_meta):
            widget.bind("<Button-1>", _select)
            widget.bind("<Enter>", _enter)
            widget.bind("<Leave>", _leave)

        btn_del.bind("<Button-1>", _delete)
        btn_del.bind("<Enter>", _enter)
        btn_del.bind("<Leave>", _leave)

    # ─── 新建会话 ─────────────────────────────────────────────
    def _new_chat(self):
        if self._thinking:
            messagebox.showinfo("稍候", "AI 正在回复，请等待完成后再新建对话",
                                parent=self.win)
            return
        self._session.clear()
        self._cur_record = self._history.new_session(self._backend)
        self._cur_ai_bubble = None
        self._clear_chat_area()
        self._show_welcome()
        self._refresh_history_list()
        self._lbl_status.config(text="已新建对话")

    # ─── 加载历史 ─────────────────────────────────────────────
    def _load_history(self, session_id: str):
        if self._thinking:
            messagebox.showinfo("稍候", "AI 正在回复，请等待完成后再切换对话",
                                parent=self.win)
            return
        rec = self._history.load(session_id)
        if not rec:
            messagebox.showerror("错误", "对话文件读取失败", parent=self.win)
            return

        self._session.clear()
        for m in rec.get("messages", []):
            role = m.get("role")
            if role in ("user", "assistant"):
                self._session.history.append({
                    "role": role,
                    "content": m.get("content", ""),
                })

        self._cur_record = rec
        self._cur_ai_bubble = None

        # 渲染
        self._clear_chat_area()
        self._bulk_loading = True
        self._add_sys_bubble(
            f"📂 已载入历史对话：{rec.get('title', '')}\n"
            f"创建 {rec.get('created_at', '')}  ·  更新 {rec.get('updated_at', '')}  ·  "
            f"{rec.get('label', '')} / {rec.get('model', '')}"
        )
        for m in rec.get("messages", []):
            t = (m.get("time") or "")[11:16]
            role = m.get("role")
            content = m.get("content", "")
            if role == "user":
                self._make_bubble("user", content, time_str=t)
            elif role == "assistant":
                self._make_bubble("assistant", content, time_str=t,
                                  model_label=m.get("label") or "")

        # 等 Tk 完成布局后，再整体 reflow 一次——
        # 避免首次创建时因为 canvas 宽度未就绪导致高度被压成 1 行、
        # 长消息内容看不见的问题。同时刷新 scrollregion 并滚到顶部，
        # 这样用户点击历史对话后看到的是对话开头，而不是一片空白。
        def _post_load_reflow():
            try:
                w = self._chat_canvas.winfo_width() or 780
                self._reflow_bubbles(w)
                # 强制 Tk 完成 inner frame 布局 → 触发 <Configure>
                # → 更新 canvas.scrollregion
                self._chat_inner.update_idletasks()
                bbox = self._chat_canvas.bbox("all")
                if bbox:
                    self._chat_canvas.configure(scrollregion=bbox)
                self._chat_canvas.update_idletasks()
                # 滚到顶部（载入历史时）
                self._chat_canvas.yview_moveto(0)
            except Exception:
                pass
        # 两次延时：覆盖 canvas <Configure> 和 inner <Configure> 的时序竞争
        self.win.after(50, _post_load_reflow)

        def _finalize():
            _post_load_reflow()
            self._bulk_loading = False
        self.win.after(300, _finalize)

        self._refresh_history_list()
        self._lbl_status.config(text=f"已载入：{rec.get('title', '')}")

    # ─── 发送消息 ─────────────────────────────────────────────
    def _on_enter(self, event):
        if event.state & 0x1:   # Shift
            return
        self._send()
        return "break"

    def _send(self, prefill: str = ""):
        if self._thinking:
            return
        msg = prefill or self.entry.get("1.0", "end-1c").strip()
        if not msg:
            return
        self.entry.delete("1.0", "end")

        ts = datetime.now().strftime("%H:%M")

        # 用户气泡
        self._make_bubble("user", msg, time_str=ts)

        # 持久化：用户消息
        try:
            self._history.append(self._cur_record, "user", msg, self._backend)
        except Exception as e:
            print(f"[chat_history] save user failed: {e}")

        self._refresh_history_list()

        # 空的 AI 气泡占位（流式追加）
        label = getattr(self._backend, "label", None) or ""
        row, bubble, ai_txt = self._make_bubble(
            "assistant", "", time_str=ts, model_label=label)
        self._cur_ai_bubble = {"text": ai_txt, "buf": ""}

        self._thinking = True
        self._btn_send.config(state="disabled", text="⏳ 思考中")
        self._lbl_status.config(text="AI 正在思考中…")

        def _append_to_ai(tok: str):
            self._cur_ai_bubble["buf"] += tok
            w = self._cur_ai_bubble["text"]
            w.configure(state="normal")
            w.insert("end", tok)
            w.configure(state="disabled")
            # 动态扩行
            try:
                line_num = int(w.index("end-1c").split(".")[0])
                if line_num != int(w.cget("height")):
                    w.configure(height=max(1, line_num))
            except Exception:
                pass
            self._scroll_to_bottom()

        def on_token(tok: str):
            self.root.after(0, lambda t=tok: _append_to_ai(t))

        def on_done(full: str):
            def _finish():
                self._thinking = False
                self._btn_send.config(state="normal", text="发送 ⏎")
                self._lbl_status.config(text=f"回复完成 · {len(full)} 字  ·  已保存")
                self._cur_ai_bubble = None
                # 持久化：AI 回复
                try:
                    self._history.append(self._cur_record, "assistant",
                                         full, self._backend)
                except Exception as e:
                    print(f"[chat_history] save ai failed: {e}")
                self._refresh_history_list()
            self.root.after(0, _finish)

        def on_error(err: str):
            def _show():
                self._make_bubble("error", err)
                self._thinking = False
                self._btn_send.config(state="normal", text="发送 ⏎")
                self._lbl_status.config(text="发送失败，请检查配置")
                self._cur_ai_bubble = None
                try:
                    self._history.append(self._cur_record, "assistant",
                                         f"[ERROR] {err}", self._backend)
                except Exception:
                    pass
                self._refresh_history_list()
            self.root.after(0, _show)

        self._session.send_stream(msg, on_token, on_done, on_error)

    # ─── 关闭 ─────────────────────────────────────────────────
    def _on_close(self):
        AIChatWin._instance = None
        self.win.destroy()
