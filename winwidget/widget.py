# -*- coding: utf-8 -*-
"""
חלונית קטנה always-on-top למסך Windows.
הרצה:  py widget.py     (או)   python widget.py
"""

import tkinter as tk
from tkinter import messagebox
import datetime


# ---------- פעולות הכפתורים (כאן משנים מה כל כפתור עושה) ----------

def on_button_1():
    messagebox.showinfo("כפתור 1", "לחצת על כפתור 1")


def on_button_2():
    now = datetime.datetime.now().strftime("%H:%M:%S")
    status_var.set("השעה: " + now)


def on_button_3():
    status_var.set("מוכן")


# ---------- בניית החלונית ----------

root = tk.Tk()
root.title("Widget")
root.overrideredirect(True)          # ללא מסגרת חלון של Windows
root.attributes("-topmost", True)    # תמיד למעלה
root.attributes("-alpha", 0.95)      # שקיפות עדינה
root.configure(bg="#1e1e2e")

# מיקום התחלתי - פינה ימנית עליונה
W, H = 220, 170
sw = root.winfo_screenwidth()
root.geometry(f"{W}x{H}+{sw - W - 20}+20")

# --- פס כותרת לגרירה + כפתור סגירה ---
bar = tk.Frame(root, bg="#313244", height=26)
bar.pack(fill="x")

title = tk.Label(bar, text="☰  Widget", bg="#313244", fg="#cdd6f4",
                 font=("Segoe UI", 9, "bold"))
title.pack(side="left", padx=8)

close_btn = tk.Label(bar, text="✕", bg="#313244", fg="#f38ba8",
                     font=("Segoe UI", 11, "bold"), cursor="hand2")
close_btn.pack(side="right", padx=8)
close_btn.bind("<Button-1>", lambda e: root.destroy())

# גרירת החלונית באמצעות פס הכותרת
_drag = {"x": 0, "y": 0}


def start_drag(e):
    _drag["x"] = e.x
    _drag["y"] = e.y


def do_drag(e):
    x = root.winfo_x() + e.x - _drag["x"]
    y = root.winfo_y() + e.y - _drag["y"]
    root.geometry(f"+{x}+{y}")


for w in (bar, title):
    w.bind("<Button-1>", start_drag)
    w.bind("<B1-Motion>", do_drag)

# --- אזור הכפתורים ---
body = tk.Frame(root, bg="#1e1e2e")
body.pack(fill="both", expand=True, padx=10, pady=8)


def make_button(text, cmd):
    b = tk.Button(body, text=text, command=cmd, bg="#45475a", fg="#cdd6f4",
                  activebackground="#585b70", activeforeground="#ffffff",
                  relief="flat", font=("Segoe UI", 10), cursor="hand2",
                  bd=0, pady=4)
    b.pack(fill="x", pady=3)
    return b


make_button("כפתור 1", on_button_1)
make_button("הצג שעה", on_button_2)
make_button("איפוס", on_button_3)

# --- שורת סטטוס ---
status_var = tk.StringVar(value="מוכן")
status = tk.Label(root, textvariable=status_var, bg="#181825", fg="#a6adc8",
                  anchor="e", font=("Segoe UI", 8), padx=8)
status.pack(fill="x", side="bottom")

root.mainloop()
