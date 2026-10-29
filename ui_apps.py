"""Aba Instalar apps: marca vários e instala tudo de uma vez pelo winget."""
import tkinter.messagebox as mb

import customtkinter as ctk

import installer
from theme import (HONEY, MUTED, PANEL, PURPLE, PURPLE_H, TEXT, FONT, LogBox, button, in_thread, title)


class AppsPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        title(self, "Instalar apps",
              "Marque o que quiser e instale tudo de uma vez, sem abrir site nem clicar em 'avançar'. "
              "Usa o winget (da própria Microsoft).")
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=24)
        self.btn_install = button(bar, "Instalar selecionados", self.install_selected, kind="primary")
        self.btn_install.pack(side="left")
        self.btn_upgrade = button(bar, "Atualizar todos os apps", self.upgrade_all)
        self.btn_upgrade.pack(side="left", padx=8)
        button(bar, "Atualizar lista", self.refresh).pack(side="left")
        self.status = ctk.CTkLabel(bar, text="", text_color=MUTED)
        self.status.pack(side="left", padx=12)

        self.box = ctk.CTkScrollableFrame(self, fg_color=PANEL)
        self.box.pack(fill="both", expand=True, padx=24, pady=(12, 6))
        self.log = LogBox(self, height=130)
        self.log.pack(fill="x", padx=24, pady=(0, 14))

        self.vars = {}
        self.checks = {}
        self.busy = False
        self.build_list()
        if installer.has_winget():
            self.after(400, self.refresh)
        else:
            self.status.configure(text="winget não encontrado")
            self.log.write("O winget não está neste PC. Abra a Microsoft Store e atualize o 'Instalador de Aplicativo' "
                           "(App Installer). Depois reabra o MelbyTune.")

    def build_list(self):
        for cat, apps in installer.CATALOG.items():
            ctk.CTkLabel(self.box, text=cat.upper(), text_color=HONEY,
                         font=("Consolas", 12, "bold")).pack(anchor="w", padx=10, pady=(14, 2))
            grid = ctk.CTkFrame(self.box, fg_color="transparent")
            grid.pack(fill="x", padx=6)
            grid.grid_columnconfigure((0, 1), weight=1)
            for i, (pid, name) in enumerate(apps):
                var = ctk.BooleanVar(value=False)
                cb = ctk.CTkCheckBox(grid, text=name, variable=var, fg_color=PURPLE, hover_color=PURPLE_H,
                                     checkmark_color="#FFFFFF", text_color=TEXT)
                cb.grid(row=i // 2, column=i % 2, sticky="w", padx=8, pady=5)
                self.vars[pid] = var
                self.checks[pid] = (cb, name)

    def refresh(self):
        self.status.configure(text="Lendo o que já está instalado...")

        def work():
            have = installer.installed_ids()
            self.after(0, lambda: self.mark_installed(have))
        in_thread(work)

    def mark_installed(self, have):
        for pid, (cb, name) in self.checks.items():
            if pid in have:
                cb.configure(text=f"{name}  ✔ instalado")
                self.vars[pid].set(False)
                cb.configure(state="disabled")
            else:
                cb.configure(text=name, state="normal")
        self.status.configure(text=f"{len(have)} do catálogo já instalados")

    def set_busy(self, busy):
        self.busy = busy
        st = "disabled" if busy else "normal"
        self.btn_install.configure(state=st)
        self.btn_upgrade.configure(state=st)

    def install_selected(self):
        chosen = [pid for pid, v in self.vars.items() if v.get()]
        if not installer.has_winget():
            mb.showerror("MelbyTune", "O winget não está instalado neste PC.")
            return
        if not chosen:
            mb.showinfo("MelbyTune", "Marque pelo menos um app.")
            return
        if not mb.askyesno("MelbyTune", f"Instalar {len(chosen)} app(s)? Pode levar alguns minutos. "
                                        "Não feche o MelbyTune enquanto instala."):
            return
        self.set_busy(True)
        self.log.clear()

        def work():
            names = {pid: n for pid, (_, n) in self.checks.items()}
            good = 0
            for i, pid in enumerate(chosen, 1):
                self.after(0, lambda i=i: self.status.configure(text=f"Instalando {i}/{len(chosen)}..."))
                self.log.write(f"[{i}/{len(chosen)}] {names[pid]}...", newline=False)
                ok, msg = installer.install(pid)
                good += ok
                self.log.write(f" {'✔' if ok else '✘'} {msg}")
            self.log.write(f"\nPronto: {good} de {len(chosen)} ok.")
            have = installer.installed_ids()
            self.after(0, lambda: (self.mark_installed(have), self.set_busy(False)))
        in_thread(work)

    def upgrade_all(self):
        if not installer.has_winget():
            mb.showerror("MelbyTune", "O winget não está instalado neste PC.")
            return
        if not mb.askyesno("MelbyTune", "Atualizar todos os apps que têm versão nova? Pode demorar."):
            return
        self.set_busy(True)
        self.log.clear()
        self.log.write("Atualizando apps... (sem barra de progresso, aguarde)")
        self.status.configure(text="Atualizando...")

        def work():
            try:
                ok = installer.upgrade_all()
            except Exception as e:
                self.log.write(f"Erro: {e}")
                ok = False
            self.log.write("✔ Terminou." if ok else "Terminou, mas alguns apps não atualizaram "
                                                   "(normal se estavam abertos).")
            self.after(0, lambda: (self.status.configure(text=""), self.set_busy(False)))
        in_thread(work)
