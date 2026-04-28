"""
Markdown 放大编辑器 — 独立 Toplevel
 * 左侧：大号 Text 编辑区（支持 Ctrl+F 搜索、F3 下一处、Shift+F3 上一处、Ctrl+H 替换）
 * 右侧：Markdown 实时预览（纯 Tk Text 渲染，无需第三方依赖）
 * 顶栏：字体缩放、搜索栏、视图切换（编辑/预览/分屏）
 * 底部：确定 / 取消；确定回调把文本写回调用方

对外仅暴露 `MarkdownEditor.open(parent, initial_text, title, on_save)`
"""
from __future__ import annotations

import os
import re
import tkinter as tk
from pathlib import Path
from tkinter import ttk, font as tkfont

from i18n import t as _t

# 图片预览依赖（可选）
try:
    from PIL import Image, ImageTk
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False

# ─── 配色（与主程序保持一致的深色调）────────────────────────
BG      = "#1e1e2e"
BG2     = "#2a2a3e"
BG3     = "#0f3460"
BG_CODE = "#11111b"
ACC     = "#4fc3f7"
ACC2    = "#7c4dff"
FG      = "#e0e0e0"
FG_DIM  = "#9e9e9e"
RED     = "#ef5350"
GREEN   = "#66bb6a"
YELLOW  = "#ffd54f"
ORANGE  = "#ff9800"
LINK    = "#81d4fa"
QUOTE   = "#b39ddb"
HL_BG   = "#5d4037"   # 搜索高亮底色
HL_CUR  = "#ff6f00"   # 当前命中


