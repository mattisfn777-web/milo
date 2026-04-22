import requests
import base64
import tkinter as tk
from tkinter import filedialog
import threading
import os
import sys
import time
import shutil
import subprocess
import urllib.request

# ─────────────────────────────────────────────
#  VERSION
# ─────────────────────────────────────────────
CURRENT_VERSION    = "1.0.0"
GITHUB_REPO        = "mattisfn777-web/milo"
GITHUB_RAW_BASE    = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main"
GITHUB_VERSION_URL = f"{GITHUB_RAW_BASE}/version.txt"
GITHUB_SCRIPT_URL  = f"{GITHUB_RAW_BASE}/milo.py"
GITHUB_RELEASES_URL = f"https://github.com/{GITHUB_REPO}/releases/latest"

def _version_gt(a, b):
    try:
        return tuple(int(x) for x in a.split(".")) > tuple(int(x) for x in b.split("."))
    except ValueError:
        return False

def fetch_latest_version():
    r = requests.get(GITHUB_VERSION_URL, timeout=8)
    r.raise_for_status()
    return r.text.strip()

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
BASE_URL = "http://127.0.0.1:1234/v1"

MODELS = {
    "quick":  "mistralai/ministral-3-3b",
    "normal": "mistralai/mistral-7b-instruct-v0.3",
    "deep":   "qwen/qwen3.5-9b",
}
MODEL_DISPLAY = {
    "quick":  "Milo/Milo 1.0",
    "normal": "Milo/Milo 1.0",
    "deep":   "Milo/Milo 1.0",
}
COMMANDS = {
    "/quick":  ("⚡ Quick mode",  "Fast responses · ministral-3b"),
    "/normal": ("◆ Normal mode", "Balanced · mistral-7b"),
    "/deep":   ("🧠 Deep mode",   "Thorough · qwen3.5-9b"),
}
SYSTEM_PROMPT = "You are Milo V1, a helpful AI assistant with mode awareness."

# ─────────────────────────────────────────────
#  COLORS
# ─────────────────────────────────────────────
BG        = "#0d0d0d"
BG2       = "#111111"
BG3       = "#191919"
BG_POPUP  = "#161616"
BG_CARD   = "#0f0f0f"
BG_VER    = "#161616"
BORDER    = "#2b2b2b"
BORDER_HI = "#3d3d3d"
ACCENT    = "#d4a843"
ACCENT2   = "#c49030"
TEXT      = "#e3dfd7"
TEXT2     = "#8a8680"
TEXT3     = "#4e4b47"
GREEN     = "#6b9e6b"
RED       = "#c0504a"
BLUE      = "#5e8fb5"
CURSOR_C  = "#d4a843"

MONO    = ("JetBrains Mono", 10) if os.name != "nt" else ("Consolas", 10)
MONO_SM = (MONO[0], 9)
MONO_LG = (MONO[0], 11)

# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
def image_to_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def ask_model(model, messages):
    try:
        r = requests.post(
            f"{BASE_URL}/chat/completions",
            json={"model": model, "messages": messages, "temperature": 0.7},
            timeout=300,
        )
        data = r.json()
        if "choices" not in data:
            return None, str(data)
        return data["choices"][0]["message"]["content"], None
    except Exception as e:
        return None, str(e)

