"""MelbyTune - otimizador de PC pra uso pessoal.  "Seu PC. Seu ritmo."

Rode como administrador (o app pede sozinho). Python 3.10+  ->  pip install -r requirements.txt
"""
import ctypes
import os
import shutil
import subprocess
import sys
import threading
import traceback
import tkinter.messagebox as mb

import customtkinter as ctk
import psutil

import tweaks
from theme import (BG, FONT, HONEY, HONEY_H, MUTED, PANEL, PANEL2, PURPLE, PURPLE_H, SIDE, TEXT,
                   button, card, resource, title)
from ui_apps import AppsPage
from ui_clean import CleanPage
from ui_davi import DaviPage
from ui_debloat import DebloatPage
from ui_security import SecurityPage
from ui_startup import StartupPage
from ui_tools import ToolsPage

NOWIN = tweaks.NOWIN

CATEGORY_NOTES = {
    "Input lag": "Reduzem atrasos entre o clique/tecla e a imagem. O efeito é pequeno e varia de PC pra PC.",
}


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


def nvidia_info():
    """Lê a GPU NVIDIA via nvidia-smi (vem junto com o driver). None se não tiver."""
    if not shutil.which("nvidia-smi"):
        return None
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,utilization.gpu,temperature.gpu,memory.used,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=2, creationflags=NOWIN).stdout.strip()
        name, util, temp, used, total = [x.strip() for x in out.splitlines()[0].split(",")]
        return {"name": name, "util": float(util), "temp": temp, "used": float(used), "total": float(total)}
    except Exception:
        return None


