"""MelbyTune - otimizador de PC pra uso pessoal.  "Seu PC. Seu ritmo."

Rode como administrador (o app pede sozinho). Python 3.10+  ->  pip install -r requirements.txt
"""
import ctypes
import os
import shutil
import subprocess
import sys
import queue
import threading
import traceback

import customtkinter as ctk

import analyze
import gamecheck
import hardware
import tweaks
from icons import icon
from sampler import Sampler
from theme import (APP_VERSION, BG, BORDER, FONT, FONT_TITLE, GOOD, HONEY, MUTED, PANEL, PANEL2, PURPLE,
                   PURPLE_H, SIDE, TEXT, load_fonts, resource)
from ui_apps import AppsPage
from ui_clean import CleanPage
from ui_davi import DaviPage
from ui_debloat import DebloatPage
from ui_overview import OverviewPage
from ui_security import SecurityPage
from ui_settings import SettingsPage
from ui_startup import StartupPage
from ui_tools import ToolsPage
from ui_tweaks import TweaksPage

NOWIN = tweaks.NOWIN

def ensure_admin():
    if os.name != "nt":
        return
    try:
        if ctypes.windll.shell32.IsUserAnAdmin():
            return
    except Exception:
        return
    args = sys.argv[1:] if getattr(sys, "frozen", False) else sys.argv
    params = " ".join(f'"{a}"' for a in args)
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
    sys.exit()


class App(ctk.CTk):
    # (nome, ícone Lucide)
    NAV = [("Visão geral", "layout-dashboard"), ("Otimização", "zap"), ("Limpeza", "brush-cleaning"),
           ("Inicialização", "power"), ("Desempenho", "gauge"), ("Ferramentas", "wrench"),
           ("Debloat", "package-x"), ("Instalar apps", "download"), ("Segurança", "shield-check"),
           ("Configurações", "settings")]

    def __init__(self):
        super().__init__()
        load_fonts()
        ctk.set_appearance_mode("dark")
        self.title("MelbyTune")
        self.geometry("1180x800")
        self.minsize(1020, 700)
        self.configure(fg_color=BG)
        self.after(250, self.set_icon)

        self.scan = None
        self._scan_q = queue.Queue()
        self._scan_cbs = []
        self._scanning = False
        self.sampler = Sampler()

        self.side = ctk.CTkFrame(self, width=232, fg_color=SIDE, corner_radius=0)
        self.side.pack(side="left", fill="y")
        self.side.pack_propagate(False)
        self.build_brand()

        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.pack(side="left", fill="both", expand=True)

        self.pages, self.buttons, self.base_color = {}, {}, {}
        self.current = None
        for name, ic in self.NAV:
            self.add_nav(name, ic)
        ctk.CTkLabel(self.side, text="PACOTES", font=("Consolas", 11, "bold"), text_color=MUTED).pack(
            anchor="w", padx=22, pady=(12, 2))
        self.add_nav("Davi Zone", "laptop", special=True)
        self.build_version_card()

        self.pages["Visão geral"] = OverviewPage(self.body, self)
        self.pages["Otimização"] = TweaksPage(
            self.body, "Otimização", "Privacidade e ajustes do sistema. Cada ajuste mostra o comando e pode ser "
            "desfeito. Crie um ponto de restauração antes, em Configurações.", ["Privacidade", "Sistema"])
        self.pages["Limpeza"] = CleanPage(self.body)
        self.pages["Inicialização"] = StartupPage(self.body)
        self.pages["Desempenho"] = TweaksPage(
            self.body, "Desempenho", "Ajustes pra jogos, menos atraso de input e plano de energia.",
            ["Jogos", "Input lag"], power=True)
        self.pages["Ferramentas"] = ToolsPage(self.body, self)
        self.pages["Debloat"] = DebloatPage(self.body)
        self.pages["Instalar apps"] = AppsPage(self.body)
        self.pages["Segurança"] = SecurityPage(self.body)
        self.pages["Configurações"] = SettingsPage(self.body)
        self.pages["Davi Zone"] = DaviPage(self.body)
        self.show("Visão geral")

        self.sampler.start()
        self.after(400, lambda: self.rescan(self._on_first_scan))
        self.after(600, self.tick)
        self.after(300, self.poll)

    # ------------------------------------------------------------ hardware
    def rescan(self, callback=None):
        """Escaneia o PC em segundo plano e chama callback(scan) na thread da interface."""
        if callback:
            self._scan_cbs.append(callback)
        if self._scanning:
            return
        self._scanning = True

        def work():
            try:
                res = hardware.scan()
            except Exception:
                res = None
            self._scan_q.put(res)
        threading.Thread(target=work, daemon=True).start()

    def poll(self):
        try:
            res = self._scan_q.get_nowait()
        except queue.Empty:
            res = False
        if res is not False:
            self._scanning = False
            if res:
                self.scan = res
            cbs, self._scan_cbs = self._scan_cbs, []
            if self.scan:
                for cb in cbs:
                    try:
                        cb(self.scan)
                    except Exception:
                        traceback.print_exc()
        self.after(300, self.poll)

    def _on_first_scan(self, scan):
        self.pages["Visão geral"].show_scan(scan)

    def tick(self):
        if self.current == "Visão geral":
            self.pages["Visão geral"].refresh_rings(self.sampler.data)
        self.after(1500, self.tick)

    # ------------------------------------------------------------ estrutura
    def set_icon(self):
        try:
            if os.name == "nt":
                self.iconbitmap(resource("assets/icon.ico"))
            else:
                import tkinter as tk
                self.iconphoto(True, tk.PhotoImage(file=resource("assets/icon.png")))
        except Exception:
            pass

    def build_brand(self):
        box = ctk.CTkFrame(self.side, fg_color="transparent")
        box.pack(fill="x", padx=18, pady=(22, 0))
        try:
            from PIL import Image
            img = Image.open(resource("assets/logo.png"))
            self.logo = ctk.CTkImage(light_image=img, dark_image=img, size=(46, 46))
            ctk.CTkLabel(box, image=self.logo, text="").pack(side="left")
        except Exception:
            pass
        names = ctk.CTkFrame(box, fg_color="transparent")
        names.pack(side="left", padx=(10, 0))
        row = ctk.CTkFrame(names, fg_color="transparent")
        row.pack(anchor="w")
        ctk.CTkLabel(row, text="Melby", font=(FONT_TITLE, 21, "bold"), text_color=TEXT).pack(side="left")
        ctk.CTkLabel(row, text="Tune", font=(FONT_TITLE, 21, "bold"), text_color=HONEY).pack(side="left")
        ctk.CTkLabel(names, text="Seu PC. Seu ritmo.", font=(FONT, 11), text_color=MUTED).pack(anchor="w")
        ctk.CTkFrame(self.side, height=1, fg_color=PANEL2).pack(fill="x", padx=18, pady=(16, 8))

    def build_version_card(self):
        c = ctk.CTkFrame(self.side, fg_color=PANEL, corner_radius=12, border_width=1, border_color=BORDER)
        c.pack(side="bottom", fill="x", padx=14, pady=14)
        ctk.CTkLabel(c, text="", image=icon("circle-check", GOOD, 20)).pack(
            side="left", padx=(12, 8), pady=12)
        col = ctk.CTkFrame(c, fg_color="transparent")
        col.pack(side="left", pady=8)
        ctk.CTkLabel(col, text=f"MelbyTune v{APP_VERSION}", font=(FONT, 12, "bold"), text_color=TEXT).pack(anchor="w")
        ctk.CTkLabel(col, text="Uso pessoal", font=(FONT, 11), text_color=MUTED).pack(anchor="w")

    def add_nav(self, name, ic, special=False):
        color = HONEY if special else TEXT
        b = ctk.CTkButton(self.side, text="  " + name, image=icon(ic, color, 18), compound="left", anchor="w",
                          height=38, corner_radius=10, fg_color="transparent", hover_color=PANEL2,
                          text_color=color, font=(FONT, 13, "bold"), command=lambda n=name: self.show(n))
        b.pack(fill="x", padx=12, pady=1)
        self.buttons[name] = (b, ic)
        self.base_color[name] = color

    def show(self, name):
        if name not in self.pages:
            return
        for n, p in self.pages.items():
            p.pack_forget()
            b, ic = self.buttons[n]
            b.configure(fg_color="transparent", text_color=self.base_color[n], image=icon(ic, self.base_color[n], 18))
        self.pages[name].pack(fill="both", expand=True)
        b, ic = self.buttons[name]
        b.configure(fg_color=PURPLE, hover_color=PURPLE_H, text_color="#FFFFFF", image=icon(ic, "#FFFFFF", 18))
        self.current = name


