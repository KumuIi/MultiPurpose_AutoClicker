#!/usr/bin/env python3
"""AutoClicker — preset-based, per-preset hotkeys, record-to-bind controls."""

import json, os, sys, time, threading, uuid
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from copy import deepcopy

try:
    from pynput.mouse import Button, Controller as MouseCtrl, Listener as MouseListener
    from pynput.keyboard import (
        Key as PKey,
        Controller as KeyCtrl,
        Listener as KeyListener,
    )
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pynput"])
    from pynput.mouse import Button, Controller as MouseCtrl, Listener as MouseListener
    from pynput.keyboard import Key as PKey, Controller as KeyCtrl, Listener as KeyListener

# ── Palette (Catppuccin Mocha) ────────────────────────────────────────────────
BG      = "#1e1e2e"
PANEL   = "#313244"
SURFACE = "#45475a"
FG      = "#cdd6f4"
SUBTLE  = "#a6adc8"
ACCENT  = "#89b4fa"
GREEN   = "#a6e3a1"
RED     = "#f38ba8"
ORANGE  = "#fab387"
YELLOW  = "#f9e2af"

def _appdata_dir() -> str:
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    path = os.path.join(base, "AutoClicker")
    os.makedirs(path, exist_ok=True)
    return path

PRESET_FILE = os.path.join(_appdata_dir(), "presets.json")

PYNPUT_BTN   = {"left": Button.left, "right": Button.right, "middle": Button.middle}
BUTTON_LABEL = {"left": "Left Click", "right": "Right Click", "middle": "Middle Click"}
BUTTON_FROM_PYNPUT = {Button.left: "left", Button.right: "right", Button.middle: "middle"}


