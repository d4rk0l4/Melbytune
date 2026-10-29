"""Aba Inicialização: liga/desliga os programas que abrem junto com o Windows."""
import tkinter.messagebox as mb

import customtkinter as ctk

import startup
from theme import MUTED, PANEL, PURPLE, PURPLE_H, TEXT, FONT, button, title


class StartupPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        title(self, "Inicialização",
              "Programas que abrem sozinhos quando o Windows liga. Desligar os que você não usa faz o "
              "PC ligar mais rápido. Dá pra religar quando quiser (é a mesma chave do Gerenciador de Tarefas).")
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=24)
        button(bar, "Atualizar lista", self.refresh).pack(side="left")
        self.count = ctk.CTkLabel(bar, text="", text_color=MUTED)
        self.count.pack(side="left", padx=14)
        self.box = ctk.CTkScrollableFrame(self, fg_color=PANEL)
        self.box.pack(fill="both", expand=True, padx=24, pady=14)
        self.refresh()

    def refresh(self):
        for w in self.box.winfo_children():
            w.destroy()
        try:
            entries = startup.list_entries()
        except Exception:
            entries = []
        if not entries:
            ctk.CTkLabel(self.box, text="Nenhum programa de inicialização encontrado.",
                         text_color=MUTED).pack(pady=20)
        for e in entries:
            row = ctk.CTkFrame(self.box, fg_color="transparent")
            row.pack(fill="x", pady=4, padx=4)
            var = ctk.BooleanVar(value=e.enabled)
            ctk.CTkSwitch(row, text="", width=44, variable=var, progress_color=PURPLE,
                          command=lambda e=e, v=var: self.toggle(e, v)).pack(side="left", padx=(8, 6))
            info = ctk.CTkFrame(row, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(info, text=e.name, font=(FONT, 14, "bold"), text_color=TEXT, anchor="w").pack(anchor="w")
            cmd = e.command if len(e.command) < 95 else e.command[:92] + "..."
            ctk.CTkLabel(info, text=f"{e.source}  ·  {cmd}", text_color=MUTED, anchor="w").pack(anchor="w")
        on = sum(1 for e in entries if e.enabled)
        self.count.configure(text=f"{on} ligados de {len(entries)}" if entries else "")

    def toggle(self, entry, var):
        try:
            startup.set_enabled(entry, var.get())
        except Exception as ex:
            var.set(not var.get())
            mb.showerror("MelbyTune", f"Não foi possível alterar '{entry.name}'.\n\n{ex}")
            return
        self.refresh_count()

    def refresh_count(self):
        try:
            entries = startup.list_entries()
            self.count.configure(text=f"{sum(1 for e in entries if e.enabled)} ligados de {len(entries)}")
        except Exception:
            pass
