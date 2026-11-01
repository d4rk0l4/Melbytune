"""Página de ajustes do Windows (liga/desliga, reversível). Serve pra Otimização e Desempenho."""
import tkinter.messagebox as mb

import customtkinter as ctk

import tweaks
from theme import FONT, HONEY, MUTED, PANEL, PURPLE, TEXT, button, card, title

CATEGORY_NOTES = {
    "Input lag": "Reduzem atrasos entre o clique/tecla e a imagem. O efeito é pequeno e varia de PC pra PC.",
}


def _safe(fn, *a):
    try:
        return fn(*a)
    except Exception:
        return False


class TweaksPage(ctk.CTkFrame):
    def __init__(self, parent, heading, sub, categories, power=False):
        super().__init__(parent, fg_color="transparent")
        title(self, heading, sub)
        sc = ctk.CTkScrollableFrame(self, fg_color="transparent")
        sc.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        if power:
            self._power_card(sc)
        for cat in categories:
            items = [t for t in tweaks.TWEAKS if t.category == cat]
            if not items:
                continue
            ctk.CTkLabel(sc, text=cat.upper(), text_color=HONEY, font=("Consolas", 12, "bold")).pack(
                anchor="w", padx=12, pady=(14, 0))
            if cat in CATEGORY_NOTES:
                ctk.CTkLabel(sc, text=CATEGORY_NOTES[cat], text_color=MUTED).pack(anchor="w", padx=12)
            for t in items:
                self._row(sc, t)

    def _row(self, sc, t):
        row = card(sc)
        row.pack(fill="x", padx=8, pady=4)
        var = ctk.BooleanVar(value=_safe(tweaks.is_applied, t))
        ctk.CTkSwitch(row, text="", width=44, variable=var, progress_color=PURPLE,
                      command=lambda t=t, v=var: self.toggle(t, v)).pack(side="left", padx=(14, 6), pady=14)
        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, pady=8)
        ctk.CTkLabel(info, text=t.name, font=(FONT, 14, "bold"), anchor="w", text_color=TEXT).pack(anchor="w")
        ctk.CTkLabel(info, text=t.desc + (f"  ⚠ {t.note}" if t.note else ""), text_color=MUTED,
                     wraplength=560, justify="left", anchor="w").pack(anchor="w")
        button(row, "Ver comando", lambda t=t: self.show_cmd(t), width=100).pack(side="right", padx=14)

    def _power_card(self, sc):
        c = card(sc)
        c.pack(fill="x", padx=8, pady=(6, 4))
        self.power_var = ctk.BooleanVar(value=_safe(tweaks.power_applied))
        ctk.CTkSwitch(c, text="", width=44, variable=self.power_var, progress_color=PURPLE,
                      command=self.toggle_power).pack(side="left", padx=(14, 6), pady=14)
        info = ctk.CTkFrame(c, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, pady=8)
        ctk.CTkLabel(info, text="Plano de energia de alto desempenho", font=(FONT, 14, "bold"),
                     text_color=TEXT).pack(anchor="w")
        ctk.CTkLabel(info, text="Ativa o plano Desempenho Máximo. Desligar volta pro plano que estava antes. "
                                "Em notebook, gasta mais bateria.", text_color=MUTED, wraplength=560,
                     justify="left").pack(anchor="w")

    def toggle(self, t, var):
        try:
            tweaks.apply(t) if var.get() else tweaks.revert(t)
        except Exception as e:
            var.set(not var.get())
            mb.showerror("MelbyTune", f"Não foi possível alterar '{t.name}'.\n\n{e}")

    def toggle_power(self):
        try:
            tweaks.power_apply() if self.power_var.get() else tweaks.power_revert()
        except Exception as e:
            self.power_var.set(not self.power_var.get())
            mb.showerror("MelbyTune", str(e))

    def show_cmd(self, t):
        win = ctk.CTkToplevel(self)
        win.title(t.name)
        win.geometry("760x260")
        win.attributes("-topmost", True)
        box = ctk.CTkTextbox(win, font=("Consolas", 12), fg_color=PANEL)
        box.pack(fill="both", expand=True, padx=12, pady=12)
        box.insert("1.0", tweaks.preview(t) + "\n\n# Desfazer: desligue a chave (restaura o valor original salvo).")
        box.configure(state="disabled")
