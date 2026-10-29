"""Cores, fontes e peças visuais compartilhadas do MelbyTune."""
import os
import sys
import threading

import customtkinter as ctk

# Paleta oficial (identity board)
BG = "#111116"        # Obsidian
SIDE = "#15141D"
PANEL = "#1C1B28"     # Graphite
PANEL2 = "#2A2940"
PURPLE = "#8B5CF6"    # Electric Purple
PURPLE_H = "#7646E0"
HONEY = "#FFC857"     # Honey Gold
HONEY_H = "#E6B14A"
TEXT = "#E8E8F0"      # Cloud White
MUTED = "#9292A3"     # Muted Gray
DANGER = "#B23A3A"
DANGER_H = "#962F2F"
GOOD = "#4FD18B"
BAD = "#F26D6D"

FONT = "Segoe UI"
MONO = "Consolas"


def resource(rel):
    """Caminho de um arquivo do app (funciona no .exe do PyInstaller também)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


_STYLES = {
    "primary": dict(fg_color=HONEY, hover_color=HONEY_H, text_color="#111116"),
    "purple": dict(fg_color=PURPLE, hover_color=PURPLE_H, text_color="#FFFFFF"),
    "ghost": dict(fg_color=PANEL2, hover_color="#363552", text_color=TEXT),
    "danger": dict(fg_color=DANGER, hover_color=DANGER_H, text_color="#FFFFFF"),
}


def button(parent, text, command=None, kind="ghost", **kw):
    opts = dict(_STYLES[kind])
    opts.update(kw)
    height = opts.pop("height", 34)
    return ctk.CTkButton(parent, text=text, command=command, corner_radius=8, height=height, **opts)


def title(page, text, sub=""):
    ctk.CTkLabel(page, text=text, font=(FONT, 24, "bold"), text_color=TEXT).pack(
        anchor="w", padx=24, pady=(22, 0))
    if sub:
        ctk.CTkLabel(page, text=sub, text_color=MUTED, wraplength=760, justify="left").pack(
            anchor="w", padx=24, pady=(2, 10))


def card(parent, **kw):
    return ctk.CTkFrame(parent, fg_color=PANEL, corner_radius=12, **kw)


def tabs(parent, names):
    tv = ctk.CTkTabview(
        parent, fg_color="transparent", segmented_button_fg_color=PANEL,
        segmented_button_selected_color=PURPLE, segmented_button_selected_hover_color=PURPLE_H,
        segmented_button_unselected_color=PANEL, segmented_button_unselected_hover_color=PANEL2,
        text_color=TEXT)
    for n in names:
        tv.add(n)
    return tv


def in_thread(fn, *args):
    threading.Thread(target=fn, args=args, daemon=True).start()


def short(path, n=78):
    return path if len(path) <= n else "…" + path[-(n - 1):]


class LogBox(ctk.CTkTextbox):
    """Caixa de texto só de leitura; pode ser escrita de qualquer thread."""

    def __init__(self, parent, **kw):
        super().__init__(parent, font=(MONO, 12), fg_color=PANEL, text_color=TEXT, **kw)
        self.configure(state="disabled")

    def write(self, text, newline=True):
        self.after(0, self._append, text + ("\n" if newline else ""))

    def _append(self, s):
        self.configure(state="normal")
        self.insert("end", s)
        self.see("end")
        self.configure(state="disabled")

    def clear(self):
        self.after(0, self._clear)

    def _clear(self):
        self.configure(state="normal")
        self.delete("1.0", "end")
        self.configure(state="disabled")