def _new_preset(name: str = "New Preset") -> dict:
    return {
        "id":           str(uuid.uuid4()),
        "name":         name,
        "hotkey":       "",
        # click action
        "click_mode":   "mouse",   # "mouse" | "keyboard"
        "button":       "left",    # used when click_mode == "mouse"
        "key":          "",        # used when click_mode == "keyboard"
        "click_type":   "single",  # "single" | "double"
        # timing
        "hours":        0,
        "minutes":      0,
        "seconds":      0,
        "ms":           100,
        # repeat
        "repeat_mode":  "forever", # "forever" | "count"
        "repeat_count": 10,
        # position (only relevant for mouse mode)
        "pos_mode":     "current", # "current" | "fixed"
        "fixed_x":      0,
        "fixed_y":      0,
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _key_to_pynput(key_str: str):
    """Convert stored key string back to a pynput key object."""
    try:
        return getattr(PKey, key_str.lower())
    except AttributeError:
        return key_str[0] if key_str else "a"


def _pynput_to_str(key) -> str:
    """Convert a raw pynput key to a display/storage string."""
    try:
        if key.char:
            return key.char   # keep lowercase so kb.press('e') presses lowercase e
    except AttributeError:
        pass
    try:
        return key.name   # e.g. "space", "f6", "shift"
    except AttributeError:
        return str(key).replace("Key.", "")


def _display_key(key_str: str) -> str:
    """Human-friendly label for a stored key string."""
    NAMES = {
        "space": "Space", "enter": "Enter", "tab": "Tab",
        "backspace": "Backspace", "delete": "Delete", "escape": "Escape",
        "shift": "Shift", "ctrl": "Ctrl", "alt": "Alt",
        "up": "Up", "down": "Down", "left": "Left", "right": "Right",
        "home": "Home", "end": "End", "page_up": "Page Up", "page_down": "Page Down",
    }
    if key_str.lower() in NAMES:
        return NAMES[key_str.lower()]
    if key_str.lower().startswith("f") and key_str[1:].isdigit():
        return key_str.upper()
    return key_str.upper() if len(key_str) == 1 else key_str


# ── Preset row widget ─────────────────────────────────────────────────────────

class PresetRow(tk.Frame):
    def __init__(self, parent, preset: dict, app, **kw):
        super().__init__(parent, bg=PANEL, **kw)
        self.preset = preset
        self.app    = app

        self._dot_c = tk.Canvas(self, width=10, height=10, bg=PANEL, highlightthickness=0)
        self._dot_c.pack(side="left", padx=(8, 5), pady=8)
        self._dot = self._dot_c.create_oval(1, 1, 9, 9, fill=RED, outline="")

        self._lbl_name = tk.Label(self, text=preset["name"],
                                   bg=PANEL, fg=FG,
                                   font=("Segoe UI", 9, "bold"),
                                   anchor="w", width=15)
        self._lbl_name.pack(side="left", padx=(0, 6))

        self._lbl_hk = tk.Label(self, text=self._hk_text(),
                                  bg=SURFACE, fg=ACCENT,
                                  font=("Segoe UI", 8),
                                  padx=6, pady=2, width=8)
        self._lbl_hk.pack(side="left", padx=(0, 8))

        self._btn_go = tk.Button(self, text="Start",
                                  bg=GREEN, fg=BG,
                                  font=("Segoe UI", 8, "bold"),
                                  relief="flat", padx=8, pady=2,
                                  command=lambda: app.toggle_preset(preset["id"]))
        self._btn_go.pack(side="left", padx=(0, 4))

        tk.Button(self, text="Edit",
                  bg=SURFACE, fg=FG,
                  font=("Segoe UI", 8),
                  relief="flat", padx=6, pady=2,
                  command=lambda: app.select_for_edit(preset["id"])).pack(side="left", padx=(0, 4))

        tk.Button(self, text="X",
                  bg=SURFACE, fg=RED,
                  font=("Segoe UI", 8, "bold"),
                  relief="flat", padx=5, pady=2,
                  command=lambda: app.delete_preset(preset["id"])).pack(side="left")

        tk.Frame(self, bg=SURFACE, height=1).pack(side="bottom", fill="x")

    def _hk_text(self) -> str:
        hk = self.preset.get("hotkey", "")
        return hk if hk else "no key"

    def refresh(self):
        self._lbl_name.configure(text=self.preset["name"])
        self._lbl_hk.configure(text=self._hk_text())

    def set_running(self, running: bool):
        if running:
            self._dot_c.itemconfig(self._dot, fill=GREEN)
            self._btn_go.configure(text="Stop", bg=RED)
        else:
            self._dot_c.itemconfig(self._dot, fill=RED)
            self._btn_go.configure(text="Start", bg=GREEN)


# ── Main application ──────────────────────────────────────────────────────────

class AutoClickerApp:

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("AutoClicker")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)

        self.presets: list[dict]           = []
        self.runtime: dict[str, dict]      = {}
        self.rows:    dict[str, PresetRow] = {}
        self.editing_id: str | None        = None

        # Recording state flags — only one active at a time
        self._rec_hotkey     = False
        self._rec_click_key  = False
        self._rec_mouse      = False
        self._mouse_listener = None

        # Current editor values (not yet saved)
        self._current_hotkey    = ""
        self._current_button    = "left"
        self._current_click_key = ""

        self.mouse  = MouseCtrl()
        self.kb     = KeyCtrl()

        self._apply_styles()
        self._build_ui()
        self._load_presets()
        self._start_kb_listener()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── Styles ────────────────────────────────────────────────────────────────

    def _apply_styles(self):
        s = ttk.Style()
        s.theme_use("clam")

        s.configure(".",            background=BG,    foreground=FG, font=("Segoe UI", 9))
        s.configure("TFrame",       background=BG)
        s.configure("P.TFrame",     background=PANEL)
        s.configure("TLabel",       background=BG,    foreground=FG)
        s.configure("P.TLabel",     background=PANEL, foreground=FG)
        s.configure("H.TLabel",     background=PANEL, foreground=ACCENT, font=("Segoe UI", 8, "bold"))
        s.configure("Dim.TLabel",   background=PANEL, foreground=SUBTLE, font=("Segoe UI", 8))
        s.configure("TRadiobutton", background=PANEL, foreground=FG)
        s.map("TRadiobutton",       background=[("active", PANEL)], foreground=[("active", FG)])
        s.configure("TSpinbox",     fieldbackground=SURFACE, foreground=FG,
                    background=SURFACE, arrowcolor=FG, borderwidth=0)

        _f = dict(relief="flat", borderwidth=0)
        s.configure("Sm.TButton",    background=SURFACE, foreground=FG,
                    font=("Segoe UI", 8), padding=(6, 3), **_f)
        s.map("Sm.TButton",          background=[("active", "#585b70")])
        s.configure("Rec.TButton",   background=SURFACE, foreground=FG,
                    font=("Segoe UI", 9), padding=(8, 4), **_f)
        s.map("Rec.TButton",         background=[("active", "#585b70")])
        s.configure("RecOn.TButton", background=ORANGE, foreground=BG,
                    font=("Segoe UI", 9, "bold"), padding=(8, 4), **_f)
        s.configure("Save.TButton",  background=YELLOW, foreground=BG,
                    font=("Segoe UI", 9, "bold"), padding=(10, 5), **_f)
        s.map("Save.TButton",        background=[("active", "#e8cf90")])
        s.configure("Add.TButton",   background=ACCENT, foreground=BG,
                    font=("Segoe UI", 9, "bold"), padding=(10, 5), **_f)
        s.map("Add.TButton",         background=[("active", "#74a7eb")])

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.root.geometry("450x700")

        # Outer frame holds canvas + scrollbar
        outer = tk.Frame(self.root, bg=BG)
        outer.pack(fill="both", expand=True)

        self._main_canvas = tk.Canvas(outer, bg=BG, highlightthickness=0)
        vsb = ttk.Scrollbar(outer, orient="vertical", command=self._main_canvas.yview)
        self._main_canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._main_canvas.pack(side="left", fill="both", expand=True)

        # Inner frame is the real content container
        wrap = ttk.Frame(self._main_canvas, padding=10)
        self._wrap_window = self._main_canvas.create_window((0, 0), window=wrap, anchor="nw")

        wrap.bind("<Configure>", self._on_wrap_configure)
        self._main_canvas.bind("<Configure>", self._on_canvas_configure)
        self._main_canvas.bind("<MouseWheel>",
            lambda e: self._main_canvas.yview_scroll(-1*(e.delta//120), "units"))
        wrap.bind("<MouseWheel>",
            lambda e: self._main_canvas.yview_scroll(-1*(e.delta//120), "units"))

        self._build_presets_panel(wrap)
        self._build_editor(wrap)

    def _on_wrap_configure(self, _event):
        self._main_canvas.configure(scrollregion=self._main_canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self._main_canvas.itemconfig(self._wrap_window, width=event.width)

    # ── Presets panel ─────────────────────────────────────────────────────────

    def _build_presets_panel(self, parent):
        card = ttk.Frame(parent, style="P.TFrame", padding=(10, 8))
        card.pack(fill="x")

        hdr = ttk.Frame(card, style="P.TFrame")
        hdr.pack(fill="x", pady=(0, 6))
        ttk.Label(hdr, text="PRESETS", style="H.TLabel").pack(side="left")
        ttk.Button(hdr, text="+ New Preset", style="Add.TButton",
                   command=self._new_preset).pack(side="right")

        host = tk.Frame(card, bg=PANEL, height=190)
        host.pack(fill="x")
        host.pack_propagate(False)

        self._list_canvas = tk.Canvas(host, bg=PANEL, highlightthickness=0)
        sb = ttk.Scrollbar(host, orient="vertical", command=self._list_canvas.yview)
        self._list_frame = tk.Frame(self._list_canvas, bg=PANEL)
        self._list_frame.bind("<Configure>",
            lambda e: self._list_canvas.configure(
                scrollregion=self._list_canvas.bbox("all")))
        self._list_canvas.create_window((0, 0), window=self._list_frame, anchor="nw")
        self._list_canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._list_canvas.pack(side="left", fill="both", expand=True)
        self._list_canvas.bind("<MouseWheel>",
            lambda e: self._list_canvas.yview_scroll(-1*(e.delta//120), "units"))

    # ── Editor ────────────────────────────────────────────────────────────────

    def _build_editor(self, parent):
        self._ed_outer = ttk.Frame(parent)
        self._ed_outer.pack(fill="x", pady=(8, 0))

        self._lbl_editing = tk.Label(self._ed_outer,
                                      text="<-- Select a preset above to edit it",
                                      bg=BG, fg=SUBTLE,
                                      font=("Segoe UI", 9, "italic"), anchor="w")
        self._lbl_editing.pack(anchor="w", pady=(0, 4))

        self._ed_inner = ttk.Frame(self._ed_outer)

        self._build_interval(self._ed_inner)
        self._build_options(self._ed_inner)
        self._build_repeat(self._ed_inner)
        self._build_position(self._ed_inner)
        self._build_hotkey_section(self._ed_inner)

        foot = ttk.Frame(self._ed_inner)
        foot.pack(fill="x", pady=(8, 0))
        ttk.Button(foot, text="Duplicate", style="Sm.TButton",
                   command=self._duplicate_editing).pack(side="right", padx=(6, 0))
        ttk.Button(foot, text="Save Preset", style="Save.TButton",
                   command=self._save_editing).pack(side="right")

    def _bind_scroll(self, widget):
        widget.bind("<MouseWheel>",
            lambda e: self._main_canvas.yview_scroll(-1*(e.delta//120), "units"))
        for child in widget.winfo_children():
            self._bind_scroll(child)

    def _section(self, parent, title: str) -> tk.Frame:
        outer = ttk.Frame(parent)
        outer.pack(fill="x", pady=(6, 0))
        card = tk.Frame(outer, bg=PANEL)
        card.pack(fill="x")
        tk.Label(card, text=title, bg=PANEL, fg=ACCENT,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=10, pady=(8, 4))
        inner = tk.Frame(card, bg=PANEL)
        inner.pack(fill="x", padx=10, pady=(0, 8))
        return inner

    def _build_interval(self, parent):
        f = self._section(parent, "CLICK INTERVAL")
        row = tk.Frame(f, bg=PANEL)
        row.pack(fill="x")
        self.v_hours   = tk.IntVar(value=0)
        self.v_minutes = tk.IntVar(value=0)
        self.v_seconds = tk.IntVar(value=0)
        self.v_ms      = tk.IntVar(value=100)
        for var, lbl, mx in [
            (self.v_hours,   "Hours", 23),
            (self.v_minutes, "Min",   59),
            (self.v_seconds, "Sec",   59),
            (self.v_ms,      "Ms",   999),
        ]:
            col = tk.Frame(row, bg=PANEL)
            col.pack(side="left", fill="x", expand=True, padx=(0, 5))
            tk.Label(col, text=lbl, bg=PANEL, fg=SUBTLE,
                     font=("Segoe UI", 8)).pack(anchor="w")
            ttk.Spinbox(col, from_=0, to=mx, textvariable=var,
                        width=5, font=("Segoe UI", 10)).pack(fill="x")

    def _build_options(self, parent):
        f = self._section(parent, "CLICK OPTIONS")

        # ── Click mode toggle ─────────────────────────────────────────────────
        mode_row = tk.Frame(f, bg=PANEL)
        mode_row.pack(fill="x", pady=(0, 8))
        tk.Label(mode_row, text="Click action:", bg=PANEL, fg=SUBTLE,
                 font=("Segoe UI", 8)).pack(side="left", padx=(0, 8))

        self.v_click_mode = tk.StringVar(value="mouse")
        for val, txt in [("mouse", "Mouse Button"), ("keyboard", "Keyboard Key")]:
            ttk.Radiobutton(mode_row, text=txt,
                            variable=self.v_click_mode, value=val,
                            command=self._sync_click_mode).pack(side="left", padx=(0, 10))

        # ── Mouse section ─────────────────────────────────────────────────────
        self._mouse_section = tk.Frame(f, bg=PANEL)
        self._mouse_section.pack(fill="x", pady=(0, 6))

        tk.Label(self._mouse_section, text="Mouse Button", bg=PANEL, fg=SUBTLE,
                 font=("Segoe UI", 8)).pack(anchor="w")
        self._lbl_mbtn = tk.Label(self._mouse_section, text="Left Click",
                                   bg=SURFACE, fg=FG,
                                   font=("Segoe UI", 10),
                                   padx=8, pady=4, anchor="w")
        self._lbl_mbtn.pack(fill="x", pady=(0, 4))
        self._btn_rec_mouse = ttk.Button(self._mouse_section, text="Record Click",
                                          style="Rec.TButton",
                                          command=self._start_mouse_record)
        self._btn_rec_mouse.pack(anchor="w")

        # ── Keyboard section ──────────────────────────────────────────────────
        self._keyboard_section = tk.Frame(f, bg=PANEL)
        # not packed yet — shown when mode == "keyboard"

        tk.Label(self._keyboard_section, text="Keyboard Key", bg=PANEL, fg=SUBTLE,
                 font=("Segoe UI", 8)).pack(anchor="w")
        self._lbl_click_key = tk.Label(self._keyboard_section, text="none",
                                        bg=SURFACE, fg=FG,
                                        font=("Segoe UI", 10),
                                        padx=8, pady=4, anchor="w")
        self._lbl_click_key.pack(fill="x", pady=(0, 4))
        self._btn_rec_click_key = ttk.Button(self._keyboard_section,
                                              text="Record Key",
                                              style="Rec.TButton",
                                              command=self._start_click_key_record)
        self._btn_rec_click_key.pack(anchor="w")

        # ── Click type (shared) ───────────────────────────────────────────────
        sep = tk.Frame(f, bg=SURFACE, height=1)
        sep.pack(fill="x", pady=8)

        type_row = tk.Frame(f, bg=PANEL)
        type_row.pack(fill="x")
        tk.Label(type_row, text="Click Type:", bg=PANEL, fg=SUBTLE,
                 font=("Segoe UI", 8)).pack(side="left", padx=(0, 10))
        self.v_click_type = tk.StringVar(value="single")
        for val, txt in [("single", "Single"), ("double", "Double")]:
            ttk.Radiobutton(type_row, text=txt,
                            variable=self.v_click_type, value=val).pack(side="left", padx=(0, 10))

        self._sync_click_mode()

    def _build_repeat(self, parent):
        f = self._section(parent, "CLICK REPEAT")
        self.v_repeat_mode  = tk.StringVar(value="forever")
        self.v_repeat_count = tk.IntVar(value=10)

        ttk.Radiobutton(f, text="Repeat forever",
                        variable=self.v_repeat_mode, value="forever",
                        command=self._sync_repeat).pack(anchor="w")
        row = tk.Frame(f, bg=PANEL)
        row.pack(anchor="w", pady=(6, 0))
        ttk.Radiobutton(row, text="Repeat",
                        variable=self.v_repeat_mode, value="count",
                        command=self._sync_repeat).pack(side="left")
        self._spin_repeat = ttk.Spinbox(row, from_=1, to=9_999_999,
                                         textvariable=self.v_repeat_count,
                                         width=8, font=("Segoe UI", 10))
        self._spin_repeat.pack(side="left", padx=8)
        tk.Label(row, text="times", bg=PANEL, fg=FG).pack(side="left")
        self._sync_repeat()

    def _build_position(self, parent):
        f = self._section(parent, "CURSOR POSITION  (mouse mode only)")
        self.v_pos_mode = tk.StringVar(value="current")
        self.v_fixed_x  = tk.IntVar(value=0)
        self.v_fixed_y  = tk.IntVar(value=0)

        ttk.Radiobutton(f, text="Current cursor location",
                        variable=self.v_pos_mode, value="current",
                        command=self._sync_position).pack(anchor="w")
        row = tk.Frame(f, bg=PANEL)
        row.pack(anchor="w", pady=(6, 0), fill="x")
        ttk.Radiobutton(row, text="Fixed position",
                        variable=self.v_pos_mode, value="fixed",
                        command=self._sync_position).pack(side="left")
        coords = tk.Frame(row, bg=PANEL)
        coords.pack(side="left", padx=(10, 0))
        tk.Label(coords, text="X:", bg=PANEL, fg=FG).pack(side="left")
        self._spin_x = ttk.Spinbox(coords, from_=0, to=9999,
                                    textvariable=self.v_fixed_x, width=5,
                                    font=("Segoe UI", 10))
        self._spin_x.pack(side="left", padx=(3, 10))
        tk.Label(coords, text="Y:", bg=PANEL, fg=FG).pack(side="left")
        self._spin_y = ttk.Spinbox(coords, from_=0, to=9999,
                                    textvariable=self.v_fixed_y, width=5,
                                    font=("Segoe UI", 10))
        self._spin_y.pack(side="left", padx=3)
        self._btn_pick = ttk.Button(f, text="Pick Location on Screen",
                                     style="Sm.TButton",
                                     command=self._pick_location)
        self._btn_pick.pack(anchor="w", pady=(8, 0))
        self._sync_position()

    def _build_hotkey_section(self, parent):
        f = self._section(parent, "PRESET HOTKEY  --  press to start / stop this preset")
        row = tk.Frame(f, bg=PANEL)
        row.pack(fill="x")

        self._lbl_hk = tk.Label(row, text="none",
                                  bg=SURFACE, fg=ACCENT,
                                  font=("Segoe UI", 11, "bold"),
                                  padx=10, pady=4, anchor="w")
        self._lbl_hk.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self._btn_rec_key = ttk.Button(row, text="Record Key",
                                        style="Rec.TButton",
                                        command=self._toggle_hotkey_record)
        self._btn_rec_key.pack(side="left")

        ttk.Button(row, text="Clear", style="Sm.TButton",
                   command=self._clear_hotkey).pack(side="left", padx=(6, 0))

    # ── Sync helpers ──────────────────────────────────────────────────────────

    def _sync_click_mode(self):
        mode = self.v_click_mode.get()
        if mode == "mouse":
            self._keyboard_section.pack_forget()
            self._mouse_section.pack(fill="x", pady=(0, 6))
        else:
            self._mouse_section.pack_forget()
            self._keyboard_section.pack(fill="x", pady=(0, 6))

    def _sync_repeat(self):
        s = "normal" if self.v_repeat_mode.get() == "count" else "disabled"
        self._spin_repeat.configure(state=s)

    def _sync_position(self):
        s = "normal" if self.v_pos_mode.get() == "fixed" else "disabled"
        self._spin_x.configure(state=s)
        self._spin_y.configure(state=s)
        self._btn_pick.configure(state=s)

    # ── Preset persistence ────────────────────────────────────────────────────

    def _load_presets(self):
        if os.path.exists(PRESET_FILE):
            try:
                with open(PRESET_FILE) as fh:
                    self.presets = json.load(fh).get("presets", [])
            except Exception:
                self.presets = []
        self._refresh_list()

    def _save_to_disk(self):
        with open(PRESET_FILE, "w") as fh:
            json.dump({"presets": self.presets}, fh, indent=2)

    def _refresh_list(self):
        for w in self._list_frame.winfo_children():
            w.destroy()
        self.rows.clear()

        if not self.presets:
            tk.Label(self._list_frame,
                     text="No presets yet -- click '+ New Preset' to create one.",
                     bg=PANEL, fg=SUBTLE, font=("Segoe UI", 9),
                     wraplength=360, pady=20).pack(fill="x")
            return

        for p in self.presets:
            r = PresetRow(self._list_frame, p, self)
            r.pack(fill="x")
            self.rows[p["id"]] = r
            rt = self.runtime.get(p["id"], {})
            r.set_running(rt.get("running", False))

        self._list_frame.update_idletasks()
        self._list_canvas.configure(width=self._list_frame.winfo_reqwidth())

    # ── Preset CRUD ───────────────────────────────────────────────────────────

    def _new_preset(self):
        name = simpledialog.askstring("New Preset", "Enter preset name:", parent=self.root)
        if name is None:
            return
        p = _new_preset(name.strip() or "Preset")
        self.presets.append(p)
        self._save_to_disk()
        self._refresh_list()
        self.select_for_edit(p["id"])

    def delete_preset(self, pid: str):
        p = self._preset(pid)
        if not p:
            return
        if not messagebox.askyesno("Delete", f"Delete preset '{p['name']}'?", parent=self.root):
            return
        rt = self.runtime.get(pid, {})
        rt["running"] = False
        self.presets = [x for x in self.presets if x["id"] != pid]
        self._save_to_disk()
        if self.editing_id == pid:
            self.editing_id = None
            self._ed_inner.pack_forget()
            self._lbl_editing.configure(text="<-- Select a preset above to edit it",
                                         fg=SUBTLE, font=("Segoe UI", 9, "italic"))
        self._refresh_list()

    def _preset(self, pid: str) -> dict | None:
        return next((p for p in self.presets if p["id"] == pid), None)

    # ── Editor ────────────────────────────────────────────────────────────────

    def select_for_edit(self, pid: str):
        p = self._preset(pid)
        if not p:
            return
        self.editing_id = pid
        self._lbl_editing.configure(
            text=f"Editing:  {p['name']}",
            fg=YELLOW, font=("Segoe UI", 10, "bold"))
        self._ed_inner.pack(fill="x")
        self._load_into_editor(p)

    def _load_into_editor(self, p: dict):
        self.v_hours.set(p.get("hours", 0))
        self.v_minutes.set(p.get("minutes", 0))
        self.v_seconds.set(p.get("seconds", 0))
        self.v_ms.set(p.get("ms", 100))

        mode = p.get("click_mode", "mouse")
        self.v_click_mode.set(mode)
        self._sync_click_mode()

        btn = p.get("button", "left")
        self._current_button = btn
        self._lbl_mbtn.configure(text=BUTTON_LABEL.get(btn, "Left Click"))

        key = p.get("key", "")
        self._current_click_key = key
        self._lbl_click_key.configure(text=_display_key(key) if key else "none")

        self.v_click_type.set(p.get("click_type", "single"))
        self.v_repeat_mode.set(p.get("repeat_mode", "forever"))
        self.v_repeat_count.set(p.get("repeat_count", 10))
        self._sync_repeat()

        self.v_pos_mode.set(p.get("pos_mode", "current"))
        self.v_fixed_x.set(p.get("fixed_x", 0))
        self.v_fixed_y.set(p.get("fixed_y", 0))
        self._sync_position()

        hk = p.get("hotkey", "")
        self._current_hotkey = hk
        self._lbl_hk.configure(text=hk or "none")

    def _save_editing(self):
        if not self.editing_id:
            return
        p = self._preset(self.editing_id)
        if not p:
            return
        p.update({
            "hours":        self.v_hours.get(),
            "minutes":      self.v_minutes.get(),
            "seconds":      self.v_seconds.get(),
            "ms":           self.v_ms.get(),
            "click_mode":   self.v_click_mode.get(),
            "button":       self._current_button,
            "key":          self._current_click_key,
            "click_type":   self.v_click_type.get(),
            "repeat_mode":  self.v_repeat_mode.get(),
            "repeat_count": self.v_repeat_count.get(),
            "pos_mode":     self.v_pos_mode.get(),
            "fixed_x":      self.v_fixed_x.get(),
            "fixed_y":      self.v_fixed_y.get(),
            "hotkey":       self._current_hotkey,
        })
        self._save_to_disk()
        self._refresh_list()
        self._lbl_editing.configure(text=f"Saved: {p['name']}", fg=GREEN)
        self.root.after(1500, lambda: self._lbl_editing.configure(
            text=f"Editing:  {p['name']}", fg=YELLOW))

    def _duplicate_editing(self):
        if not self.editing_id:
            return
        p = self._preset(self.editing_id)
        if not p:
            return
        dup = deepcopy(p)
        dup["id"]     = str(uuid.uuid4())
        dup["name"]   = p["name"] + " (copy)"
        dup["hotkey"] = ""
        self.presets.append(dup)
        self._save_to_disk()
        self._refresh_list()
        self.select_for_edit(dup["id"])

    # ── Mouse button recording ────────────────────────────────────────────────

    def _start_mouse_record(self):
        if self._rec_mouse:
            return
        self._rec_mouse = True
        self._btn_rec_mouse.configure(text="Click any mouse button...", style="RecOn.TButton")
        self.root.after(400, self._attach_mouse_listener)

    def _attach_mouse_listener(self):
        if not self._rec_mouse:
            return

        def on_click(x, y, button, pressed):
            if pressed and self._rec_mouse:
                btn_str = BUTTON_FROM_PYNPUT.get(button, "left")
                self.root.after(0, self._finish_mouse_record, btn_str)
                return False

        self._mouse_listener = MouseListener(on_click=on_click)
        self._mouse_listener.daemon = True
        self._mouse_listener.start()

    def _finish_mouse_record(self, btn_str: str):
        self._rec_mouse      = False
        self._current_button = btn_str
        self._lbl_mbtn.configure(text=BUTTON_LABEL.get(btn_str, "Left Click"))
        self._btn_rec_mouse.configure(text="Record Click", style="Rec.TButton")
        if self._mouse_listener:
            self._mouse_listener.stop()
            self._mouse_listener = None

    # ── Click-key recording ───────────────────────────────────────────────────

    def _start_click_key_record(self):
        if self._rec_click_key or self._rec_hotkey:
            return
        self._rec_click_key = True
        self._btn_rec_click_key.configure(text="Press a key...  (ESC = cancel)",
                                           style="RecOn.TButton")
        self._lbl_click_key.configure(text="...")

    def _finish_click_key_record(self, name: str):
        self._rec_click_key     = False
        self._current_click_key = name
        self._lbl_click_key.configure(text=_display_key(name))
        self._btn_rec_click_key.configure(text="Record Key", style="Rec.TButton")

    def _cancel_click_key_record(self):
        self._rec_click_key = False
        self._lbl_click_key.configure(
            text=_display_key(self._current_click_key) if self._current_click_key else "none")
        self._btn_rec_click_key.configure(text="Record Key", style="Rec.TButton")

    # ── Hotkey recording ──────────────────────────────────────────────────────

    def _toggle_hotkey_record(self):
        if self._rec_hotkey:
            self._cancel_hotkey_record()
        else:
            self._start_hotkey_record()

    def _start_hotkey_record(self):
        if self._rec_click_key:
            return
        self._rec_hotkey = True
        self._btn_rec_key.configure(text="Press any key...  (ESC = cancel)", style="RecOn.TButton")
        self._lbl_hk.configure(text="...")

    def _cancel_hotkey_record(self):
        self._rec_hotkey = False
        self._btn_rec_key.configure(text="Record Key", style="Rec.TButton")
        self._lbl_hk.configure(text=self._current_hotkey or "none")

    def _finish_hotkey_record(self, name: str):
        self._rec_hotkey     = False
        self._current_hotkey = name
        self._btn_rec_key.configure(text="Record Key", style="Rec.TButton")
        self._lbl_hk.configure(text=name)

    def _clear_hotkey(self):
        self._current_hotkey = ""
        self._lbl_hk.configure(text="none")

    # ── Pick location ─────────────────────────────────────────────────────────

    def _pick_location(self):
        self.root.withdraw()
        ov = tk.Toplevel()
        ov.attributes("-fullscreen", True, "-alpha", 0.25, "-topmost", True)
        ov.configure(bg="black", cursor="crosshair")
        tk.Label(ov, text="Click anywhere to set fixed position  --  ESC to cancel",
                 fg="white", bg="black",
                 font=("Segoe UI", 14, "bold")).place(relx=0.5, rely=0.5, anchor="center")

        def pick(e):
            self.v_fixed_x.set(ov.winfo_pointerx())
            self.v_fixed_y.set(ov.winfo_pointery())
            ov.destroy()
            self.root.deiconify()

        ov.bind("<Button-1>", pick)
        ov.bind("<Escape>", lambda _: (ov.destroy(), self.root.deiconify()))
        ov.focus_set()

    # ── Click engine ──────────────────────────────────────────────────────────

    def toggle_preset(self, pid: str):
        rt = self.runtime.setdefault(pid, {"running": False, "thread": None, "count": 0})
        if rt["running"]:
            rt["running"] = False
        else:
            p = self._preset(pid)
            if not p:
                return
            rt["running"] = True
            rt["count"]   = 0
            if r := self.rows.get(pid):
                r.set_running(True)
            t = threading.Thread(target=self._click_loop, args=(pid,), daemon=True)
            rt["thread"] = t
            t.start()

    def _click_loop(self, pid: str):
        p  = self._preset(pid)
        rt = self.runtime[pid]
        if not p:
            return

        interval = max(0.001, (
            p["hours"] * 3600 + p["minutes"] * 60 + p["seconds"] + p["ms"] / 1000.0
        ))
        forever = p["repeat_mode"] == "forever"
        limit   = p["repeat_count"] if not forever else None
        done    = 0

        # Resolve what to click/press once before the loop
        mode = p.get("click_mode", "mouse")
        if mode == "keyboard":
            k = _key_to_pynput(p.get("key", "space"))
            n_presses = 2 if p["click_type"] == "double" else 1
        else:
            btn    = PYNPUT_BTN.get(p["button"], Button.left)
            clicks = 2 if p["click_type"] == "double" else 1

        while rt["running"]:
            if mode == "keyboard":
                for _ in range(n_presses):
                    self.kb.press(k)
                    self.kb.release(k)
            else:
                if p["pos_mode"] == "fixed":
                    self.mouse.position = (p["fixed_x"], p["fixed_y"])
                self.mouse.click(btn, clicks)

            done += 1
            rt["count"] = done
            if not forever and done >= limit:
                break

            end = time.perf_counter() + interval
            while rt["running"] and time.perf_counter() < end:
                time.sleep(0.005)

        rt["running"] = False
        self.root.after(0, self._preset_stopped, pid)

    def _preset_stopped(self, pid: str):
        if r := self.rows.get(pid):
            r.set_running(False)

    # ── Global keyboard listener ──────────────────────────────────────────────

    def _start_kb_listener(self):
        def on_press(key):
            name = _pynput_to_str(key)
            esc  = name in ("esc", "escape", "ESC", "ESCAPE")

            # Click-key recording takes priority
            if self._rec_click_key:
                if esc:
                    self.root.after(0, self._cancel_click_key_record)
                else:
                    self.root.after(0, self._finish_click_key_record, name)
                return

            # Hotkey recording
            if self._rec_hotkey:
                if esc:
                    self.root.after(0, self._cancel_hotkey_record)
                else:
                    self.root.after(0, self._finish_hotkey_record, name.upper())
                return

            # Trigger presets
            for p in self.presets:
                hk = p.get("hotkey", "")
                if hk and name.upper() == hk.upper():
                    self.root.after(0, self.toggle_preset, p["id"])

        self._kb_listener = KeyListener(on_press=on_press)
        self._kb_listener.daemon = True
        self._kb_listener.start()

    # ── Cleanup ───────────────────────────────────────────────────────────────

    def _on_close(self):
        for rt in self.runtime.values():
            rt["running"] = False
        self._kb_listener.stop()
        if self._mouse_listener:
            self._mouse_listener.stop()
        self.root.destroy()


def main():
    root = tk.Tk()
    AutoClickerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
