"""
闹钟提醒弹窗
"""
import tkinter as tk
import threading
import winsound
from models import Task


def ring(root: tk.Tk, tasks: list):
    """弹出提醒弹窗（非阻塞）"""
    if not tasks:
        return
    # 后台播放提示音
    threading.Thread(target=_beep, daemon=True).start()
    # 每个任务一个弹窗
    for t in tasks:
        _popup(root, t)


def _beep():
    try:
        for _ in range(3):
            winsound.Beep(880, 200)
            winsound.Beep(660, 180)
    except Exception:
        pass


def _popup(root: tk.Tk, t: Task):
    pop = tk.Toplevel(root)
    pop.title("⏰ 任务提醒")
    pop.geometry("360x220")
    pop.configure(bg="#1a1a2e")
    pop.resizable(False, False)
    pop.wm_attributes("-topmost", True)
    # 居中
    pop.update_idletasks()
    sw = pop.winfo_screenwidth()
    sh = pop.winfo_screenheight()
    x = (sw - 360) // 2
    y = (sh - 220) // 2
    pop.geometry(f"360x220+{x}+{y}")

    tk.Label(pop, text="⏰ 任务提醒", bg="#1a1a2e", fg="#4fc3f7",
             font=("Microsoft YaHei UI", 14, "bold")).pack(pady=(16, 4))

    tk.Label(pop, text=t.title, bg="#1a1a2e", fg="#fff",
             font=("Microsoft YaHei UI", 13, "bold"),
             wraplength=320).pack(pady=4)

    if t.content:
        s = (t.content[:80] + "…") if len(t.content) > 80 else t.content
        tk.Label(pop, text=s, bg="#1a1a2e", fg="#aaa",
                 font=("Microsoft YaHei UI", 10),
                 wraplength=320, justify="center").pack(pady=2)

    if t.goal:
        tk.Label(pop, text=f"🎯 {t.goal}", bg="#1a1a2e", fg="#ffd54f",
                 font=("Microsoft YaHei UI", 10)).pack(pady=2)

    tk.Button(pop, text="知道了", command=pop.destroy,
              bg="#0d7377", fg="#fff", relief="flat",
              padx=20, pady=6, cursor="hand2",
              font=("Microsoft YaHei UI", 11, "bold"),
              activebackground="#14a085").pack(pady=10)

    # 30秒后自动关闭
    pop.after(30000, lambda: pop.destroy() if pop.winfo_exists() else None)
