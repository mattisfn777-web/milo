import requests
import base64
import tkinter as tk
from tkinter import filedialog
import threading
import os
import time

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
    "/quick":  ("⚡ Quick mode",   "Fast responses · ministral-3b"),
    "/normal": ("◆ Normal mode",  "Balanced · mistral-7b"),
    "/deep":   ("🧠 Deep mode",    "Thorough · qwen3.5-9b"),
}

SYSTEM_PROMPT = "You are Milo V1, a helpful AI assistant with mode awareness."

# ─────────────────────────────────────────────
#  COLORS  (dark terminal palette)
# ─────────────────────────────────────────────
BG        = "#0d0d0d"
BG2       = "#111111"
BG3       = "#191919"
BG_POPUP  = "#161616"
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

MONO = ("JetBrains Mono", 10) if os.name != "nt" else ("Consolas", 10)
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
#  MAIN APP
# ─────────────────────────────────────────────
class MiloApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Milo V1")
        self.root.geometry("860x600")
        self.root.minsize(660, 420)
        self.root.configure(bg=BG)

        self.messages    = []
        self._system_injected = False
        self.image_path  = None
        self.current_mode = "normal"
        self.popup_visible = False
        self.popup_sel   = 0
        self.popup_cmds  = []

        self._build_titlebar()
        self._build_sidebar()
        self._build_main()
        self._build_popup()

        self._print_welcome()

    # ── TITLE BAR ──────────────────────────────
    def _build_titlebar(self):
        bar = tk.Frame(self.root, bg=BG2, height=30)
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)

        # drag
        bar.bind("<ButtonPress-1>",   self._drag_start)
        bar.bind("<B1-Motion>",       self._drag_motion)

        tk.Label(bar, text="◈ Milo V1", font=(MONO[0], 10, "bold"),
                 bg=BG2, fg=ACCENT).pack(side=tk.LEFT, padx=12)

        self.mode_label = tk.Label(bar, text=f"[{self.current_mode}]",
                                   font=MONO_SM, bg=BG2, fg=TEXT2)
        self.mode_label.pack(side=tk.LEFT, padx=4)

        # window controls (visual only)
        for color, cmd in [("#c0504a", self.root.destroy),
                           ("#d4a843", self._minimize),
                           ("#6b9e6b", None)]:
            b = tk.Label(bar, text="●", font=(MONO[0], 12), bg=BG2, fg=color, cursor="hand2")
            b.pack(side=tk.RIGHT, padx=3)
            if cmd:
                b.bind("<Button-1>", lambda e, c=cmd: c())

        self._drag_x = 0
        self._drag_y = 0

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

        sep = tk.Frame(self.sidebar, bg=BORDER, width=1)
        sep.pack(side=tk.RIGHT, fill=tk.Y)

        inner = tk.Frame(self.sidebar, bg=BG2)
        inner.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        # pixel mascot (canvas drawing)
        self._draw_mascot(inner)

        tk.Frame(inner, bg=BORDER, height=1).pack(fill=tk.X, pady=10)

        # model info
        tk.Label(inner, text="Model", font=MONO_SM, bg=BG2, fg=TEXT3,
                 anchor="w").pack(fill=tk.X)
        self.model_name_lbl = tk.Label(inner, text=MODEL_DISPLAY[self.current_mode],
                                       font=MONO_SM, bg=BG2, fg=TEXT2,
                                       anchor="w", wraplength=150, justify="left")
        self.model_name_lbl.pack(fill=tk.X, pady=(2, 10))

        tk.Frame(inner, bg=BORDER, height=1).pack(fill=tk.X, pady=4)

        # switch hint
        hint = (
            "Switch modes:\n"
            "/quick  ⚡ fast\n"
            "/normal ◆ balanced\n"
            "/deep   🧠 thorough"
        )
        tk.Label(inner, text=hint, font=MONO_SM, bg=BG2, fg=TEXT3,
                 anchor="w", justify="left").pack(fill=tk.X, pady=(8, 0))

        tk.Frame(inner, bg=BORDER, height=1).pack(fill=tk.X, pady=10)

        # image attach status
        self.attach_lbl = tk.Label(inner, text="No image attached",
                                   font=MONO_SM, bg=BG2, fg=TEXT3,
                                   anchor="w", wraplength=150, justify="left")
        self.attach_lbl.pack(fill=tk.X)

        # clear btn
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
        # pixel robot face
        pixels = [
            "..XXXX..",
            ".X....X.",
            "X.O..O.X",
            "X......X",
            "X.XXXX.X",
            ".X....X.",
            "..XXXX..",
            "...XX...",
        ]
        pw = 7
        off_x, off_y = 2, 2
        for r, row in enumerate(pixels):
            for col, ch in enumerate(row):
                if ch == "X":
                    x1 = off_x + col * pw
                    y1 = off_y + r * pw
                    c.create_rectangle(x1, y1, x1+pw-1, y1+pw-1,
                                       fill=ACCENT, outline="")
                elif ch == "O":
                    x1 = off_x + col * pw
                    y1 = off_y + r * pw
                    c.create_rectangle(x1, y1, x1+pw-1, y1+pw-1,
                                       fill=BG, outline="")

    # ── MAIN PANEL ─────────────────────────────
    def _build_main(self):
        main = tk.Frame(self.root, bg=BG)
        main.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # chat log
        self.chat_frame = tk.Frame(main, bg=BG)
        self.chat_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        self.chat = tk.Text(
            self.chat_frame,
            bg=BG, fg=TEXT,
            insertbackground=CURSOR_C,
            font=MONO_LG,
            wrap=tk.WORD,
            relief="flat",
            bd=0,
            padx=16, pady=12,
            selectbackground=BORDER_HI,
            selectforeground=TEXT,
            spacing1=2, spacing3=2,
            state=tk.DISABLED,
        )
        self.chat.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sb = tk.Scrollbar(self.chat_frame, orient=tk.VERTICAL,
                          command=self.chat.yview, bg=BG2,
                          troughcolor=BG2, width=8, relief="flat")
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.chat.configure(yscrollcommand=sb.set)

        # tags
        self.chat.tag_configure("you",    foreground=ACCENT,  font=(MONO[0], 10, "bold"))
        self.chat.tag_configure("milo",   foreground=GREEN,   font=(MONO[0], 10, "bold"))
        self.chat.tag_configure("system", foreground=TEXT2,   font=(MONO[0], 9))
        self.chat.tag_configure("error",  foreground=RED,     font=(MONO[0], 10))
        self.chat.tag_configure("body",   foreground=TEXT,    font=MONO_LG)
        self.chat.tag_configure("dim",    foreground=TEXT3,   font=MONO_SM)
        self.chat.tag_configure("mode",   foreground=BLUE,    font=(MONO[0], 9))

        # ── INPUT BAR ──
        input_wrap = tk.Frame(main, bg=BG3)
        input_wrap.pack(fill=tk.X, side=tk.BOTTOM)

        tk.Frame(main, bg=BORDER, height=1).pack(fill=tk.X, side=tk.BOTTOM)

        bar = tk.Frame(input_wrap, bg=BG3)
        bar.pack(fill=tk.X, padx=12, pady=8)

        # prompt icon
        self.prompt_lbl = tk.Label(bar, text=">", font=(MONO[0], 11, "bold"),
                                   bg=BG3, fg=ACCENT)
        self.prompt_lbl.pack(side=tk.LEFT, padx=(0, 6))

        self.entry = tk.Entry(
            bar,
            bg=BG3, fg=TEXT,
            insertbackground=CURSOR_C,
            font=MONO_LG,
            relief="flat",
            bd=0,
            selectbackground=BORDER_HI,
        )
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entry.bind("<Return>",  self._on_enter)
        self.entry.bind("<KeyRelease>", self._on_key)
        self.entry.bind("<Up>",      self._popup_up)
        self.entry.bind("<Down>",    self._popup_down)
        self.entry.bind("<Tab>",     self._popup_select)
        self.entry.bind("<Escape>",  lambda e: self._hide_popup())

        # attach button
        attach_btn = tk.Label(bar, text="📎", font=(MONO[0], 13),
                              bg=BG3, fg=TEXT2, cursor="hand2")
        attach_btn.pack(side=tk.RIGHT, padx=(6, 0))
        attach_btn.bind("<Button-1>", lambda e: self._attach_image())
        attach_btn.bind("<Enter>",    lambda e: attach_btn.config(fg=ACCENT))
        attach_btn.bind("<Leave>",    lambda e: attach_btn.config(fg=TEXT2))
        self._attach_btn_widget = attach_btn

    # ── SLASH POPUP ────────────────────────────
    def _build_popup(self):
        self.popup = tk.Toplevel(self.root)
        self.popup.withdraw()
        self.popup.overrideredirect(True)
        self.popup.configure(bg=BORDER)

        inner = tk.Frame(self.popup, bg=BG_POPUP)
        inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        # filter hint
        self.popup_filter_lbl = tk.Label(
            inner, text="Type to filter",
            font=MONO_SM, bg=BG_POPUP, fg=TEXT3,
            anchor="w", padx=8, pady=4,
        )
        self.popup_filter_lbl.pack(fill=tk.X)
        tk.Frame(inner, bg=BORDER, height=1).pack(fill=tk.X)

        self.popup_list_frame = tk.Frame(inner, bg=BG_POPUP)
        self.popup_list_frame.pack(fill=tk.BOTH, expand=True)

        self.popup_rows = []
        self._rebuild_popup_rows()

    def _rebuild_popup_rows(self, filter_text=""):
        for w in self.popup_rows:
            w.destroy()
        self.popup_rows = []

        self.popup_cmds = [
            cmd for cmd in COMMANDS
            if filter_text == "" or filter_text.lower() in cmd
        ]

        for i, cmd in enumerate(self.popup_cmds):
            title, desc = COMMANDS[cmd]
            row = tk.Frame(self.popup_list_frame, bg=BG_POPUP, cursor="hand2")
            row.pack(fill=tk.X)

            icon_lbl = tk.Label(row, text="⊡", font=MONO_SM, bg=BG_POPUP, fg=TEXT2,
                                width=3, anchor="center")
            icon_lbl.pack(side=tk.LEFT, padx=(8, 4), pady=6)

            txt_frame = tk.Frame(row, bg=BG_POPUP)
            txt_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=4)

            title_lbl = tk.Label(txt_frame, text=title, font=(MONO[0], 9, "bold"),
                                 bg=BG_POPUP, fg=TEXT, anchor="w")
            title_lbl.pack(fill=tk.X)

            desc_lbl = tk.Label(txt_frame, text=desc, font=MONO_SM,
                                bg=BG_POPUP, fg=TEXT2, anchor="w")
            desc_lbl.pack(fill=tk.X)

            row._cmd = cmd
            row._title = title_lbl
            row._desc  = desc_lbl
            row._icon  = icon_lbl

            row.bind("<Button-1>", lambda e, c=cmd: self._run_command(c))
            for child in (title_lbl, desc_lbl, icon_lbl):
                child.bind("<Button-1>", lambda e, c=cmd: self._run_command(c))

            self.popup_rows.append(row)

        self._highlight_popup(0)
        if not self.popup_cmds:
            self._hide_popup()

    def _highlight_popup(self, idx):
        self.popup_sel = idx
        for i, row in enumerate(self.popup_rows):
            bg = BG3 if i == idx else BG_POPUP
            row.config(bg=bg)
            row._title.config(bg=bg)
            row._desc.config(bg=bg)
            row._icon.config(bg=bg)

    def _show_popup(self, filter_text=""):
        self._rebuild_popup_rows(filter_text)
        if not self.popup_cmds:
            self._hide_popup()
            return

        # position above input bar
        self.root.update_idletasks()
        ex = self.entry.winfo_rootx()
        ey = self.entry.winfo_rooty()
        height = len(self.popup_cmds) * 54 + 30
        width  = 280
        self.popup.geometry(f"{width}x{height}+{ex - 4}+{ey - height - 8}")
        self.popup.deiconify()
        self.popup.lift()
        self.popup_visible = True

    def _hide_popup(self):
        self.popup.withdraw()
        self.popup_visible = False

    def _popup_up(self, e):
        if self.popup_visible:
            self._highlight_popup(max(0, self.popup_sel - 1))
            return "break"

    def _popup_down(self, e):
        if self.popup_visible:
            self._highlight_popup(min(len(self.popup_cmds) - 1, self.popup_sel + 1))
            return "break"

    def _popup_select(self, e):
        if self.popup_visible and self.popup_cmds:
            self._run_command(self.popup_cmds[self.popup_sel])
            return "break"

    def _run_command(self, cmd):
        self._hide_popup()
        self.entry.delete(0, tk.END)
        mode = cmd.lstrip("/")
        self._set_mode(mode)

    # ── KEY HANDLER ────────────────────────────
    def _on_key(self, e):
        text = self.entry.get()
        if text.startswith("/"):
            after_slash = text[1:]
            self._show_popup(after_slash)
        else:
            self._hide_popup()

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
        lines = [
            ("dim",    "─" * 52 + "\n"),
            ("milo",   " Milo V1  "),
            ("dim",    "AI assistant\n"),
            ("dim",    "─" * 52 + "\n"),
            ("system", " Type /  to see available commands\n"),
            ("system", " 📎 Attach images using the clip button\n"),
            ("system", " Models: quick · normal · deep\n"),
            ("dim",    "─" * 52 + "\n\n"),
        ]
        for tag, text in lines:
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
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp *.gif")]
        )
        if path:
            self.image_path = path
            name = os.path.basename(path)
            self.attach_lbl.config(text=f"📎 {name}", fg=ACCENT)
            self._append("dim", " 📎 ", "system", f"Image attached: {name}")
            self._attach_btn_widget.config(fg=ACCENT)

    def _clear_chat(self):
        self.messages = []
        self._system_injected = False
        self.image_path = None
        self.attach_lbl.config(text="No image attached", fg=TEXT3)
        self._attach_btn_widget.config(fg=TEXT2)
        self.chat.config(state=tk.NORMAL)
        self.chat.delete("1.0", tk.END)
        self.chat.config(state=tk.DISABLED)
        self._print_welcome()

    # ── SEND ───────────────────────────────────
    def _send(self):
        text = self.entry.get().strip()
        if not text:
            return
        self.entry.delete(0, tk.END)
        self._append("you", " you  ", "body", text)
        threading.Thread(target=self._process, args=(text,), daemon=True).start()

    def _process(self, text):
        model = MODELS[self.current_mode]

        # Prepend system prompt into first user message (avoids "system" role error)
        content_text = text
        if not self._system_injected:
            content_text = f"[System: {SYSTEM_PROMPT}]\n\n{text}"
            self._system_injected = True

        user_msg = {"role": "user", "content": content_text}

        if self.image_path:
            try:
                b64 = image_to_base64(self.image_path)
                user_msg = {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": content_text},
                        {"type": "image_url",
                         "image_url": {"url": f"data:image/png;base64,{b64}"}}
                    ]
                }
            except Exception as ex:
                self.root.after(0, self._append, "error", " ✗ ", "error",
                                f"Image error: {ex}")
                return

        self.messages.append(user_msg)

        # typing indicator
        self.root.after(0, self._append, "dim", " milo  ", "dim", "thinking…")

        reply, error = ask_model(model, self.messages)

        # remove last "thinking" line
        def _remove_thinking():
            self.chat.config(state=tk.NORMAL)
            content = self.chat.get("1.0", tk.END)
            idx = content.rfind("thinking…\n")
            if idx != -1:
                start = f"1.0 + {idx} chars"
                end   = f"1.0 + {idx + len('thinking…' + chr(10))} chars"
                self.chat.delete(start, end)
            self.chat.config(state=tk.DISABLED)

        self.root.after(0, _remove_thinking)

        if reply is None:
            self.root.after(0, self._append, "error", " ✗ error  ", "error", str(error))
            self.root.after(0, self._finish_response)
        else:
            self.messages.append({"role": "assistant", "content": reply})
            prefix = f" milo [{self.current_mode}]  "
            self.root.after(0, self._start_typewriter, prefix, reply)

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
    root.overrideredirect(False)   # set True for fully frameless
    app = MiloApp(root)
    root.mainloop()