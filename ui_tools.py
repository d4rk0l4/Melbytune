"""Aba Ferramentas: teste de CPS, teste de monitor, teste de velocidade e comparar placas de vídeo."""
import time
import tkinter as tk

import customtkinter as ctk

import speedtest
import tweaks
from gpus import GPUS, detect_gpu
from theme import (HONEY, MUTED, PANEL, PANEL2, PURPLE, PURPLE_H, TEXT, FONT, button, card, in_thread,
                   tabs, title)


def _seg(parent, values, default, command=None):
    s = ctk.CTkSegmentedButton(parent, values=values, command=command, selected_color=PURPLE,
                               selected_hover_color=PURPLE_H, unselected_color=PANEL2,
                               unselected_hover_color="#363552", text_color=TEXT)
    s.set(default)
    return s


class ToolsPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        title(self, "Ferramentas", "Testes rápidos e comparador de placas de vídeo.")
        tv = tabs(self, ["Teste de CPS", "Teste de monitor", "Velocidade", "Comparar placas"])
        tv.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        self.cps = CpsTab(tv.tab("Teste de CPS"))
        self.monitor = MonitorTab(tv.tab("Teste de monitor"), self)
        self.speed = SpeedTab(tv.tab("Velocidade"))
        self.gpu = GpuTab(tv.tab("Comparar placas"))


# ------------------------------------------------------------------------ CPS
class CpsTab:
    def __init__(self, tab):
        self.tab = tab
        self.dur = 5
        self.state = "idle"  # idle | run | done
        self.clicks = 0
        self.t0 = 0.0
        self.done_t = 0.0
        self.best = {}
        top = ctk.CTkFrame(tab, fg_color="transparent")
        top.pack(fill="x", pady=(6, 0))
        ctk.CTkLabel(top, text="Tempo do teste", text_color=MUTED).pack(side="left")
        self.seg = _seg(top, ["1s", "5s", "10s", "30s"], "5s", self.set_dur)
        self.seg.pack(side="left", padx=10)
        self.big = ctk.CTkLabel(tab, text="0.00", font=(FONT, 60, "bold"), text_color=HONEY)
        self.big.pack(pady=(10, 0))
        ctk.CTkLabel(tab, text="cliques por segundo (CPS)", text_color=MUTED).pack()
        self.info = ctk.CTkLabel(tab, text="Clique na área abaixo pra começar", text_color=TEXT)
        self.info.pack(pady=6)
        self.area = ctk.CTkFrame(tab, fg_color=PANEL, corner_radius=14, border_width=2, border_color=PURPLE)
        self.area.pack(fill="both", expand=True, pady=(0, 6))
        self.hint = ctk.CTkLabel(self.area, text="CLIQUE AQUI", font=(FONT, 22, "bold"), text_color=MUTED)
        self.hint.place(relx=0.5, rely=0.5, anchor="center")
        for w in (self.area, self.hint):
            w.bind("<Button-1>", self.click)

    def set_dur(self, v):
        self.dur = int(v[:-1])
        self.reset()

    def reset(self):
        self.state = "idle"
        self.clicks = 0
        self.big.configure(text="0.00")
        self.info.configure(text="Clique na área abaixo pra começar")
        self.hint.configure(text="CLIQUE AQUI")

    def click(self, _e=None):
        now = time.perf_counter()
        if self.state == "done" and now - self.done_t < 0.7:
            return
        if self.state in ("idle", "done"):
            self.state, self.clicks, self.t0 = "run", 0, now
            self.hint.configure(text="CONTINUE CLICANDO!")
            self.tick()
        if now - self.t0 <= self.dur:
            self.clicks += 1

    def tick(self):
        if self.state != "run":
            return
        el = time.perf_counter() - self.t0
        if el >= self.dur:
            self.finish()
            return
        self.big.configure(text=f"{self.clicks / max(el, 0.25):.2f}")
        self.info.configure(text=f"Faltam {self.dur - el:.1f}s  ·  {self.clicks} cliques")
        self.tab.after(50, self.tick)

    def finish(self):
        self.state = "done"
        self.done_t = time.perf_counter()
        cps = self.clicks / self.dur
        best = max(self.best.get(self.dur, 0), cps)
        self.best[self.dur] = best
        self.big.configure(text=f"{cps:.2f}")
        self.info.configure(text=f"{self.clicks} cliques em {self.dur}s  ·  recorde ({self.dur}s): {best:.2f} CPS")
        self.hint.configure(text="Clique pra tentar de novo")


