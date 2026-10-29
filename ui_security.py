"""Aba Segurança: Microsoft Defender (antivírus) e reparo de arquivos do Windows."""
import tkinter.messagebox as mb
from tkinter import filedialog

import customtkinter as ctk

import security
from theme import BAD, GOOD, HONEY, MUTED, PANEL, TEXT, FONT, LogBox, button, card, in_thread, tabs, title


class _Feed:
    """Quebra a saída dos comandos em linhas; linhas de progresso (com %) vão pra barra de status."""

    def __init__(self, log, status):
        self.log, self.status, self.buf = log, status, ""

    def __call__(self, text):
        self.buf += text.replace("\r\n", "\n").replace("\r", "\n")
        *lines, self.buf = self.buf.split("\n")
        for ln in lines:
            ln = ln.strip()
            if not ln:
                continue
            if "%" in ln:
                self.status(ln)
            else:
                self.log.write(ln)
        if "%" in self.buf:
            self.status(self.buf.strip())


class SecurityPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        title(self, "Segurança", "Antivírus (Microsoft Defender) e reparo de arquivos do Windows.")
        tv = tabs(self, ["Antivírus", "Reparar Windows"])
        tv.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        self.busy = False
        self.buttons = []
        self._av(tv.tab("Antivírus"))
        self._repair(tv.tab("Reparar Windows"))
        self.after(400, self.refresh_status)

    def set_busy(self, busy):
        self.busy = busy
        for b in self.buttons:
            b.configure(state="disabled" if busy else "normal")

    def _btn(self, parent, text, cmd, kind="ghost"):
        b = button(parent, text, cmd, kind=kind)
        self.buttons.append(b)
        return b

    # -------------------------------------------------------------- antivírus
    def _av(self, tab):
        ctk.CTkLabel(tab, wraplength=780, justify="left", text_color=MUTED,
                     text="O MelbyTune usa o Microsoft Defender, que já vem no Windows. Ele não é um antivírus "
                          "próprio: só comanda o Defender e mostra o resultado. Se você usa outro antivírus, o "
                          "Defender fica em modo passivo e as análises podem não funcionar.").pack(anchor="w", pady=(4, 8))
        c = card(tab)
        c.pack(fill="x", pady=4)
        self.lbl = {}
        for key, text in (("rt", "Proteção em tempo real"), ("sig", "Definições de vírus"),
                          ("scan", "Última análise rápida"), ("mode", "Modo")):
            row = ctk.CTkFrame(c, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=3)
            ctk.CTkLabel(row, text=text, width=190, anchor="w", text_color=MUTED).pack(side="left")
            self.lbl[key] = ctk.CTkLabel(row, text="...", anchor="w", font=(FONT, 13, "bold"), text_color=TEXT)
            self.lbl[key].pack(side="left")
        ctk.CTkFrame(c, height=6, fg_color="transparent").pack()

        r1 = ctk.CTkFrame(tab, fg_color="transparent")
        r1.pack(fill="x", pady=(10, 4))
        self._btn(r1, "Análise rápida", self.scan_quick, "primary").pack(side="left")
        self._btn(r1, "Analisar uma pasta...", self.scan_folder).pack(side="left", padx=8)
        self._btn(r1, "Análise completa", self.scan_full).pack(side="left")
        self._btn(r1, "Atualizar definições", self.update_defs).pack(side="left", padx=8)
        r2 = ctk.CTkFrame(tab, fg_color="transparent")
        r2.pack(fill="x", pady=(0, 6))
        self._btn(r2, "Ver ameaças", self.show_threats).pack(side="left")
        self._btn(r2, "Remover ameaças ativas", self.remove_threats, "danger").pack(side="left", padx=8)
        button(r2, "Abrir Segurança do Windows", security.open_windows_security).pack(side="left")
        self.av_log = LogBox(tab)
        self.av_log.pack(fill="both", expand=True, pady=(4, 6))

    def refresh_status(self):
        def work():
            s = security.status()
            self.after(0, lambda: self.show_status(s))
        in_thread(work)

    def show_status(self, s):
        if not s:
            for k in self.lbl:
                self.lbl[k].configure(text="indisponível (só no Windows com Defender)", text_color=MUTED)
            return
        rt = s.get("RealTimeProtectionEnabled")
        self.lbl["rt"].configure(text="✔ Ligada" if rt else "✘ Desligada", text_color=GOOD if rt else BAD)
        age = s.get("AntivirusSignatureAge")
        if age is None:
            self.lbl["sig"].configure(text="não sei", text_color=MUTED)
        else:
            self.lbl["sig"].configure(text="✔ em dia" if age <= 3 else f"! desatualizadas há {age} dias",
                                      text_color=GOOD if age <= 3 else HONEY)
        q = s.get("QuickScanAge")
        self.lbl["scan"].configure(text="nunca" if q in (None, 4294967295) else f"há {q} dia(s)", text_color=TEXT)
        self.lbl["mode"].configure(text=str(s.get("AMRunningMode") or "Normal"), text_color=TEXT)

    def _run(self, label, fn, then_threats=False):
        if self.busy:
            return
        self.set_busy(True)
        self.av_log.write(f"▶ {label}...")

        def work():
            try:
                ok, err = fn()
            except Exception as e:
                ok, err = False, str(e)
            self.av_log.write("✔ Terminou." if ok else f"✘ Não deu certo. {err}")
            if then_threats and ok:
                self._threats_text()
            self.after(0, lambda: self.set_busy(False))
            self.refresh_status()
        in_thread(work)

    def update_defs(self):
        self._run("Atualizando as definições de vírus", security.update_signatures)

    def scan_quick(self):
        self._run("Análise rápida (alguns minutos)", lambda: security.scan("quick"), True)

    def scan_full(self):
        if mb.askyesno("MelbyTune", "A análise completa pode levar de 30 minutos a algumas horas "
                                    "e deixa o PC mais lento. Continuar?"):
            self._run("Análise completa", lambda: security.scan("full"), True)

    def scan_folder(self):
        d = filedialog.askdirectory(title="Escolha a pasta pra analisar")
        if d:
            self._run(f"Analisando {d}", lambda: security.scan("custom", d), True)

    def _threats_text(self):
        items = security.threats()
        if not items:
            self.av_log.write("Nenhuma ameaça registrada pelo Defender.")
            return
        for t in items:
            sev = security.SEVERITY.get(t.get("SeverityID"), "?")
            state = "ATIVA" if t.get("IsActive") else "já tratada"
            self.av_log.write(f"• {t.get('ThreatName')} — gravidade {sev} — {state}\n    {t.get('Resources') or ''}")

    def show_threats(self):
        if self.busy:
            return
        self.set_busy(True)

        def work():
            self.av_log.write("▶ Ameaças registradas:")
            self._threats_text()
            self.after(0, lambda: self.set_busy(False))
        in_thread(work)

    def remove_threats(self):
        if mb.askyesno("MelbyTune", "Pedir pro Defender remover as ameaças ativas? "
                                    "Ele pode mandar arquivos pra quarentena ou apagar."):
            self._run("Removendo ameaças ativas", security.remove_threats)

    # ----------------------------------------------------------------- reparo
    def _repair(self, tab):
        ctk.CTkLabel(tab, wraplength=780, justify="left", text_color=MUTED,
                     text="Conserta arquivos do Windows corrompidos e erros do disco. NÃO recupera arquivos seus "
                          "(fotos, documentos) que estejam corrompidos. Leva de 10 a 40 minutos; não feche o "
                          "app e deixe o notebook na tomada.").pack(anchor="w", pady=(4, 8))
        r1 = ctk.CTkFrame(tab, fg_color="transparent")
        r1.pack(fill="x", pady=4)
        self._btn(r1, "Reparo completo (recomendado)", lambda: self.run_steps(security.FULL_REPAIR), "primary").pack(side="left")
        r2 = ctk.CTkFrame(tab, fg_color="transparent")
        r2.pack(fill="x", pady=4)
        self._btn(r2, "Só DISM", lambda: self.run_steps(["dism"])).pack(side="left")
        self._btn(r2, "Só SFC", lambda: self.run_steps(["sfc"])).pack(side="left", padx=8)
        self._btn(r2, "Só verificar o disco", lambda: self.run_steps(["chkdsk"])).pack(side="left")
        self._btn(r2, "Agendar reparo do disco (reinicia)", self.sched_chkdsk).pack(side="left", padx=8)
        self.rep_status = ctk.CTkLabel(tab, text="", text_color=HONEY)
        self.rep_status.pack(anchor="w", pady=(6, 0))
        self.rep_log = LogBox(tab)
        self.rep_log.pack(fill="both", expand=True, pady=6)

    def _feed(self):
        return _Feed(self.rep_log, lambda s: self.after(0, lambda: self.rep_status.configure(text=s)))

    def run_steps(self, keys):
        if self.busy:
            return
        names = "\n".join("• " + security.REPAIR_STEPS[k][0] for k in keys)
        if not mb.askyesno("MelbyTune", f"Vou rodar:\n\n{names}\n\nPode demorar bastante. Continuar?"):
            return
        self.set_busy(True)
        self.rep_log.clear()
        feed = self._feed()

        def work():
            for k in keys:
                label, cmd = security.REPAIR_STEPS[k]
                self.rep_log.write(f"\n▶ {label}")
                rc = security.stream(cmd, feed)
                self.rep_log.write(f"  terminou (código {rc})")
            self.rep_log.write("\n✔ Tudo terminado. Se algo foi consertado, reinicie o PC.")
            self.after(0, lambda: (self.rep_status.configure(text=""), self.set_busy(False)))
        in_thread(work)

    def sched_chkdsk(self):
        if not mb.askyesno("MelbyTune", "Agendar a verificação e o reparo do disco pro próximo boot? "
                                        "O Windows vai demorar mais pra ligar uma vez."):
            return
        if self.busy:
            return
        self.set_busy(True)
        feed = self._feed()

        def work():
            self.rep_log.write("\n▶ Agendando reparo do disco")
            security.schedule_chkdsk_fix(feed)
            self.rep_log.write("✔ Agendado. Reinicie o PC pra rodar.")
            self.after(0, lambda: self.set_busy(False))
        in_thread(work)