# ══════════════════════════════════════════════════════════
# 轻量级 Markdown → Tk Text 渲染
#   支持：H1~H6 / 粗体 / 斜体 / 行内代码 / 代码块 / 无序列表 /
#        有序列表 / 引用 / 链接 / 分割线 / 任务列表 / 水平线
# ══════════════════════════════════════════════════════════
class _MarkdownRenderer:
    """把 markdown 文本渲染到一个只读 Text 控件上，用 tag 做样式"""

    HEADING_SIZES = {1: 20, 2: 17, 3: 15, 4: 13, 5: 12, 6: 11}

    def __init__(self, text_widget: tk.Text, base_font_size: int = 11,
                 base_dir: Path | None = None):
        self.w = text_widget
        self.base = base_font_size
        self.base_dir = Path(base_dir) if base_dir else None
        # 图片引用缓存，防止 PhotoImage 被 GC 后图片消失
        self._img_refs: list = []
        self._setup_tags()

    # ── 标签样式（Tk Text 的 tag_configure） ──────────────
    def _setup_tags(self):
        w = self.w
        family = "Microsoft YaHei UI"
        code_family = "Consolas"

        # 标题
        for level, size in self.HEADING_SIZES.items():
            w.tag_configure(
                f"h{level}",
                font=(family, size, "bold"),
                foreground="#fff" if level <= 2 else ACC,
                spacing1=10, spacing3=6,
            )
        # 段落正文
        w.tag_configure("body", font=(family, self.base),
                        foreground=FG, spacing1=2, spacing3=4)
        # 粗体 / 斜体 / 粗斜体
        w.tag_configure("bold",    font=(family, self.base, "bold"),
                        foreground="#fff")
        w.tag_configure("italic",  font=(family, self.base, "italic"),
                        foreground=FG)
        w.tag_configure("bolditalic",
                        font=(family, self.base, "bold italic"),
                        foreground="#fff")
        # 行内代码
        w.tag_configure("code_inline",
                        font=(code_family, self.base),
                        background=BG_CODE, foreground="#ffab40")
        # 代码块
        w.tag_configure("code_block",
                        font=(code_family, self.base),
                        background=BG_CODE, foreground="#c5e1a5",
                        lmargin1=16, lmargin2=16, spacing1=4, spacing3=4,
                        wrap="none")
        # 引用
        w.tag_configure("quote",
                        font=(family, self.base, "italic"),
                        foreground=QUOTE, background="#2a2538",
                        lmargin1=18, lmargin2=18, spacing1=2, spacing3=2)
        # 列表
        w.tag_configure("list",
                        font=(family, self.base),
                        foreground=FG, lmargin1=20, lmargin2=36,
                        spacing1=1, spacing3=1)
        # 链接
        w.tag_configure("link", font=(family, self.base, "underline"),
                        foreground=LINK)
        # 任务框
        w.tag_configure("task_done", foreground=GREEN,
                        font=(family, self.base))
        w.tag_configure("task_todo", foreground=YELLOW,
                        font=(family, self.base))
        # 分隔线
        w.tag_configure("hr", foreground="#666",
                        font=(family, self.base), justify="center",
                        spacing1=4, spacing3=4)

    # ── 渲染入口 ─────────────────────────────────────────
    def render(self, md: str):
        w = self.w
        # 清空旧图片引用，让被撤掉的图片可以 GC
        self._img_refs = []
        w.configure(state="normal")
        w.delete("1.0", "end")
        if not md.strip():
            w.insert("1.0", _t("common.preview_empty") + "\n", ("body",))
            w.configure(state="disabled")
            return

        lines = md.split("\n")
        i = 0
        in_code_block = False
        code_lang = ""
        code_buf: list[str] = []

        while i < len(lines):
            line = lines[i]

            # ── 代码块 ```... ``` ─────────────────────────
            m = re.match(r"^\s*```(\w*)\s*$", line)
            if m:
                if in_code_block:
                    # 结束代码块
                    w.insert("end", "\n".join(code_buf) + "\n", ("code_block",))
                    code_buf = []
                    in_code_block = False
                else:
                    in_code_block = True
                    code_lang = m.group(1)
                i += 1
                continue

            if in_code_block:
                code_buf.append(line)
                i += 1
                continue

            # ── 独立图片行 ![alt](path) —— 优先处理 ──────
            m = re.match(r"^\s*!\[([^\]]*)\]\(([^)]+)\)\s*$", line)
            if m:
                self._insert_image(m.group(2).strip(), m.group(1).strip())
                i += 1
                continue

            # ── 空行 ─────────────────────────────────────
            if not line.strip():
                w.insert("end", "\n")
                i += 1
                continue

            # ── 水平分隔线 ───────────────────────────────
            if re.match(r"^\s*([-*_])\s*\1\s*\1[\s\1]*$", line):
                w.insert("end", "─" * 50 + "\n", ("hr",))
                i += 1
                continue

            # ── 标题 #~###### ────────────────────────────
            m = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line)
            if m:
                level = len(m.group(1))
                self._insert_inline(m.group(2), (f"h{level}",))
                w.insert("end", "\n")
                i += 1
                continue

            # ── 引用 > ──────────────────────────────────
            if line.lstrip().startswith(">"):
                quote_text = re.sub(r"^\s*>\s?", "", line)
                w.insert("end", "▎ ", ("quote",))
                self._insert_inline(quote_text, ("quote",))
                w.insert("end", "\n")
                i += 1
                continue

            # ── 任务列表 - [ ] / - [x] ────────────────────
            m = re.match(r"^(\s*)[-*+]\s+\[([ xX])\]\s+(.+)$", line)
            if m:
                indent = len(m.group(1))
                checked = m.group(2).lower() == "x"
                text = m.group(3)
                w.insert("end", "   " * (indent // 2), ("list",))
                if checked:
                    w.insert("end", "☑ ", ("task_done",))
                else:
                    w.insert("end", "☐ ", ("task_todo",))
                self._insert_inline(text, ("body",))
                w.insert("end", "\n")
                i += 1
                continue

            # ── 无序列表 - / * / + ───────────────────────
            m = re.match(r"^(\s*)([-*+])\s+(.+)$", line)
            if m:
                indent = len(m.group(1))
                bullet = "•" if indent == 0 else "◦"
                w.insert("end", "   " * (indent // 2) + f"{bullet} ",
                         ("list",))
                self._insert_inline(m.group(3), ("body",))
                w.insert("end", "\n")
                i += 1
                continue

            # ── 有序列表 1. ─────────────────────────────
            m = re.match(r"^(\s*)(\d+)\.\s+(.+)$", line)
            if m:
                indent = len(m.group(1))
                w.insert("end",
                         "   " * (indent // 2) + f"{m.group(2)}. ",
                         ("list",))
                self._insert_inline(m.group(3), ("body",))
                w.insert("end", "\n")
                i += 1
                continue

            # ── 普通段落 ─────────────────────────────────
            self._insert_inline(line, ("body",))
            w.insert("end", "\n")
            i += 1

        # 未闭合代码块兜底
        if in_code_block and code_buf:
            w.insert("end", "\n".join(code_buf) + "\n", ("code_block",))

        w.configure(state="disabled")

    # ── 行内样式解析 ─────────────────────────────────────
    _INLINE_PAT = re.compile(
        r"(`[^`\n]+?`)"                          # 行内代码
        r"|(\*\*\*[^*\n]+?\*\*\*)"               # 粗斜体
        r"|(\*\*[^*\n]+?\*\*)"                   # 粗体
        r"|(__[^_\n]+?__)"                       # 粗体 _
        r"|(\*[^*\n]+?\*)"                       # 斜体
        r"|(_[^_\n]+?_)"                         # 斜体 _
        r"|(\[[^\]\n]+?\]\([^)\n]+?\))"          # 链接
    )

    def _insert_inline(self, text: str, base_tags: tuple):
        """解析行内 Markdown，按段写入，各段挂不同 tag"""
        w = self.w
        pos = 0
        for m in self._INLINE_PAT.finditer(text):
            # 前置普通文本
            if m.start() > pos:
                w.insert("end", text[pos:m.start()], base_tags)

            code, bi, b1, b2, i1, i2, link = m.groups()
            if code:
                w.insert("end", code[1:-1], ("code_inline",) + base_tags)
            elif bi:
                w.insert("end", bi[3:-3], ("bolditalic",) + base_tags)
            elif b1:
                w.insert("end", b1[2:-2], ("bold",) + base_tags)
            elif b2:
                w.insert("end", b2[2:-2], ("bold",) + base_tags)
            elif i1:
                w.insert("end", i1[1:-1], ("italic",) + base_tags)
            elif i2:
                w.insert("end", i2[1:-1], ("italic",) + base_tags)
            elif link:
                lm = re.match(r"\[([^\]]+)\]\(([^)]+)\)", link)
                if lm:
                    w.insert("end", lm.group(1), ("link",) + base_tags)
                    # URL 以灰色小字紧随其后（便于肉眼识别）
                    w.insert("end", f"  ({lm.group(2)})",
                             ("body",) + base_tags)
            pos = m.end()

        # 末尾剩余
        if pos < len(text):
            w.insert("end", text[pos:], base_tags)

    # ── 图片插入（本地路径 / 相对路径） ─────────────────
    def _insert_image(self, path_str: str, alt: str = ""):
        """在预览 Text 中插入本地图片；加载失败则写占位文本"""
        w = self.w
        if not _HAS_PIL:
            w.insert("end", _t("md.image_no_pil", path=path_str) + "\n", ("body",))
            return

        # 路径解析：绝对 / 相对 base_dir / 相对 CWD
        p = Path(path_str)
        if not p.is_absolute() and self.base_dir:
            cand = self.base_dir / path_str
            if cand.exists():
                p = cand
        if not p.exists():
            # 再试一次相对 CWD
            alt_p = Path.cwd() / path_str
            if alt_p.exists():
                p = alt_p

        if not p.exists():
            w.insert("end",
                     _t("md.image_missing", path=path_str) + "\n",
                     ("body",))
            return

        try:
            img = Image.open(p)
            # 缩放：预览区最大宽 = Text 实际宽度的 0.9（尽量填满，不超原图）
            # 无法精确拿宽度时用固定上限 720
            try:
                pix_w = max(360, min(720, int(w.winfo_width() * 0.9)))
            except Exception:
                pix_w = 680
            if img.size[0] > pix_w:
                ratio = pix_w / img.size[0]
                new_size = (pix_w, max(1, int(img.size[1] * ratio)))
                img = img.resize(new_size, Image.LANCZOS)
            tk_img = ImageTk.PhotoImage(img)
        except Exception as e:
            w.insert("end",
                     _t("md.image_failed", path=path_str, e=e) + "\n",
                     ("body",))
            return

        # 引用必须保留，否则会被 GC 掉
        self._img_refs.append(tk_img)
        # 图片独占一行
        w.insert("end", "\n")
        w.image_create("end", image=tk_img, padx=4, pady=4)
        w.insert("end", "\n")
        if alt:
            w.insert("end", f"  🖼 {alt}\n",
                     ("body",))


# ══════════════════════════════════════════════════════════
# 编辑器窗口
# ══════════════════════════════════════════════════════════
class MarkdownEditor:
    """放大编辑 + Markdown 预览浮窗（单例，防止多开）"""

    _instance: "MarkdownEditor | None" = None

    @classmethod
    def open(cls, parent: tk.Misc, initial_text: str = "",
             title: str | None = None,
             on_save=None,
             image_base_dir: Path | str | None = None,
             on_screenshot=None) -> "MarkdownEditor":
        if title is None:
            title = _t("edit.window.title", hint=_t("edit.title.hint"))
        """
        parent          : 父窗口（通常是任务管理 Toplevel）
        initial_text    : 打开时要回填的文本
        title           : 窗口标题
        on_save(text)   : 点"保存"时的回调，参数为编辑后的完整文本
        image_base_dir  : 预览解析 ![](相对路径) 的根目录（通常是 data_dir）
        on_screenshot(cb_insert) :
            点"📷 截图"时的回调，调用方负责启动截图并最终回调
            cb_insert(path) 把保存路径插入到编辑器
            为 None 时截图按钮隐藏
        """
        if cls._instance and cls._instance.win.winfo_exists():
            cls._instance.win.lift()
            cls._instance.win.focus_force()
            return cls._instance
        cls._instance = cls(parent, initial_text, title, on_save,
                            image_base_dir, on_screenshot)
        return cls._instance

    def __init__(self, parent, initial_text, title, on_save,
                 image_base_dir=None, on_screenshot=None):
        self.parent          = parent
        self.on_save         = on_save
        self.on_screenshot   = on_screenshot
        self._image_base_dir = Path(image_base_dir) if image_base_dir else None
        self._font_size      = 12              # 编辑区当前字号
        self._view_mode      = "split"         # split / edit / preview
        self._search_matches: list[tuple[str, str]] = []   # [(start,end), ...]
        self._search_cur     = -1              # 当前命中下标
        self._render_after_id: str | None = None

        self.win = tk.Toplevel(parent)
        self.win.title(title)
        self.win.geometry("1200x720")
        self.win.minsize(900, 520)
        self.win.configure(bg=BG)
        self.win.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.win.transient(parent)

        self._build_topbar()
        self._build_search_bar()
        self._build_body()
        self._build_bottom_bar()

        # 渲染器（挂在预览 Text 上）
        self._renderer = _MarkdownRenderer(self.preview, self._font_size,
                                            base_dir=self._image_base_dir)

        # 回填初始内容
        if initial_text:
            self.editor.insert("1.0", initial_text)
        self._schedule_render()

        # 快捷键
        self._bind_shortcuts()

        # 焦点
        self.editor.focus_set()

    # ══════════════════════════════════════════════════════
    # UI 组件
    # ══════════════════════════════════════════════════════
    def _build_topbar(self):
        bar = tk.Frame(self.win, bg=BG2, height=40)
        bar.pack(fill="x", side="top")
        bar.pack_propagate(False)

        # 左：视图切换
        left = tk.Frame(bar, bg=BG2)
        left.pack(side="left", padx=10)

        self._view_var = tk.StringVar(value="split")
        for val, txt in [("edit",    _t("md.view.edit")),
                         ("split",   _t("md.view.split")),
                         ("preview", _t("md.view.preview"))]:
            tk.Radiobutton(
                left, text=txt, variable=self._view_var, value=val,
                command=self._switch_view,
                bg=BG2, fg=FG, activebackground=BG2, activeforeground=ACC,
                selectcolor=BG3, indicatoron=False,
                relief="flat", padx=10, pady=4, bd=0, cursor="hand2",
                font=("Microsoft YaHei UI", 9),
            ).pack(side="left", padx=2)

        # 中：字号调节
        mid = tk.Frame(bar, bg=BG2)
        mid.pack(side="left", padx=20)
        tk.Label(mid, text=_t("md.font.label"), bg=BG2, fg=FG_DIM,
                 font=("Microsoft YaHei UI", 9)).pack(side="left")
        tk.Button(mid, text="A-", command=lambda: self._zoom(-1),
                  bg=BG3, fg=FG, relief="flat", padx=8, cursor="hand2",
                  font=("Microsoft YaHei UI", 9),
                  activebackground=ACC).pack(side="left", padx=2)
        self.lbl_font = tk.Label(mid, text=str(self._font_size),
                                 bg=BG2, fg=ACC, width=3,
                                 font=("Microsoft YaHei UI", 10, "bold"))
        self.lbl_font.pack(side="left", padx=4)
        tk.Button(mid, text="A+", command=lambda: self._zoom(1),
                  bg=BG3, fg=FG, relief="flat", padx=8, cursor="hand2",
                  font=("Microsoft YaHei UI", 9),
                  activebackground=ACC).pack(side="left", padx=2)

        # 右：搜索切换 / 字符计数
        right = tk.Frame(bar, bg=BG2)
        right.pack(side="right", padx=10)

        self.lbl_stats = tk.Label(right, text="",
                                  bg=BG2, fg=FG_DIM,
                                  font=("Microsoft YaHei UI", 9))
        self.lbl_stats.pack(side="right", padx=10)

        tk.Button(right, text=_t("md.btn.search"),
                  command=self._toggle_search,
                  bg=BG3, fg=FG, relief="flat", padx=10, pady=4,
                  cursor="hand2",
                  font=("Microsoft YaHei UI", 9),
                  activebackground=ACC).pack(side="right", padx=4)

        # 截图按钮（仅当调用方提供了 on_screenshot 时显示）
        if self.on_screenshot is not None:
            tk.Button(right, text=_t("md.btn.shot"),
                      command=self._trigger_screenshot,
                      bg="#7c4dff", fg="#fff", relief="flat",
                      padx=10, pady=4, cursor="hand2",
                      font=("Microsoft YaHei UI", 9, "bold"),
                      activebackground=ACC2).pack(side="right", padx=4)

    def _build_search_bar(self):
        """搜索栏：默认隐藏，Ctrl+F 切换"""
        self.search_frame = tk.Frame(self.win, bg=BG3, height=38)
        # 默认不 pack，用到时才显示

        tk.Label(self.search_frame, text="🔍", bg=BG3, fg=ACC,
                 font=("Segoe UI Emoji", 11)).pack(side="left", padx=(10, 4),
                                                    pady=6)

        self.search_var = tk.StringVar()
        self.e_search = tk.Entry(self.search_frame, textvariable=self.search_var,
                                 bg=BG2, fg=FG, insertbackground=FG,
                                 relief="flat", font=("Microsoft YaHei UI", 10),
                                 width=30)
        self.e_search.pack(side="left", padx=4, pady=6, ipady=3)
        self.search_var.trace_add("write", lambda *_: self._on_search_change())

        tk.Button(self.search_frame, text=_t("md.find.prev"),
                  command=lambda: self._search_next(-1),
                  bg=BG2, fg=FG, relief="flat", padx=8, cursor="hand2",
                  font=("Microsoft YaHei UI", 9),
                  activebackground=ACC).pack(side="left", padx=2, pady=6)
        tk.Button(self.search_frame, text=_t("md.find.next"),
                  command=lambda: self._search_next(1),
                  bg=BG2, fg=FG, relief="flat", padx=8, cursor="hand2",
                  font=("Microsoft YaHei UI", 9),
                  activebackground=ACC).pack(side="left", padx=2, pady=6)

        tk.Label(self.search_frame, text=_t("md.replace.label"), bg=BG3, fg=FG_DIM,
                 font=("Microsoft YaHei UI", 9)).pack(side="left", padx=(12, 2))
        self.replace_var = tk.StringVar()
        self.e_replace = tk.Entry(self.search_frame, textvariable=self.replace_var,
                                  bg=BG2, fg=FG, insertbackground=FG,
                                  relief="flat", font=("Microsoft YaHei UI", 10),
                                  width=24)
        self.e_replace.pack(side="left", padx=4, pady=6, ipady=3)

        tk.Button(self.search_frame, text=_t("md.replace.cur"),
                  command=self._replace_cur,
                  bg=BG2, fg=FG, relief="flat", padx=8, cursor="hand2",
                  font=("Microsoft YaHei UI", 9),
                  activebackground=ACC).pack(side="left", padx=2, pady=6)
        tk.Button(self.search_frame, text=_t("md.replace.all"),
                  command=self._replace_all,
                  bg=BG2, fg=FG, relief="flat", padx=8, cursor="hand2",
                  font=("Microsoft YaHei UI", 9),
                  activebackground=ORANGE).pack(side="left", padx=2, pady=6)

        self.case_var = tk.BooleanVar(value=False)
        tk.Checkbutton(self.search_frame, text=_t("md.case_sensitive"),
                       variable=self.case_var,
                       command=self._on_search_change,
                       bg=BG3, fg=FG_DIM,
                       activebackground=BG3, activeforeground=FG,
                       selectcolor=BG2,
                       font=("Microsoft YaHei UI", 9)).pack(side="left",
                                                             padx=8, pady=6)

        self.lbl_search_count = tk.Label(self.search_frame, text="",
                                         bg=BG3, fg=YELLOW,
                                         font=("Microsoft YaHei UI", 9))
        self.lbl_search_count.pack(side="left", padx=8)

        tk.Button(self.search_frame, text="✕", command=self._toggle_search,
                  bg=BG3, fg=FG_DIM, relief="flat", padx=8, cursor="hand2",
                  font=("Segoe UI Emoji", 10),
                  activebackground=RED).pack(side="right", padx=8, pady=6)

    def _build_body(self):
        """编辑区 + 预览区（PanedWindow 可拖拽分隔）"""
        self.body = tk.PanedWindow(self.win, orient="horizontal",
                                   bg=BG, bd=0, sashwidth=4,
                                   sashrelief="flat")
        self.body.pack(fill="both", expand=True, padx=6, pady=(0, 4))

        # ── 左侧：编辑区 ─────────────────────────────────
        self.edit_panel = tk.Frame(self.body, bg=BG)
        self.body.add(self.edit_panel, minsize=300)

        edit_head = tk.Frame(self.edit_panel, bg=BG)
        edit_head.pack(fill="x", padx=2, pady=(2, 0))
        tk.Label(edit_head, text=_t("md.editor.label"), bg=BG, fg=ACC,
                 font=("Microsoft YaHei UI", 10, "bold")
                 ).pack(side="left")

        # 编辑器 + 滚动条
        ef = tk.Frame(self.edit_panel, bg=BG)
        ef.pack(fill="both", expand=True, padx=2, pady=2)

        self.editor = tk.Text(
            ef, wrap="word", undo=True, maxundo=200,
            bg=BG2, fg=FG, insertbackground=FG,
            selectbackground=BG3, selectforeground="#fff",
            relief="flat",
            font=("Consolas", self._font_size),
            padx=12, pady=10,
        )
        sb_e = tk.Scrollbar(ef, command=self.editor.yview, bg=BG)
        self.editor.configure(yscrollcommand=sb_e.set)
        sb_e.pack(side="right", fill="y")
        self.editor.pack(side="left", fill="both", expand=True)

        # 配置搜索高亮 tag
        self.editor.tag_configure("search_hit", background=HL_BG,
                                  foreground="#fff")
        self.editor.tag_configure("search_cur", background=HL_CUR,
                                  foreground="#000")

        # 文本变化 → 触发预览渲染（防抖）
        self.editor.bind("<<Modified>>", self._on_editor_modified)

        # ── 右侧：预览 ───────────────────────────────────
        self.prev_panel = tk.Frame(self.body, bg=BG)
        self.body.add(self.prev_panel, minsize=300)

        prev_head = tk.Frame(self.prev_panel, bg=BG)
        prev_head.pack(fill="x", padx=2, pady=(2, 0))
        tk.Label(prev_head, text=_t("md.preview.label"), bg=BG, fg=ACC2,
                 font=("Microsoft YaHei UI", 10, "bold")
                 ).pack(side="left")

        pf = tk.Frame(self.prev_panel, bg=BG)
        pf.pack(fill="both", expand=True, padx=2, pady=2)
        self.preview = tk.Text(
            pf, wrap="word", state="disabled",
            bg=BG2, fg=FG, relief="flat",
            font=("Microsoft YaHei UI", self._font_size),
            padx=14, pady=12, spacing2=2,
        )
        sb_p = tk.Scrollbar(pf, command=self.preview.yview, bg=BG)
        self.preview.configure(yscrollcommand=sb_p.set)
        sb_p.pack(side="right", fill="y")
        self.preview.pack(side="left", fill="both", expand=True)

        # 等控件真正布局完毕后，把分隔条定位到正中
        self.win.update_idletasks()
        self.win.after(50, lambda: self.body.sash_place(
            0, max(400, self.body.winfo_width() // 2), 1))

    def _build_bottom_bar(self):
        bar = tk.Frame(self.win, bg=BG2, height=44)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        # 提示
        tk.Label(bar, text=_t("md.bottom.hint"),
                 bg=BG2, fg=FG_DIM,
                 font=("Microsoft YaHei UI", 9)
                 ).pack(side="left", padx=14)

        tk.Button(bar, text=_t("common.cancel"), command=self._on_cancel,
                  bg=BG3, fg=FG, relief="flat", padx=16, pady=4,
                  cursor="hand2", font=("Microsoft YaHei UI", 10),
                  activebackground=RED, activeforeground="#fff"
                  ).pack(side="right", padx=(4, 12), pady=8)
        tk.Button(bar, text=_t("md.btn.save_close"), command=self._on_save,
                  bg="#0d7377", fg="#fff", relief="flat", padx=16, pady=4,
                  cursor="hand2", font=("Microsoft YaHei UI", 10, "bold"),
                  activebackground="#14a085", activeforeground="#fff"
                  ).pack(side="right", padx=4, pady=8)

    # ══════════════════════════════════════════════════════
    # 快捷键
    # ══════════════════════════════════════════════════════
    def _bind_shortcuts(self):
        w = self.win
        w.bind("<Control-f>",       lambda _e: self._toggle_search(True))
        w.bind("<Control-F>",       lambda _e: self._toggle_search(True))
        w.bind("<Control-h>",       lambda _e: self._toggle_search(True, focus_replace=True))
        w.bind("<Control-H>",       lambda _e: self._toggle_search(True, focus_replace=True))
        w.bind("<Control-s>",       lambda _e: self._on_save())
        w.bind("<Control-S>",       lambda _e: self._on_save())
        w.bind("<Escape>",          lambda _e: self._on_escape())
        w.bind("<F3>",              lambda _e: self._search_next(1))
        w.bind("<Shift-F3>",        lambda _e: self._search_next(-1))
        w.bind("<Control-plus>",    lambda _e: self._zoom(1))
        w.bind("<Control-equal>",   lambda _e: self._zoom(1))
        w.bind("<Control-minus>",   lambda _e: self._zoom(-1))
        # 截图
        w.bind("<Control-Shift-A>", lambda _e: self._trigger_screenshot())
        w.bind("<Control-Shift-a>", lambda _e: self._trigger_screenshot())
        # 搜索框内回车 = 下一处
        self.e_search.bind("<Return>", lambda _e: self._search_next(1))
        self.e_search.bind("<Shift-Return>", lambda _e: self._search_next(-1))

    # ══════════════════════════════════════════════════════
    # 截图 / 图片插入
    # ══════════════════════════════════════════════════════
    def _trigger_screenshot(self):
        """触发外部截图流程。由 on_screenshot 回调负责 hide/restore 本窗口，
        这里只做最终插入；异常兜底防止窗口卡住"""
        if not self.on_screenshot:
            return

        def _after_capture(path):
            # 编辑器回到顶部并聚焦
            try:
                if self.win.winfo_exists():
                    self.win.deiconify()
                    self.win.lift()
                    self.win.focus_force()
            except Exception:
                pass
            if path:
                try:
                    self.insert_image(path)
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    from tkinter import messagebox
                    messagebox.showerror(
                        _t("md.insert_failed"),
                        _t("md.insert_failed_body", path=path, e=e),
                        parent=self.win)

        try:
            self.on_screenshot(_after_capture)
        except Exception as e:
            import traceback
            traceback.print_exc()
            try:
                if self.win.winfo_exists():
                    self.win.deiconify()
                    self.win.lift()
            except Exception:
                pass
            from tkinter import messagebox
            messagebox.showerror(_t("md.shot_failed"), str(e), parent=self.win)

    def insert_image(self, image_path: str):
        """把一张本地图片以 Markdown 语法插入编辑器当前光标位置"""
        p = Path(image_path)
        # 若 base_dir 存在且图片在其下，使用相对路径（方便工程迁移）
        if self._image_base_dir:
            try:
                rel = p.resolve().relative_to(self._image_base_dir.resolve())
                md_path = rel.as_posix()
            except Exception:
                md_path = p.as_posix()
        else:
            md_path = p.as_posix()

        alt = f"{_t('shot.alt_prefix')}{p.stem}"
        snippet = f"\n![{alt}]({md_path})\n"

        # 插入到光标位置（若编辑器还未聚焦则插到末尾）
        try:
            self.editor.insert("insert", snippet)
        except Exception:
            self.editor.insert("end", snippet)

        # 触发预览刷新
        self._schedule_render()
        self._update_stats()

    # ══════════════════════════════════════════════════════
    # 视图切换
    # ══════════════════════════════════════════════════════
    def _switch_view(self):
        mode = self._view_var.get()
        self._view_mode = mode
        # 先全部隐藏
        try:
            self.body.forget(self.edit_panel)
        except Exception:
            pass
        try:
            self.body.forget(self.prev_panel)
        except Exception:
            pass

        if mode == "edit":
            self.body.add(self.edit_panel, minsize=300)
        elif mode == "preview":
            self.body.add(self.prev_panel, minsize=300)
            self._schedule_render()
        else:  # split
            self.body.add(self.edit_panel, minsize=300)
            self.body.add(self.prev_panel, minsize=300)
            self.win.after(50, lambda: self.body.sash_place(
                0, max(400, self.body.winfo_width() // 2), 1))

    # ══════════════════════════════════════════════════════
    # 字号
    # ══════════════════════════════════════════════════════
    def _zoom(self, delta: int):
        new_size = max(8, min(28, self._font_size + delta))
        if new_size == self._font_size:
            return
        self._font_size = new_size
        self.lbl_font.config(text=str(new_size))
        self.editor.configure(font=("Consolas", new_size))
        # 重建预览 tag 字号
        self._renderer = _MarkdownRenderer(self.preview, new_size,
                                            base_dir=self._image_base_dir)
        self._schedule_render()

    # ══════════════════════════════════════════════════════
    # 预览渲染（防抖）
    # ══════════════════════════════════════════════════════
    def _on_editor_modified(self, _evt=None):
        # <<Modified>> 触发后要手动复位 flag
        try:
            self.editor.edit_modified(False)
        except Exception:
            pass
        self._schedule_render()
        self._update_stats()
        # 搜索状态下内容变更 → 重刷搜索结果
        if self._search_matches and self.search_var.get().strip():
            self._on_search_change()

    def _schedule_render(self, delay_ms: int = 180):
        if self._render_after_id:
            try:
                self.win.after_cancel(self._render_after_id)
            except Exception:
                pass
        self._render_after_id = self.win.after(delay_ms, self._do_render)

    def _do_render(self):
        self._render_after_id = None
        if self._view_mode == "edit":
            return   # 编辑模式下预览不可见，不渲染省资源
        text = self.editor.get("1.0", "end-1c")
        try:
            self._renderer.render(text)
        except Exception as e:
            self.preview.configure(state="normal")
            self.preview.delete("1.0", "end")
            self.preview.insert("1.0", f"[Markdown render error] {e}")
            self.preview.configure(state="disabled")

    def _update_stats(self):
        text = self.editor.get("1.0", "end-1c")
        chars = len(text)
        lines = text.count("\n") + (0 if text.endswith("\n") or not text else 1)
        self.lbl_stats.config(text=_t("md.stats", lines=lines, chars=chars))

    # ══════════════════════════════════════════════════════
    # 搜索 / 替换
    # ══════════════════════════════════════════════════════
    def _toggle_search(self, force_show: bool = False, focus_replace: bool = False):
        visible = self.search_frame.winfo_ismapped()
        if visible and not force_show:
            self.search_frame.pack_forget()
            self._clear_search_marks()
            self.editor.focus_set()
            return
        if not visible:
            # 插在 topbar 之下，body 之上
            self.search_frame.pack(fill="x", side="top", before=self.body)
        (self.e_replace if focus_replace else self.e_search).focus_set()
        (self.e_replace if focus_replace else self.e_search).select_range(0, "end")

    def _clear_search_marks(self):
        self.editor.tag_remove("search_hit", "1.0", "end")
        self.editor.tag_remove("search_cur", "1.0", "end")
        self._search_matches = []
        self._search_cur = -1
        self.lbl_search_count.config(text="")

    def _on_search_change(self):
        pat = self.search_var.get()
        self._clear_search_marks()
        if not pat:
            return

        case_sensitive = self.case_var.get()
        start = "1.0"
        matches: list[tuple[str, str]] = []
        # Tk 内置 search 循环查找所有位置
        while True:
            idx = self.editor.search(
                pat, start, stopindex="end",
                nocase=not case_sensitive,
            )
            if not idx:
                break
            end = f"{idx}+{len(pat)}c"
            self.editor.tag_add("search_hit", idx, end)
            matches.append((idx, end))
            start = end

        self._search_matches = matches
        if matches:
            self._search_cur = 0
            self._highlight_current()
            self.lbl_search_count.config(
                text=f"1 / {len(matches)}", fg=YELLOW)
        else:
            self.lbl_search_count.config(text=_t("md.find.none"), fg=RED)

    def _search_next(self, step: int):
        if not self._search_matches:
            # 若搜索栏未打开也允许通过 F3 触发一次搜索
            if self.search_var.get().strip():
                self._on_search_change()
            if not self._search_matches:
                return
        n = len(self._search_matches)
        self._search_cur = (self._search_cur + step) % n
        self._highlight_current()
        self.lbl_search_count.config(
            text=f"{self._search_cur + 1} / {n}", fg=YELLOW)

    def _highlight_current(self):
        self.editor.tag_remove("search_cur", "1.0", "end")
        if 0 <= self._search_cur < len(self._search_matches):
            s, e = self._search_matches[self._search_cur]
            self.editor.tag_add("search_cur", s, e)
            self.editor.mark_set("insert", s)
            self.editor.see(s)

    def _replace_cur(self):
        if not self._search_matches:
            return
        if not (0 <= self._search_cur < len(self._search_matches)):
            return
        s, e = self._search_matches[self._search_cur]
        new_text = self.replace_var.get()
        self.editor.delete(s, e)
        self.editor.insert(s, new_text)
        # 替换后重搜
        self._on_search_change()

    def _replace_all(self):
        pat = self.search_var.get()
        if not pat:
            return
        new_text = self.replace_var.get()
        case_sensitive = self.case_var.get()

        content = self.editor.get("1.0", "end-1c")
        if case_sensitive:
            new_content = content.replace(pat, new_text)
            count = content.count(pat)
        else:
            # 不区分大小写：正则替换
            count = len(re.findall(re.escape(pat), content, flags=re.IGNORECASE))
            new_content = re.sub(re.escape(pat), lambda _m: new_text,
                                 content, flags=re.IGNORECASE)

        if count == 0:
            self.lbl_search_count.config(text=_t("md.find.none"), fg=RED)
            return

        # 整体替换并保持光标位置
        cur_index = self.editor.index("insert")
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", new_content)
        try:
            self.editor.mark_set("insert", cur_index)
        except Exception:
            pass

        self.lbl_search_count.config(text=_t("md.find.replaced", n=count), fg=GREEN)
        self._on_search_change()

    # ══════════════════════════════════════════════════════
    # 保存 / 取消
    # ══════════════════════════════════════════════════════
    def _on_escape(self):
        # 搜索栏打开时，Esc 优先关搜索栏
        if self.search_frame.winfo_ismapped():
            self._toggle_search()
            return
        self._on_cancel()

    def _on_save(self, _evt=None):
        text = self.editor.get("1.0", "end-1c")
        if self.on_save:
            try:
                self.on_save(text)
            except Exception as e:
                print(f"[MarkdownEditor] on_save 回调异常: {e}")
        self._close()
        return "break"

    def _on_cancel(self):
        self._close()

    def _close(self):
        try:
            self.win.destroy()
        except Exception:
            pass
        MarkdownEditor._instance = None
