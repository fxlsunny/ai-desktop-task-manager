"""
桌面截图模块 — 区域选择 + 简易标注编辑 + 保存到 data/img/

对外入口：
    capture_and_edit(root, save_dir, on_done, hide_windows=None)
        root      : Tk 主窗（全局 Tk 实例）
        save_dir  : 保存根目录（data/img），会自动按日期分子目录
        on_done(path:str|None)  ：
            - 编辑器"保存"   → path = 绝对路径字符串
            - 编辑器"取消/ESC" → path = None
        hide_windows : 截图前临时 withdraw 的 Toplevel 列表（主窗/浮球/编辑窗）

依赖：Pillow（PIL），已在桌面管家其他模块中使用
"""
from __future__ import annotations

import math
import random
import re
import sys
import tkinter as tk
import traceback
from datetime import datetime
from pathlib import Path
from tkinter import colorchooser, messagebox, simpledialog
from typing import Callable, Optional, Tuple

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageGrab, ImageTk
except ImportError as _e:   # pragma: no cover
    raise ImportError(
        "Pillow is required: pip install pillow"
    ) from _e

from i18n import t as _t


def _log(msg: str):
    """统一日志前缀，便于在控制台定位问题"""
    print(f"[screenshot] {msg}", flush=True)


# ══════════════════════════════════════════════════════════
# 工具：DPI 感知（Windows 多屏高 DPI 下截图坐标正确）
# ══════════════════════════════════════════════════════════
def _enable_dpi_awareness():
    """在应用最早期调用；Tk 已经初始化过时也无害，但效果可能打折"""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            import ctypes
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def _get_dpi_scale(root: tk.Misc) -> float:
    """
    获取 Tk 的逻辑坐标到物理像素的比例。
    Tk 如果未 DPI-aware，e.x_root 是未放大的逻辑坐标；
    而 ImageGrab.grab(all_screens=True) 返回物理像素。
    系统缩放 = (物理像素屏幕宽度) / (Tk 报告的屏幕宽度)。
    """
    if sys.platform != "win32":
        return 1.0
    try:
        import ctypes
        user32 = ctypes.windll.user32
        phys_w = int(user32.GetSystemMetrics(0))   # SM_CXSCREEN，物理或逻辑取决于 DPI 感知
        # GetSystemMetricsForDpi 在 Win10+ 可获取真物理
        try:
            mon_w = int(user32.GetSystemMetricsForDpi(0, 96))
            # 若拿不到真实的物理，这里 mon_w == phys_w；用 EnumDisplaySettings 更稳
        except Exception:
            mon_w = phys_w
        # 再和 Tk 认识的屏宽对比
        tk_w = root.winfo_screenwidth()
        if tk_w <= 0:
            return 1.0
        # 若 DPI 感知失败，phys_w 可能仍等于 tk_w；这时退而求 devicePixelRatio
        if phys_w > tk_w:
            return phys_w / tk_w
        # 取窗口 DPI
        try:
            hwnd = int(root.frame(), 16) if False else 0
        except Exception:
            hwnd = 0
        # 最后兜底：查 ctypes GetDpiForSystem
        try:
            dpi = int(user32.GetDpiForSystem())
            if dpi > 0:
                return dpi / 96.0
        except Exception:
            pass
        return 1.0
    except Exception:
        return 1.0