# -------------------------------------------------------------------- Monitor
def _solid(color):
    return lambda cv, w, h: cv.configure(bg=color)


def _gradient(cv, w, h):
    cv.configure(bg="black")
    bands = [(1, 1, 1), (1, 0, 0), (0, 1, 0), (0, 0, 1)]
    bh = h / len(bands)
    steps = 256
    sw = w / steps
    for b, (r, g, bl) in enumerate(bands):
        for i in range(steps):
            col = "#%02x%02x%02x" % (i * r, i * g, i * bl)
            cv.create_rectangle(i * sw, b * bh, (i + 1) * sw + 1, (b + 1) * bh, fill=col, outline="")


PATTERNS = [
    ("Preto (procure pixels acesos e vazamento de luz)", _solid("#000000"), "#888888"),
    ("Branco (procure pixels mortos e manchas)", _solid("#FFFFFF"), "#444444"),
    ("Vermelho", _solid("#FF0000"), "#FFFFFF"),
    ("Verde", _solid("#00FF00"), "#000000"),
    ("Azul", _solid("#0000FF"), "#FFFFFF"),
    ("Amarelo", _solid("#FFFF00"), "#000000"),
    ("Ciano", _solid("#00FFFF"), "#000000"),
    ("Magenta", _solid("#FF00FF"), "#000000"),
    ("Cinza médio (procure manchas e faixas)", _solid("#808080"), "#FFFFFF"),
    ("Degradê (procure degraus/faixas nas cores)", _gradient, "#FFFFFF"),
]


class Overlay(tk.Toplevel):
    def __init__(self, master, patterns):
        super().__init__(master)
        self.patterns, self.i = patterns, 0
        self.configure(bg="black", cursor="none")
        self.attributes("-fullscreen", True)
        self.attributes("-topmost", True)
        self.cv = tk.Canvas(self, highlightthickness=0, bd=0, bg="black")
        self.cv.pack(fill="both", expand=True)
        for w in (self, self.cv):
            w.bind("<Button-1>", self.next)
            w.bind("<space>", self.next)
            w.bind("<Right>", self.next)
            w.bind("<Left>", self.prev)
            w.bind("<Button-3>", self.prev)
            w.bind("<Escape>", lambda e: self.destroy())
        self.cv.bind("<Configure>", lambda e: self.draw())
        self.focus_force()

    def next(self, _e=None):
        self.i = (self.i + 1) % len(self.patterns)
        self.draw()

    def prev(self, _e=None):
        self.i = (self.i - 1) % len(self.patterns)
        self.draw()

    def draw(self):
        cv = self.cv
        cv.delete("all")
        w, h = cv.winfo_width(), cv.winfo_height()
        name, fn, hint = self.patterns[self.i]
        fn(cv, w, h)
        cv.create_text(24, 20, anchor="nw", fill=hint, font=(FONT, 15, "bold"), tags="hint",
                       text=f"{name}   ({self.i + 1}/{len(self.patterns)})\n"
                            "clique ou → próxima  ·  ← ou botão direito volta  ·  Esc sai")
        cv.after(3000, lambda: cv.delete("hint"))