# ─────────────────────────────────────────────
#  UPDATE OVERLAY
# ─────────────────────────────────────────────
class UpdateOverlay:
    """Full-window overlay with a polished card-style update UI."""

    def __init__(self, parent, current_ver, latest_ver, on_cancel):
        self.parent      = parent
        self.current_ver = current_ver
        self.latest_ver  = latest_ver
        self.on_cancel   = on_cancel
        self._updating   = False

        self.overlay = tk.Toplevel(parent)
        self.overlay.overrideredirect(True)
        self.overlay.configure(bg="#07070a")
        self.overlay.attributes("-topmost", True)

        parent.update_idletasks()
        x = parent.winfo_x()
        y = parent.winfo_y()
        w = parent.winfo_width()
        h = parent.winfo_height()
        self.overlay.geometry(f"{w}x{h}+{x}+{y}")
        self._w = w
        self._h = h

        self._build()

    # ── BUILD ──────────────────────────────────
    def _build(self):
        ov = self.overlay

        # dim grid background
        bg_canvas = tk.Canvas(ov, bg="#07070a", highlightthickness=0)
        bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        step = 28
        for i in range(0, 1200, step):
            bg_canvas.create_line(i, 0, i, 800, fill="#0e0e12", width=1)
            bg_canvas.create_line(0, i, 1200, i, fill="#0e0e12", width=1)

        # ── card container ──
        self.card = tk.Frame(ov, bg=BG_CARD, bd=0)
        self.card.place(relx=0.5, rely=0.5, anchor="center", width=440)

        # gold top bar
        tk.Frame(self.card, bg=ACCENT, height=3).pack(fill=tk.X)

        self._inner = tk.Frame(self.card, bg=BG_CARD)
        self._inner.pack(fill=tk.BOTH, expand=True, padx=36, pady=30)

        self._build_header()
        self._build_version_diff()
        self._build_description()
        self._build_progress()   # hidden until update starts
        self._build_buttons()
        self._build_footer()

    def _build_header(self):
        row = tk.Frame(self._inner, bg=BG_CARD)
        row.pack(fill=tk.X, pady=(0, 22))

        tk.Label(row, text="◈", font=(MONO[0], 30, "bold"),
                 bg=BG_CARD, fg=ACCENT).pack(side=tk.LEFT, padx=(0, 14))

        col = tk.Frame(row, bg=BG_CARD)
        col.pack(side=tk.LEFT)
        tk.Label(col, text="Update Available",
                 font=(MONO[0], 15, "bold"), bg=BG_CARD, fg=TEXT,
                 anchor="w").pack(anchor="w")
        tk.Label(col, text="Milo AI Assistant",
                 font=MONO_SM, bg=BG_CARD, fg=TEXT3,
                 anchor="w").pack(anchor="w")

    def _build_version_diff(self):
        frame = tk.Frame(self._inner, bg=BG_VER)
        frame.pack(fill=tk.X, pady=(0, 18))

        tk.Frame(frame, bg=BORDER, height=1).pack(fill=tk.X)
        inner = tk.Frame(frame, bg=BG_VER)
        inner.pack(fill=tk.X, padx=20, pady=14)

        # current
        l = tk.Frame(inner, bg=BG_VER)
        l.pack(side=tk.LEFT, expand=True)
        tk.Label(l, text="CURRENT", font=(MONO[0], 7),
                 bg=BG_VER, fg=TEXT3).pack()
        tk.Label(l, text=f"v{self.current_ver}",
                 font=(MONO[0], 14, "bold"), bg=BG_VER, fg=TEXT2).pack()

        # arrow
        tk.Label(inner, text="→", font=(MONO[0], 18),
                 bg=BG_VER, fg=ACCENT).pack(side=tk.LEFT, padx=20)

        # latest
        r = tk.Frame(inner, bg=BG_VER)
        r.pack(side=tk.LEFT, expand=True)
        tk.Label(r, text="LATEST", font=(MONO[0], 7),
                 bg=BG_VER, fg=TEXT3).pack()
        tk.Label(r, text=f"v{self.latest_ver}",
                 font=(MONO[0], 14, "bold"), bg=BG_VER, fg=GREEN).pack()

        tk.Frame(frame, bg=BORDER, height=1).pack(fill=tk.X)

    def _build_description(self):
        self._desc_lbl = tk.Label(
            self._inner,
            text="Downloads the latest version, replaces this\nfile, and restarts Milo automatically.",
            font=MONO_SM, bg=BG_CARD, fg=TEXT2,
            justify="center",
        )
        self._desc_lbl.pack(pady=(0, 20))

    def _build_progress(self):
        self._prog_frame = tk.Frame(self._inner, bg=BG_CARD)
        # not packed yet — shown when update starts

        self._status_lbl = tk.Label(
            self._prog_frame, text="Preparing…",
            font=MONO_SM, bg=BG_CARD, fg=TEXT2, anchor="w",
        )
        self._status_lbl.pack(fill=tk.X, pady=(0, 7))

        # track
        track_wrap = tk.Frame(self._prog_frame, bg=BORDER, height=6)
        track_wrap.pack(fill=tk.X)
        track_wrap.pack_propagate(False)
        self._track = track_wrap

        self._bar = tk.Frame(track_wrap, bg=ACCENT, height=6)
        self._bar.place(x=0, y=0, relheight=1, width=0)

        self._pct_lbl = tk.Label(
            self._prog_frame, text="0%",
            font=(MONO[0], 8), bg=BG_CARD, fg=TEXT3, anchor="e",
        )
        self._pct_lbl.pack(fill=tk.X, pady=(4, 0))

    def _build_buttons(self):
        self._btn_row = tk.Frame(self._inner, bg=BG_CARD)
        self._btn_row.pack(fill=tk.X)

        self._cancel_lbl = tk.Label(
            self._btn_row, text="Cancel",
            font=MONO_SM, bg=BG_CARD, fg=TEXT2,
            cursor="hand2", padx=4, pady=8,
        )
        self._cancel_lbl.pack(side=tk.LEFT)
        self._cancel_lbl.bind("<Button-1>", lambda e: self._cancel())
        self._cancel_lbl.bind("<Enter>",    lambda e: self._cancel_lbl.config(fg=TEXT))
        self._cancel_lbl.bind("<Leave>",    lambda e: self._cancel_lbl.config(fg=TEXT2))

        self._install_wrap = tk.Frame(self._btn_row, bg=ACCENT, cursor="hand2")
        self._install_wrap.pack(side=tk.RIGHT)
        self._install_lbl = tk.Label(
            self._install_wrap, text="  Install & Restart  ",
            font=(MONO[0], 10, "bold"),
            bg=ACCENT, fg=BG, padx=4, pady=8, cursor="hand2",
        )
        self._install_lbl.pack()
        self._install_wrap.bind("<Button-1>",     lambda e: self._start_update())
        self._install_lbl.bind("<Button-1>",      lambda e: self._start_update())
        self._install_wrap.bind("<Enter>",  lambda e: (
            self._install_wrap.config(bg=ACCENT2),
            self._install_lbl.config(bg=ACCENT2)))
        self._install_wrap.bind("<Leave>",  lambda e: (
            self._install_wrap.config(bg=ACCENT),
            self._install_lbl.config(bg=ACCENT)))

    def _build_footer(self):
        tk.Label(
            self._inner,
            text=f"github.com/{GITHUB_REPO}",
            font=(MONO[0], 8), bg=BG_CARD, fg=TEXT3, cursor="hand2",
        ).pack(pady=(18, 0))

    # ── UPDATE FLOW ────────────────────────────
    def _start_update(self):
        if self._updating:
            return
        self._updating = True

        # Freeze buttons
        self._install_wrap.config(bg=BORDER)
        self._install_lbl.config(bg=BORDER, fg=TEXT3, text="  Installing…  ")
        self._install_wrap.unbind("<Button-1>")
        self._install_lbl.unbind("<Button-1>")
        self._cancel_lbl.config(fg=TEXT3)
        self._cancel_lbl.unbind("<Button-1>")

        # Show progress bar
        self._desc_lbl.pack_forget()
        self._prog_frame.pack(fill=tk.X, pady=(0, 20), before=self._btn_row)

        threading.Thread(target=self._do_update, daemon=True).start()

    def _set_progress(self, text, pct):
        def _update():
            self._status_lbl.config(text=text)
            self._pct_lbl.config(text=f"{pct}%")
            self.overlay.update_idletasks()
            tw = self._track.winfo_width()
            self._bar.place(x=0, y=0, relheight=1, width=max(0, int(tw * pct / 100)))
        self.overlay.after(0, _update)

    def _do_update(self):
        try:
            script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "milo.py")
            backup_path = script_path + ".bak"
            tmp_path    = script_path + ".tmp"

            self._set_progress("Connecting to GitHub…", 8)
            time.sleep(0.35)

            self._set_progress("Downloading update…", 20)

            # Stream download
            with urllib.request.urlopen(GITHUB_SCRIPT_URL, timeout=30) as resp:
                total      = int(resp.headers.get("Content-Length", 0) or 0)
                downloaded = 0
                with open(tmp_path, "wb") as f:
                    while True:
                        chunk = resp.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total:
                            pct = 20 + int((downloaded / total) * 45)
                            kb  = downloaded // 1024
                            self._set_progress(f"Downloading… {kb} KB", pct)

            self._set_progress("Verifying file…", 68)
            time.sleep(0.25)

            with open(tmp_path, "r", encoding="utf-8", errors="ignore") as f:
                head = f.read(512)
            if "import" not in head:
                raise ValueError("Downloaded file appears invalid.")

            self._set_progress("Backing up current version…", 78)
            shutil.copy2(script_path, backup_path)
            time.sleep(0.2)

            self._set_progress("Replacing files…", 90)
            shutil.move(tmp_path, script_path)
            time.sleep(0.2)

            # Update local version.txt so update loop doesn't repeat on restart
            self._set_progress("Updating version file…", 95)
            version_path = os.path.join(os.path.dirname(script_path), "version.txt")
            with open(version_path, "w", encoding="utf-8") as f:
                f.write(self.latest_ver + "\n")
            time.sleep(0.2)

            self._set_progress("Done! Restarting Milo…", 100)
            time.sleep(1.0)

            self.overlay.after(0, self._relaunch)

        except Exception as ex:
            self.overlay.after(0, self._show_error, str(ex))

    def _relaunch(self):
        python = sys.executable
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "milo.py")
        self.parent.destroy()
        subprocess.Popen([python, script])

    def _show_error(self, msg):
        self._updating = False
        self._set_progress(f"✗  {msg}", 0)

        self._install_wrap.config(bg=RED)
        self._install_lbl.config(bg=RED, fg=TEXT, text="  Retry  ")
        self._install_wrap.bind("<Button-1>",    lambda e: self._start_update())
        self._install_lbl.bind("<Button-1>",     lambda e: self._start_update())

        self._cancel_lbl.config(fg=TEXT2)
        self._cancel_lbl.bind("<Button-1>", lambda e: self._cancel())

    def _cancel(self):
        self.overlay.destroy()
        if self.on_cancel:
            self.on_cancel()

    def destroy(self):
        self.overlay.destroy()


