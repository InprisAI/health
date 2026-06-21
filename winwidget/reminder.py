# -*- coding: utf-8 -*-
"""
תזכורת לקום מהכסא ולעשות פעילות.
מקפיצה התראה כל שעתיים בשעות 8:00, 10:00, 12:00, 14:00, 16:00, 18:00.

הרצה:  py reminder.py        (עם חלון מסוף)
        run_reminder.bat      (ברקע, ללא מסוף)
"""

import tkinter as tk
import datetime
import winsound

# השעות שבהן תוצג תזכורת (כל שעתיים, 8 עד 18)
REMINDER_HOURS = [8, 10, 12, 14, 16, 18]

# מעקב כדי לא להקפיץ פעמיים באותה שעה
_last_fired_hour = None


def next_reminder_text():
    """טקסט: מתי התזכורת הבאה."""
    now = datetime.datetime.now()
    for h in REMINDER_HOURS:
        if h > now.hour or (h == now.hour and now.minute == 0):
            return f"{h:02d}:00 🚶"
    return "מחר 08:00 🚶"


def show_alert():
    """חלון התראה גדול וברור שקופץ מעל הכל."""
    try:
        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
    except Exception:
        pass

    alert = tk.Toplevel(root)
    alert.title("תזכורת")
    alert.attributes("-topmost", True)
    alert.configure(bg="#1e1e2e")
    alert.overrideredirect(True)

    W, H = 380, 230
    sw, sh = alert.winfo_screenwidth(), alert.winfo_screenheight()
    alert.geometry(f"{W}x{H}+{(sw - W) // 2}+{(sh - H) // 3}")

    tk.Label(alert, text="🚶", bg="#1e1e2e", fg="#f9e2af",
             font=("Segoe UI Emoji", 48)).pack(pady=(22, 4))
    tk.Label(alert, text="זמן לקום מהכסא!", bg="#1e1e2e", fg="#f38ba8",
             font=("Segoe UI", 18, "bold")).pack()
    tk.Label(alert, text="קום, מתח את הגוף ועשה קצת פעילות 🙂",
             bg="#1e1e2e", fg="#cdd6f4", font=("Segoe UI", 11)).pack(pady=6)

    tk.Button(alert, text="קמתי ✓", command=alert.destroy,
              bg="#a6e3a1", fg="#11111b", activebackground="#94d3a2",
              relief="flat", font=("Segoe UI", 12, "bold"),
              cursor="hand2", bd=0, padx=20, pady=6).pack(pady=14)

    # סגירה אוטומטית אחרי 5 דקות אם לא נסגר ידנית
    alert.after(5 * 60 * 1000, lambda: alert.winfo_exists() and alert.destroy())


def tick():
    """נבדק כל 20 שניות: האם הגיעה שעת תזכורת."""
    global _last_fired_hour
    now = datetime.datetime.now()

    if now.hour in REMINDER_HOURS and now.minute == 0:
        if _last_fired_hour != now.hour:
            _last_fired_hour = now.hour
            show_alert()
    elif now.minute != 0:
        _last_fired_hour = None  # איפוס לקראת השעה הבאה

    canvas.itemconfig(status_item, text=next_reminder_text())
    root.after(20 * 1000, tick)


# ---------- חלון סטטוס קטן (always-on-top, פינות מעוגלות) ----------
TRANSP = "#ff00ff"   # צבע "מפתח כרומה" - הופך לשקוף, יוצר את הפינות המעוגלות
W, H = 220, 96
RADIUS = 22

root = tk.Tk()
root.title("תזכורת פעילות")
root.attributes("-topmost", True)
root.overrideredirect(True)
root.configure(bg=TRANSP)
root.wm_attributes("-transparentcolor", TRANSP)

canvas = tk.Canvas(root, width=W, height=H, bg=TRANSP, highlightthickness=0)
canvas.pack()


def round_rect(c, x1, y1, x2, y2, r, **kw):
    """מצייר מלבן עם פינות מעוגלות באמצעות פוליגון חלק."""
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return c.create_polygon(pts, smooth=True, **kw)


# גוף החלונית: רקע כהה + מסגרת ירוקה עדינה, פינות מעוגלות
round_rect(canvas, 2, 2, W - 2, H - 2, RADIUS,
           fill="#1e1e2e", outline="#a6e3a1", width=2)

# שעה + אייקון במרכז
status_item = canvas.create_text(W // 2, H // 2 + 6, text="",
                                 fill="#a6e3a1", font=("Segoe UI Emoji", 26))

# כפתורי סגירה (✕) ובדיקה (▶) בפינות העליונות
canvas.create_text(W - 18, 16, text="✕", fill="#f38ba8",
                   font=("Segoe UI", 12, "bold"), tags="close")
canvas.create_text(18, 16, text="▶", fill="#585b70",
                   font=("Segoe UI", 10), tags="test")

canvas.tag_bind("close", "<Button-1>", lambda e: root.destroy())
canvas.tag_bind("test", "<Button-1>", lambda e: show_alert())
for tag in ("close", "test"):
    canvas.tag_bind(tag, "<Enter>", lambda e: canvas.config(cursor="hand2"))
    canvas.tag_bind(tag, "<Leave>", lambda e: canvas.config(cursor=""))

# גרירת החלונית מאזור הרקע
_drag = {"x": 0, "y": 0}
canvas.bind("<Button-1>", lambda e: _drag.update(x=e.x, y=e.y))
canvas.bind("<B1-Motion>", lambda e: root.geometry(
    f"+{root.winfo_x() + e.x - _drag['x']}+{root.winfo_y() + e.y - _drag['y']}"))

# מיקום בפינה ימנית עליונה
sw = root.winfo_screenwidth()
root.geometry(f"{W}x{H}+{sw - W - 20}+20")

tick()
root.mainloop()
