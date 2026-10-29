"""Segurança: usa o Microsoft Defender (já vem no Windows) e as ferramentas de reparo do próprio Windows.

O MelbyTune NÃO é um antivírus: ele só comanda o Defender e organiza os comandos de reparo.
"""
import codecs
import json
import os
import subprocess

from tweaks import NOWIN

SYSDRIVE = os.environ.get("SystemDrive", "C:")


def ps(command, timeout=120):
    full = ("[Console]::OutputEncoding=[Text.Encoding]::UTF8; $ProgressPreference='SilentlyContinue'; "
            + command)
    try:
        return subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", full],
                              capture_output=True, text=True, encoding="utf-8", errors="replace",
                              timeout=timeout, creationflags=NOWIN)
    except (OSError, subprocess.SubprocessError) as e:
        return subprocess.CompletedProcess([], 127, "", str(e))


def _q(s):
    return "'" + str(s).replace("'", "''") + "'"


def _as_list(stdout):
    stdout = (stdout or "").strip()
    if not stdout:
        return []
    data = json.loads(stdout)
    return data if isinstance(data, list) else [data]


# ------------------------------------------------------------------ Defender
def status():
    """Dict com o estado do Defender, ou None se não estiver disponível."""
    r = ps("Get-MpComputerStatus | Select-Object AMServiceEnabled,RealTimeProtectionEnabled,"
           "AntivirusEnabled,AntivirusSignatureAge,AMRunningMode,QuickScanAge,FullScanAge "
           "| ConvertTo-Json -Compress", 60)
    try:
        items = _as_list(r.stdout)
    except ValueError:
        return None
    return items[0] if r.returncode == 0 and items else None


def update_signatures():
    r = ps("Update-MpSignature", 300)
    return r.returncode == 0, (r.stderr or "").strip()


def scan(kind, path=None):
    """kind: quick, full ou custom. Bloqueia até terminar. Retorna (ok, erro)."""
    if kind == "custom":
        cmd = f"Start-MpScan -ScanType CustomScan -ScanPath {_q(path)}"
    elif kind == "full":
        cmd = "Start-MpScan -ScanType FullScan"
    else:
        cmd = "Start-MpScan -ScanType QuickScan"
    r = ps(cmd, None)
    return r.returncode == 0, (r.stderr or "").strip()


SEVERITY = {1: "baixa", 2: "moderada", 4: "alta", 5: "grave"}


def threats():
    r = ps("Get-MpThreat | Select-Object ThreatName,SeverityID,IsActive,"
           "@{n='Resources';e={$_.Resources -join '; '}} | ConvertTo-Json -Compress", 60)
    try:
        return _as_list(r.stdout)
    except ValueError:
        return []


def remove_threats():
    r = ps("Remove-MpThreat", 300)
    return r.returncode == 0, (r.stderr or "").strip()


def open_windows_security():
    try:
        os.startfile("windowsdefender:")  # type: ignore[attr-defined]
    except Exception:
        pass


# -------------------------------------------------------------------- Reparo
def _oem():
    try:
        import ctypes
        return f"cp{ctypes.windll.kernel32.GetOEMCP()}"
    except Exception:
        return "utf-8"


def stream(cmd, on_text, shell=False):
    """Roda um comando e manda a saída (aos poucos) pra on_text. Retorna o código de saída."""
    try:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             creationflags=NOWIN, shell=shell)
    except OSError as e:
        on_text(f"Não consegui rodar: {e}\n")
        return 127
    dec = None
    while True:
        chunk = p.stdout.read1(512)
        if not chunk:
            break
        if dec is None:  # o SFC escreve em UTF-16; os outros em página OEM
            enc = "utf-16-le" if b"\x00" in chunk[:8] else _oem()
            dec = codecs.getincrementaldecoder(enc)(errors="replace")
        on_text(dec.decode(chunk).replace("﻿", ""))
    return p.wait()


REPAIR_STEPS = {
    "dism": ("Reparar a imagem do Windows (DISM)",
             ["DISM", "/Online", "/Cleanup-Image", "/RestoreHealth"]),
    "sfc": ("Verificar e reparar arquivos do sistema (SFC)", ["sfc", "/scannow"]),
    "chkdsk": ("Verificar o disco (CHKDSK, sem reiniciar)", ["chkdsk", SYSDRIVE, "/scan"]),
}
FULL_REPAIR = ["dism", "sfc", "chkdsk"]  # ordem recomendada


def schedule_chkdsk_fix(on_text):
    """Agenda o reparo do disco pro próximo boot (chkdsk /f)."""
    return stream(f"echo Y| chkdsk {SYSDRIVE} /F", on_text, shell=True)
