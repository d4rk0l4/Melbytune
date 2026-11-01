"""Ferramentas > "Rodo esse jogo?": escaneia o PC e compara com os requisitos do jogo escolhido."""
import customtkinter as ctk

import gamecheck
from icons import icon
from theme import (BAD, FONT, GOOD, HONEY, MUTED, PANEL2, PURPLE, TEXT, button, card, in_thread)

LEVEL_COLOR = {"great": GOOD, "ok": HONEY, "no": BAD, "unknown": MUTED}
LEVEL_ICON = {"great": "circle-check-big", "ok": "triangle-alert", "no": "circle-x", "unknown": "info"}
STATUS = {"ok": ("Atende", GOOD), "min": ("Só o mínimo", HONEY), "low": ("Abaixo", BAD), "unknown": ("?", MUTED)}


class GameTab:
    def __init__(self, tab, app):
        self.app = app
        self.hw = None
        self.tab = tab
        sc = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        sc.pack(fill="both", expand=True)
        self.sc = sc

        c = card(sc)
        c.pack(fill="x", padx=6, pady=(6, 4))
        top = ctk.CTkFrame(c, fg_color="transparent")
        top.pack(fill="x", padx=14, pady=(12, 4))
        ctk.CTkLabel(top, text="", image=icon("scan-search", PURPLE, 24)).pack(side="left")
        ctk.CTkLabel(top, text="Seu PC", font=(FONT, 15, "bold"), text_color=TEXT).pack(side="left", padx=8)
        self.btn_scan = button(top, "Escanear meu PC", self.scan, kind="primary", width=150)
        self.btn_scan.pack(side="right")
        self.pc_lbl = ctk.CTkLabel(c, text="Clique em Escanear pra descobrir seus componentes.",
                                   text_color=MUTED, justify="left", wraplength=720, anchor="w")
        self.pc_lbl.pack(fill="x", padx=16, pady=(0, 12))

        s = card(sc)
        s.pack(fill="x", padx=6, pady=4)
        ctk.CTkLabel(s, text="Qual jogo?", font=(FONT, 15, "bold"), text_color=TEXT).pack(
            anchor="w", padx=16, pady=(12, 4))
        row = ctk.CTkFrame(s, fg_color="transparent")
        row.pack(fill="x", padx=16)
        self.entry = ctk.CTkEntry(row, placeholder_text="Ex.: GTA V, Valorant, Elden Ring, Cyberpunk...",
                                  height=36, fg_color=PANEL2, border_width=0)
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", lambda e: self.search())
        button(row, "Buscar", self.search, kind="purple", width=90, height=36).pack(side="left", padx=(8, 0))
        self.hint = ctk.CTkLabel(s, text="Jogos populares ficam salvos no app; qualquer outro é buscado na Steam "
                                         "(precisa de internet).", text_color=MUTED, font=(FONT, 11))
        self.hint.pack(anchor="w", padx=16, pady=(4, 4))
        self.results = ctk.CTkFrame(s, fg_color="transparent")
        self.results.pack(fill="x", padx=16, pady=(0, 12))

        self.out = ctk.CTkFrame(sc, fg_color="transparent")
        self.out.pack(fill="x", padx=6, pady=4)
        self.show_popular()

    # --------------------------------------------------------------- PC
    def scan(self):
        self.btn_scan.configure(state="disabled", text="Escaneando...")
        self.app.rescan(self.on_scan)

    def on_scan(self, scan):
        self.btn_scan.configure(state="normal", text="Escanear de novo")
        self.hw = gamecheck.hw_from_scan(scan)
        g = scan.get("gpu_main") or {}
        extra = [x["name"] for x in scan.get("gpus", []) if x is not g]
        lines = [f"Processador: {scan['cpu_name']}  ({scan['cores']} núcleos / {scan['threads']} threads)",
                 f"Placa de vídeo: {g.get('name', 'não identificada')}"
                 + (f"  ({g['vram_gb']:g} GB)" if g.get("vram_gb") else ""),
                 f"Memória RAM: {scan['ram_gb']:g} GB",
                 f"Disco {scan['disk_drive']}: {scan['disk_free_gb']:.0f} GB livres"
                 + (f"  ({scan['disk_kind']})" if scan.get("disk_kind") else "")]
        if scan.get("laptop"):
            lines.append("Tipo: notebook (desempenho costuma ser menor que o de um PC com a mesma placa).")
        if extra and not g.get("integrated"):
            lines.append("Também encontrada: " + ", ".join(extra) + ". Em notebook, confira se o jogo usa a placa dedicada.")
        self.pc_lbl.configure(text="\n".join(lines))

    # ------------------------------------------------------------- busca
    def _clear(self, frame):
        for w in frame.winfo_children():
            w.destroy()

    def show_popular(self):
        self._clear(self.results)
        self._list(gamecheck.curated_search("")[:12], [])

    def _list(self, curated, steam):
        self._clear(self.results)
        seen = {g["name"].lower() for g in curated}
        items = [("c", g) for g in curated] + [("s", g) for g in steam if g["name"].lower() not in seen]
        if not items:
            ctk.CTkLabel(self.results, text="Nada encontrado.", text_color=MUTED).pack(anchor="w")
        grid = ctk.CTkFrame(self.results, fg_color="transparent")
        grid.pack(fill="x")
        for i, (kind, g) in enumerate(items[:18]):
            grid.grid_columnconfigure(i % 3, weight=1, uniform="g")
            b = ctk.CTkButton(grid, text=g["name"], height=32, corner_radius=8, fg_color=PANEL2,
                              hover_color="#363552", text_color=TEXT, anchor="w",
                              command=lambda k=kind, g=g: self.pick(k, g))
            b.grid(row=i // 3, column=i % 3, sticky="ew", padx=3, pady=3)

    def search(self):
        term = self.entry.get().strip()
        curated = gamecheck.curated_search(term)
        if not term:
            self.show_popular()
            return
        self._list(curated, [])
        self.hint.configure(text="Buscando na Steam...")

        def work():
            try:
                found = gamecheck.steam_search(term)
                msg = "Resultados da Steam incluídos."
            except Exception:
                found, msg = [], "Sem acesso à Steam agora (internet?). Mostrando só a lista salva."
            self.after(0, lambda: (self._list(curated, found), self.hint.configure(text=msg)))
        in_thread(work)

    def after(self, ms, fn):
        self.tab.after(ms, fn)

    def pick(self, kind, g):
        if self.hw is None:
            self.pc_lbl.configure(text="Escaneando seu PC primeiro...")
            self.btn_scan.configure(state="disabled", text="Escaneando...")
            self.app.rescan(lambda s: (self.on_scan(s), self.pick(kind, g)))
            return
        if kind == "c":
            self.render(gamecheck.evaluate(self.hw, g))
            return
        self._clear(self.out)
        ctk.CTkLabel(self.out, text=f"Buscando requisitos de {g['name']}...", text_color=MUTED).pack(anchor="w", padx=10)

        def work():
            try:
                game = gamecheck.steam_game(g["id"])
                res = gamecheck.evaluate(self.hw, game)
            except Exception as e:
                res = {"level": "unknown", "title": "Não deu pra concluir", "subtitle": f"Erro ao buscar na Steam: {e}",
                       "quality": "", "rows": [], "tips": [], "game": g["name"]}
            self.after(0, lambda: self.render(res))
        in_thread(work)

    # ------------------------------------------------------------ resultado
    def render(self, r):
        self._clear(self.out)
        color = LEVEL_COLOR[r["level"]]
        c = card(self.out)
        c.pack(fill="x", pady=4)
        top = ctk.CTkFrame(c, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(14, 6))
        ctk.CTkLabel(top, text="", image=icon(LEVEL_ICON[r["level"]], color, 40)).pack(side="left")
        col = ctk.CTkFrame(top, fg_color="transparent")
        col.pack(side="left", padx=12)
        ctk.CTkLabel(col, text=r["game"], font=(FONT, 12), text_color=MUTED).pack(anchor="w")
        ctk.CTkLabel(col, text=r["title"], font=(FONT, 20, "bold"), text_color=color).pack(anchor="w")
        if r.get("subtitle"):
            ctk.CTkLabel(col, text=r["subtitle"], text_color=TEXT, wraplength=620, justify="left").pack(anchor="w")
        if r.get("quality"):
            ctk.CTkLabel(col, text=f"Expectativa: {r['quality']}", text_color=MUTED).pack(anchor="w")
        if r["rows"]:
            tbl = ctk.CTkFrame(c, fg_color=PANEL2, corner_radius=10)
            tbl.pack(fill="x", padx=16, pady=(6, 8))
            for j, h in enumerate(("", "Seu PC", "Mínimo", "Recomendado", "")):
                ctk.CTkLabel(tbl, text=h, text_color=MUTED, font=(FONT, 11, "bold"), anchor="w").grid(
                    row=0, column=j, sticky="w", padx=10, pady=(8, 2))
            for i, row in enumerate(r["rows"], 1):
                txt, scol = STATUS[row["status"]]
                vals = (row["label"], row["pc"] or "—", row["min"] or "—", row["rec"] or "—")
                for j, v in enumerate(vals):
                    ctk.CTkLabel(tbl, text=v, text_color=TEXT if j else MUTED, anchor="w", wraplength=210,
                                 justify="left", font=(FONT, 12, "bold" if j == 0 else "normal")).grid(
                        row=i, column=j, sticky="w", padx=10, pady=4)
                ctk.CTkLabel(tbl, text=txt, text_color=scol, font=(FONT, 12, "bold")).grid(
                    row=i, column=4, sticky="w", padx=10, pady=4)
            tbl.grid_columnconfigure((1, 2, 3), weight=1)
        for t in r["tips"]:
            ctk.CTkLabel(c, text="• " + t, text_color=MUTED, wraplength=720, justify="left", anchor="w").pack(
                anchor="w", padx=18, pady=1)
        ctk.CTkLabel(c, text="Estimativa feita pelo app a partir dos requisitos oficiais e de uma tabela aproximada "
                             "de desempenho. Serve de guia, não é garantia.", text_color=MUTED,
                     font=(FONT, 11, "italic"), wraplength=720, justify="left").pack(anchor="w", padx=18, pady=(8, 14))