class MonitorTab:
    def __init__(self, tab, root):
        self.root = root
        # lido aqui (thread principal): o Tk não gosta de ser chamado de outra thread
        self.fallback = f"Tela: {root.winfo_screenwidth()}x{root.winfo_screenheight()}"
        ctk.CTkLabel(tab, wraplength=760, justify="left", text_color=MUTED,
                     text="Enche a tela com uma cor de cada vez pra você achar pixels mortos ou travados, "
                          "manchas, vazamento de luz e faixas no degradê. Chegue perto da tela e olhe com atenção."
                     ).pack(anchor="w", pady=(6, 10))
        c = card(tab)
        c.pack(fill="x", pady=4)
        self.info = ctk.CTkLabel(c, text="Lendo a tela...", font=(FONT, 14), text_color=TEXT, justify="left")
        self.info.pack(anchor="w", padx=16, pady=14)
        row = ctk.CTkFrame(tab, fg_color="transparent")
        row.pack(fill="x", pady=10)
        button(row, "Testar cores e pixels mortos", lambda: self.open(PATTERNS[:9]), kind="primary", height=42).pack(side="left")
        button(row, "Testar degradê (faixas)", lambda: self.open(PATTERNS[9:]), height=42).pack(side="left", padx=10)
        button(row, "Todos em sequência", lambda: self.open(PATTERNS), height=42).pack(side="left")
        tab.after(400, lambda: in_thread(self.read_info))

    def read_info(self):
        r = tweaks.run(["powershell", "-NoProfile", "-Command",
                        "(Get-CimInstance Win32_VideoController | ForEach-Object { \"$($_.Name): "
                        "$($_.CurrentHorizontalResolution)x$($_.CurrentVerticalResolution) @ $($_.CurrentRefreshRate) Hz\" }) -join [Environment]::NewLine"],
                       timeout=15)
        text = (r.stdout or "").strip() or self.fallback
        self.info.after(0, lambda: self.info.configure(text=text))

    def open(self, patterns):
        Overlay(self.root.winfo_toplevel(), patterns)


# ------------------------------------------------------------------ Velocidade
class SpeedTab:
    def __init__(self, tab):
        self.busy = False
        ctk.CTkLabel(tab, text_color=MUTED, wraplength=760, justify="left",
                     text="Mede ping, download e upload usando os servidores da Cloudflare. Gasta uns 100 a 300 MB "
                          "da sua internet. Feche downloads e streaming antes pra o resultado ficar certo."
                     ).pack(anchor="w", pady=(6, 10))
        row = ctk.CTkFrame(tab, fg_color="transparent")
        row.pack(fill="x", pady=6)
        self.vals = {}
        for key, name, unit in (("ping", "Ping", "ms"), ("download", "Download", "Mbps"), ("upload", "Upload", "Mbps")):
            c = card(row)
            c.pack(side="left", fill="x", expand=True, padx=6)
            ctk.CTkLabel(c, text=name, text_color=MUTED).pack(anchor="w", padx=16, pady=(12, 0))
            v = ctk.CTkLabel(c, text="--", font=(FONT, 34, "bold"), text_color=HONEY if key != "ping" else TEXT)
            v.pack(anchor="w", padx=16)
            ctk.CTkLabel(c, text=unit, text_color=MUTED).pack(anchor="w", padx=16, pady=(0, 12))
            self.vals[key] = v
        self.status = ctk.CTkLabel(tab, text="", text_color=MUTED)
        self.status.pack(pady=8)
        self.btn = button(tab, "Iniciar teste", self.start, kind="primary", height=44, width=200)
        self.btn.pack()

    def start(self):
        if self.busy:
            return
        self.busy = True
        self.btn.configure(state="disabled")
        for v in self.vals.values():
            v.configure(text="--")
        names = {"ping": "Medindo o ping...", "download": "Medindo o download...", "upload": "Medindo o upload..."}

        def cb(stage, value, final):
            fmt = f"{value:.0f}" if stage == "ping" else f"{value:.1f}"
            self.vals[stage].after(0, lambda: (self.vals[stage].configure(text=fmt),
                                               self.status.configure(text="" if final and stage == "upload" else names[stage])))

        def work():
            err = ""
            try:
                speedtest.run(cb)
            except Exception as e:
                err = f"Não foi possível testar: {e}"
            self.status.after(0, lambda: (self.status.configure(text=err or "Pronto."),
                                          self.btn.configure(state="normal")))
            self.busy = False
        in_thread(work)


