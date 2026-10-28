"""MelbyTune - otimizador de PC pra uso pessoal.

Rode como administrador (o app pede sozinho). Python 3.10+  ->  pip install -r requirements.txt
"""
import ctypes
import os
import shutil
import subprocess
import sys
import threading
import tkinter.messagebox as mb

import customtkinter as ctk
import psutil

import cleaner
import debloat
import tweaks
from gpus import GPUS, detect_gpu

BG, PANEL, ACCENT, MUTED = "#0B0B0E", "#16161B", "#FFC928", "#8C8C96"
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


def gpu_name_windows():
    try:
        r = tweaks.run(["powershell", "-NoProfile", "-Command",
                        "(Get-CimInstance Win32_VideoController | Select-Object -First 1).Name"], timeout=10)
        return r.stdout.strip()
    except Exception:
        return ""


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        self.title("MelbyTune")
        self.geometry("1020x680")
        self.minsize(900, 600)
        self.configure(fg_color=BG)

        self.side = ctk.CTkFrame(self, width=210, fg_color=PANEL, corner_radius=0)
        self.side.pack(side="left", fill="y")
        ctk.CTkLabel(self.side, text="MELBY", font=("Segoe UI", 24, "bold"),
                     text_color=ACCENT).pack(anchor="w", padx=22, pady=(24, 0))
        ctk.CTkLabel(self.side, text="T U N E", font=("Consolas", 12),
                     text_color=MUTED).pack(anchor="w", padx=24, pady=(0, 24))

        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.pack(side="left", fill="both", expand=True)

        self.pages, self.buttons = {}, {}
        for name in ("Painel", "Ajustes", "Limpeza", "Debloat", "Placas de vídeo", "Sistema"):
            b = ctk.CTkButton(self.side, text=name, anchor="w", height=38, corner_radius=8,
                              fg_color="transparent", hover_color="#23232B", text_color="#E6E6EA",
                              command=lambda n=name: self.show(n))
            b.pack(fill="x", padx=12, pady=2)
            self.buttons[name] = b
            self.pages[name] = ctk.CTkFrame(self.body, fg_color="transparent")

        self.cpu_hist = [0] * 60
        self.has_nvidia = bool(shutil.which("nvidia-smi"))
        self.build_painel()
        self.build_ajustes()
        self.build_limpeza()
        self.build_debloat()
        self.build_placas()
        self.build_sistema()
        self.show("Painel")
        self.tick()

    # ------------------------------------------------------------- navegação
    def show(self, name):
        for n, p in self.pages.items():
            p.pack_forget()
            self.buttons[n].configure(fg_color="transparent", text_color="#E6E6EA")
        self.pages[name].pack(fill="both", expand=True)
        self.buttons[name].configure(fg_color=ACCENT, text_color="#111111")

    def title_(self, page, text, sub=""):
        ctk.CTkLabel(page, text=text, font=("Segoe UI", 24, "bold")).pack(anchor="w", padx=24, pady=(22, 0))
        if sub:
            ctk.CTkLabel(page, text=sub, text_color=MUTED, wraplength=700,
                         justify="left").pack(anchor="w", padx=24, pady=(2, 10))

    # ----------------------------------------------------------------- painel
    def build_painel(self):
        p = self.pages["Painel"]
        self.title_(p, "Painel", "Uso do PC em tempo real.")
        grid = ctk.CTkFrame(p, fg_color="transparent")
        grid.pack(fill="x", padx=18)
        self.meters = {}
        for i, key in enumerate(("CPU", "RAM", "Disco", "GPU")):
            card = ctk.CTkFrame(grid, fg_color=PANEL, corner_radius=12)
            card.grid(row=i // 2, column=i % 2, sticky="nsew", padx=6, pady=6)
            grid.grid_columnconfigure(i % 2, weight=1)
            ctk.CTkLabel(card, text=key, text_color=MUTED).pack(anchor="w", padx=16, pady=(12, 0))
            val = ctk.CTkLabel(card, text="--", font=("Segoe UI", 26, "bold"))
            val.pack(anchor="w", padx=16)
            bar = ctk.CTkProgressBar(card, progress_color=ACCENT, height=8)
            bar.set(0)
            bar.pack(fill="x", padx=16, pady=(4, 4))
            det = ctk.CTkLabel(card, text="", text_color=MUTED, font=("Segoe UI", 11))
            det.pack(anchor="w", padx=16, pady=(0, 12))
            self.meters[key] = (val, bar, det)
        box = ctk.CTkFrame(p, fg_color=PANEL, corner_radius=12)
        box.pack(fill="x", padx=24, pady=8)
        ctk.CTkLabel(box, text="CPU - último minuto", text_color=MUTED).pack(anchor="w", padx=16, pady=(10, 0))
        self.canvas = ctk.CTkCanvas(box, height=120, bg=PANEL, highlightthickness=0)
        self.canvas.pack(fill="x", padx=16, pady=(0, 12))

    def tick(self):
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage(os.environ.get("SystemDrive", "C:") + "\\")
        freq = psutil.cpu_freq()
        self.set_meter("CPU", cpu, f"{cpu:.0f}%", f"{freq.current / 1000:.2f} GHz" if freq else "")
        self.set_meter("RAM", ram.percent, f"{ram.percent:.0f}%",
                       f"{ram.used / 2**30:.1f} / {ram.total / 2**30:.1f} GB")
        self.set_meter("Disco", disk.percent, f"{disk.percent:.0f}%",
                       f"{disk.free / 2**30:.0f} GB livres")
        g = nvidia_info() if self.has_nvidia else None
        if g:
            self.set_meter("GPU", g["util"], f"{g['util']:.0f}%",
                           f"{g['name']} · {g['temp']}°C · {g['used']:.0f}/{g['total']:.0f} MB")
        else:
            self.set_meter("GPU", 0, "--", "Leitura disponível só em placas NVIDIA")
        self.cpu_hist = self.cpu_hist[1:] + [cpu]
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
        h = 120
        pts = []
        for i, v in enumerate(self.cpu_hist):
            pts += [i * w / (len(self.cpu_hist) - 1), h - 4 - v / 100 * (h - 8)]
        c.create_line(*pts, fill=ACCENT, width=2, smooth=True)

    # ---------------------------------------------------------------- ajustes
    def build_ajustes(self):
        p = self.pages["Ajustes"]
        self.title_(p, "Ajustes do Windows",
                    "Cada ajuste mostra o comando e pode ser desfeito (o valor original fica salvo). "
                    "Crie um ponto de restauração antes, na aba Sistema.")
        sc = ctk.CTkScrollableFrame(p, fg_color="transparent")
        sc.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        last = None
        for t in tweaks.TWEAKS:
            if t.category != last:
                ctk.CTkLabel(sc, text=t.category.upper(), text_color=ACCENT,
                             font=("Consolas", 12, "bold")).pack(anchor="w", padx=12, pady=(14, 2))
                last = t.category
            row = ctk.CTkFrame(sc, fg_color=PANEL, corner_radius=10)
            row.pack(fill="x", padx=8, pady=4)
            var = ctk.BooleanVar(value=self.safe_applied(t))
            ctk.CTkSwitch(row, text="", width=44, variable=var, progress_color=ACCENT,
                          command=lambda t=t, v=var: self.toggle(t, v)).pack(side="left", padx=(14, 6), pady=14)
            info = ctk.CTkFrame(row, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True, pady=8)
            ctk.CTkLabel(info, text=t.name, font=("Segoe UI", 14, "bold"), anchor="w").pack(anchor="w")
            ctk.CTkLabel(info, text=t.desc + (f"  ⚠ {t.note}" if t.note else ""), text_color=MUTED,
                         wraplength=520, justify="left", anchor="w").pack(anchor="w")
            ctk.CTkButton(row, text="Ver comando", width=100, fg_color="#23232B", hover_color="#2E2E38",
                          command=lambda t=t: self.show_cmd(t)).pack(side="right", padx=14)

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
        box = ctk.CTkTextbox(win, font=("Consolas", 12))
        box.pack(fill="both", expand=True, padx=12, pady=12)
        box.insert("1.0", tweaks.preview(t) + "\n\n# Desfazer: desligue a chave (restaura o valor original salvo).")
        box.configure(state="disabled")

    # ---------------------------------------------------------------- limpeza
    def build_limpeza(self):
        p = self.pages["Limpeza"]
        self.title_(p, "Limpeza", "Apaga só arquivos temporários que o Windows recria sozinho. "
                                  "O que estiver em uso é ignorado.")
        bar = ctk.CTkFrame(p, fg_color="transparent")
        bar.pack(fill="x", padx=24)
        ctk.CTkButton(bar, text="Analisar", fg_color="#23232B", hover_color="#2E2E38",
                      command=self.do_scan).pack(side="left")
        self.btn_clean = ctk.CTkButton(bar, text="Limpar agora", fg_color=ACCENT, text_color="#111",
                                       hover_color="#E6B31F", state="disabled", command=self.do_clean)
        self.btn_clean.pack(side="left", padx=10)
        self.clean_out = ctk.CTkTextbox(p, font=("Consolas", 13), fg_color=PANEL)
        self.clean_out.pack(fill="both", expand=True, padx=24, pady=14)
        self.clean_out.configure(state="disabled")

    def write_clean(self, text):
        self.clean_out.configure(state="normal")
        self.clean_out.delete("1.0", "end")
        self.clean_out.insert("1.0", text)
        self.clean_out.configure(state="disabled")

    def do_scan(self):
        self.write_clean("Analisando...")

        def work():
            res = cleaner.scan()
            total = sum(r[2] for r in res)
            txt = "\n".join(f"{n:<34}{cleaner.fmt(s):>10}" for n, _, s in res)
            txt += f"\n{'-' * 44}\n{'Total':<34}{cleaner.fmt(total):>10}\n\nLixeira também será esvaziada."
            self.after(0, lambda: (self.write_clean(txt), self.btn_clean.configure(state="normal")))
        threading.Thread(target=work, daemon=True).start()

    def do_clean(self):
        if not mb.askyesno("MelbyTune", "Apagar os arquivos temporários listados e esvaziar a lixeira?"):
            return
        self.btn_clean.configure(state="disabled")
        self.write_clean("Limpando...")

        def work():
            freed = 0
            for _, path, _ in cleaner.scan():
                freed += cleaner.clean_folder(path)
            cleaner.empty_recycle_bin()
            self.after(0, lambda: self.write_clean(f"Pronto. Liberado: {cleaner.fmt(freed)} (fora a lixeira)."))
        threading.Thread(target=work, daemon=True).start()

    # ----------------------------------------------------------------- debloat
    def build_debloat(self):
        p = self.pages["Debloat"]
        self.title_(p, "Debloat",
                    "Remove apps que já vêm no Windows. A lista é fixa e segura: não inclui Loja, "
                    "Calculadora, Fotos, Paint nem Edge. Vale pra sua conta. Dá pra tentar reinstalar "
                    "aqui; se não voltar, baixe pela Microsoft Store.")
        bar = ctk.CTkFrame(p, fg_color="transparent")
        bar.pack(fill="x", padx=24)
        ctk.CTkButton(bar, text="Atualizar lista", fg_color="#23232B", hover_color="#2E2E38",
                      command=self.refresh_debloat).pack(side="left")
        ctk.CTkButton(bar, text="Remover marcados", fg_color="#B23A3A", hover_color="#962F2F",
                      command=lambda: self.debloat_action(True)).pack(side="left", padx=10)
        ctk.CTkButton(bar, text="Reinstalar marcados", fg_color=ACCENT, text_color="#111",
                      hover_color="#E6B31F", command=lambda: self.debloat_action(False)).pack(side="left")
        self.deb_status = ctk.CTkLabel(p, text="", text_color=ACCENT)
        self.deb_status.pack(anchor="w", padx=24, pady=(8, 0))
        self.deb_list = ctk.CTkScrollableFrame(p, fg_color=PANEL)
        self.deb_list.pack(fill="both", expand=True, padx=24, pady=10)
        self.deb_vars = {}
        self.deb_installed = set()
        self.refresh_debloat()

    def refresh_debloat(self):
        self.deb_status.configure(text="Lendo apps instalados...")

        def work():
            have = debloat.installed()
            self.after(0, lambda: self.render_debloat(have))
        threading.Thread(target=work, daemon=True).start()

    def render_debloat(self, have):
        self.deb_installed = have
        for w in self.deb_list.winfo_children():
            w.destroy()
        self.deb_vars = {}
        for pkg, label in debloat.APPS:
            row = ctk.CTkFrame(self.deb_list, fg_color="transparent")
            row.pack(fill="x", pady=2)
            var = ctk.BooleanVar(value=False)
            self.deb_vars[pkg] = var
            ctk.CTkCheckBox(row, text=label, variable=var, fg_color=ACCENT,
                            checkmark_color="#111").pack(side="left", padx=8)
            ok = pkg in have
            ctk.CTkLabel(row, text="instalado" if ok else "removido",
                         text_color="#E6E6EA" if ok else MUTED).pack(side="right", padx=12)
        self.deb_status.configure(text="")

    def debloat_action(self, remove):
        marked = [p for p, v in self.deb_vars.items()
                  if v.get() and ((p in self.deb_installed) == remove)]
        if not marked:
            mb.showinfo("MelbyTune", "Marque apps " + ("instalados" if remove else "removidos") + " primeiro.")
            return
        verbo = "Remover" if remove else "Reinstalar"
        if not mb.askyesno("MelbyTune", f"{verbo} {len(marked)} app(s)? Isso pode levar alguns minutos."):
            return
        self.deb_status.configure(text="Trabalhando... não feche o app.")

        def work():
            for pkg in marked:
                (debloat.remove if remove else debloat.reinstall)(pkg)
            have = debloat.installed()
            self.after(0, lambda: self.render_debloat(have))
        threading.Thread(target=work, daemon=True).start()

    # ----------------------------------------------------------------- placas
    def build_placas(self):
        p = self.pages["Placas de vídeo"]
        self.title_(p, "Comparar placas de vídeo",
                    "Desempenho relativo aproximado, lista local (edite em gpus.py). Nada vai pra internet.")
        names = sorted(GPUS, key=GPUS.get, reverse=True)
        mine = detect_gpu(gpu_name_windows())
        row = ctk.CTkFrame(p, fg_color="transparent")
        row.pack(fill="x", padx=24)
        ctk.CTkLabel(row, text="Placa A").grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(row, text="Placa B").grid(row=0, column=1, sticky="w", padx=14)
        self.cmb_a = ctk.CTkComboBox(row, values=names, width=260, command=lambda _: self.update_gpu())
        self.cmb_b = ctk.CTkComboBox(row, values=names, width=260, command=lambda _: self.update_gpu())
        self.cmb_a.grid(row=1, column=0)
        self.cmb_b.grid(row=1, column=1, padx=14)
        self.cmb_a.set(mine or "GeForce RTX 3070")
        self.cmb_b.set("GeForce RTX 4080")
        self.gpu_result = ctk.CTkLabel(p, text="", font=("Segoe UI", 16, "bold"), text_color=ACCENT,
                                       wraplength=700, justify="left")
        self.gpu_result.pack(anchor="w", padx=24, pady=12)
        self.gpu_list = ctk.CTkScrollableFrame(p, fg_color=PANEL)
        self.gpu_list.pack(fill="both", expand=True, padx=24, pady=(0, 16))
        self.update_gpu()

    def update_gpu(self):
        a, b = self.cmb_a.get(), self.cmb_b.get()
        if a not in GPUS or b not in GPUS:
            return
        sa, sb = GPUS[a], GPUS[b]
        diff = (sb / sa - 1) * 100
        if abs(diff) < 1:
            self.gpu_result.configure(text=f"A {a} e a {b} têm desempenho praticamente igual.")
        elif diff > 0:
            self.gpu_result.configure(text=f"A {b} é {diff:.0f}% mais rápida que a {a}.")
        else:
            self.gpu_result.configure(text=f"A {b} é {-diff:.0f}% mais lenta que a {a}.")
        for w in self.gpu_list.winfo_children():
            w.destroy()
        top = max(GPUS.values()) / sa * 100
        for n in sorted(GPUS, key=GPUS.get, reverse=True):
            pct = GPUS[n] / sa * 100
            color = ACCENT if n == b else ("#4DA3FF" if n == a else "#3A3A46")
            line = ctk.CTkFrame(self.gpu_list, fg_color="transparent")
            line.pack(fill="x", pady=2)
            ctk.CTkLabel(line, text=n, width=190, anchor="w").pack(side="left")
            pb = ctk.CTkProgressBar(line, progress_color=color, height=10)
            pb.set(pct / top)
            pb.pack(side="left", fill="x", expand=True, padx=8)
            ctk.CTkLabel(line, text=f"{pct:.0f}%", width=50, anchor="e").pack(side="left")

    # ---------------------------------------------------------------- sistema
    def build_sistema(self):
        p = self.pages["Sistema"]
        self.title_(p, "Sistema", "Segurança e plano de energia.")
        c1 = ctk.CTkFrame(p, fg_color=PANEL, corner_radius=12)
        c1.pack(fill="x", padx=24, pady=6)
        ctk.CTkLabel(c1, text="Ponto de restauração", font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=16, pady=(12, 0))
        ctk.CTkLabel(c1, text="Crie antes de aplicar ajustes. O Windows limita a 1 ponto a cada 24h "
                              "e precisa da Proteção do Sistema ligada.", text_color=MUTED,
                     wraplength=700, justify="left").pack(anchor="w", padx=16)
        ctk.CTkButton(c1, text="Criar ponto de restauração", fg_color=ACCENT, text_color="#111",
                      hover_color="#E6B31F", command=self.do_restore_point).pack(anchor="w", padx=16, pady=12)

        c2 = ctk.CTkFrame(p, fg_color=PANEL, corner_radius=12)
        c2.pack(fill="x", padx=24, pady=6)
        ctk.CTkLabel(c2, text="Plano de energia de alto desempenho", font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=16, pady=(12, 0))
        ctk.CTkLabel(c2, text="Ativa o plano Desempenho Máximo. Desligar volta pro plano que estava antes. "
                              "Em notebook, gasta mais bateria.", text_color=MUTED,
                     wraplength=700, justify="left").pack(anchor="w", padx=16)
        self.power_var = ctk.BooleanVar(value=self.safe_power())
        ctk.CTkSwitch(c2, text="Ativado", variable=self.power_var, progress_color=ACCENT,
                      command=self.toggle_power).pack(anchor="w", padx=16, pady=12)

        c3 = ctk.CTkFrame(p, fg_color=PANEL, corner_radius=12)
        c3.pack(fill="x", padx=24, pady=6)
        ctk.CTkLabel(c3, text="Desfazer tudo", font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=16, pady=(12, 0))
        ctk.CTkLabel(c3, text="Volta todos os ajustes e o plano de energia ao que era antes do MelbyTune.",
                     text_color=MUTED).pack(anchor="w", padx=16)
        ctk.CTkButton(c3, text="Restaurar tudo", fg_color="#B23A3A", hover_color="#962F2F",
                      command=self.do_revert_all).pack(anchor="w", padx=16, pady=12)

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


if __name__ == "__main__":
    ensure_admin()
    App().mainloop()
