"""Davi Zone: pacote com 2 botões pro notebook fraco."""
import tkinter.messagebox as mb

import customtkinter as ctk

import davi
import tweaks
from theme import FONT, HONEY, MUTED, PURPLE, TEXT, LogBox, button, card, in_thread, title


class DaviPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        title(self, "Davi Zone", "Pacote pro notebook fraco. Dois botões, sem complicação.")
        c1 = card(self)
        c1.pack(fill="x", padx=24, pady=8)
        self.btn_perf = button(c1, "Tentar melhorar o desempenho", self.perf, kind="primary", height=58,
                               font=(FONT, 18, "bold"))
        self.btn_perf.pack(fill="x", padx=20, pady=(20, 6))
        ctk.CTkLabel(c1, text="não dá pra fazer milagre", font=(FONT, 13, "italic"), text_color=MUTED).pack()
        ctk.CTkLabel(c1, wraplength=700, justify="center", text_color=MUTED,
                     text="Cria ponto de restauração · aplica ajustes leves · limpa temporários · desliga programas "
                          "pesados da inicialização · remove apps inúteis do Windows"
                     ).pack(padx=20, pady=(8, 18))
        c2 = card(self)
        c2.pack(fill="x", padx=24, pady=8)
        self.btn_rp = button(c2, "Gerar ponto de restauração", self.restore_point, kind="purple", height=50,
                             font=(FONT, 16, "bold"))
        self.btn_rp.pack(fill="x", padx=20, pady=20)
        self.log = LogBox(self, height=190)
        self.log.pack(fill="both", expand=True, padx=24, pady=(6, 16))
        self.log.write("O resultado aparece aqui.")

    def set_busy(self, busy):
        st = "disabled" if busy else "normal"
        self.btn_perf.configure(state=st)
        self.btn_rp.configure(state=st)

    def perf(self):
        if not mb.askyesno("MelbyTune", "Vou criar um ponto de restauração e depois melhorar o que dá "
                                        "(ajustes leves, limpeza, inicialização e apps inúteis do Windows).\n\n"
                                        "Pode levar alguns minutos. Continuar?"):
            return
        self.set_busy(True)
        self.log.clear()
        self.log.write("Trabalhando... não feche o app.\n")

        def work():
            try:
                davi.run_pack(self.log.write)
            except Exception as e:
                self.log.write(f"\nDeu erro: {e}")
            self.after(0, lambda: self.set_busy(False))
        in_thread(work)

    def restore_point(self):
        self.set_busy(True)
        self.log.clear()
        self.log.write("Criando ponto de restauração...")

        def work():
            ok, msg = tweaks.create_restore_point()
            self.log.write("✔ Ponto de restauração criado." if ok else
                           f"✘ Não deu: {msg}\n(O Windows só deixa criar 1 a cada 24h, e a Proteção do Sistema "
                           "precisa estar ligada.)")
            self.after(0, lambda: self.set_busy(False))
        in_thread(work)
