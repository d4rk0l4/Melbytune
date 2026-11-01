"""Ícones (Lucide, licença ISC) em PNG branco; aqui eles são pintados na cor que o app precisar."""
import customtkinter as ctk
from PIL import Image

from theme import resource

_pil = {}
_ctk = {}


def pil_icon(name, color="#FFFFFF", size=20):
    key = (name, color, size)
    if key not in _pil:
        try:
            base = Image.open(resource(f"assets/icons/{name}.png")).convert("RGBA")
        except OSError:  # ícone faltando: quadradinho vazio, o app continua
            base = Image.new("RGBA", (96, 96), (0, 0, 0, 0))
        solid = Image.new("RGBA", base.size, color)
        solid.putalpha(base.getchannel("A"))
        _pil[key] = solid.resize((size, size), Image.LANCZOS)
    return _pil[key]


def icon(name, color="#FFFFFF", size=20):
    key = (name, color, size)
    if key not in _ctk:
        img = pil_icon(name, color, size * 2)  # 2x: fica nítido em tela com zoom 125%/150%
        _ctk[key] = ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
    return _ctk[key]