def log_crash(text):
    """Grava o erro em %APPDATA%\\MelbyTune\\erro.log e avisa na tela (funciona até se o Tk falhar)."""
    path = os.path.join(tweaks.APP_DIR, "erro.log")
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(text + "\n" + "-" * 60 + "\n")
    except OSError:
        pass
    try:
        ctypes.windll.user32.MessageBoxW(
            0, f"O MelbyTune encontrou um erro e precisa fechar.\n\nDetalhes salvos em:\n{path}\n\n{text[-600:]}",
            "MelbyTune - erro", 0x10)
    except Exception:
        pass


def selftest():
    """Abre o app, passa por todas as telas e fecha. Usado pelo GitHub pra testar o .exe no Windows."""
    out = os.path.join(tweaks.APP_DIR, "selftest.txt")
    errs = []
    app = App()
    app.report_callback_exception = lambda *a: errs.append("".join(traceback.format_exception(*a)))
    names = list(app.pages)
    i = [0]

    def step():
        if i[0] < len(names):
            app.show(names[i[0]])
            i[0] += 1
            app.after(500, step)
        else:
            app.after(8000 if app.scan is None else 500, app.quit)
    app.after(800, step)
    app.mainloop()
    extra = []
    try:
        s = app.scan
        if s:
            extra.append(f"CPU: {s['cpu_name']} ({s['cores']}c/{s['threads']}t) | RAM {s['ram_gb']} GB | "
                         f"GPU: {[g['name'] for g in s['gpus']]} | disco {s['disk_kind']} {s['disk_total_gb']} GB")
            hw = gamecheck.hw_from_scan(s)
            r = gamecheck.evaluate(hw, gamecheck.curated_search("minecraft")[0])
            extra.append(f"Rodo Minecraft? {r['title']}")
            a = analyze.run_analysis(s)
            extra.append(f"Analise: {a['head']} ({len(a['items'])} itens)")
        else:
            errs.append("hardware.scan() nao retornou nada")
    except Exception:
        errs.append(traceback.format_exc())
    app.sampler.stop()
    app.destroy()
    with open(out, "w", encoding="utf-8") as f:
        f.write(("ERROS:\n" + "\n".join(errs)) if errs else f"OK - {len(names)} telas abriram sem erro\n" + "\n".join(extra))
    return 1 if errs else 0


if __name__ == "__main__":
    try:
        if "--selftest" in sys.argv:
            sys.exit(selftest())
        ensure_admin()
        app = App()
        app.report_callback_exception = lambda *a: log_crash("".join(traceback.format_exception(*a)))
        app.mainloop()
    except SystemExit:
        raise
    except BaseException:
        log_crash(traceback.format_exc())
        sys.exit(1)
