"""
闹钟提醒弹窗（跨平台）
"""
import tkinter as tk
import threading

from models import Task
from platform_utils import beep
from i18n import t


def ring(root: tk.Tk, tasks: list):
    """弹出提醒弹窗（非阻塞）"""
    if not tasks:
        return
    # 后台播放提示音
    threading.Thread(target=beep, daemon=True).start()
    for task in tasks:
        _popup(root, task)


def _popup(root: tk.Tk, task: Task):
    pop = tk.Toplevel(root)
    pop.title(t("alarm.title"))
    pop.geometry("360x220")
    pop.configure(bg="#1a1a2e")
    pop.resizable(False, False)
    pop.wm_attributes("-topmost", True)
    pop.update_idletasks()
    sw = pop.winfo_screenwidth()
    sh = pop.winfo_screenheight()
    x = (sw - 360) // 2
    y = (sh - 220) // 2
    pop.geometry(f"360x220+{x}+{y}")

    tk.Label(pop, text=t("alarm.title"), bg="#1a1a2e", fg="#4fc3f7",
             font=("Microsoft YaHei UI", 14, "bold")).pack(pady=(16, 4))

    tk.Label(pop, text=task.title, bg="#1a1a2e", fg="#fff",
             font=("Microsoft YaHei UI", 13, "bold"),
             wraplength=320).pack(pady=4)

    if task.content:
        s = (task.content[:80] + "…") if len(task.content) > 80 else task.content
        tk.Label(pop, text=s, bg="#1a1a2e", fg="#aaa",
                 font=("Microsoft YaHei UI", 10),
                 wraplength=320, justify="center").pack(pady=2)

    if task.goal:
        tk.Label(pop, text=f"🎯 {task.goal}", bg="#1a1a2e", fg="#ffd54f",
                 font=("Microsoft YaHei UI", 10)).pack(pady=2)

    tk.Button(pop, text=t("alarm.btn.ack"), command=pop.destroy,
              bg="#0d7377", fg="#fff", relief="flat",
              padx=20, pady=6, cursor="hand2",
              font=("Microsoft YaHei UI", 11, "bold"),
              activebackground="#14a085").pack(pady=10)

    pop.after(30000, lambda: pop.destroy() if pop.winfo_exists() else None)
