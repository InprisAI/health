# -*- coding: utf-8 -*-
"""
תזכורת לקום מהכסא ולעשות פעילות.
מקפיצה התראה כל שעתיים בשעות 8:00, 10:00, 12:00, 14:00, 16:00, 18:00.

הרצה:  py reminder.py        (עם חלון מסוף)
        run_reminder.bat      (ברקע, ללא מסוף)
"""

import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk
import datetime
import json
import os
import shutil
import sys
import winsound
from pathlib import Path
from PIL import Image, ImageTk

SKY = "#74c7ec"  # ניסוי: תכלת
GREEN = "#a6e3a1"
GREEN_HOVER = "#94d3a2"
MAGENTA = "#ff00ff"
ALERT_TRANSP = "#010001"  # כרומה לפינות — לא מגנטה


def _is_frozen():
    return getattr(sys, "frozen", False)


def _user_data_dir():
    if _is_frozen():
        d = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "HealthReminder"
        d.mkdir(parents=True, exist_ok=True)
        return d
    return Path(__file__).parent


def _resource_dir():
    if _is_frozen():
        return Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    return Path(__file__).parent


DEFAULT_RULES = [
    {"from": "08:00", "to": "18:00", "every_minutes": 120, "reason": "כושר גופני"},
    {"from": "13:00", "to": "", "every_minutes": "", "reason": "ארוחת צהרים"},
]
DEFAULT_VOICE = "male"
ACTIVITY_MSG = {
    "male": "קום, מתח את הגוף ועשה קצת פעילות",
    "female": "קומי, מתחי את הגוף ועשי קצת פעילות",
}

_POS_FILE = _user_data_dir() / "windows_reminder_pos.json"
_SETTINGS_FILE = _user_data_dir() / "windows_reminder_settings.json"