# --------------------------------------------------------------- Placas de vídeo
def gpu_name_windows():
    r = tweaks.run(["powershell", "-NoProfile", "-Command",
                    "(Get-CimInstance Win32_VideoController | Select-Object -First 1).Name"], timeout=10)
    return (r.stdout or "").strip()


class GpuTab:
    def __init__(self, tab):
        ctk.CTkLabel(tab, text="Desempenho relativo aproximado, lista local (edite em gpus.py). Nada vai pra internet.",
                     text_color=MUTED).pack(anchor="w", pady=(6, 8))
        names = sorted(GPUS, key=GPUS.get, reverse=True)
        row = ctk.CTkFrame(tab, fg_color="transparent")
        row.pack(fill="x")
        ctk.CTkLabel(row, text="Placa A (a sua)", text_color=MUTED).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(row, text="Placa B", text_color=MUTED).grid(row=0, column=1, sticky="w", padx=14)
        kw = dict(values=names, width=270, fg_color=PANEL2, button_color=PURPLE, button_hover_color=PURPLE_H,
                  command=lambda _: self.update())
        self.a = ctk.CTkComboBox(row, **kw)
        self.b = ctk.CTkComboBox(row, **kw)
        self.a.grid(row=1, column=0)
        self.b.grid(row=1, column=1, padx=14)
        self.a.set("GeForce RTX 3070")
        self.b.set("GeForce RTX 4080")
        self.result = ctk.CTkLabel(tab, text="", font=(FONT, 16, "bold"), text_color=HONEY, wraplength=760, justify="left")
        self.result.pack(anchor="w", pady=10)
        self.box = ctk.CTkScrollableFrame(tab, fg_color=PANEL)
        self.box.pack(fill="both", expand=True, pady=(0, 6))
        self.update()
        self.box.after(400, lambda: in_thread(self.detect))

    def detect(self):
        mine = detect_gpu(gpu_name_windows())
        if mine:
            self.a.after(0, lambda: (self.a.set(mine), self.update()))

    def update(self):
        a, b = self.a.get(), self.b.get()
        if a not in GPUS or b not in GPUS:
            return
        sa, sb = GPUS[a], GPUS[b]
        diff = (sb / sa - 1) * 100
        if abs(diff) < 1:
            self.result.configure(text=f"A {a} e a {b} têm desempenho praticamente igual.")
        elif diff > 0:
            self.result.configure(text=f"A {b} é {diff:.0f}% mais rápida que a {a}.")
        else:
            self.result.configure(text=f"A {b} é {-diff:.0f}% mais lenta que a {a}.")
        for w in self.box.winfo_children():
            w.destroy()
        top = max(GPUS.values()) / sa * 100
        for n in sorted(GPUS, key=GPUS.get, reverse=True):
            pct = GPUS[n] / sa * 100
            color = HONEY if n == b else (PURPLE if n == a else "#3A3A52")
            line = ctk.CTkFrame(self.box, fg_color="transparent")
            line.pack(fill="x", pady=2)
            ctk.CTkLabel(line, text=n, width=190, anchor="w", text_color=TEXT).pack(side="left")
            pb = ctk.CTkProgressBar(line, progress_color=color, fg_color=PANEL2, height=10)
            pb.set(pct / top)
            pb.pack(side="left", fill="x", expand=True, padx=8)
            ctk.CTkLabel(line, text=f"{pct:.0f}%", width=50, anchor="e", text_color=TEXT).pack(side="left")
