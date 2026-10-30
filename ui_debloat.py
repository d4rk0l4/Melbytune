"""Aba Debloat: apps da Store (lista por grupos) + Edge e OneDrive."""
import tkinter.messagebox as mb

import customtkinter as ctk

import debloat
import programs
from theme import (GOOD, HONEY, MUTED, PANEL, PANEL2, PURPLE, PURPLE_H, TEXT, FONT, button, card, in_thread, title)


class DebloatPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        title(self, "Debloat",
              "Tira do PC o que já vem instalado e quase ninguém usa. A lista é conservadora: não inclui Loja, "
              "Calculadora, Fotos, Paint nem Xbox. Só aparece o que existe neste PC.")
        self.busy = False
        self.vars, self.have, self.removed = {}, set(), set()

        # ---- programas grandes
        big = card(self)
        big.pack(fill="x", padx=24, pady=(0, 8))
        self.edge_lbl = self._big_row(
            big, "Microsoft Edge",
            "O navegador do Windows. O Windows pode bloquear a remoção; se bloquear, use o ajuste "
            "'Edge sem rodar em segundo plano'.", self.edge_remove, self.edge_back)
        ctk.CTkFrame(big, height=1, fg_color=PANEL2).pack(fill="x", padx=16)
        self.od_lbl = self._big_row(
            big, "OneDrive", "Sincronização na nuvem da Microsoft. Só remove se suas pastas não estiverem nele.",
            self.od_remove, self.od_back)

        # ---- apps da Store
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=24, pady=(4, 0))
        button(bar, "Atualizar lista", self.refresh).pack(side="left")
        button(bar, "Marcar recomendados", self.mark_rec).pack(side="left", padx=8)
        button(bar, "Desmarcar tudo", self.unmark).pack(side="left")
        self.btn_remove = button(bar, "Remover marcados", lambda: self.action(True), kind="danger")
        self.btn_remove.pack(side="right")
        self.btn_back = button(bar, "Reinstalar marcados", lambda: self.action(False), kind="primary")
        self.btn_back.pack(side="right", padx=8)
        self.status = ctk.CTkLabel(self, text="", text_color=HONEY)
        self.status.pack(anchor="w", padx=24, pady=(6, 0))
        self.box = ctk.CTkScrollableFrame(self, fg_color=PANEL)
        self.box.pack(fill="both", expand=True, padx=24, pady=(6, 14))
        self.after(400, self.refresh)

    # ------------------------------------------------------- programas grandes
    def _big_row(self, parent, name, desc, remove_cmd, back_cmd):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=10)
        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True)
        head = ctk.CTkFrame(info, fg_color="transparent")
        head.pack(anchor="w")
        ctk.CTkLabel(head, text=name, font=(FONT, 15, "bold"), text_color=TEXT).pack(side="left")
        lbl = ctk.CTkLabel(head, text="  verificando...", text_color=MUTED)
        lbl.pack(side="left")
        ctk.CTkLabel(info, text=desc, text_color=MUTED, wraplength=520, justify="left", anchor="w").pack(anchor="w")
        button(row, "Reinstalar", back_cmd, width=90).pack(side="right", padx=(6, 0))
        button(row, f"Remover {name.split()[-1]}", remove_cmd, kind="danger", width=130).pack(side="right")
        return lbl

    def refresh_programs(self):
        def work():
            e, o = programs.edge_installed(), programs.onedrive_installed()
            self.after(0, lambda: (
                self.edge_lbl.configure(text="  ● instalado" if e else "  ○ não está instalado", text_color=TEXT if e else GOOD),
                self.od_lbl.configure(text="  ● instalado" if o else "  ○ não está instalado", text_color=TEXT if o else GOOD)))
        in_thread(work)

    def _run_big(self, label, fn, ask):
        if self.busy:
            return
        if ask and not mb.askyesno("MelbyTune", ask):
            return
        self.busy = True
        self.status.configure(text=f"{label}... pode levar alguns minutos, não feche o app.")

        def work():
            try:
                ok, msg = fn()
            except Exception as e:
                ok, msg = False, str(e)
            def done():
                self.busy = False
                self.status.configure(text="")
                (mb.showinfo if ok else mb.showwarning)("MelbyTune", msg)
                self.refresh_programs()
            self.after(0, done)
        in_thread(work)

    def edge_remove(self):
        self._run_big("Removendo o Edge", programs.edge_remove,
                      "Remover o Microsoft Edge?\n\n"
                      "• Eu confiro antes se existe outro navegador instalado.\n"
                      "• Widgets, busca do Windows e alguns links podem parar de funcionar.\n"
                      "• O Windows Update pode instalar o Edge de novo.\n"
                      "• O WebView2 (usado por vários programas) NÃO é removido.\n\n"
                      "Em alguns PCs o Windows bloqueia a remoção por comando. Continuar?")

    def edge_back(self):
        self._run_big("Reinstalando o Edge", programs.edge_reinstall, "Reinstalar o Microsoft Edge (pelo winget)?")

    def od_remove(self):
        self._run_big("Removendo o OneDrive", programs.onedrive_remove,
                      "Remover o OneDrive?\n\nArquivos que já estão na pasta OneDrive continuam no PC.")

    def od_back(self):
        self._run_big("Reinstalando o OneDrive", programs.onedrive_reinstall, "Reinstalar o OneDrive?")

    # --------------------------------------------------------------- apps Store
    def refresh(self):
        self.status.configure(text="Lendo apps instalados...")
        self.refresh_programs()

        def work():
            have, removed = debloat.installed(), debloat.removed_set()
            self.after(0, lambda: self.render(have, removed))
        in_thread(work)

    def render(self, have, removed):
        self.have, self.removed = have, removed
        for w in self.box.winfo_children():
            w.destroy()
        self.vars = {}
        shown = 0
        for group, items in debloat.GROUPS:
            rows = [(p, l) for p, l, _ in items if debloat.is_installed(p, have) or p.lower() in removed]
            if not rows:
                continue
            ctk.CTkLabel(self.box, text=group.upper(), text_color=HONEY,
                         font=("Consolas", 12, "bold")).pack(anchor="w", padx=10, pady=(12, 2))
            for pkg, label in rows:
                row = ctk.CTkFrame(self.box, fg_color="transparent")
                row.pack(fill="x", pady=1)
                var = ctk.BooleanVar(value=False)
                self.vars[pkg] = var
                ctk.CTkCheckBox(row, text=label, variable=var, fg_color=PURPLE, hover_color=PURPLE_H,
                                checkmark_color="#FFFFFF", text_color=TEXT).pack(side="left", padx=8, pady=3)
                on = debloat.is_installed(pkg, have)
                ctk.CTkLabel(row, text="instalado" if on else "removido por você",
                             text_color=TEXT if on else MUTED).pack(side="right", padx=12)
                shown += 1
        if not shown:
            ctk.CTkLabel(self.box, text="Nada da lista está instalado neste PC. Tudo limpo!", text_color=MUTED).pack(pady=20)
        self.status.configure(text=f"{shown} itens" if shown else "")

    def mark_rec(self):
        for pkg, var in self.vars.items():
            var.set(pkg in debloat.RECOMMENDED and debloat.is_installed(pkg, self.have))

    def unmark(self):
        for var in self.vars.values():
            var.set(False)

    def action(self, remove):
        if self.busy:
            return
        marked = [p for p, v in self.vars.items()
                  if v.get() and debloat.is_installed(p, self.have) == remove]
        if not marked:
            mb.showinfo("MelbyTune", "Marque apps " + ("instalados" if remove else "já removidos por você") + " primeiro.")
            return
        verbo = "Remover" if remove else "Reinstalar"
        if not mb.askyesno("MelbyTune", f"{verbo} {len(marked)} app(s)? Isso pode levar alguns minutos."
                           + ("\n\nPra voltar um app depois, use 'Reinstalar' ou a Microsoft Store." if remove else "")):
            return
        self.busy = True
        self.status.configure(text="Trabalhando... não feche o app.")

        def work():
            fails = []
            for pkg in marked:
                ok, _ = (debloat.remove if remove else debloat.reinstall)(pkg)
                if not ok:
                    fails.append(pkg)
            have, removed = debloat.installed(), debloat.removed_set()

            def done():
                self.busy = False
                self.render(have, removed)
                if fails:
                    self.status.configure(text=f"{len(marked) - len(fails)} ok, {len(fails)} falharam.")
            self.after(0, done)
        in_thread(work)
