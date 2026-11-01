"""Configurações: ponto de restauração, desfazer tudo e sobre."""
import tkinter.messagebox as mb

import customtkinter as ctk

import tweaks
from theme import APP_VERSION, FONT, MUTED, TEXT, button, card, in_thread, title


class SettingsPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        title(self, "Configurações", "Segurança do app e como desfazer o que ele fez.")
        c1 = card(self)
        c1.pack(fill="x", padx=24, pady=6)
        ctk.CTkLabel(c1, text="Ponto de restauração", font=(FONT, 15, "bold"), text_color=TEXT).pack(
            anchor="w", padx=16, pady=(12, 0))
        ctk.CTkLabel(c1, text="Crie antes de aplicar ajustes. O Windows limita a 1 ponto a cada 24h "
                              "e precisa da Proteção do Sistema ligada.", text_color=MUTED,
                     wraplength=700, justify="left").pack(anchor="w", padx=16)
        button(c1, "Criar ponto de restauração", self.restore_point, kind="primary").pack(
            anchor="w", padx=16, pady=12)
        c2 = card(self)
        c2.pack(fill="x", padx=24, pady=6)
        ctk.CTkLabel(c2, text="Desfazer tudo", font=(FONT, 15, "bold"), text_color=TEXT).pack(
            anchor="w", padx=16, pady=(12, 0))
        ctk.CTkLabel(c2, text="Volta todos os ajustes e o plano de energia ao que era antes do MelbyTune. "
                              "(Não reinstala apps do Debloat nem religa a inicialização: use as abas deles.)",
                     text_color=MUTED, wraplength=700, justify="left").pack(anchor="w", padx=16)
        button(c2, "Restaurar tudo", self.revert_all, kind="danger").pack(anchor="w", padx=16, pady=12)
        c3 = card(self)
        c3.pack(fill="x", padx=24, pady=6)
        ctk.CTkLabel(c3, text=f"MelbyTune {APP_VERSION}", font=(FONT, 15, "bold"), text_color=TEXT).pack(
            anchor="w", padx=16, pady=(12, 0))
        ctk.CTkLabel(c3, text="Seu PC. Seu ritmo.  ·  Uso pessoal, sem venda.  ·  Ícones: Lucide (ISC).  "
                              "Fontes: Exo 2 e Inter (SIL OFL).", text_color=MUTED).pack(
            anchor="w", padx=16, pady=(0, 12))

    def restore_point(self):
        def work():
            ok, msg = tweaks.create_restore_point()
            text = "Ponto de restauração criado." if ok else f"Não foi possível criar:\n{msg}"
            self.after(0, lambda: mb.showinfo("MelbyTune", text))
        in_thread(work)

    def revert_all(self):
        if not mb.askyesno("MelbyTune", "Desfazer todos os ajustes feitos pelo MelbyTune?"):
            return
        tweaks.revert_all()
        mb.showinfo("MelbyTune", "Tudo restaurado. Reabra o app pra atualizar as chaves.")
