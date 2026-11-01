"""Cores, fontes e peças visuais compartilhadas do MelbyTune.

Identidade: Obsidian (fundo), Graphite (painéis), Electric Purple (ações e destaques),
Honey Gold (detalhes e identidade), Cloud White (texto) e Muted Gray (texto secundário).
Fontes: Exo 2 (títulos) e Inter (textos e interface).
"""
import glob
import os
import sys
import threading

import customtkinter as ctk
from PIL import Image, ImageDraw

APP_VERSION = "2.1.0"

# ----------------------------------------------------------------------- cores
BG = "#111116"        # Obsidian
SIDE = "#15141D"
PANEL = "#1C1B28"     # Graphite
PANEL2 = "#2A2940"
BORDER = "#2B2A40"
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
BLUE = "#4C8DF6"
LAVENDER = "#9D8CF7"

FONT = "Inter"
FONT_TITLE = "Exo 2"
MONO = "Consolas"


def resource(rel):
    """Caminho de um arquivo do app (funciona também no .exe do PyInstaller)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


def load_fonts():
    """Registra as fontes da pasta assets/fonts (só vale pro MelbyTune, não instala nada no Windows)."""
    for path in glob.glob(resource("assets/fonts/*.ttf")):
        try:
            ctk.FontManager.load_font(path)
        except Exception:
            pass


# --------------------------------------------------------------------- botões
_STYLES = {
    "primary": dict(fg_color=PURPLE, hover_color=PURPLE_H, text_color="#FFFFFF"),
    "purple": dict(fg_color=PURPLE, hover_color=PURPLE_H, text_color="#FFFFFF"),
    "accent": dict(fg_color=HONEY, hover_color=HONEY_H, text_color="#111116"),
    "ghost": dict(fg_color=PANEL2, hover_color="#363552", text_color=TEXT),
    "outline": dict(fg_color="transparent", hover_color=PANEL2, text_color=TEXT, border_width=1, border_color=BORDER),
    "danger": dict(fg_color=DANGER, hover_color=DANGER_H, text_color="#FFFFFF"),
}


def button(parent, text, command=None, kind="ghost", **kw):
    opts = dict(_STYLES[kind])
    opts.update(kw)
    height = opts.pop("height", 34)
    font = opts.pop("font", (FONT, 13, "bold"))
    return ctk.CTkButton(parent, text=text, command=command, corner_radius=8, height=height, font=font, **opts)


def title(page, text, sub=""):
    ctk.CTkLabel(page, text=text, font=(FONT_TITLE, 26, "bold"), text_color=TEXT).pack(
        anchor="w", padx=24, pady=(22, 0))
    if sub:
        ctk.CTkLabel(page, text=sub, text_color=MUTED, wraplength=780, justify="left",
                     font=(FONT, 13)).pack(anchor="w", padx=24, pady=(2, 10))


def card(parent, **kw):
    return ctk.CTkFrame(parent, fg_color=PANEL, corner_radius=14, border_width=1, border_color=BORDER, **kw)


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


# ------------------------------------------------------------------ anel (gauge)
_ring_cache = {}


def ring_image(pct, color, icon=None, size=76, thickness=7, icon_size=26):
    """Anel de progresso com ícone no meio, desenhado em alta resolução e reduzido (borda lisa)."""
    from icons import pil_icon
    pct = 0 if pct is None else max(0, min(100, int(round(pct))))
    key = (pct, color, icon, size, thickness, icon_size)
    if key in _ring_cache:
        return _ring_cache[key]
    k = 4
    big = Image.new("RGBA", (size * k, size * k), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    pad = thickness * k // 2 + 2 * k
    box = (pad, pad, size * k - pad, size * k - pad)
    d.arc(box, 0, 360, fill=PANEL2, width=thickness * k)
    if pct > 0:
        d.arc(box, -90, -90 + 360 * pct / 100, fill=color, width=thickness * k)
        # pontas arredondadas
        r = thickness * k / 2
        cx, cy = size * k / 2, size * k / 2
        rad = (size * k - 2 * pad) / 2
        import math
        for ang in ((-90, -90 + 360 * pct / 100) if pct >= 8 else (-90,)):
            x = cx + rad * math.cos(math.radians(ang))
            y = cy + rad * math.sin(math.radians(ang))
            d.ellipse((x - r, y - r, x + r, y + r), fill=color)
    px = size * 2  # 2x: nítido em tela com zoom; o CTkImage exibe no tamanho pedido
    img = big.resize((px, px), Image.LANCZOS)
    if icon:
        ic = pil_icon(icon, color, icon_size * 2)
        img.alpha_composite(ic, ((px - icon_size * 2) // 2, (px - icon_size * 2) // 2))
    out = ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
    if len(_ring_cache) > 400:
        _ring_cache.clear()
    _ring_cache[key] = out
    return out
