"""Visão geral: anéis de uso, estado do sistema, recomendações, ferramentas rápidas e informações."""
import customtkinter as ctk

import analyze
from icons import icon
from theme import (BAD, BG, BLUE, BORDER, FONT, FONT_TITLE, GOOD, HONEY, MUTED, PANEL, PANEL2, PURPLE, TEXT,
                   button, card, in_thread, ring_image)

QUICK = [
    ("brush-cleaning", "Limpeza de arquivos", "Libere espaço removendo arquivos desnecessários.", "Limpeza"),
    ("timer", "Gerenciador de inicialização", "Controle os programas que abrem com o Windows.", "Inicialização"),
    ("shield-check", "Verificação de sistema", "Verifique e repare arquivos do Windows.", "Segurança"),
    ("package-minus", "Desinstalar programas", "Remova apps que você não usa mais.", "Debloat"),
]


class OverviewPage(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.result = None
        sc = ctk.CTkScrollableFrame(self, fg_color="transparent")
        sc.pack(fill="both", expand=True)

        head = ctk.CTkFrame(sc, fg_color="transparent")
        head.pack(fill="x", padx=24, pady=(20, 6))
        left = ctk.CTkFrame(head, fg_color="transparent")
        left.pack(side="left")
        ctk.CTkLabel(left, text="Visão geral", font=(FONT_TITLE, 26, "bold"), text_color=TEXT).pack(anchor="w")
        ctk.CTkLabel(left, text="Acompanhe a saúde e o desempenho do seu PC.", text_color=MUTED,
                     font=(FONT, 13)).pack(anchor="w")
        for name, page in (("settings", "Configurações"), ("bell", None)):
            b = ctk.CTkButton(head, text="", image=icon(name, TEXT, 18), width=38, height=38, corner_radius=10,
                              fg_color=PANEL, hover_color=PANEL2, border_width=1, border_color=BORDER,
                              command=(lambda p=page: app.show(p)) if page else self.details)
            b.pack(side="right", padx=(8, 0))

        # ---- anéis
        grid = ctk.CTkFrame(sc, fg_color="transparent")
        grid.pack(fill="x", padx=18, pady=(8, 0))
        self.rings = {}
        spec = [("CPU", "cpu", PURPLE), ("Memória RAM", "memory-stick", GOOD),
                ("Armazenamento", "hard-drive", HONEY), ("Temperatura", "thermometer", BLUE)]
        for i, (name, ic, color) in enumerate(spec):
            grid.grid_columnconfigure(i, weight=1, uniform="r")
            c = card(grid)
            c.grid(row=0, column=i, sticky="nsew", padx=6, pady=6)
            img = ctk.CTkLabel(c, text="", image=ring_image(0, color, ic))
            img.pack(side="left", padx=(14, 8), pady=14)
            col = ctk.CTkFrame(c, fg_color="transparent")
            col.pack(side="left", fill="x", expand=True, pady=10)
            ctk.CTkLabel(col, text=name, text_color=MUTED, font=(FONT, 12)).pack(anchor="w")
            val = ctk.CTkLabel(col, text="--", font=(FONT, 22, "bold"), text_color=TEXT)
            val.pack(anchor="w")
            det = ctk.CTkLabel(col, text="", text_color=MUTED, font=(FONT, 11), wraplength=120, justify="left")
            det.pack(anchor="w")
            self.rings[name] = (img, val, det, color, ic)

        # ---- saúde + recomendações
        mid = ctk.CTkFrame(sc, fg_color="transparent")
        mid.pack(fill="x", padx=18, pady=(2, 0))
        mid.grid_columnconfigure((0, 1), weight=1, uniform="m")
        self.health = card(mid)
        self.health.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        self.health_icon = ctk.CTkLabel(self.health, text="", image=icon("circle-check-big", GOOD, 46))
        self.health_icon.pack(side="left", padx=(18, 12), pady=18)
        hc = ctk.CTkFrame(self.health, fg_color="transparent")
        hc.pack(side="left", fill="x", expand=True, pady=14)
        self.health_title = ctk.CTkLabel(hc, text="Pronto pra analisar", font=(FONT, 17, "bold"), text_color=TEXT)
        self.health_title.pack(anchor="w")
        self.health_sub = ctk.CTkLabel(hc, text="Clique em Analisar PC pra ver como está o seu sistema.",
                                       text_color=MUTED, wraplength=200, justify="left")
        self.health_sub.pack(anchor="w")
        self.btn_an = button(self.health, "Analisar PC", self.analyze, kind="primary", width=150, height=38)
        self.btn_an.pack(side="right", padx=18)

        self.reco = card(mid)
        self.reco.grid(row=0, column=1, sticky="nsew", padx=6, pady=6)
        self.reco_icon = ctk.CTkLabel(self.reco, text="", image=icon("lightbulb", HONEY, 40))
        self.reco_icon.pack(side="left", padx=(18, 12), pady=18)
        rc = ctk.CTkFrame(self.reco, fg_color="transparent")
        rc.pack(side="left", fill="x", expand=True, pady=14)
        self.reco_title = ctk.CTkLabel(rc, text="Recomendações", font=(FONT, 17, "bold"), text_color=TEXT)
        self.reco_title.pack(anchor="w")
        self.reco_sub = ctk.CTkLabel(rc, text="Sugestões aparecem depois da análise.", text_color=MUTED,
                                     wraplength=250, justify="left")
        self.reco_sub.pack(anchor="w")
        button(self.reco, "Ver detalhes", self.details, kind="outline", width=110, height=38).pack(
            side="right", padx=18)

        # ---- ferramentas rápidas
        ctk.CTkLabel(sc, text="Ferramentas rápidas", font=(FONT, 16, "bold"), text_color=TEXT).pack(
            anchor="w", padx=26, pady=(14, 2))
        q = ctk.CTkFrame(sc, fg_color="transparent")
        q.pack(fill="x", padx=18)
        for i, (ic, name, desc, page) in enumerate(QUICK):
            q.grid_columnconfigure(i, weight=1, uniform="q")
            c = card(q)
            c.grid(row=0, column=i, sticky="nsew", padx=6, pady=6)
            ctk.CTkLabel(c, text="", image=icon(ic, PURPLE, 26)).pack(anchor="w", padx=16, pady=(14, 4))
            ctk.CTkLabel(c, text=name, font=(FONT, 13, "bold"), text_color=TEXT, wraplength=150,
                         justify="left").pack(anchor="w", padx=16)
            ctk.CTkLabel(c, text=desc, text_color=MUTED, font=(FONT, 11), wraplength=150,
                         justify="left").pack(anchor="w", padx=16, pady=(2, 8))
            button(c, "Executar", lambda p=page: app.show(p), kind="outline", height=30).pack(
                anchor="w", padx=16, pady=(0, 14))

        # ---- informações do sistema
        ctk.CTkLabel(sc, text="Informações do sistema", font=(FONT, 16, "bold"), text_color=TEXT).pack(
            anchor="w", padx=26, pady=(10, 2))
        self.info = card(sc)
        self.info.pack(fill="x", padx=24, pady=(0, 24))
        self.info_rows = {}
        for ic, key in (("monitor", "Sistema operacional"), ("cpu", "Processador"), ("memory-stick", "Memória RAM"),
                        ("gpu", "Placa de vídeo"), ("hard-drive", "Armazenamento")):
            r = ctk.CTkFrame(self.info, fg_color="transparent")
            r.pack(fill="x", padx=16, pady=5)
            ctk.CTkLabel(r, text="", image=icon(ic, PURPLE, 18)).pack(side="left")
            ctk.CTkLabel(r, text=key, text_color=MUTED, width=150, anchor="w").pack(side="left", padx=(10, 0))
            v = ctk.CTkLabel(r, text="Lendo...", text_color=TEXT, anchor="w", wraplength=520, justify="left")
            v.pack(side="left", fill="x", expand=True)
            self.info_rows[key] = v

    # ----------------------------------------------------------------- dados
    def refresh_rings(self, d):
        def put(name, pct, text, detail):
            img, val, det, color, ic = self.rings[name]
            img.configure(image=ring_image(pct, color, ic))
            val.configure(text=text)
            det.configure(text=detail)
        put("CPU", d["cpu"], f"{d['cpu']:.0f}%", "Uso do processador")
        put("Memória RAM", d["ram"], f"{d['ram']:.0f}%", "Em uso")
        put("Armazenamento", d["disk"], f"{d['disk']:.0f}%", f"{d['disk_free_gb']:.0f} GB livres")
        t = d.get("temp_cpu") or d.get("temp_gpu")
        if t is None:
            put("Temperatura", 0, "--", "Sem sensor legível")
        else:
            which = "CPU" if d.get("temp_cpu") else "GPU"
            put("Temperatura", min(100, t), f"{t:.0f}°C", f"{which}")

    def show_scan(self, s):
        gpus = ", ".join(g["name"] + (f" ({g['vram_gb']:g} GB)" if g.get("vram_gb") else "") for g in s["gpus"]) \
            or "Não identificada"
        disk = f"{s['disk_drive']} · {s['disk_total_gb']:.0f} GB" + (f" {s['disk_kind']}" if s.get("disk_kind") else "") \
            + f" · {s['disk_free_gb']:.0f} GB livres"
        vals = {
            "Sistema operacional": s["os"] + (f" (build {s['os_build']})" if s.get("os_build") else ""),
            "Processador": f"{s['cpu_name']} · {s['cores']} núcleos / {s['threads']} threads",
            "Memória RAM": f"{s['ram_gb']:g} GB",
            "Placa de vídeo": gpus,
            "Armazenamento": disk,
        }
        for k, v in vals.items():
            self.info_rows[k].configure(text=v)

    # --------------------------------------------------------------- análise
    def analyze(self):
        self.btn_an.configure(state="disabled", text="Analisando...")
        self.health_title.configure(text="Analisando seu PC...")
        scan = self.app.scan

        def work():
            res = analyze.run_analysis(scan)
            self.after(0, lambda: self.show_result(res))
        in_thread(work)

    def show_result(self, res):
        self.result = res
        self.btn_an.configure(state="normal", text="Reanalisar")
        n = len(res["items"])
        bad = any(i["level"] == "bad" for i in res["items"])
        if res["ok"]:
            self.health_icon.configure(image=icon("circle-check-big", GOOD, 46))
            self.health_sub.configure(text="Nenhum problema encontrado. Seu PC está em boa forma.")
        else:
            self.health_icon.configure(image=icon("circle-alert" if bad else "triangle-alert",
                                                  BAD if bad else HONEY, 46))
            self.health_sub.configure(text="Encontramos pontos que podem ser melhorados.")
        self.health_title.configure(text=res["head"])
        self.reco_title.configure(text=f"{n} recomendaç{'ão' if n == 1 else 'ões'}")
        self.reco_sub.configure(text="Veja o que dá pra melhorar." if n else "Nada a fazer por enquanto.")

    def details(self):
        if self.result is None:
            self.analyze()
            return
        win = ctk.CTkToplevel(self)
        win.title("Recomendações")
        win.geometry("560x420")
        win.configure(fg_color=BG)
        win.attributes("-topmost", True)
        ctk.CTkLabel(win, text="Recomendações", font=(FONT_TITLE, 20, "bold"), text_color=TEXT).pack(
            anchor="w", padx=20, pady=(18, 8))
        if not self.result["items"]:
            ctk.CTkLabel(win, text="Nada a fazer por enquanto.", text_color=MUTED).pack(anchor="w", padx=20)
        for it in self.result["items"]:
            row = card(win)
            row.pack(fill="x", padx=20, pady=4)
            ic = "circle-alert" if it["level"] == "bad" else "triangle-alert"
            ctk.CTkLabel(row, text="", image=icon(ic, BAD if it["level"] == "bad" else HONEY, 20)).pack(
                side="left", padx=12, pady=12)
            ctk.CTkLabel(row, text=it["text"], text_color=TEXT, wraplength=330, justify="left").pack(
                side="left", fill="x", expand=True)
            button(row, "Abrir", lambda p=it["page"], w=win: (w.destroy(), self.app.show(p)),
                   kind="outline", width=70, height=30).pack(side="right", padx=12)
