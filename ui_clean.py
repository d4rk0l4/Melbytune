"""Aba Limpeza: temporários, arquivos duplicados e arquivos grandes."""
import os
import subprocess
import threading
import tkinter.messagebox as mb
from tkinter import filedialog

import customtkinter as ctk

import cleaner
import dupes
from theme import (HONEY, MUTED, PANEL, PANEL2, PURPLE, PURPLE_H, TEXT, FONT, LogBox,
                   button, in_thread, short, tabs, title)

SIZES = {"100 KB": 100 * 1024, "1 MB": 1 << 20, "10 MB": 10 << 20}
MAX_GROUPS = 150


def default_folders():
    home = os.path.expanduser("~")
    bases = [home] + ([os.environ["OneDrive"]] if os.environ.get("OneDrive") else [])
    names = ["Downloads", "Documents", "Documentos", "Pictures", "Imagens", "Videos", "Vídeos",
             "Music", "Músicas", "Desktop", "Área de Trabalho"]
    out = []
    for b in bases:
        for n in names:
            p = os.path.join(b, n)
            if os.path.isdir(p) and p not in out:
                out.append(p)
    return out or [home]


def open_location(path):
    try:
        if os.name == "nt":
            subprocess.Popen(["explorer", "/select,", path])
        else:
            subprocess.Popen(["xdg-open", os.path.dirname(path)])
    except OSError:
        pass


def _seg(parent, values, default):
    s = ctk.CTkSegmentedButton(parent, values=values, selected_color=PURPLE, selected_hover_color=PURPLE_H,
                               unselected_color=PANEL2, unselected_hover_color="#363552", text_color=TEXT)
    s.set(default)
    return s


class CleanPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        title(self, "Limpeza", "Libere espaço: arquivos temporários, duplicados e os maiores arquivos do PC.")
        tv = tabs(self, ["Temporários", "Duplicados", "Arquivos grandes"])
        tv.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        self._temp(tv.tab("Temporários"))
        self._dups(tv.tab("Duplicados"))
        self._big(tv.tab("Arquivos grandes"))

    # ------------------------------------------------------------ temporários
    def _temp(self, tab):
        ctk.CTkLabel(tab, text="Apaga só arquivos temporários que o Windows recria sozinho. "
                               "O que estiver em uso é ignorado.", text_color=MUTED).pack(anchor="w", pady=(4, 6))
        bar = ctk.CTkFrame(tab, fg_color="transparent")
        bar.pack(fill="x")
        button(bar, "Analisar", self.scan_temp).pack(side="left")
        self.btn_clean = button(bar, "Limpar agora", self.clean_temp, kind="primary", state="disabled")
        self.btn_clean.pack(side="left", padx=10)
        self.temp_out = LogBox(tab)
        self.temp_out.pack(fill="both", expand=True, pady=10)
        self.temp_out.write("Clique em Analisar pra ver quanto espaço dá pra liberar.")

    def scan_temp(self):
        self.temp_out.clear()
        self.temp_out.write("Analisando...")

        def work():
            res = cleaner.scan()
            total = sum(r[2] for r in res)
            lines = [f"{n:<34}{cleaner.fmt(s):>10}" for n, _, s in res]
            lines += ["-" * 44, f"{'Total':<34}{cleaner.fmt(total):>10}", "", "A lixeira também será esvaziada."]
            self.temp_out.clear()
            self.temp_out.write("\n".join(lines))
            self.after(0, lambda: self.btn_clean.configure(state="normal"))
        in_thread(work)

    def clean_temp(self):
        if not mb.askyesno("MelbyTune", "Apagar os arquivos temporários listados e esvaziar a lixeira?"):
            return
        self.btn_clean.configure(state="disabled")
        self.temp_out.clear()
        self.temp_out.write("Limpando...")

        def work():
            freed = sum(cleaner.clean_folder(p) for _, p, _ in cleaner.scan())
            cleaner.empty_recycle_bin()
            self.temp_out.clear()
            self.temp_out.write(f"Pronto. Liberado: {cleaner.fmt(freed)} (fora a lixeira).")
        in_thread(work)

    # -------------------------------------------------------------- duplicados
    def _dups(self, tab):
        self.dup_roots = default_folders()
        self.dup_stop = threading.Event()
        self.dup_groups = []
        ctk.CTkLabel(tab, text="Acha arquivos com exatamente o mesmo conteúdo. Os marcados vão pra Lixeira "
                               "(dá pra restaurar) e o mais antigo de cada grupo fica.",
                     text_color=MUTED, wraplength=760, justify="left").pack(anchor="w", pady=(4, 6))
        top = ctk.CTkFrame(tab, fg_color="transparent")
        top.pack(fill="x")
        button(top, "Pastas padrão", self.dup_default).pack(side="left")
        button(top, "Escolher pasta...", self.dup_choose).pack(side="left", padx=8)
        self.dup_where = ctk.CTkLabel(top, text="", text_color=MUTED)
        self.dup_where.pack(side="left", padx=8)
        row = ctk.CTkFrame(tab, fg_color="transparent")
        row.pack(fill="x", pady=8)
        ctk.CTkLabel(row, text="Ignorar menores que", text_color=MUTED).pack(side="left")
        self.dup_size = _seg(row, list(SIZES), "1 MB")
        self.dup_size.pack(side="left", padx=10)
        self.btn_dup_scan = button(row, "Procurar duplicados", self.dup_scan, kind="primary")
        self.btn_dup_scan.pack(side="left", padx=6)
        button(row, "Parar", lambda: self.dup_stop.set()).pack(side="left")
        self.dup_status = ctk.CTkLabel(tab, text="", text_color=MUTED)
        self.dup_status.pack(anchor="w")
        self.dup_list = ctk.CTkScrollableFrame(tab, fg_color=PANEL)
        self.dup_list.pack(fill="both", expand=True, pady=6)
        bottom = ctk.CTkFrame(tab, fg_color="transparent")
        bottom.pack(fill="x")
        self.dup_sum = ctk.CTkLabel(bottom, text="", text_color=TEXT)
        self.dup_sum.pack(side="left")
        self.btn_dup_trash = button(bottom, "Mandar marcados pra Lixeira", self.dup_trash, kind="danger",
                                    state="disabled")
        self.btn_dup_trash.pack(side="right")
        self.dup_default()

    def dup_default(self):
        self.dup_roots = default_folders()
        self.dup_where.configure(text=f"{len(self.dup_roots)} pasta(s) padrão (Downloads, Documentos, Imagens...)")

    def dup_choose(self):
        d = filedialog.askdirectory(title="Escolha a pasta")
        if d:
            self.dup_roots = [d]
            self.dup_where.configure(text=short(d, 55))

    def dup_scan(self):
        min_size = SIZES[self.dup_size.get()]
        self.dup_stop = stop = threading.Event()
        self.btn_dup_scan.configure(state="disabled")
        self.dup_status.configure(text="Procurando...")

        def prog(msg):
            self.after(0, lambda: self.dup_status.configure(text=msg))

        def work():
            try:
                groups = dupes.find_duplicates(self.dup_roots, min_size, prog, stop)
            except Exception as ex:
                groups = []
                err = str(ex)
                self.after(0, lambda: mb.showerror("MelbyTune", err))
            self.after(0, lambda: self.dup_show(groups, stop.is_set()))
        in_thread(work)

    def dup_show(self, groups, stopped):
        for w in self.dup_list.winfo_children():
            w.destroy()
        self.dup_groups = []
        self.btn_dup_scan.configure(state="normal")
        if not groups:
            self.dup_status.configure(text="Nenhum duplicado encontrado." + (" (busca interrompida)" if stopped else ""))
            self.dup_update()
            return
        wasted = sum(g["size"] * (len(g["files"]) - 1) for g in groups)
        extra = f" · mostrando os {MAX_GROUPS} maiores" if len(groups) > MAX_GROUPS else ""
        self.dup_status.configure(
            text=f"{len(groups)} grupos · {cleaner.fmt(wasted)} em cópias{extra}"
                 + (" · busca interrompida" if stopped else ""))
        for g in groups[:MAX_GROUPS]:
            box = ctk.CTkFrame(self.dup_list, fg_color=PANEL2, corner_radius=8)
            box.pack(fill="x", padx=4, pady=5)
            ctk.CTkLabel(box, text=f"{len(g['files'])} cópias · {cleaner.fmt(g['size'])} cada",
                         font=(FONT, 13, "bold"), text_color=HONEY).pack(anchor="w", padx=10, pady=(6, 0))
            items = []
            for i, (p, _) in enumerate(g["files"]):
                var = ctk.BooleanVar(value=i > 0)
                ctk.CTkCheckBox(box, text=short(p, 82) + ("   ← mais antigo (fica)" if i == 0 else ""),
                                variable=var, command=self.dup_update, fg_color=PURPLE, hover_color=PURPLE_H,
                                checkmark_color="#FFFFFF", text_color=TEXT).pack(anchor="w", padx=10, pady=2)
                items.append((p, var))
            self.dup_groups.append((g["size"], items))
        self.dup_update()

    def dup_update(self):
        n = sum(1 for _, items in self.dup_groups for _, v in items if v.get())
        size = sum(s for s, items in self.dup_groups for _, v in items if v.get())
        self.dup_sum.configure(text=f"{n} marcados · libera {cleaner.fmt(size)}" if n else "")
        self.btn_dup_trash.configure(state="normal" if n else "disabled")

    def dup_trash(self):
        todo, skipped = [], 0
        for _, items in self.dup_groups:
            marked = [p for p, v in items if v.get()]
            if len(marked) == len(items):  # nunca apaga todas as cópias
                skipped += 1
                continue
            todo += marked
        if not todo:
            mb.showinfo("MelbyTune", "Em cada grupo, deixe pelo menos uma cópia sem marcar.")
            return
        if not mb.askyesno("MelbyTune", f"Mandar {len(todo)} arquivo(s) pra Lixeira?"
                                        + (f"\n\n{skipped} grupo(s) com tudo marcado foram ignorados." if skipped else "")):
            return
        self.btn_dup_trash.configure(state="disabled")
        self.dup_status.configure(text="Enviando pra Lixeira...")

        def work():
            sent, fails = dupes.recycle(todo)
            msg = f"{sent} arquivo(s) na Lixeira." + (f" {len(fails)} falharam." if fails else "")
            self.after(0, lambda: (self.dup_status.configure(text=msg), mb.showinfo("MelbyTune", msg)))
        in_thread(work)

    # --------------------------------------------------------- arquivos grandes
    def _big(self, tab):
        self.big_root = os.path.expanduser("~")
        self.big_stop = threading.Event()
        ctk.CTkLabel(tab, text="Mostra os maiores arquivos de uma pasta pra você decidir o que apagar.",
                     text_color=MUTED).pack(anchor="w", pady=(4, 6))
        top = ctk.CTkFrame(tab, fg_color="transparent")
        top.pack(fill="x")
        button(top, "Escolher pasta...", self.big_choose).pack(side="left")
        self.big_where = ctk.CTkLabel(top, text=short(self.big_root, 55), text_color=MUTED)
        self.big_where.pack(side="left", padx=10)
        self.btn_big = button(top, "Procurar", self.big_scan, kind="primary")
        self.btn_big.pack(side="left", padx=6)
        button(top, "Parar", lambda: self.big_stop.set()).pack(side="left")
        self.big_status = ctk.CTkLabel(tab, text="", text_color=MUTED)
        self.big_status.pack(anchor="w", pady=(8, 0))
        self.big_list = ctk.CTkScrollableFrame(tab, fg_color=PANEL)
        self.big_list.pack(fill="both", expand=True, pady=6)

    def big_choose(self):
        d = filedialog.askdirectory(title="Escolha a pasta")
        if d:
            self.big_root = d
            self.big_where.configure(text=short(d, 55))

    def big_scan(self):
        self.big_stop = stop = threading.Event()
        self.btn_big.configure(state="disabled")
        self.big_status.configure(text="Procurando...")

        def prog(msg):
            self.after(0, lambda: self.big_status.configure(text=msg))

        def work():
            try:
                res = dupes.biggest(self.big_root, 40, prog, stop)
            except Exception:
                res = []
            self.after(0, lambda: self.big_show(res))
        in_thread(work)

    def big_show(self, res):
        for w in self.big_list.winfo_children():
            w.destroy()
        self.btn_big.configure(state="normal")
        self.big_status.configure(text=f"{len(res)} maiores arquivos" if res else "Nada encontrado.")
        for size, path in res:
            row = ctk.CTkFrame(self.big_list, fg_color="transparent")
            row.pack(fill="x", pady=3, padx=4)
            ctk.CTkLabel(row, text=cleaner.fmt(size), width=80, anchor="e", font=(FONT, 13, "bold"),
                         text_color=HONEY).pack(side="left")
            ctk.CTkLabel(row, text=short(path, 70), anchor="w", text_color=TEXT).pack(side="left", padx=10)
            button(row, "Lixeira", lambda p=path, r=row: self.big_trash(p, r), kind="danger",
                   width=70, height=28).pack(side="right", padx=(6, 4))
            button(row, "Abrir local", lambda p=path: open_location(p), width=90, height=28).pack(side="right")

    def big_trash(self, path, row):
        if not mb.askyesno("MelbyTune", f"Mandar pra Lixeira?\n\n{path}"):
            return

        def work():
            sent, _ = dupes.recycle([path])
            if sent:
                self.after(0, row.destroy)
            else:
                self.after(0, lambda: mb.showerror("MelbyTune", "Não consegui mandar pra Lixeira."))
        in_thread(work)