class App(ctk.CTk):
    NAV = ["Painel", "Ajustes", "Inicialização", "Debloat", "Instalar apps", "Limpeza",
           "Segurança", "Ferramentas", "Sistema"]

    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        self.title("MelbyTune")
        self.geometry("1120x780")
        self.minsize(980, 680)
        self.configure(fg_color=BG)
        self.after(250, self.set_icon)

        self.side = ctk.CTkFrame(self, width=226, fg_color=SIDE, corner_radius=0)
        self.side.pack(side="left", fill="y")
        self.side.pack_propagate(False)
        self.build_brand()

        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.pack(side="left", fill="both", expand=True)

        self.pages, self.buttons, self.base_color = {}, {}, {}
        self.current = None
        for name in self.NAV:
            self.add_nav(name)
        ctk.CTkLabel(self.side, text="PACOTES", font=("Consolas", 11, "bold"), text_color=MUTED).pack(
            anchor="w", padx=22, pady=(14, 2))
        self.add_nav("Davi Zone", special=True)

        self.cpu_hist = [0] * 60
        self.has_nvidia = bool(shutil.which("nvidia-smi"))
        self.pages["Painel"] = self.frame()
        self.build_painel(self.pages["Painel"])
        self.pages["Ajustes"] = self.frame()
        self.build_ajustes(self.pages["Ajustes"])
        self.pages["Inicialização"] = StartupPage(self.body)
        self.pages["Debloat"] = DebloatPage(self.body)
        self.pages["Instalar apps"] = AppsPage(self.body)
        self.pages["Limpeza"] = CleanPage(self.body)
        self.pages["Segurança"] = SecurityPage(self.body)
        self.pages["Ferramentas"] = ToolsPage(self.body)
        self.pages["Sistema"] = self.frame()
        self.build_sistema(self.pages["Sistema"])
        self.pages["Davi Zone"] = DaviPage(self.body)
        self.show("Painel")
        self.tick()

    # ------------------------------------------------------------ estrutura
    def frame(self):
        return ctk.CTkFrame(self.body, fg_color="transparent")

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
        ctk.CTkLabel(row, text="Melby", font=(FONT, 20, "bold"), text_color=TEXT).pack(side="left")
        ctk.CTkLabel(row, text="Tune", font=(FONT, 20), text_color=TEXT).pack(side="left")
        ctk.CTkLabel(names, text="Seu PC. Seu ritmo.", font=(FONT, 11), text_color=MUTED).pack(anchor="w")
        ctk.CTkFrame(self.side, height=1, fg_color=PANEL2).pack(fill="x", padx=18, pady=(14, 8))

    def add_nav(self, name, special=False):
        color = HONEY if special else TEXT
        b = ctk.CTkButton(self.side, text=name, anchor="w", height=36, corner_radius=8,
                          fg_color="transparent", hover_color=PANEL2, text_color=color,
                          command=lambda n=name: self.show(n))
        b.pack(fill="x", padx=12, pady=1)
        self.buttons[name] = b
        self.base_color[name] = color

    def show(self, name):
        for n, p in self.pages.items():
            p.pack_forget()
            self.buttons[n].configure(fg_color="transparent", text_color=self.base_color[n])
        self.pages[name].pack(fill="both", expand=True)
        self.buttons[name].configure(fg_color=PURPLE, hover_color=PURPLE_H, text_color="#FFFFFF")
        self.current = name

    # ----------------------------------------------------------------- painel
    def build_painel(self, p):
        title(p, "Painel", "Uso do PC em tempo real.")
        grid = ctk.CTkFrame(p, fg_color="transparent")
        grid.pack(fill="x", padx=18)
        self.meters = {}
        for i, key in enumerate(("CPU", "RAM", "Disco", "GPU")):
            c = card(grid)
            c.grid(row=i // 2, column=i % 2, sticky="nsew", padx=6, pady=6)
            grid.grid_columnconfigure(i % 2, weight=1)
            ctk.CTkLabel(c, text=key, text_color=MUTED).pack(anchor="w", padx=16, pady=(12, 0))
            val = ctk.CTkLabel(c, text="--", font=(FONT, 26, "bold"), text_color=TEXT)
            val.pack(anchor="w", padx=16)
            bar = ctk.CTkProgressBar(c, progress_color=PURPLE, fg_color=PANEL2, height=8)
            bar.set(0)
            bar.pack(fill="x", padx=16, pady=(4, 4))
            det = ctk.CTkLabel(c, text="", text_color=MUTED, font=(FONT, 11))
            det.pack(anchor="w", padx=16, pady=(0, 12))
            self.meters[key] = (val, bar, det)
        box = card(p)
        box.pack(fill="x", padx=24, pady=8)
        ctk.CTkLabel(box, text="CPU - último minuto", text_color=MUTED).pack(anchor="w", padx=16, pady=(10, 0))
        self.canvas = ctk.CTkCanvas(box, height=130, bg=PANEL, highlightthickness=0)
        self.canvas.pack(fill="x", padx=16, pady=(0, 12))

    def tick(self):
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory()
        try:
            disk = psutil.disk_usage(os.environ.get("SystemDrive", "C:") + "\\" if os.name == "nt" else "/")
            self.set_meter("Disco", disk.percent, f"{disk.percent:.0f}%", f"{disk.free / 2**30:.0f} GB livres")
        except Exception:
            pass
        freq = psutil.cpu_freq()
        self.set_meter("CPU", cpu, f"{cpu:.0f}%", f"{freq.current / 1000:.2f} GHz" if freq else "")
        self.set_meter("RAM", ram.percent, f"{ram.percent:.0f}%",
                       f"{ram.used / 2**30:.1f} / {ram.total / 2**30:.1f} GB")
        g = nvidia_info() if (self.has_nvidia and self.current == "Painel") else None
        if g:
            self.set_meter("GPU", g["util"], f"{g['util']:.0f}%",
                           f"{g['name']} · {g['temp']}°C · {g['used']:.0f}/{g['total']:.0f} MB")
        elif not self.has_nvidia:
            self.set_meter("GPU", 0, "--", "Leitura disponível só em placas NVIDIA")
        self.cpu_hist = self.cpu_hist[1:] + [cpu]
        if self.current == "Painel":
            self.draw_graph()
        self.after(1000, self.tick)

    def set_meter(self, key, pct, text, detail):
        val, bar, det = self.meters[key]
        val.configure(text=text)
        bar.set(min(pct, 100) / 100)
        det.configure(text=detail)

    def draw_graph(self):
        c = self.canvas
        c.delete("all")
        w = max(c.winfo_width(), 200)
        h = 130
        pts = []
        for i, v in enumerate(self.cpu_hist):
            pts += [i * w / (len(self.cpu_hist) - 1), h - 4 - v / 100 * (h - 8)]
        c.create_line(*pts, fill=HONEY, width=2, smooth=True)

    # ---------------------------------------------------------------- ajustes
    def build_ajustes(self, p):
        title(p, "Ajustes do Windows",
              "Cada ajuste mostra o comando e pode ser desfeito (o valor original fica salvo). "
              "Crie um ponto de restauração antes, na aba Sistema.")
        sc = ctk.CTkScrollableFrame(p, fg_color="transparent")
        sc.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        last = None
        for t in tweaks.TWEAKS:
            if t.category != last:
                ctk.CTkLabel(sc, text=t.category.upper(), text_color=HONEY,
                             font=("Consolas", 12, "bold")).pack(anchor="w", padx=12, pady=(14, 0))
                if t.category in CATEGORY_NOTES:
                    ctk.CTkLabel(sc, text=CATEGORY_NOTES[t.category], text_color=MUTED).pack(anchor="w", padx=12)
                last = t.category
            row = card(sc)
            row.pack(fill="x", padx=8, pady=4)
            var = ctk.BooleanVar(value=self.safe_applied(t))
            ctk.CTkSwitch(row, text="", width=44, variable=var, progress_color=PURPLE,
                          command=lambda t=t, v=var: self.toggle(t, v)).pack(side="left", padx=(14, 6), pady=14)
            info = ctk.CTkFrame(row, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True, pady=8)
            ctk.CTkLabel(info, text=t.name, font=(FONT, 14, "bold"), anchor="w", text_color=TEXT).pack(anchor="w")
            ctk.CTkLabel(info, text=t.desc + (f"  ⚠ {t.note}" if t.note else ""), text_color=MUTED,
                         wraplength=560, justify="left", anchor="w").pack(anchor="w")
            button(row, "Ver comando", lambda t=t: self.show_cmd(t), width=100).pack(side="right", padx=14)

    @staticmethod
    def safe_applied(t):
        try:
            return tweaks.is_applied(t)
        except Exception:
            return False

    def toggle(self, t, var):
        try:
            tweaks.apply(t) if var.get() else tweaks.revert(t)
        except Exception as e:
            var.set(not var.get())
            mb.showerror("MelbyTune", f"Não foi possível alterar '{t.name}'.\n\n{e}")

    def show_cmd(self, t):
        win = ctk.CTkToplevel(self)
        win.title(t.name)
        win.geometry("760x260")
        win.attributes("-topmost", True)
        box = ctk.CTkTextbox(win, font=("Consolas", 12), fg_color=PANEL)
        box.pack(fill="both", expand=True, padx=12, pady=12)
        box.insert("1.0", tweaks.preview(t) + "\n\n# Desfazer: desligue a chave (restaura o valor original salvo).")
        box.configure(state="disabled")

    # ---------------------------------------------------------------- sistema
    def build_sistema(self, p):
        title(p, "Sistema", "Segurança e plano de energia.")
        c1 = card(p)
        c1.pack(fill="x", padx=24, pady=6)
        ctk.CTkLabel(c1, text="Ponto de restauração", font=(FONT, 15, "bold"), text_color=TEXT).pack(
            anchor="w", padx=16, pady=(12, 0))
        ctk.CTkLabel(c1, text="Crie antes de aplicar ajustes. O Windows limita a 1 ponto a cada 24h "
                              "e precisa da Proteção do Sistema ligada.", text_color=MUTED,
                     wraplength=700, justify="left").pack(anchor="w", padx=16)
        button(c1, "Criar ponto de restauração", self.do_restore_point, kind="primary").pack(
            anchor="w", padx=16, pady=12)

        c2 = card(p)
        c2.pack(fill="x", padx=24, pady=6)
        ctk.CTkLabel(c2, text="Plano de energia de alto desempenho", font=(FONT, 15, "bold"),
                     text_color=TEXT).pack(anchor="w", padx=16, pady=(12, 0))
        ctk.CTkLabel(c2, text="Ativa o plano Desempenho Máximo. Desligar volta pro plano que estava antes. "
                              "Em notebook, gasta mais bateria.", text_color=MUTED,
                     wraplength=700, justify="left").pack(anchor="w", padx=16)
        self.power_var = ctk.BooleanVar(value=self.safe_power())
        ctk.CTkSwitch(c2, text="Ativado", variable=self.power_var, progress_color=PURPLE,
                      command=self.toggle_power).pack(anchor="w", padx=16, pady=12)

        c3 = card(p)
        c3.pack(fill="x", padx=24, pady=6)
        ctk.CTkLabel(c3, text="Desfazer tudo", font=(FONT, 15, "bold"), text_color=TEXT).pack(
            anchor="w", padx=16, pady=(12, 0))
        ctk.CTkLabel(c3, text="Volta todos os ajustes e o plano de energia ao que era antes do MelbyTune. "
                              "(Não reinstala apps do Debloat nem religa a inicialização: use as abas deles.)",
                     text_color=MUTED, wraplength=700, justify="left").pack(anchor="w", padx=16)
        button(c3, "Restaurar tudo", self.do_revert_all, kind="danger").pack(anchor="w", padx=16, pady=12)

    @staticmethod
    def safe_power():
        try:
            return tweaks.power_applied()
        except Exception:
            return False

    def toggle_power(self):
        try:
            tweaks.power_apply() if self.power_var.get() else tweaks.power_revert()
        except Exception as e:
            self.power_var.set(not self.power_var.get())
            mb.showerror("MelbyTune", str(e))

    def do_restore_point(self):
        def work():
            ok, msg = tweaks.create_restore_point()
            text = "Ponto de restauração criado." if ok else f"Não foi possível criar:\n{msg}"
            self.after(0, lambda: mb.showinfo("MelbyTune", text))
        threading.Thread(target=work, daemon=True).start()

    def do_revert_all(self):
        if not mb.askyesno("MelbyTune", "Desfazer todos os ajustes feitos pelo MelbyTune?"):
            return
        tweaks.revert_all()
        mb.showinfo("MelbyTune", "Tudo restaurado. Reabra o app pra atualizar as chaves.")


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
            app.after(1500, app.quit)
    app.after(800, step)
    app.mainloop()
    app.destroy()
    with open(out, "w", encoding="utf-8") as f:
        f.write(("ERROS:\n" + "\n".join(errs)) if errs else f"OK - {len(names)} telas abriram sem erro")
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