def _ensure_user_settings():
    if _SETTINGS_FILE.exists():
        return
    bundled = _resource_dir() / "windows_reminder_settings.json"
    try:
        if bundled.exists():
            shutil.copy(bundled, _SETTINGS_FILE)
        else:
            _SETTINGS_FILE.write_text(
                json.dumps({"rules": [dict(r) for r in DEFAULT_RULES], "voice": DEFAULT_VOICE},
                           ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
    except OSError:
        pass


def _load_position(default_x, default_y):
    try:
        data = json.loads(_POS_FILE.read_text(encoding="utf-8"))
        return int(data["x"]), int(data["y"])
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return default_x, default_y


def _save_position():
    try:
        _POS_FILE.write_text(
            json.dumps({"x": root.winfo_x(), "y": root.winfo_y()}),
            encoding="utf-8",
        )
    except OSError:
        pass


_settings = None
_last_fired_slot = None


def _is_empty_field(text):
    s = (text or "").strip()
    return not s or set(s) <= {"-", "—", "–"}


def _normalize_rule(rule):
    """רק מ- מלא = אירוע חד-פעמי באותה שעה."""
    rule = dict(rule)
    from_v = (rule.get("from") or "").strip()
    to_v = (rule.get("to") or "").strip()
    if from_v and (_is_empty_field(to_v) or to_v == from_v):
        rule["to"] = ""
        rule["every_minutes"] = ""
    return rule


def _parse_hm(text):
    h, m = text.strip().split(":")
    return datetime.time(int(h), int(m))


def _normalize_settings(data):
    voice = data.get("voice", DEFAULT_VOICE)
    if voice not in ACTIVITY_MSG:
        voice = DEFAULT_VOICE
    rules = data.get("rules") or [dict(r) for r in DEFAULT_RULES]
    return {
        "voice": voice,
        "rules": [_normalize_rule(r) for r in rules],
    }


def load_settings():
    global _settings
    _ensure_user_settings()
    try:
        data = json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
        _settings = _normalize_settings(data)
        if data.get("voice") not in ACTIVITY_MSG:
            save_settings()
        return
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        pass
    _settings = _normalize_settings({})


def _activity_message():
    voice = (_settings or {}).get("voice", DEFAULT_VOICE)
    return ACTIVITY_MSG.get(voice, ACTIVITY_MSG[DEFAULT_VOICE])


def _set_voice(voice):
    global _settings
    if voice not in ACTIVITY_MSG:
        return
    if _settings is None:
        load_settings()
    _settings["voice"] = voice
    save_settings()


def save_settings():
    if not _settings:
        return
    payload = {
        "voice": _settings.get("voice", DEFAULT_VOICE),
        "rules": _settings.get("rules", [dict(r) for r in DEFAULT_RULES]),
    }
    try:
        _SETTINGS_FILE.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        _settings["voice"] = payload["voice"]
        _settings["rules"] = payload["rules"]
    except OSError:
        pass


def _rule_slots(rule, day):
    rule = _normalize_rule(rule)
    t0 = _parse_hm(rule["from"])
    if _is_empty_field(rule.get("to")):
        return [datetime.datetime.combine(day, t0)]
    t1 = _parse_hm(rule["to"])
    if t0 == t1:
        return [datetime.datetime.combine(day, t0)]
    start = datetime.datetime.combine(day, t0)
    end = datetime.datetime.combine(day, t1)
    every = max(1, int(rule.get("every_minutes") or 1))
    slots, cur = [], start
    while cur <= end:
        slots.append(cur)
        cur += datetime.timedelta(minutes=every)
    return slots


def _all_slots(from_day, days=2):
    slots = []
    for d in range(days):
        day = from_day + datetime.timedelta(days=d)
        for rule in _settings["rules"]:
            for slot in _rule_slots(rule, day):
                slots.append((slot, rule))
    return sorted(slots, key=lambda x: x[0])


def next_reminder_datetime(now=None):
    """מועד התזכורת הבאה."""
    now = now or datetime.datetime.now()
    for slot, _rule in _all_slots(now.date()):
        if slot > now:
            return slot
    return _all_slots(now.date() + datetime.timedelta(days=1))[0][0]


def _rule_at(now):
    key = now.replace(second=0, microsecond=0).isoformat()
    for slot, rule in _all_slots(now.date()):
        if slot.replace(second=0, microsecond=0).isoformat() == key:
            return rule
    return None


def next_reminder_time(now=None):
    """טקסט השעה הבאה."""
    dt = next_reminder_datetime(now)
    now = now or datetime.datetime.now()
    if dt.date() == now.date():
        return dt.strftime("%H:%M")
    return f"מחר {dt.strftime('%H:%M')}"


def format_remaining(delta):
    """פורמט זמן שנותר."""
    total = max(0, int(delta.total_seconds()))
    if total == 0:
        return "עכשיו!"
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def place_text_right(item, text, font, right_x, y):
    """מיקום מדויק: קצה ימין של הטקסט ב-right_x (Arial proportional)."""
    canvas.itemconfig(item, text=text, font=font, anchor="w")
    canvas.coords(item, right_x - font.measure(text), y)
    canvas.update_idletasks()
    bbox = canvas.bbox(item)
    if bbox:
        canvas.move(item, right_x - bbox[2], 0)


def update_status_display():
    """מעדכן שעה וספירה לאחור."""
    now = datetime.datetime.now()
    place_text_right(status_time, next_reminder_time(now), _wake_font, TIME_RIGHT_X, _wake_y)
    remaining = next_reminder_datetime(now) - now
    place_text_right(status_countdown, format_remaining(remaining), _countdown_font,
                     TIME_RIGHT_X, _countdown_y)


def _load_run_icon(size, *names):
    base = _resource_dir()
    if not names:
        names = ("run.png", "ran.png")
    for name in names:
        path = base / name
        if path.exists():
            img = Image.open(path).convert("RGBA")
            img.thumbnail((size, size), Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(img)
    raise FileNotFoundError(f"Image not found: {names}")


def round_rect(c, x1, y1, x2, y2, r, **kw):
    """מצייר מלבן עם פינות מעוגלות באמצעות פוליגון חלק."""
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return c.create_polygon(pts, smooth=True, **kw)


def _round_radius(h, cap=14):
    """רדיוס פינות — כמו לחצני ההגדרות."""
    return min(cap, max(1, h // 2))


def _draw_round_panel(cv, w, h, border, fill, border_w=1):
    """מצייר רקע מעוגל (מסגרת דקה + מילוי) כמו לחצן."""
    r = _round_radius(h)
    r_in = max(1, r - border_w)
    cv.delete("rshape")
    round_rect(cv, 0, 0, w - 1, h - 1, r, fill=border, outline=border, tags="rshape")
    round_rect(cv, border_w, border_w, w - 1 - border_w, h - 1 - border_w,
               r_in, fill=fill, outline=fill, tags="rshape")
    cv.tag_lower("rshape")


def _card_content_inset(ih, border_w=1, cap=6):
    """Inset לכרטיס — פינות מעוגלות עם מעט padding בלבד."""
    r = _round_radius(ih + border_w * 2)
    extra = min(max(1, r - border_w), cap)
    return border_w + extra, ih + 2 * (border_w + extra)


def _field_pill_size(inner_w, inner_h, border_w=1):
    """מידות גלולה לשדה — פינות בצדדים, גובה קומפקטי."""
    H = inner_h + 2 * border_w
    r = min(14, max(1, H // 2))
    W = inner_w + 2 * r if inner_w is not None else None
    return H, W, r


def _rounded_border_frame(parent, border, fill, border_w=1, padx=0, pady=0, fit_content=False):
    """מסגרת מעוגלת עם frame פנימי."""
    bg = parent.cget("bg")
    wrap = tk.Frame(parent, bg=bg)
    cv = tk.Canvas(wrap, bg=bg, highlightthickness=0, bd=0, height=8)
    if fit_content:
        cv.pack()
    else:
        cv.pack(fill="x")
    inner = tk.Frame(cv, bg=fill, padx=padx, pady=pady)
    win_id = cv.create_window(border_w, border_w, window=inner, anchor="nw")

    def _redraw(_=None):
        cv.update_idletasks()
        ih = inner.winfo_reqheight()
        inset, h = _card_content_inset(ih, border_w)
        iw = inner.winfo_reqwidth()
        w = iw + 2 * inset if fit_content else cv.winfo_width()
        if w <= 1:
            return
        cv.config(width=w, height=h)
        _draw_round_panel(cv, w, h, border, fill, border_w)
        cv.tag_raise(win_id)
        cv.coords(win_id, inset, inset)
        cv.itemconfig(win_id, width=max(1, iw if fit_content else w - 2 * inset))

    inner.bind("<Configure>", _redraw)
    if not fit_content:
        cv.bind("<Configure>", _redraw)
    wrap.after_idle(_redraw)
    return wrap, inner


def make_round_button(parent, text, command, suffix="", font=("Arial", 32, "bold"),
                      padx=48, ipady=16, fill="#a6e3a1", hover="#94d3a2"):
    """כפתור עם פינות מעוגלות."""
    fnt = tkfont.Font(font=font)
    gap = 4 if suffix else 0
    tw = fnt.measure(text) + fnt.measure(suffix) + gap + padx * 2
    th = fnt.metrics("linespace") + ipady * 2 + 6
    r = min(18, th // 2)
    c = tk.Canvas(parent, width=tw, height=th, bg="#1e1e2e",
                  highlightthickness=0, cursor="hand2", bd=0)
    shape = round_rect(c, 1, 1, tw - 1, th - 1, r, fill=fill, outline=fill)
    cy = th // 2
    if suffix:
        mw = fnt.measure(text)
        right = tw - padx
        c.create_text(right, cy, text=text, font=fnt,
                      fill="#11111b", anchor="e", tags="label")
        c.create_text(right - mw - gap, cy, text=suffix, font=fnt,
                      fill="#11111b", anchor="e", tags="label")
    else:
        c.create_text(tw // 2, cy, text=text, font=fnt,
                      fill="#11111b", anchor="center", tags="label")
    c.tag_raise("label")

    def _hover(on):
        c.itemconfig(shape, fill=hover if on else fill, outline=hover if on else fill)

    c.bind("<Button-1>", lambda e: command())
    c.bind("<Enter>", lambda e: _hover(True))
    c.bind("<Leave>", lambda e: _hover(False))
    return c


def _alert_context(now=None):
    """שעה וסיבה להתראה — הכלל הפעיל עכשיו, או התזכורת הבאה."""
    now = now or datetime.datetime.now()
    rule = _rule_at(now)
    if rule:
        t = now.replace(second=0, microsecond=0)
        return t.strftime("%H:%M"), rule.get("reason", "")
    dt = next_reminder_datetime(now)
    dt_key = dt.replace(second=0, microsecond=0)
    for slot, r in _all_slots(now.date()):
        if slot.replace(second=0, microsecond=0) == dt_key:
            return dt.strftime("%H:%M"), r.get("reason", "")
    return dt.strftime("%H:%M"), ""


def _alert_schedule_line(parent, time_part, reason_part, font, fg=MAGENTA, bg="#1e1e2e"):
    """שורת 'בשעה HH:MM - סיבה' — מיקום ידני ללא bidi."""
    fnt = tkfont.Font(font=font)
    h = fnt.metrics("linespace") + 8
    cy = h // 2
    segments = []
    if time_part and reason_part:
        segments = ["\u200fבשעה", " ", f"\u200e{time_part}", " - ", f"\u200f{reason_part}"]
    elif time_part:
        segments = ["\u200fבשעה", " ", f"\u200e{time_part}"]
    else:
        segments = [f"\u200f{reason_part}"]
    total_w = sum(fnt.measure(s) for s in segments)
    wrap = tk.Frame(parent, bg=bg)
    c = tk.Canvas(wrap, width=total_w, height=h, bg=bg, highlightthickness=0, bd=0)
    c.pack()
    x = total_w
    for text in segments:
        w = fnt.measure(text)
        c.create_text(x, cy, text=text, anchor="e", font=font, fill=fg)
        x -= w
    wrap.pack(pady=(0, 8))
    return wrap


def show_alert(reason="", at_time=None):
    """חלון התראה גדול וברור שקופץ מעל הכל."""
    try:
        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
    except Exception:
        pass

    alert = tk.Toplevel(root)
    alert.title("תזכורת")
    alert.attributes("-topmost", True)
    alert.overrideredirect(True)
    alert.configure(bg=ALERT_TRANSP)
    alert.wm_attributes("-transparentcolor", ALERT_TRANSP)

    W, H = 560, 480
    R = 28
    sw, sh = alert.winfo_screenwidth(), alert.winfo_screenheight()
    alert.geometry(f"{W}x{H}+{(sw - W) // 2}+{(sh - H) // 2}")

    ac = tk.Canvas(alert, width=W, height=H, bg=ALERT_TRANSP, highlightthickness=0)
    ac.pack()
    round_rect(ac, 2, 2, W - 2, H - 2, R, fill="#1e1e2e", outline=MAGENTA, width=6)

    inner_h = H - 48
    body = tk.Frame(ac, bg="#1e1e2e", width=W - 24, height=inner_h)
    body.pack_propagate(False)
    ac.create_window(W // 2, H // 2, window=body, width=W - 24, height=inner_h)

    top = tk.Frame(body, bg="#1e1e2e")
    top.pack(side="top", fill="x", pady=(8, 0))

    alert_icon = _load_run_icon(168)
    icon_lbl = tk.Label(top, image=alert_icon, bg="#1e1e2e")
    icon_lbl.image = alert_icon
    icon_lbl.pack(pady=(0, 8))

    if at_time is None or not (reason or "").strip():
        ctx_time, ctx_reason = _alert_context()
        if at_time is None:
            at_time = ctx_time
        if not (reason or "").strip():
            reason = ctx_reason

    time_part = (at_time or "").strip()
    reason_part = (reason or "").strip()
    if time_part or reason_part:
        _alert_schedule_line(top, time_part, reason_part, ("Arial", 26, "bold"))

    title_row = tk.Frame(top, bg="#1e1e2e")
    title_font = ("Arial", 36, "bold")
    title_lbl = tk.Label(title_row, text="\u200fזמן לקום מהכסא", bg="#1e1e2e", fg=GREEN,
                         font=title_font)
    title_lbl.pack(side="right")
    bang_lbl = tk.Label(title_row, text="!", bg="#1e1e2e", fg=GREEN, font=title_font)
    bang_lbl.pack(side="right")
    title_row.pack()

    def _blink_title(on=True):
        if not alert.winfo_exists():
            return
        fg = GREEN if on else "#1e1e2e"
        title_lbl.config(fg=fg)
        bang_lbl.config(fg=fg)
        alert.after(550, lambda: _blink_title(not on))

    alert.after(550, _blink_title)
    sub_row = tk.Frame(top, bg="#1e1e2e")
    sub_font = ("Arial", 22)
    tk.Label(sub_row, text=f"\u200f{_activity_message()}", bg="#1e1e2e",
             fg="#cdd6f4", font=sub_font).pack(side="right")
    _thumbs = _load_run_icon(44, "windows_reminder_thumbsup.png")
    _thumb_lbl = tk.Label(sub_row, image=_thumbs, bg="#1e1e2e")
    _thumb_lbl.image = _thumbs
    _thumb_lbl.pack(side="right", padx=(0, 6))
    sub_row.pack(pady=(10, 0))

    tk.Frame(body, bg="#1e1e2e").pack(side="top", fill="both", expand=True)

    btn_row = tk.Frame(body, bg="#1e1e2e")
    btn_row.pack(side="bottom", pady=(0, 8))
    btn = make_round_button(btn_row, "\u200fקמתי", alert.destroy, suffix="...",
                            font=("Arial", 24, "bold"), ipady=4)
    btn.pack()

    alert.after(5 * 60 * 1000, lambda: alert.winfo_exists() and alert.destroy())


def _style_entry(parent, **kw):
    """שדה קלט בסגנון כהה עם הדגשת תכלת."""
    defaults = dict(
        bg="#181825", fg="#cdd6f4", insertbackground=SKY,
        relief="flat", highlightthickness=1,
        highlightbackground="#45475a", highlightcolor=SKY,
        bd=0, justify="right",
    )
    defaults.update(kw)
    return tk.Entry(parent, **defaults)


def _insert_field(entry, text, ltr=False, rtl_text=False):
    if ltr and text and not text.startswith("\u200e"):
        text = "\u200e" + text
    if rtl_text and text and not text.startswith("\u200f"):
        text = "\u200f" + text
    entry.delete(0, tk.END)
    entry.insert(0, text or "")
    entry.after_idle(lambda: entry.xview_moveto(1.0))


def _bind_entry_visual_right(entry, ltr=False, rtl_text=False):
    """שומר טקסט צמוד לימין בתוך השדה."""
    entry.configure(justify="right")

    def _go(*_):
        entry.update_idletasks()
        entry.xview_moveto(1.0)
        try:
            entry.icursor(tk.END)
        except tk.TclError:
            pass

    entry.bind("<FocusIn>", _go, add="+")
    entry.bind("<KeyRelease>", _go, add="+")
    entry.bind("<FocusOut>", _go, add="+")
    entry.after_idle(_go)


def _field_value(entry, ltr=False):
    v = entry.get().strip().replace("\u200e", "").replace("\u200f", "")
    return v


def _field_entry(parent, font, chars=None, width_sample=None, extra_pad=0, ltr=False,
                 rtl_text=False, bind_width_to=None):
    """שדה עם מסגרת מעוגלת — טקסט צמוד לימין."""
    fnt = tkfont.Font(font=font)
    pad_l = 0 if rtl_text else 2
    bg_outer = parent.cget("bg")
    inner_bg = "#181825"
    border_col = SKY
    bd = max(1, _dp(1))
    box = tk.Frame(parent, bg=bg_outer)
    cv = tk.Canvas(box, bg=bg_outer, highlightthickness=0, bd=0, takefocus=0)
    cv.pack(fill="both", expand=(chars is None))
    if chars is not None:
        ref = width_sample or ("0" * chars)
        inner_w = int(max(fnt.measure("0" * chars), fnt.measure(ref)) + pad_l + extra_pad)
        inner_h = fnt.metrics("linespace") + 8
    else:
        inner_w = None
        inner_h = fnt.metrics("linespace") + 8
        box.pack_propagate(False)
    e = tk.Entry(
        cv, font=font, bd=0, highlightthickness=0,
        bg=inner_bg, fg="#cdd6f4", insertbackground=SKY, justify="right",
    )
    _bind_entry_visual_right(e, ltr=ltr, rtl_text=rtl_text)
    win_id = cv.create_window(0, 0, window=e, anchor="ne")
    _last_size = [None, None]

    def _layout(_=None):
        cv.update_idletasks()
        H, pill_w, r = _field_pill_size(inner_w, inner_h, bd)
        if inner_w is not None:
            W = pill_w
            ew = inner_w
        else:
            W = max(cv.winfo_width(), box.winfo_width(), 2 * r + 8, 1)
            if bind_width_to is not None:
                bind_width_to.update_idletasks()
                tw = bind_width_to.winfo_reqwidth()
                if tw <= 1:
                    tw = bind_width_to.winfo_width()
                W = max(tw, 40) + 2 * r
            ew = max(1, W - 2 * r)
            box.configure(height=H)
        if _last_size[0] == W and _last_size[1] == H:
            return
        _last_size[0], _last_size[1] = W, H
        cv.config(width=W, height=H)
        box.configure(width=W, height=H)
        _draw_round_panel(cv, W, H, border_col, inner_bg, bd)
        cv.tag_raise(win_id)
        cv.coords(win_id, r + ew, bd)
        cv.itemconfig(win_id, width=ew, height=inner_h)
        e.xview_moveto(1.0)

    def _focus(_=None):
        e.focus_set()

    cv.bind("<Button-1>", _focus, add="+")
    if bind_width_to is not None:
        bind_width_to.bind("<Configure>", _layout, add="+")
    if chars is None:
        box.bind("<Configure>", _layout, add="+")
    else:
        box.after_idle(_layout)
    return box, e


def _cm(n=1):
    """1 ס"מ בפיקסלים."""
    return max(1, round(n * root.winfo_fpixels("1i") / 2.54))


def _dp(n=1):
    """1dp ≈ 1/160 inch."""
    return max(1, round(n * root.winfo_fpixels("1i") / 160))


def _rtl_label(parent, parts, font, fg=SKY, bg="#252536"):
    """תווית RTL — מיקום ידני של מילה + סימן (ללא bidi)."""
    fr = tk.Frame(parent, bg=bg)
    fnt = tkfont.Font(font=font)
    h = fnt.metrics("linespace") + 8
    cy = h // 2
    if len(parts) == 1:
        w = max(10, fnt.measure(parts[0]) + 2)
        c = tk.Canvas(fr, width=w, height=h, bg=bg, highlightthickness=0, bd=0)
        c.pack(side="right")
        c.create_text(w, cy, text=parts[0], anchor="e", font=font, fill=fg)
    else:
        word, punct = parts[0], parts[1]
        w_word = fnt.measure(word)
        w_punct = fnt.measure(punct)
        w = w_word + w_punct
        c = tk.Canvas(fr, width=w, height=h, bg=bg, highlightthickness=0, bd=0)
        c.pack(side="right")
        c.create_text(w, cy, text=word, anchor="e", font=font, fill=fg)
        c.create_text(w - w_word, cy, text=punct, anchor="e", font=font, fill=fg)
    return fr


def _outline_button(parent, text, command, font=("Arial", 16), fg="#cdd6f4",
                    width=None, height=None, border="#ffffff",
                    fill="#252536", hover="#313244"):
    """כפתור עם מסגרת דקה ופינות עגולות."""
    fnt = tkfont.Font(font=font)
    padx, ipady = 14, 7
    bw = max(1, _dp(1))
    tw = fnt.measure(text) + padx * 2
    th = fnt.metrics("linespace") + ipady * 2 + 4
    W = width if width is not None else tw + bw * 2
    H = height if height is not None else th + bw * 2
    r = _round_radius(th)
    c = tk.Canvas(parent, width=W, height=H, bg="#1e1e2e",
                  highlightthickness=0, cursor="hand2", bd=0)
    round_rect(c, 1, 1, W - 1, H - 1, r, fill=border, outline=border)
    shape = round_rect(c, 1 + bw, 1 + bw, W - 1 - bw, H - 1 - bw, max(1, r - bw),
                         fill=fill, outline=fill)
    c.create_text(W // 2, H // 2, text=text, font=font, fill=fg, tags="label")
    c.tag_raise("label")

    def _hover(on):
        c.itemconfig(shape, fill=hover if on else fill, outline=hover if on else fill)

    def _click(_=None):
        command()

    c.bind("<Button-1>", _click)
    c.bind("<Enter>", lambda e: _hover(True))
    c.bind("<Leave>", lambda e: _hover(False))
    return c


def _segment_toggle(parent, variable, options, font=("Arial", 16), gap=8, on_change=None):
    """כפתורי בחירה מעוגלים — RTL, בסגנון מסגרת תכלת."""
    fr = tk.Frame(parent, bg="#1e1e2e")
    fnt = tkfont.Font(font=font)
    padx, ipady = 18, 7
    bw = max(1, _dp(1))
    th = fnt.metrics("linespace") + ipady * 2 + 4
    r = _round_radius(th)
    items = []

    def _paint():
        cur = variable.get()
        for it in items:
            on = it["value"] == cur
            border = SKY if on else "#45475a"
            fill = "#313244" if on else "#252536"
            fg = SKY if on else "#cdd6f4"
            c = it["canvas"]
            c.itemconfig(it["border"], fill=border, outline=border)
            c.itemconfig(it["inner"], fill=fill, outline=fill)
            c.itemconfig(it["label"], fill=fg)

    for label, value in options:
        text = f"\u200f{label}"
        tw = fnt.measure(text) + padx * 2
        W, H = tw + bw * 2, th + bw * 2
        c = tk.Canvas(fr, width=W, height=H, bg="#1e1e2e",
                        highlightthickness=0, cursor="hand2", bd=0)
        c.pack(side="right", padx=(gap, 0))
        border_id = round_rect(c, 1, 1, W - 1, H - 1, r, fill="#45475a", outline="#45475a")
        inner_id = round_rect(
            c, 1 + bw, 1 + bw, W - 1 - bw, H - 1 - bw, max(1, r - bw),
            fill="#252536", outline="#252536",
        )
        label_id = c.create_text(W // 2, H // 2, text=text, font=font, fill="#cdd6f4")
        it = {"canvas": c, "border": border_id, "inner": inner_id,
              "label": label_id, "value": value}

        def _pick(_=None, v=value):
            variable.set(v)
            _paint()
            if on_change:
                on_change(v)

        def _hover(on, item=it):
            if variable.get() == item["value"]:
                return
            col = "#585b70" if on else "#45475a"
            c.itemconfig(item["border"], fill=col, outline=col)

        c.bind("<Button-1>", _pick)
        c.bind("<Enter>", lambda e, item=it: _hover(True, item))
        c.bind("<Leave>", lambda e, item=it: _hover(False, item))
        items.append(it)

    variable.trace_add("write", lambda *_: _paint())
    _paint()
    return fr


def show_settings():
    """מסך הגדרות כללי תזכורת — בסגנון ווידג'ט השעון."""
    # 80% מהגודל שהיה (כפול × 0.8)
    F_HDR = 26
    F_LABEL = 16
    F_ENTRY = 18
    F_BTN = 16
    X_FONT = ("Roboto", 14, "bold")
    X_FG = "#f38ba8"
    X_HOVER = "#ff6b8a"
    HDR_ICON = 68  # 54 + ~25%
    SET_W = max(720, 960 - _cm(5))
    PH = 672
    R = 20
    _rules_right_pad = 4 + 11 + 6 + 2  # scrollbar + inset + card — יישור לימין עם מסגרת הכללים
    _voice_left_nudge = 4  # הזזה עדינה שמאלה מיישור הכללים

    win = tk.Toplevel(root)
    win.title("הגדרות תזכורת")
    win.attributes("-topmost", True)
    win.overrideredirect(True)
    win.configure(bg=TRANSP)
    win.wm_attributes("-transparentcolor", TRANSP)
    win.resizable(False, False)

    sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
    win.geometry(f"{SET_W}x{PH}+{(sw - SET_W) // 2}+{(sh - PH) // 2}")

    sc = tk.Canvas(win, width=SET_W, height=PH, bg=TRANSP, highlightthickness=0)
    sc.pack()
    round_rect(sc, 2, 2, SET_W - 2, PH - 2, R, fill="#1e1e2e", outline=SKY, width=2, tags="panel")

    body = tk.Frame(sc, bg="#1e1e2e", width=SET_W - 20, height=PH - 20)
    body.pack_propagate(False)
    body_win = sc.create_window(SET_W // 2, PH // 2, window=body, width=SET_W - 20, height=PH - 20)

    top_bar = tk.Frame(body, bg="#1e1e2e")
    top_bar.pack(fill="x", padx=8, pady=(6, 0))

    hdr_row = tk.Frame(top_bar, bg="#1e1e2e")
    hdr_row.pack(fill="x")
    hdr_center = tk.Frame(hdr_row, bg="#1e1e2e")
    hdr_center.pack(fill="x")
    hdr_inner = tk.Frame(hdr_center, bg="#1e1e2e")
    hdr_inner.pack(anchor="center", pady=2)
    try:
        hdr_icon = _load_run_icon(HDR_ICON)
        icon_lbl = tk.Label(hdr_inner, image=hdr_icon, bg="#1e1e2e")
        icon_lbl.image = hdr_icon
        icon_lbl.pack(side="right", padx=(4, 0))
    except FileNotFoundError:
        pass
    tk.Label(hdr_inner, text="כללי תזכורת", bg="#1e1e2e", fg=SKY,
             font=("Arial", F_HDR, "bold")).pack(side="right")

    voice_row = tk.Frame(body, bg="#1e1e2e")
    voice_row.pack(fill="x", padx=12, pady=(6, 0))
    voice_var = tk.StringVar(value=_settings.get("voice", DEFAULT_VOICE))
    _segment_toggle(
        voice_row, voice_var,
        [("גבר", "male"), ("אשה", "female")],
        font=("Arial", F_LABEL),
        on_change=_set_voice,
    ).pack(side="right", padx=(0, _rules_right_pad + _voice_left_nudge))

    scroll_wrap = tk.Frame(body, bg="#1e1e2e")
    scroll_wrap.pack(fill="both", expand=True, padx=12, pady=(8, 4))
    rules_cv = tk.Canvas(scroll_wrap, bg="#1e1e2e", highlightthickness=0, bd=0)
    sb_style = ttk.Style(win)
    sb_style.theme_use("clam")
    sb_style.configure(
        "Muted.Vertical.TScrollbar",
        troughcolor="#1e1e2e",
        background="#6c7086",
        bordercolor="#45475a",
        arrowcolor="#585b70",
        lightcolor="#7f849c",
        darkcolor="#45475a",
        width=11,
    )
    sb_style.map(
        "Muted.Vertical.TScrollbar",
        background=[("pressed", SKY), ("active", "#89dceb"), ("!active", "#6c7086")],
    )
    rules_sb = ttk.Scrollbar(scroll_wrap, orient="vertical", command=rules_cv.yview,
                             style="Muted.Vertical.TScrollbar")
    frm = tk.Frame(rules_cv, bg="#1e1e2e")
    frm_id = rules_cv.create_window((0, 0), window=frm, anchor="nw")
    _scroll_inset = 6

    def _sync_frm_width():
        cv_w = rules_cv.winfo_width()
        if cv_w > 1:
            rules_cv.itemconfig(frm_id, width=max(1, cv_w - _scroll_inset))

    def _scroll_region(_=None):
        rules_cv.update_idletasks()
        _sync_frm_width()
        rules_cv.configure(scrollregion=rules_cv.bbox("all"))

    def _scroll_width(_=None):
        _sync_frm_width()

    frm.bind("<Configure>", _scroll_region)
    rules_cv.bind("<Configure>", _scroll_width)
    rules_cv.configure(yscrollcommand=rules_sb.set)
    rules_sb.pack(side="right", fill="y", padx=(4, 0))
    rules_cv.pack(side="left", fill="both", expand=True)

    def _on_wheel(e):
        rules_cv.yview_scroll(int(-1 * (e.delta / 120)), "units")

    def _bind_wheel(_=None):
        win.bind_all("<MouseWheel>", _on_wheel)

    def _unbind_wheel(_=None):
        win.unbind_all("<MouseWheel>")

    win.bind("<Destroy>", _unbind_wheel)
    _bind_wheel()

    _entry_ipady = 3
    _rule_x_gap = _dp(8)
    _lbl_fnt = tkfont.Font(family="Arial", size=F_LABEL)
    label_col_w = max(
        _lbl_fnt.measure("מ") + _lbl_fnt.measure("-"),
        _lbl_fnt.measure("סיבה") + _lbl_fnt.measure(":"),
    ) + 8

    rows = []

    def add_row(rule=None):
        rule = _normalize_rule(rule or {"from": "08:00", "to": "18:00", "every_minutes": 120, "reason": ""})
        card, row = _rounded_border_frame(frm, border=SKY, fill="#252536",
                                          border_w=1, padx=10, pady=10, fit_content=False)
        card.pack(fill="x", pady=5, padx=(0, 2))

        def remove():
            card.destroy()
            rows[:] = [r for r in rows if r["card"] is not card]

        strip = tk.Frame(row, bg="#252536")
        strip.pack(fill="x")

        body = tk.Frame(strip, bg="#252536")
        body.pack(side="right", fill="x", expand=True)

        form = tk.Frame(body, bg="#252536")
        form.pack(fill="x", anchor="e")
        form.columnconfigure(0, weight=1)
        form.columnconfigure(1, minsize=label_col_w)

        inputs = tk.Frame(form, bg="#252536")
        inputs.grid(row=0, column=0, rowspan=2, sticky="e")

        align = tk.Frame(inputs, bg="#252536")
        align.pack(anchor="e")

        row0 = tk.Frame(align, bg="#252536")
        row0.pack(anchor="e")

        from_box, e_from = _field_entry(row0, ("Arial", F_ENTRY), chars=5, ltr=True)
        _insert_field(e_from, rule.get("from", "08:00"), ltr=True)
        from_box.pack(side="right")

        rest = tk.Frame(row0, bg="#252536")
        rest.pack(side="right", padx=(0, 8))
        _rtl_label(rest, ["עד"], ("Arial", F_LABEL)).pack(side="right", pady=_entry_ipady)
        to_box, e_to = _field_entry(rest, ("Arial", F_ENTRY), chars=5, ltr=True)
        _insert_field(e_to, rule.get("to", ""), ltr=True)
        to_box.pack(side="right", padx=4)
        every_grp = tk.Frame(rest, bg="#252536")
        every_grp.pack(side="right", padx=(0, _cm(1)))
        _rtl_label(every_grp, ["כל"], ("Arial", F_LABEL)).pack(side="right", pady=_entry_ipady)
        every_box, e_every = _field_entry(
            every_grp, ("Arial", F_ENTRY), chars=3, width_sample="120", extra_pad=6, ltr=True)
        every_val = rule.get("every_minutes", "")
        if every_val != "" and every_val is not None:
            _insert_field(e_every, str(every_val), ltr=True)
        every_box.pack(side="right", padx=4)
        _rtl_label(every_grp, ["דקות"], ("Arial", F_LABEL)).pack(side="right", pady=_entry_ipady)

        _rtl_label(form, ["מ", "-"], ("Arial", F_LABEL)).grid(
            row=0, column=1, sticky="e", pady=_entry_ipady)

        reason_box, e_reason = _field_entry(
            align, ("Arial", F_ENTRY), rtl_text=True, bind_width_to=row0)
        _insert_field(e_reason, rule.get("reason", ""), rtl_text=True)
        reason_box.pack(anchor="e", pady=(8 + _entry_ipady, 0))
        _rtl_label(form, ["סיבה", ":"], ("Arial", F_LABEL)).grid(
            row=1, column=1, sticky="e", pady=(8 + _entry_ipady, 0))

        del_btn = tk.Label(strip, text="✕", bg="#252536", fg=X_FG,
                           font=X_FONT, cursor="hand2")
        del_btn.pack(side="right", padx=(0, _rule_x_gap), anchor="n", pady=_entry_ipady)
        del_btn.bind("<Button-1>", lambda e: remove())
        del_btn.bind("<Enter>", lambda e: del_btn.config(fg=X_HOVER))
        del_btn.bind("<Leave>", lambda e: del_btn.config(fg=X_FG))

        rows.append({"card": card, "from": e_from, "to": e_to, "every": e_every, "reason": e_reason})

    for r in _settings["rules"]:
        add_row(r)
    _scroll_region()

    btns = tk.Frame(body, bg="#1e1e2e")
    btns.pack(fill="x", padx=12, pady=(4, 10))

    def _collect_rules():
        new_rules = []
        for r in rows:
            from_v = _field_value(r["from"], ltr=True)
            to_v = _field_value(r["to"], ltr=True)
            every_v = _field_value(r["every"], ltr=True)
            reason_v = _field_value(r["reason"])
            if not from_v:
                continue
            if _is_empty_field(to_v):
                new_rules.append({
                    "from": from_v,
                    "to": "",
                    "every_minutes": "",
                    "reason": reason_v,
                })
            else:
                try:
                    every = int(every_v or "1")
                except ValueError:
                    every = 120
                new_rules.append({
                    "from": from_v,
                    "to": to_v,
                    "every_minutes": every,
                    "reason": reason_v,
                })
        return new_rules or [dict(r) for r in DEFAULT_RULES]

    def _persist_settings():
        global _settings
        _settings["rules"] = _collect_rules()
        _set_voice(voice_var.get())
        save_settings()
        update_status_display()

    def _close_settings():
        _persist_settings()
        win.destroy()

    def add_rule():
        add_row()
        _scroll_region()

    btn_specs = [
        ("\u200fיציאה", ("Arial", F_BTN)),
        ("\u200f+ הוסף כלל", ("Arial", F_BTN)),
    ]
    btn_padx, btn_ipady = 14, 7
    btn_bw = max(1, _dp(1))
    btn_w = btn_h = 0
    for txt, fnt in btn_specs:
        fm = tkfont.Font(font=fnt)
        w = fm.measure(txt) + btn_padx * 2 + btn_bw * 2
        h = fm.metrics("linespace") + btn_ipady * 2 + 4 + btn_bw * 2
        btn_w, btn_h = max(btn_w, w), max(btn_h, h)
    _outline_button(btns, btn_specs[0][0], _close_settings, font=btn_specs[0][1],
                    fg="#f38ba8", border="#f38ba8", width=btn_w, height=btn_h).pack(side="left")
    _outline_button(btns, btn_specs[1][0], add_rule, font=btn_specs[1][1],
                    fg=SKY, border=SKY, width=btn_w, height=btn_h).pack(
                        side="right", padx=(0, _rules_right_pad))


def tick():
    """נבדק כל שנייה: תזכורת, ספירה לאחור."""
    global _last_fired_slot
    now = datetime.datetime.now()
    slot_key = now.replace(second=0, microsecond=0).isoformat()
    rule = _rule_at(now)
    if rule and _last_fired_slot != slot_key:
        _last_fired_slot = slot_key
        show_alert(rule.get("reason", ""), now.strftime("%H:%M"))

    update_status_display()
    root.after(1000, tick)


# ---------- חלון סטטוס קטן (always-on-top, פינות מעוגלות) ----------
TRANSP = "#ff00ff"   # צבע "מפתח כרומה" - הופך לשקוף, יוצר את הפינות המעוגלות
W, H = 188, 96
RADIUS = 20
INNER_LEFT = 6
INNER_BOTTOM = H - 6

root = tk.Tk()
root.title("תזכורת פעילות")
root.attributes("-topmost", True)
root.overrideredirect(True)
root.configure(bg=TRANSP)
root.wm_attributes("-transparentcolor", TRANSP)

canvas = tk.Canvas(root, width=W, height=H, bg=TRANSP, highlightthickness=0)
canvas.pack()


# גוף החלונית: רקע כהה + מסגרת ירוקה עדינה, פינות מעוגלות
round_rect(canvas, 2, 2, W - 2, H - 2, RADIUS,
           fill="#1e1e2e", outline=SKY, width=2)

# אייקון הליכה במיקום קבוע + שעה במיקום קבוע
ICON_X = W - 36
ICON_Y = H // 2 + 8 - int(2 * root.winfo_fpixels("1i") / 25.4)  # 2 מ"מ למעלה
TIME_RIGHT_X, TIME_Y = 102, H // 2 + 18
_countdown_font = tkfont.Font(root=root, family="Arial", size=17)
_wake_font = tkfont.Font(root=root, family="Arial", size=26)
ICON_SIZE = 86


def _load_status_icon():
    return _load_run_icon(ICON_SIZE)


_walk_icon = _load_status_icon()
canvas.create_image(ICON_X, ICON_Y, image=_walk_icon, tags="icon")

status_countdown = canvas.create_text(0, TIME_Y - 32, text="", fill="#ffffff", tags="clock")
status_time = canvas.create_text(0, TIME_Y, text="16:00", fill=SKY, tags="clock")
canvas.update_idletasks()
_wake_y = TIME_Y
_bbox = canvas.bbox(status_time)
if _bbox:
    place_text_right(status_time, "16:00", _wake_font, TIME_RIGHT_X, _wake_y)
    canvas.update_idletasks()
    _bbox = canvas.bbox(status_time)
if _bbox:
    _left_margin = _bbox[0] - INNER_LEFT
    _bottom_margin = INNER_BOTTOM - _bbox[3]
    if _bottom_margin > _left_margin:
        _wake_y = TIME_Y + (_bottom_margin - _left_margin)
_wake_y += int(root.winfo_fpixels("1i") / 25.4)  # 1 מ"מ למטה
_countdown_y = _wake_y - 32
place_text_right(status_time, "16:00", _wake_font, TIME_RIGHT_X, _wake_y)
place_text_right(status_countdown, format_remaining(datetime.timedelta(hours=1)),
                 _countdown_font, TIME_RIGHT_X, _countdown_y)

# כפתורי סגירה (✕) ובדיקה (▶) בפינות העליונות
canvas.create_text(12, 16, text="✕", fill="#a6adc8",
                   font=("Roboto", 12, "bold"), tags="close")
canvas.create_text(W - 12, 16, text="▶", fill="#585b70",
                   font=("Roboto", 10), tags="test")

canvas.tag_bind("close", "<Button-1>", lambda e: (_save_position(), root.destroy()))
canvas.tag_bind("test", "<Button-1>", lambda e: show_alert())
canvas.tag_bind("icon", "<Button-1>", lambda e: show_alert())
canvas.tag_bind("clock", "<Button-1>", lambda e: show_settings())
for tag in ("close", "test", "icon", "clock"):
    canvas.tag_bind(tag, "<Enter>", lambda e: canvas.config(cursor="hand2"))
    canvas.tag_bind(tag, "<Leave>", lambda e: canvas.config(cursor=""))

# גרירת החלונית מאזור הרקע
_drag = {"x": 0, "y": 0}


def _start_drag(e):
    tags = canvas.gettags("current")
    if any(t in tags for t in ("icon", "close", "test", "clock")):
        return
    _drag.update(x=e.x, y=e.y)


canvas.bind("<Button-1>", _start_drag)
canvas.bind("<B1-Motion>", lambda e: root.geometry(
    f"+{root.winfo_x() + e.x - _drag['x']}+{root.winfo_y() + e.y - _drag['y']}"))
canvas.bind("<ButtonRelease-1>", lambda e: _save_position())

# מיקום: שמור מהפעלה קודמת, אחרת פינה ימנית עליונה
sw = root.winfo_screenwidth()
sh = root.winfo_screenheight()
_x, _y = _load_position(sw - W - 20, 20)
_x = max(0, min(_x, sw - W))
_y = max(0, min(_y, sh - H))
root.geometry(f"{W}x{H}+{_x}+{_y}")

load_settings()
tick()
root.mainloop()