# ─────────────────────────────────────────────
#  MAIN APP
# ─────────────────────────────────────────────
class MiloApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Milo V1")
        self.root.geometry("860x600")
        self.root.minsize(660, 420)
        self.root.configure(bg=BG)

        self.messages         = []
        self._system_injected = False
        self.image_path       = None
        self.current_mode     = "normal"
        self.popup_visible    = False
        self.popup_sel        = 0
        self.popup_cmds       = []
        self._update_overlay  = None

        self._build_titlebar()
        self._build_sidebar()
        self._build_main()
        self._build_popup()

        self._print_welcome()

        # Silent startup check
        threading.Thread(target=self._silent_update_check, daemon=True).start()

    # ── UPDATE LOGIC ───────────────────────────
    def _silent_update_check(self):
        try:
            latest = fetch_latest_version()
            if _version_gt(latest, CURRENT_VERSION):
                self.root.after(900, self._open_update_overlay, latest)
        except Exception:
            pass

    def _manual_update_check(self):
        if self._update_overlay:
            return
        self._set_upd_state("checking")
        def _worker():
            try:
                latest = fetch_latest_version()
                if _version_gt(latest, CURRENT_VERSION):
                    self.root.after(0, self._set_upd_state, "available")
                    self.root.after(0, self._open_update_overlay, latest)
                else:
                    self.root.after(0, self._set_upd_state, "uptodate")
                    self.root.after(3000, self._set_upd_state, "idle")
            except Exception:
                self.root.after(0, self._set_upd_state, "error")
                self.root.after(3000, self._set_upd_state, "idle")
        threading.Thread(target=_worker, daemon=True).start()

    _UPD_STATES = {
        "idle":      ("↑", TEXT3),
        "checking":  ("…", TEXT2),
        "available": ("↑", ACCENT),
        "uptodate":  ("✓", GREEN),
        "error":     ("✗", RED),
    }

    def _set_upd_state(self, state):
        sym, col = self._UPD_STATES.get(state, self._UPD_STATES["idle"])
        self._upd_btn.config(text=sym, fg=col)

    def _open_update_overlay(self, latest_ver):
        if self._update_overlay:
            return
        self._set_upd_state("available")
        self._update_overlay = UpdateOverlay(
            self.root, CURRENT_VERSION, latest_ver,
            on_cancel=self._close_update_overlay,
        )

    def _close_update_overlay(self):
        self._update_overlay = None

    # ── TITLE BAR ──────────────────────────────
    def _build_titlebar(self):
        bar = tk.Frame(self.root, bg=BG2, height=30)
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)
        bar.bind("<ButtonPress-1>", self._drag_start)
        bar.bind("<B1-Motion>",     self._drag_motion)

        tk.Label(bar, text="◈ Milo", font=(MONO[0], 10, "bold"),
                 bg=BG2, fg=ACCENT).pack(side=tk.LEFT, padx=12)
        self.mode_label = tk.Label(bar, text=f"[{self.current_mode}]",
                                   font=MONO_SM, bg=BG2, fg=TEXT2)
        self.mode_label.pack(side=tk.LEFT, padx=4)
        tk.Label(bar, text=f"v{CURRENT_VERSION}", font=MONO_SM,
                 bg=BG2, fg=TEXT3).pack(side=tk.LEFT, padx=2)

        for color, cmd in [("#c0504a", self.root.destroy),
                           ("#d4a843", self._minimize),
                           ("#6b9e6b", None)]:
            b = tk.Label(bar, text="●", font=(MONO[0], 12),
                         bg=BG2, fg=color, cursor="hand2")
            b.pack(side=tk.RIGHT, padx=3)
            if cmd:
                b.bind("<Button-1>", lambda e, c=cmd: c())

        # Update button
        self._upd_btn = tk.Label(
            bar, text="↑", font=(MONO[0], 12, "bold"),
            bg=BG2, fg=TEXT3, cursor="hand2", padx=8,
        )
        self._upd_btn.pack(side=tk.RIGHT, padx=(0, 2))
        self._upd_btn.bind("<Button-1>", lambda e: self._manual_update_check())
        self._upd_btn.bind("<Enter>",    lambda e: self._upd_btn.config(fg=ACCENT) if self._upd_btn.cget("fg") == TEXT3 else None)
        self._upd_btn.bind("<Leave>",    lambda e: self._upd_btn.config(fg=TEXT3)  if self._upd_btn.cget("fg") == ACCENT else None)

        self._drag_x = self._drag_y = 0

    def _drag_start(self, e):
        self._drag_x = e.x_root - self.root.winfo_x()
        self._drag_y = e.y_root - self.root.winfo_y()

    def _drag_motion(self, e):
        self.root.geometry(f"+{e.x_root - self._drag_x}+{e.y_root - self._drag_y}")

    def _minimize(self):
        self.root.iconify()

    # ── SIDEBAR ────────────────────────────────
    def _build_sidebar(self):
        self.sidebar = tk.Frame(self.root, bg=BG2, width=180)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)
        tk.Frame(self.sidebar, bg=BORDER, width=1).pack(side=tk.RIGHT, fill=tk.Y)

        inner = tk.Frame(self.sidebar, bg=BG2)
        inner.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        self._draw_mascot(inner)
        tk.Frame(inner, bg=BORDER, height=1).pack(fill=tk.X, pady=10)

        tk.Label(inner, text="Model", font=MONO_SM,
                 bg=BG2, fg=TEXT3, anchor="w").pack(fill=tk.X)
        self.model_name_lbl = tk.Label(
            inner, text=MODEL_DISPLAY[self.current_mode],
            font=MONO_SM, bg=BG2, fg=TEXT2,
            anchor="w", wraplength=150, justify="left")
        self.model_name_lbl.pack(fill=tk.X, pady=(2, 10))

        tk.Frame(inner, bg=BORDER, height=1).pack(fill=tk.X, pady=4)
        tk.Label(inner,
                 text="Switch modes:\n/quick  ⚡ fast\n/normal ◆ balanced\n/deep   🧠 thorough",
                 font=MONO_SM, bg=BG2, fg=TEXT3,
                 anchor="w", justify="left").pack(fill=tk.X, pady=(8, 0))

        tk.Frame(inner, bg=BORDER, height=1).pack(fill=tk.X, pady=10)
        self.attach_lbl = tk.Label(inner, text="No image attached",
                                   font=MONO_SM, bg=BG2, fg=TEXT3,
                                   anchor="w", wraplength=150, justify="left")
        self.attach_lbl.pack(fill=tk.X)

        tk.Frame(self.sidebar, bg=BORDER, height=1).pack(fill=tk.X, side=tk.BOTTOM)
        clear_btn = tk.Label(self.sidebar, text="  ⟳  New chat",
                             font=MONO_SM, bg=BG2, fg=TEXT2, cursor="hand2", anchor="w")
        clear_btn.pack(side=tk.BOTTOM, fill=tk.X, pady=6, padx=8)
        clear_btn.bind("<Button-1>", lambda e: self._clear_chat())
        clear_btn.bind("<Enter>",    lambda e: clear_btn.config(fg=ACCENT))
        clear_btn.bind("<Leave>",    lambda e: clear_btn.config(fg=TEXT2))

    def _draw_mascot(self, parent):
        c = tk.Canvas(parent, width=60, height=60, bg=BG2,
                      highlightthickness=0, bd=0)
        c.pack(pady=(4, 8))
        pixels = ["..XXXX..", ".X....X.", "X.O..O.X",
                  "X......X", "X.XXXX.X", ".X....X.",
                  "..XXXX..", "...XX..."]
        pw, ox, oy = 7, 2, 2
        for r, row in enumerate(pixels):
            for col, ch in enumerate(row):
                x1, y1 = ox + col*pw, oy + r*pw
                if ch == "X":
                    c.create_rectangle(x1, y1, x1+pw-1, y1+pw-1, fill=ACCENT, outline="")
                elif ch == "O":
                    c.create_rectangle(x1, y1, x1+pw-1, y1+pw-1, fill=BG, outline="")

    # ── MAIN PANEL ─────────────────────────────
    def _build_main(self):
        main = tk.Frame(self.root, bg=BG)
        main.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        cf = tk.Frame(main, bg=BG)
        cf.pack(fill=tk.BOTH, expand=True)

        self.chat = tk.Text(
            cf, bg=BG, fg=TEXT,
            insertbackground=CURSOR_C, font=MONO_LG,
            wrap=tk.WORD, relief="flat", bd=0,
            padx=16, pady=12,
            selectbackground=BORDER_HI, selectforeground=TEXT,
            spacing1=2, spacing3=2, state=tk.DISABLED,
        )
        self.chat.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sb = tk.Scrollbar(cf, orient=tk.VERTICAL, command=self.chat.yview,
                          bg=BG2, troughcolor=BG2, width=8, relief="flat")
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.chat.configure(yscrollcommand=sb.set)

        for tag, fg, font in [
            ("you",    ACCENT, (MONO[0], 10, "bold")),
            ("milo",   GREEN,  (MONO[0], 10, "bold")),
            ("system", TEXT2,  (MONO[0], 9)),
            ("error",  RED,    (MONO[0], 10)),
            ("body",   TEXT,   MONO_LG),
            ("dim",    TEXT3,  MONO_SM),
            ("mode",   BLUE,   (MONO[0], 9)),
        ]:
            self.chat.tag_configure(tag, foreground=fg, font=font)

        tk.Frame(main, bg=BORDER, height=1).pack(fill=tk.X, side=tk.BOTTOM)
        input_wrap = tk.Frame(main, bg=BG3)
        input_wrap.pack(fill=tk.X, side=tk.BOTTOM)
        bar = tk.Frame(input_wrap, bg=BG3)
        bar.pack(fill=tk.X, padx=12, pady=8)

        tk.Label(bar, text=">", font=(MONO[0], 11, "bold"),
                 bg=BG3, fg=ACCENT).pack(side=tk.LEFT, padx=(0, 6))

        self.entry = tk.Entry(bar, bg=BG3, fg=TEXT,
                              insertbackground=CURSOR_C, font=MONO_LG,
                              relief="flat", bd=0, selectbackground=BORDER_HI)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entry.bind("<Return>",     self._on_enter)
        self.entry.bind("<KeyRelease>", self._on_key)
        self.entry.bind("<Up>",         self._popup_up)
        self.entry.bind("<Down>",       self._popup_down)
        self.entry.bind("<Tab>",        self._popup_select)
        self.entry.bind("<Escape>",     lambda e: self._hide_popup())

        ab = tk.Label(bar, text="📎", font=(MONO[0], 13),
                      bg=BG3, fg=TEXT2, cursor="hand2")
        ab.pack(side=tk.RIGHT, padx=(6, 0))
        ab.bind("<Button-1>", lambda e: self._attach_image())
        ab.bind("<Enter>",    lambda e: ab.config(fg=ACCENT))
        ab.bind("<Leave>",    lambda e: ab.config(fg=TEXT2))
        self._attach_btn_widget = ab

    # ── SLASH POPUP ────────────────────────────
    def _build_popup(self):
        self.popup = tk.Toplevel(self.root)
        self.popup.withdraw()
        self.popup.overrideredirect(True)
        self.popup.configure(bg=BORDER)

        inner = tk.Frame(self.popup, bg=BG_POPUP)
        inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        tk.Label(inner, text="Type to filter", font=MONO_SM,
                 bg=BG_POPUP, fg=TEXT3, anchor="w", padx=8, pady=4).pack(fill=tk.X)
        tk.Frame(inner, bg=BORDER, height=1).pack(fill=tk.X)

        self.popup_list_frame = tk.Frame(inner, bg=BG_POPUP)
        self.popup_list_frame.pack(fill=tk.BOTH, expand=True)
        self.popup_rows = []
        self._rebuild_popup_rows()

    def _rebuild_popup_rows(self, filter_text=""):
        for w in self.popup_rows:
            w.destroy()
        self.popup_rows = []
        self.popup_cmds = [c for c in COMMANDS
                           if not filter_text or filter_text.lower() in c]

        for cmd in self.popup_cmds:
            title, desc = COMMANDS[cmd]
            row = tk.Frame(self.popup_list_frame, bg=BG_POPUP, cursor="hand2")
            row.pack(fill=tk.X)
            icon = tk.Label(row, text="⊡", font=MONO_SM, bg=BG_POPUP,
                            fg=TEXT2, width=3, anchor="center")
            icon.pack(side=tk.LEFT, padx=(8, 4), pady=6)
            tf = tk.Frame(row, bg=BG_POPUP)
            tf.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=4)
            tl = tk.Label(tf, text=title, font=(MONO[0], 9, "bold"),
                          bg=BG_POPUP, fg=TEXT, anchor="w")
            tl.pack(fill=tk.X)
            dl = tk.Label(tf, text=desc, font=MONO_SM,
                          bg=BG_POPUP, fg=TEXT2, anchor="w")
            dl.pack(fill=tk.X)
            row._cmd = cmd; row._title = tl; row._desc = dl; row._icon = icon
            row.bind("<Button-1>", lambda e, c=cmd: self._run_command(c))
            for w in (tl, dl, icon):
                w.bind("<Button-1>", lambda e, c=cmd: self._run_command(c))
            self.popup_rows.append(row)

        self._highlight_popup(0)
        if not self.popup_cmds:
            self._hide_popup()

    def _highlight_popup(self, idx):
        self.popup_sel = idx
        for i, row in enumerate(self.popup_rows):
            bg = BG3 if i == idx else BG_POPUP
            for w in (row, row._title, row._desc, row._icon):
                w.config(bg=bg)

    def _show_popup(self, filter_text=""):
        self._rebuild_popup_rows(filter_text)
        if not self.popup_cmds:
            self._hide_popup(); return
        self.root.update_idletasks()
        ex = self.entry.winfo_rootx()
        ey = self.entry.winfo_rooty()
        h  = len(self.popup_cmds) * 54 + 30
        self.popup.geometry(f"280x{h}+{ex-4}+{ey-h-8}")
        self.popup.deiconify()
        self.popup.lift()
        self.popup_visible = True

    def _hide_popup(self):
        self.popup.withdraw()
        self.popup_visible = False

    def _popup_up(self, e):
        if self.popup_visible:
            self._highlight_popup(max(0, self.popup_sel - 1)); return "break"

    def _popup_down(self, e):
        if self.popup_visible:
            self._highlight_popup(min(len(self.popup_cmds)-1, self.popup_sel+1)); return "break"

    def _popup_select(self, e):
        if self.popup_visible and self.popup_cmds:
            self._run_command(self.popup_cmds[self.popup_sel]); return "break"

    def _run_command(self, cmd):
        self._hide_popup()
        self.entry.delete(0, tk.END)
        self._set_mode(cmd.lstrip("/"))

    def _on_key(self, e):
        t = self.entry.get()
        self._show_popup(t[1:]) if t.startswith("/") else self._hide_popup()

    def _on_enter(self, e):
        if self.popup_visible and self.popup_cmds:
            self._run_command(self.popup_cmds[self.popup_sel])
        else:
            self._send()

    # ── CHAT HELPERS ───────────────────────────
    def _append(self, tag, prefix, body_tag, body):
        self.chat.config(state=tk.NORMAL)
        self.chat.insert(tk.END, prefix, tag)
        self.chat.insert(tk.END, body + "\n", body_tag)
        self.chat.config(state=tk.DISABLED)
        self.chat.yview(tk.END)

    def _print_welcome(self):
        self.chat.config(state=tk.NORMAL)
        for tag, text in [
            ("dim",    "─" * 52 + "\n"),
            ("milo",   " Milo V1  "),
            ("dim",    "AI assistant\n"),
            ("dim",    "─" * 52 + "\n"),
            ("system", " Type /  to see available commands\n"),
            ("system", " 📎 Attach images using the clip button\n"),
            ("system", f" ↑  Click ↑ in the title bar to check for updates\n"),
            ("system", " Models: quick · normal · deep\n"),
            ("dim",    "─" * 52 + "\n\n"),
        ]:
            self.chat.insert(tk.END, text, tag)
        self.chat.config(state=tk.DISABLED)

    def _set_mode(self, mode):
        self.current_mode = mode
        self.mode_label.config(text=f"[{mode}]")
        self.model_name_lbl.config(text=MODEL_DISPLAY[mode])
        icons = {"quick": "⚡", "normal": "◆", "deep": "🧠"}
        self._append("mode", f" {icons.get(mode,'◆')} Mode → ", "system",
                     f"{mode}  ({MODEL_DISPLAY[mode]})")

    def _attach_image(self):
        path = filedialog.askopenfilename(
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp *.gif")])
        if path:
            self.image_path = path
            name = os.path.basename(path)
            self.attach_lbl.config(text=f"📎 {name}", fg=ACCENT)
            self._append("dim", " 📎 ", "system", f"Image attached: {name}")
            self._attach_btn_widget.config(fg=ACCENT)

    def _clear_chat(self):
        self.messages = []; self._system_injected = False; self.image_path = None
        self.attach_lbl.config(text="No image attached", fg=TEXT3)
        self._attach_btn_widget.config(fg=TEXT2)
        self.chat.config(state=tk.NORMAL)
        self.chat.delete("1.0", tk.END)
        self.chat.config(state=tk.DISABLED)
        self._print_welcome()

    # ── SEND ───────────────────────────────────
    def _send(self):
        text = self.entry.get().strip()
        if not text: return
        self.entry.delete(0, tk.END)
        self._append("you", " you  ", "body", text)
        threading.Thread(target=self._process, args=(text,), daemon=True).start()

    def _process(self, text):
        model = MODELS[self.current_mode]
        ct    = text
        if not self._system_injected:
            ct = f"[System: {SYSTEM_PROMPT}]\n\n{text}"
            self._system_injected = True

        user_msg = {"role": "user", "content": ct}
        if self.image_path:
            try:
                b64 = image_to_base64(self.image_path)
                user_msg = {"role": "user", "content": [
                    {"type": "text", "text": ct},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}
                ]}
            except Exception as ex:
                self.root.after(0, self._append, "error", " ✗ ", "error", f"Image error: {ex}")
                return

        self.messages.append(user_msg)
        self.root.after(0, self._append, "dim", " milo  ", "dim", "thinking…")

        reply, error = ask_model(model, self.messages)

        def _rm():
            self.chat.config(state=tk.NORMAL)
            c = self.chat.get("1.0", tk.END)
            i = c.rfind("thinking…\n")
            if i != -1:
                self.chat.delete(f"1.0 + {i} chars",
                                 f"1.0 + {i + len('thinking…' + chr(10))} chars")
            self.chat.config(state=tk.DISABLED)

        self.root.after(0, _rm)

        if reply is None:
            self.root.after(0, self._append, "error", " ✗ error  ", "error", str(error))
            self.root.after(0, self._finish_response)
        else:
            self.messages.append({"role": "assistant", "content": reply})
            self.root.after(0, self._start_typewriter,
                            f" milo [{self.current_mode}]  ", reply)

    def _finish_response(self):
        self.image_path = None
        self.attach_lbl.config(text="No image attached", fg=TEXT3)
        self._attach_btn_widget.config(fg=TEXT2)

    def _start_typewriter(self, prefix, reply):
        self.chat.config(state=tk.NORMAL)
        self.chat.insert(tk.END, prefix, "milo")
        self.chat.config(state=tk.DISABLED)
        self.chat.yview(tk.END)
        self._typewriter(reply, 0)

    def _typewriter(self, text, idx):
        if idx < len(text):
            self.chat.config(state=tk.NORMAL)
            self.chat.insert(tk.END, text[idx], "body")
            self.chat.config(state=tk.DISABLED)
            self.chat.yview(tk.END)
            self.root.after(12, self._typewriter, text, idx + 1)
        else:
            self.chat.config(state=tk.NORMAL)
            self.chat.insert(tk.END, "\n", "body")
            self.chat.config(state=tk.DISABLED)
            self.chat.yview(tk.END)
            self._finish_response()


# ─────────────────────────────────────────────
#  RUN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    root.overrideredirect(False)
    app = MiloApp(root)
    root.mainloop()