# ══════════════════════════════════════════════════════════
# 步骤 1：全屏区域选择窗口
# ══════════════════════════════════════════════════════════
class _RegionPicker:
    """全屏半透明遮罩 + 鼠标拖拽选区

    选中区域后调 on_pick(pil_image, bbox)；ESC 取消调 on_pick(None, None)。
    """

    MASK_COLOR  = "#000000"
    MASK_ALPHA  = 0.32
    LINE_COLOR  = "#4fc3f7"
    LINE_WIDTH  = 2
    HINT_BG     = "#1e1e2e"
    HINT_FG     = "#e0e0e0"

    def __init__(self, root: tk.Misc,
                 on_pick: Callable[[Optional[Image.Image],
                                    Optional[Tuple[int, int, int, int]]],
                                   None]):
        self.root     = root
        self.on_pick  = on_pick
        self._start   = None     # (x_root, y_root) 逻辑坐标
        self._rect_id = None
        self._done    = False

        # ── DPI 比例：Tk 逻辑坐标 → 物理像素 ─────────────
        self._dpi_scale = _get_dpi_scale(root)
        _log(f"DPI scale = {self._dpi_scale:.3f}")

        # ── 先抓全屏（物理像素），避免遮罩出现在截图里 ──
        try:
            try:
                self._full = ImageGrab.grab(all_screens=True)
            except TypeError:
                # Pillow < 9 不支持 all_screens 参数
                self._full = ImageGrab.grab()
            _log(f"grab full screen = {self._full.size}")
        except Exception as e:
            _log(f"ImageGrab 失败: {e}")
            self._full = None
            self.root.after(0, lambda: on_pick(None, None))
            return

        # ── 虚拟屏范围（物理像素）───────────────────────
        self._vs_left = 0
        self._vs_top  = 0
        self._vs_w    = self._full.size[0]
        self._vs_h    = self._full.size[1]
        if sys.platform == "win32":
            try:
                import ctypes
                user32 = ctypes.windll.user32
                # SM_XVIRTUALSCREEN=76/77/78/79 —— 返回的单位取决于进程 DPI 感知
                # 我们希望用物理像素；但如果 Tk 没 DPI 感知，这里拿的可能是逻辑单位
                # 所以先按物理抓，再按比例换算到 Tk 逻辑坐标覆盖窗口
                vs_left = int(user32.GetSystemMetrics(76))
                vs_top  = int(user32.GetSystemMetrics(77))
                vs_w    = int(user32.GetSystemMetrics(78))
                vs_h    = int(user32.GetSystemMetrics(79))
                if vs_w > 0 and vs_h > 0:
                    self._vs_left = vs_left
                    self._vs_top  = vs_top
                    self._vs_w    = vs_w
                    self._vs_h    = vs_h
            except Exception as e:
                _log(f"GetSystemMetrics 失败: {e}")

        _log(f"virtual screen = ({self._vs_left},{self._vs_top}) "
             f"{self._vs_w}x{self._vs_h}")

        self._build_overlay()

    # ── 构造全屏遮罩 ─────────────────────────────────────
    def _build_overlay(self):
        self.win = tk.Toplevel(self.root)
        self.win.withdraw()
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        try:
            self.win.attributes("-alpha", self.MASK_ALPHA)
        except tk.TclError:
            pass
        self.win.configure(bg=self.MASK_COLOR)

        # 几何设置使用 Tk 逻辑坐标。若 Tk 未 DPI 感知，虚拟屏的物理坐标除以 scale。
        # 若 Tk 已 DPI 感知（scale == 1.0），直接用物理坐标即可。
        s = self._dpi_scale
        geom_x = int(round(self._vs_left / s))
        geom_y = int(round(self._vs_top  / s))
        geom_w = int(round(self._vs_w    / s))
        geom_h = int(round(self._vs_h    / s))
        geom = f"{geom_w}x{geom_h}+{geom_x}+{geom_y}"
        _log(f"overlay geometry = {geom}")
        self.win.geometry(geom)

        self.canvas = tk.Canvas(
            self.win, bg=self.MASK_COLOR,
            highlightthickness=0, cursor="cross",
        )
        self.canvas.pack(fill="both", expand=True)

        # 提示文字
        self.canvas.create_rectangle(
            10, 10, 420, 48, fill=self.HINT_BG, outline="",
            tags="hint_box")
        self.canvas.create_text(
            20, 30, anchor="w",
            text=_t("shot.hint"),
            fill=self.HINT_FG,
            font=("Microsoft YaHei UI", 11, "bold"),
            tags="hint_text")

        # 事件
        self.canvas.bind("<ButtonPress-1>",   self._on_press)
        self.canvas.bind("<B1-Motion>",       self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Motion>",          self._on_hover)
        self.win.bind("<Escape>",             lambda _e: self._cancel())
        self.win.bind("<Key-Escape>",         lambda _e: self._cancel())
        # 失去焦点也不允许取消（防止主窗 focus_force 导致误触发）

        # 展示
        self.win.deiconify()
        self.win.lift()
        self.win.attributes("-topmost", True)
        self.win.update_idletasks()
        # 多次 focus_force 确保键盘事件能收到
        self.win.focus_force()
        self.canvas.focus_set()
        self.root.after(50, self._force_focus)
        self.root.after(200, self._force_focus)

    def _force_focus(self):
        try:
            if self.win.winfo_exists():
                self.win.lift()
                self.win.focus_force()
                self.canvas.focus_set()
        except Exception:
            pass

    # ── 鼠标移动时提示 ───────────────────────────────────
    def _on_hover(self, e):
        if self._start is not None:
            return
        # 仅更新坐标显示
        self.canvas.itemconfigure(
            "hint_text",
            text=_t("shot.hint.coord", x=e.x_root, y=e.y_root))

    # ── 鼠标事件：记录起点 / 实时画框 / 松开完成 ────────
    def _on_press(self, e):
        self._start = (e.x_root, e.y_root)
        if self._rect_id is not None:
            self.canvas.delete(self._rect_id)
            self._rect_id = None

    def _on_drag(self, e):
        if self._start is None:
            return
        x0, y0 = self._start
        x1, y1 = e.x_root, e.y_root

        # 窗口内画布坐标 = x_root - 窗口左上角(逻辑坐标)
        wx = self.win.winfo_rootx()
        wy = self.win.winfo_rooty()
        cx0, cy0 = x0 - wx, y0 - wy
        cx1, cy1 = x1 - wx, y1 - wy

        if self._rect_id is None:
            self._rect_id = self.canvas.create_rectangle(
                cx0, cy0, cx1, cy1,
                outline=self.LINE_COLOR, width=self.LINE_WIDTH)
        else:
            self.canvas.coords(self._rect_id, cx0, cy0, cx1, cy1)

        w, h = abs(x1 - x0), abs(y1 - y0)
        self.canvas.itemconfigure(
            "hint_text",
            text=_t("shot.hint.size", w=w, h=h))

    def _on_release(self, e):
        if self._start is None or self._done:
            return
        x0, y0 = self._start
        x1, y1 = e.x_root, e.y_root
        bbox_logical = (min(x0, x1), min(y0, y1),
                        max(x0, x1), max(y0, y1))
        if bbox_logical[2] - bbox_logical[0] < 5 or \
                bbox_logical[3] - bbox_logical[1] < 5:
            # 太小视为取消
            return self._cancel()
        self._done = True

        # ── 逻辑坐标 → 物理像素 → 在 self._full 里的坐标 ──
        s = self._dpi_scale
        px0 = int(round(bbox_logical[0] * s))
        py0 = int(round(bbox_logical[1] * s))
        px1 = int(round(bbox_logical[2] * s))
        py1 = int(round(bbox_logical[3] * s))

        # 转到 self._full 图里的坐标：减去虚拟屏左上
        crop = (
            max(0, px0 - self._vs_left),
            max(0, py0 - self._vs_top),
            min(self._full.size[0], px1 - self._vs_left),
            min(self._full.size[1], py1 - self._vs_top),
        )
        _log(f"bbox logical={bbox_logical}  crop={crop}  "
             f"full_size={self._full.size}")

        img = None
        try:
            if crop[2] - crop[0] >= 1 and crop[3] - crop[1] >= 1:
                img = self._full.crop(crop).convert("RGB")
        except Exception as ex:
            _log(f"crop 失败: {ex}")
            img = None

        # 先关自己再回调，防回调里修改焦点/弹窗冲突
        try:
            self.win.destroy()
        except Exception:
            pass
        # 延迟一帧再回调，让 overlay 真的消失
        self.root.after(30, lambda: self.on_pick(img, bbox_logical))

    def _cancel(self):
        if self._done:
            return
        self._done = True
        try:
            self.win.destroy()
        except Exception:
            pass
        self.root.after(30, lambda: self.on_pick(None, None))


# ══════════════════════════════════════════════════════════
# 步骤 2：截图编辑器
# ══════════════════════════════════════════════════════════
class _Annotation:
    """一条标注（矩形 / 椭圆 / 箭头 / 画笔 / 文字 / 马赛克）"""
    __slots__ = ("kind", "points", "color", "width", "text", "font_size",
                 "mosaic_size")

    def __init__(self, kind: str, points: list, color: str = "#ef5350",
                 width: int = 3, text: str = "", font_size: int = 16,
                 mosaic_size: int = 12):
        self.kind        = kind       # rect/oval/arrow/pen/text/mosaic
        self.points      = points     # [(x,y), ...]
        self.color       = color
        self.width       = width
        self.text        = text
        self.font_size   = font_size
        self.mosaic_size = mosaic_size


class ScreenshotEditor:
    """截图编辑窗口（单例）"""
    _instance: "ScreenshotEditor | None" = None

    BG        = "#1e1e2e"
    BG2       = "#2a2a3e"
    BG3       = "#0f3460"
    ACC       = "#4fc3f7"
    FG        = "#e0e0e0"
    FG_DIM    = "#9e9e9e"
    TOOL_ACT  = "#7c4dff"

    COLORS = ["#ef5350", "#ffd54f", "#66bb6a", "#4fc3f7", "#7c4dff",
              "#ffffff", "#000000"]

    @classmethod
    def open(cls, root, image: Image.Image, save_dir: Path,
             on_done: Callable[[Optional[str]], None]):
        if cls._instance and cls._instance.win.winfo_exists():
            cls._instance.win.lift()
            return
        cls._instance = cls(root, image, save_dir, on_done)
        return cls._instance

    def __init__(self, root, image: Image.Image, save_dir: Path,
                 on_done: Callable[[Optional[str]], None]):
        self.root     = root
        self.src_img  = image.convert("RGB")
        self.save_dir = Path(save_dir)
        self.on_done  = on_done

        # 编辑状态
        self._tool       = "rect"
        self._color      = self.COLORS[0]
        self._width      = 3
        self._font_size  = 18
        self._mosaic_size= 14
        self._annots: list[_Annotation] = []
        self._redo_stack: list[_Annotation] = []
        self._drawing: Optional[_Annotation] = None
        self._tool_btns: dict[str, tk.Button] = {}
        self._color_btns: list[tk.Button] = []
        self._tk_img = None
        self._flatten_img = None

        self.win = tk.Toplevel(root)
        self.win.title(_t("shot.window.title"))
        self.win.configure(bg=self.BG)
        self.win.protocol("WM_DELETE_WINDOW", self._on_cancel)

        # 根据图片尺寸决定窗口大小（缩放 ≤ 屏幕 80%）
        sw = self.win.winfo_screenwidth()
        sh = self.win.winfo_screenheight()
        img_w, img_h = self.src_img.size
        max_w = int(sw * 0.82) - 140
        max_h = int(sh * 0.82) - 120
        scale = min(1.0, max_w / img_w, max_h / img_h)
        self._scale = scale
        show_w = max(100, int(img_w * scale))
        show_h = max(100, int(img_h * scale))
        self._win_w = show_w + 150
        self._win_h = show_h + 118  # 底栏两行 + 工具区预留
        self.win.geometry(f"{self._win_w}x{self._win_h}")
        self.win.minsize(700, 420)

        self._build_ui(show_w, show_h)
        self._bind_shortcuts()
        self._render()

        # 置顶 + 焦点
        self.win.update_idletasks()
        self.win.lift()
        self.win.attributes("-topmost", True)
        self.win.after(150, lambda: self.win.attributes("-topmost", False))
        self.win.focus_force()

    # ══════════════════════════════════════════════════════
    # UI
    # ══════════════════════════════════════════════════════
    def _build_ui(self, show_w, show_h):
        side = tk.Frame(self.win, bg=self.BG2, width=130)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)

        tk.Label(side, text=_t("shot.tools"), bg=self.BG2, fg=self.ACC,
                 font=("Microsoft YaHei UI", 11, "bold")
                 ).pack(pady=(10, 6))

        for key, label in [
            ("rect",   _t("shot.tool.rect")),
            ("oval",   _t("shot.tool.oval")),
            ("arrow",  _t("shot.tool.arrow")),
            ("pen",    _t("shot.tool.pen")),
            ("text",   _t("shot.tool.text")),
            ("mosaic", _t("shot.tool.mosaic")),
        ]:
            b = tk.Button(side, text=label, width=12,
                          command=lambda k=key: self._set_tool(k),
                          bg=self.BG3, fg=self.FG, relief="flat",
                          font=("Microsoft YaHei UI", 10),
                          padx=6, pady=5, cursor="hand2",
                          activebackground=self.ACC)
            b.pack(padx=10, pady=2, fill="x")
            self._tool_btns[key] = b

        tk.Label(side, text=_t("shot.color"), bg=self.BG2, fg=self.FG_DIM,
                 font=("Microsoft YaHei UI", 10)
                 ).pack(pady=(14, 2))
        cf = tk.Frame(side, bg=self.BG2)
        cf.pack(pady=2)
        for i, c in enumerate(self.COLORS):
            b = tk.Button(cf, bg=c, width=2, height=1, bd=0,
                          relief="flat", cursor="hand2",
                          command=lambda cc=c: self._set_color(cc),
                          activebackground=c)
            b.grid(row=i // 4, column=i % 4, padx=2, pady=2)
            self._color_btns.append(b)
        tk.Button(side, text=_t("shot.color.more"), command=self._pick_color,
                  bg=self.BG3, fg=self.FG, relief="flat",
                  font=("Microsoft YaHei UI", 9),
                  padx=4, pady=2, cursor="hand2",
                  activebackground=self.ACC
                  ).pack(pady=(4, 10), padx=10, fill="x")

        tk.Label(side, text=_t("shot.thickness"), bg=self.BG2, fg=self.FG_DIM,
                 font=("Microsoft YaHei UI", 10)).pack(pady=(4, 0))
        self._w_var = tk.IntVar(value=self._width)
        tk.Scale(side, from_=1, to=12, orient="horizontal",
                 variable=self._w_var, command=lambda v: self._set_width(int(v)),
                 bg=self.BG2, fg=self.FG, troughcolor=self.BG3,
                 highlightthickness=0, length=110,
                 font=("Microsoft YaHei UI", 8)
                 ).pack(padx=10)

        tk.Frame(side, bg="#333355", height=1).pack(fill="x",
                                                     pady=10, padx=6)
        tk.Button(side, text=_t("shot.btn.undo"), command=self._undo,
                  bg=self.BG3, fg=self.FG, relief="flat",
                  font=("Microsoft YaHei UI", 9),
                  padx=4, pady=5, cursor="hand2",
                  activebackground=self.ACC
                  ).pack(padx=10, pady=2, fill="x")
        tk.Button(side, text=_t("shot.btn.redo"), command=self._redo,
                  bg=self.BG3, fg=self.FG, relief="flat",
                  font=("Microsoft YaHei UI", 9),
                  padx=4, pady=5, cursor="hand2",
                  activebackground=self.ACC
                  ).pack(padx=10, pady=2, fill="x")
        tk.Button(side, text=_t("shot.btn.clear"), command=self._clear_all,
                  bg=self.BG3, fg=self.FG, relief="flat",
                  font=("Microsoft YaHei UI", 9),
                  padx=4, pady=5, cursor="hand2",
                  activebackground="#ef5350"
                  ).pack(padx=10, pady=2, fill="x")

        main = tk.Frame(self.win, bg=self.BG)
        main.pack(side="right", fill="both", expand=True)

        self.canvas = tk.Canvas(main, bg="#111",
                                width=show_w, height=show_h,
                                highlightthickness=0, cursor="cross")
        self.canvas.pack(side="top", fill="both", expand=True,
                         padx=8, pady=8)

        # ── 底栏（两行布局）────────────────────────────
        bot = tk.Frame(main, bg=self.BG2, height=78)
        bot.pack(side="bottom", fill="x")
        bot.pack_propagate(False)

        # 第 1 行：尺寸信息
        row1 = tk.Frame(bot, bg=self.BG2)
        row1.pack(fill="x", padx=12, pady=(6, 0))
        self.lbl_info = tk.Label(
            row1,
            text=_t("shot.info",
                    w=self.src_img.size[0], h=self.src_img.size[1],
                    pct=int(self._scale * 100)),
            bg=self.BG2, fg=self.FG_DIM,
            font=("Microsoft YaHei UI", 9))
        self.lbl_info.pack(side="left")

        # 第 2 行：文件名编辑 + 保存路径预览 + 保存/取消 按钮
        row2 = tk.Frame(bot, bg=self.BG2)
        row2.pack(fill="x", padx=12, pady=(2, 8))

        # 取消
        tk.Button(row2, text=_t("shot.btn.cancel"), command=self._on_cancel,
                  bg=self.BG3, fg=self.FG, relief="flat",
                  font=("Microsoft YaHei UI", 10), padx=14, pady=6,
                  cursor="hand2", activebackground="#ef5350",
                  activeforeground="#fff"
                  ).pack(side="right", padx=(4, 0), pady=0)
        # 保存
        tk.Button(row2, text=_t("shot.btn.save"), command=self._on_save,
                  bg="#0d7377", fg="#fff", relief="flat",
                  font=("Microsoft YaHei UI", 10, "bold"),
                  padx=16, pady=6, cursor="hand2",
                  activebackground="#14a085", activeforeground="#fff"
                  ).pack(side="right", padx=4, pady=0)

        # 保存路径预览（左中）—— 在"保存"按钮左边
        path_frame = tk.Frame(row2, bg=self.BG2)
        path_frame.pack(side="left", fill="x", expand=True)

        tk.Label(path_frame, text=_t("shot.filename"), bg=self.BG2, fg=self.FG_DIM,
                 font=("Microsoft YaHei UI", 9)
                 ).pack(side="left")

        import random as _rnd
        self._default_basename = (
            f"{datetime.now().strftime('%H%M%S')}_"
            f"{_rnd.randint(0, 999):03d}{_t('shot.tag.suffix')}"
        )
        self._name_var = tk.StringVar(value=self._default_basename)
        self.e_name = tk.Entry(
            path_frame, textvariable=self._name_var, width=22,
            bg=self.BG3, fg=self.FG, insertbackground=self.FG,
            relief="flat", font=("Consolas", 10))
        self.e_name.pack(side="left", padx=4, ipady=3)
        tk.Label(path_frame, text=".jpg", bg=self.BG2, fg=self.ACC,
                 font=("Microsoft YaHei UI", 9, "bold")
                 ).pack(side="left")

        # 完整路径预览
        self.lbl_path = tk.Label(
            path_frame, text="", bg=self.BG2, fg=self.FG_DIM,
            font=("Microsoft YaHei UI", 9),
            anchor="w", justify="left")
        self.lbl_path.pack(side="left", padx=(12, 0), fill="x", expand=True)

        # 文件名变化时刷新路径预览
        self._name_var.trace_add("write", lambda *_: self._update_path_preview())
        self._update_path_preview()

        self.canvas.bind("<ButtonPress-1>",   self._on_canvas_press)
        self.canvas.bind("<B1-Motion>",       self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)

        self._set_tool(self._tool)
        self._set_color(self._color)

    def _bind_shortcuts(self):
        self.win.bind("<Control-z>", lambda _e: self._undo())
        self.win.bind("<Control-Z>", lambda _e: self._undo())
        self.win.bind("<Control-y>", lambda _e: self._redo())
        self.win.bind("<Control-Y>", lambda _e: self._redo())
        self.win.bind("<Control-s>", lambda _e: self._on_save())
        self.win.bind("<Control-S>", lambda _e: self._on_save())
        self.win.bind("<Escape>",    lambda _e: self._on_cancel())

    def _set_tool(self, t: str):
        self._tool = t
        for key, btn in self._tool_btns.items():
            btn.config(bg=self.TOOL_ACT if key == t else self.BG3)

    def _set_color(self, c: str):
        self._color = c
        for i, btn in enumerate(self._color_btns):
            btn.config(relief="sunken" if self.COLORS[i] == c else "flat",
                       bd=2 if self.COLORS[i] == c else 0)

    def _pick_color(self):
        r = colorchooser.askcolor(color=self._color, parent=self.win)
        if r and r[1]:
            self._color = r[1]
            for btn in self._color_btns:
                btn.config(relief="flat", bd=0)

    def _set_width(self, w: int):
        self._width = w

    def _to_img_coord(self, cx, cy) -> Tuple[int, int]:
        return int(cx / self._scale), int(cy / self._scale)

    def _on_canvas_press(self, e):
        self._redo_stack.clear()
        ix, iy = self._to_img_coord(e.x, e.y)

        if self._tool == "text":
            txt = simpledialog.askstring(_t("shot.text.dialog.title"),
                                         _t("shot.text.dialog.prompt"),
                                         parent=self.win)
            if txt:
                self._annots.append(_Annotation(
                    "text", [(ix, iy)], color=self._color,
                    text=txt, font_size=self._font_size))
                self._render()
            return

        self._drawing = _Annotation(
            self._tool, [(ix, iy)], color=self._color,
            width=self._width, mosaic_size=self._mosaic_size)

    def _on_canvas_drag(self, e):
        if self._drawing is None:
            return
        ix, iy = self._to_img_coord(e.x, e.y)
        if self._drawing.kind == "pen":
            self._drawing.points.append((ix, iy))
        else:
            if len(self._drawing.points) == 1:
                self._drawing.points.append((ix, iy))
            else:
                self._drawing.points[-1] = (ix, iy)
        self._render_preview()

    def _on_canvas_release(self, e):
        if self._drawing is None:
            return
        pts = self._drawing.points
        if len(pts) >= 2:
            (x0, y0), (x1, y1) = pts[0], pts[-1]
            if self._drawing.kind != "pen" and \
                    abs(x1 - x0) < 3 and abs(y1 - y0) < 3:
                self._drawing = None
                self._render()
                return
        if len(pts) < 1:
            self._drawing = None
            return
        self._annots.append(self._drawing)
        self._drawing = None
        self._render()

    def _undo(self):
        if self._annots:
            self._redo_stack.append(self._annots.pop())
            self._render()

    def _redo(self):
        if self._redo_stack:
            self._annots.append(self._redo_stack.pop())
            self._render()

    def _clear_all(self):
        if not self._annots:
            return
        if messagebox.askyesno(_t("common.confirm"), _t("shot.confirm.clear"), parent=self.win):
            self._redo_stack.extend(reversed(self._annots))
            self._annots.clear()
            self._render()

    def _render(self):
        self._flatten_img = self._compose_image(include_drawing=False)
        disp = self._flatten_img
        if self._scale != 1.0:
            disp = disp.resize(
                (int(disp.size[0] * self._scale),
                 int(disp.size[1] * self._scale)),
                Image.LANCZOS)
        self._tk_img = ImageTk.PhotoImage(disp)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self._tk_img)

    def _render_preview(self):
        if not self._drawing:
            self._render()
            return
        img = self._flatten_img.copy() if self._flatten_img \
            else self.src_img.copy()
        self._draw_annotation(img, self._drawing)
        if self._scale != 1.0:
            img = img.resize(
                (int(img.size[0] * self._scale),
                 int(img.size[1] * self._scale)),
                Image.LANCZOS)
        self._tk_img = ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self._tk_img)

    def _compose_image(self, include_drawing: bool = True) -> Image.Image:
        img = self.src_img.copy()
        for a in self._annots:
            self._draw_annotation(img, a)
        if include_drawing and self._drawing:
            self._draw_annotation(img, self._drawing)
        return img

    def _draw_annotation(self, img: Image.Image, a: _Annotation):
        if not a.points:
            return
        if a.kind == "mosaic":
            self._apply_mosaic(img, a)
            return

        draw = ImageDraw.Draw(img, "RGBA")
        col  = a.color
        w    = a.width

        if a.kind == "rect":
            if len(a.points) >= 2:
                (x0, y0), (x1, y1) = a.points[0], a.points[-1]
                bbox = (min(x0, x1), min(y0, y1),
                        max(x0, x1), max(y0, y1))
                draw.rectangle(bbox, outline=col, width=w)

        elif a.kind == "oval":
            if len(a.points) >= 2:
                (x0, y0), (x1, y1) = a.points[0], a.points[-1]
                bbox = (min(x0, x1), min(y0, y1),
                        max(x0, x1), max(y0, y1))
                draw.ellipse(bbox, outline=col, width=w)

        elif a.kind == "arrow":
            if len(a.points) >= 2:
                (x0, y0), (x1, y1) = a.points[0], a.points[-1]
                draw.line([(x0, y0), (x1, y1)], fill=col, width=w)
                self._draw_arrow_head(draw, x0, y0, x1, y1, col, w)

        elif a.kind == "pen":
            pts = a.points
            if len(pts) >= 2:
                draw.line(pts, fill=col, width=w, joint="curve")

        elif a.kind == "text":
            x, y = a.points[0]
            try:
                font = ImageFont.truetype("msyh.ttc", a.font_size)
            except Exception:
                try:
                    font = ImageFont.truetype("simhei.ttf", a.font_size)
                except Exception:
                    font = ImageFont.load_default()
            self._draw_text_with_outline(draw, (x, y), a.text, font, col)

    @staticmethod
    def _draw_arrow_head(draw, x0, y0, x1, y1, color, width):
        size = 10 + width * 2
        angle = math.atan2(y1 - y0, x1 - x0)
        a1 = angle + math.radians(160)
        a2 = angle - math.radians(160)
        p1 = (x1 + size * math.cos(a1), y1 + size * math.sin(a1))
        p2 = (x1 + size * math.cos(a2), y1 + size * math.sin(a2))
        draw.polygon([(x1, y1), p1, p2], fill=color)

    @staticmethod
    def _draw_text_with_outline(draw, xy, text, font, color):
        x, y = xy
        outline = "#000000" if color.lower() != "#000000" else "#ffffff"
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                draw.text((x + dx, y + dy), text, fill=outline, font=font)
        draw.text((x, y), text, fill=color, font=font)

    def _apply_mosaic(self, img: Image.Image, a: _Annotation):
        if len(a.points) < 2:
            return
        (x0, y0), (x1, y1) = a.points[0], a.points[-1]
        bbox = (max(0, min(x0, x1)), max(0, min(y0, y1)),
                min(img.size[0], max(x0, x1)),
                min(img.size[1], max(y0, y1)))
        if bbox[2] - bbox[0] < 4 or bbox[3] - bbox[1] < 4:
            return
        region = img.crop(bbox)
        block = max(4, a.mosaic_size)
        small_w = max(1, region.size[0] // block)
        small_h = max(1, region.size[1] // block)
        region = region.resize((small_w, small_h), Image.NEAREST)
        region = region.resize(
            (bbox[2] - bbox[0], bbox[3] - bbox[1]), Image.NEAREST)
        img.paste(region, bbox)

    def _on_save(self, _e=None):
        final = self._compose_image(include_drawing=False)
        path = None
        try:
            path = self._gen_save_path()
            # 若同名文件已存在，自动追加 _1 / _2 ...
            if path.exists():
                stem = path.stem
                parent = path.parent
                i = 1
                while True:
                    cand = parent / f"{stem}_{i}.jpg"
                    if not cand.exists():
                        path = cand
                        break
                    i += 1
            path.parent.mkdir(parents=True, exist_ok=True)
            final.save(path, "JPEG", quality=90, optimize=True)
            _log(f"saved → {path}")
        except Exception as ex:
            messagebox.showerror(_t("shot.save_failed"), str(ex), parent=self.win)
            return
        self._close()
        if self.on_done:
            try:
                self.on_done(str(path))
            except Exception:
                traceback.print_exc()

    # ── 文件名/路径 ─────────────────────────────────────
    _INVALID_NAME_CHARS = re.compile(r'[\\/:*?"<>|\r\n\t]+')

    def _sanitize_name(self, raw: str) -> str:
        """把用户输入的文件名清洗成合法的 Windows 文件名基名（不带扩展）"""
        name = (raw or "").strip()
        # 去掉非法字符
        name = self._INVALID_NAME_CHARS.sub("_", name)
        # 去除用户自己多打的 .jpg/.jpeg
        for ext in (".jpg", ".jpeg", ".JPG", ".JPEG"):
            if name.endswith(ext):
                name = name[: -len(ext)]
        name = name.strip(". ")
        if not name:
            name = self._default_basename
        # Windows 路径总长度限制，保险截断
        return name[:120]

    def _gen_save_path(self) -> Path:
        base = self._sanitize_name(
            self._name_var.get() if hasattr(self, "_name_var")
            else self._default_basename)
        sub = self.save_dir / datetime.now().strftime("%Y%m%d")
        return sub / f"{base}.jpg"

    def _update_path_preview(self):
        """实时刷新底栏的完整保存路径显示"""
        if not hasattr(self, "lbl_path"):
            return
        p = self._gen_save_path()
        # 过长时中间省略
        full = str(p)
        if len(full) > 72:
            full = full[:32] + "…" + full[-38:]
        self.lbl_path.config(text=f"→ {full}")

    def _on_cancel(self, _e=None):
        if self._annots and \
                not messagebox.askyesno(_t("common.confirm"),
                                        _t("shot.cancel.confirm"),
                                        parent=self.win):
            return
        self._close()
        if self.on_done:
            try:
                self.on_done(None)
            except Exception:
                traceback.print_exc()

    def _close(self):
        try:
            self.win.destroy()
        except Exception:
            pass
        ScreenshotEditor._instance = None


# ══════════════════════════════════════════════════════════
# 对外入口
# ══════════════════════════════════════════════════════════
def capture_and_edit(root, save_dir, on_done: Callable[[Optional[str]], None],
                     hide_windows: Optional[list] = None):
    """
    启动截图流程：
      1) 临时 withdraw 调用方窗口（避免挡屏、避免被截进去）
      2) 弹出全屏选区
      3) 选到区域 → 打开编辑器；取消 → 立刻恢复+回调 None
      4) 编辑器保存/取消 → 恢复调用方窗口 + 回调路径

    任何异常都保证恢复窗口并回调 None，不吞异常而 crash。
    """
    save_dir = Path(save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)

    # 记录并隐藏需要临时隐藏的窗口
    hidden: list = []
    for w in (hide_windows or []):
        try:
            if w is None:
                continue
            if not w.winfo_exists():
                continue
            if w.winfo_viewable():
                w.withdraw()
                hidden.append(w)
        except Exception:
            pass

    restored = {"v": False}

    def _restore_windows():
        if restored["v"]:
            return
        restored["v"] = True
        for w in hidden:
            try:
                w.deiconify()
                w.lift()
            except Exception:
                pass

    def _safe_done(path):
        _restore_windows()
        try:
            if on_done:
                on_done(path)
        except Exception:
            traceback.print_exc()

    def _after_pick(img, bbox):
        if img is None:
            _log("user cancelled region pick")
            _safe_done(None)
            return

        def _on_editor_done(path):
            _safe_done(path)

        try:
            ScreenshotEditor.open(root, img, save_dir, _on_editor_done)
        except Exception as e:
            traceback.print_exc()
            _log(f"打开编辑器失败: {e}")
            _safe_done(None)

    def _do_capture():
        try:
            _RegionPicker(root, _after_pick)
        except Exception as e:
            traceback.print_exc()
            _log(f"启动截图失败: {e}")
            _safe_done(None)

    # 让 withdraw 生效（Windows 有时要 200ms 左右）
    root.after(250, _do_capture)
