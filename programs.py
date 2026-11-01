"""Remoção de programas grandes que não são 'apps da Store': Microsoft Edge e OneDrive.

Os dois têm trava de segurança (só remove se for seguro) e caminho de volta (reinstalar).
"""
import glob
import os

from tweaks import run

try:
    import winreg
except ImportError:  # permite testar fora do Windows
    winreg = None

PF86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
PF = os.environ.get("ProgramFiles", r"C:\Program Files")
LOCAL = os.environ.get("LOCALAPPDATA", "")
WINDIR = os.environ.get("WINDIR", r"C:\Windows")

WINGET = ["--accept-package-agreements", "--accept-source-agreements", "--disable-interactivity"]


def _ver(path):
    """Versão a partir do nome da pasta (ex.: .../Application/131.0.2903.51/Installer/setup.exe)."""
    parts = path.replace("\\", "/").split("/")
    for p in reversed(parts):
        nums = p.split(".")
        if len(nums) >= 2 and all(n.isdigit() for n in nums):
            return tuple(int(n) for n in nums)
    return (0,)


# ----------------------------------------------------------------------- Edge
def _edge_dirs():
    return [os.path.join(b, "Microsoft", "Edge", "Application") for b in (PF86, PF)]


def edge_setup():
    found = []
    for d in _edge_dirs():
        found += glob.glob(os.path.join(d, "*", "Installer", "setup.exe"))
    return max(found, key=_ver) if found else None


def edge_installed():
    return any(os.path.exists(os.path.join(d, "msedge.exe")) for d in _edge_dirs()) or edge_setup() is not None


def other_browsers():
    """Nomes dos outros navegadores achados no PC (pra não deixar o PC sem navegador)."""
    spots = {
        "Chrome": [os.path.join(b, "Google", "Chrome", "Application", "chrome.exe") for b in (PF, PF86, LOCAL)],
        "Firefox": [os.path.join(b, "Mozilla Firefox", "firefox.exe") for b in (PF, PF86)],
        "Brave": [os.path.join(b, "BraveSoftware", "Brave-Browser", "Application", "brave.exe") for b in (PF, PF86, LOCAL)],
        "Opera": [os.path.join(LOCAL, "Programs", n, "opera.exe") for n in ("Opera", "Opera GX")],
        "Vivaldi": [os.path.join(LOCAL, "Vivaldi", "Application", "vivaldi.exe")],
    }
    return [name for name, paths in spots.items() if any(p and os.path.exists(p) for p in paths)]


def edge_remove():
    """Retorna (ok, mensagem). Não força nada: se o Windows bloquear, só avisa."""
    if not edge_installed():
        return True, "O Edge já não está instalado."
    if not other_browsers():
        return False, ("Não achei nenhum outro navegador (Chrome, Firefox, Brave, Opera ou Vivaldi). "
                       "Instale um na aba 'Instalar apps' antes de remover o Edge.")
    setup = edge_setup()
    if not setup:
        return False, "Não achei o desinstalador do Edge neste PC."
    run(["taskkill", "/F", "/IM", "msedge.exe", "/T"], timeout=30)
    r = run([setup, "--uninstall", "--system-level", "--verbose-logging", "--force-uninstall"], timeout=420)
    if not edge_installed():
        return True, "Edge removido. O Windows Update pode instalar de novo numa atualização grande."
    return False, (f"O Windows bloqueou a remoção do Edge (código {r.returncode}). Em muitos PCs e regiões a "
                   "Microsoft não deixa remover por comando. Alternativa: na aba Otimização, ligue 'Edge sem rodar "
                   "em segundo plano', que tira quase todo o peso dele.")


def edge_reinstall():
    r = run(["winget", "install", "--id", "Microsoft.Edge", "-e", "--silent", "--source", "winget"] + WINGET,
            timeout=900)
    return (r.returncode == 0 or edge_installed()), (r.stderr or r.stdout or "").strip()[-200:]


# -------------------------------------------------------------------- OneDrive
def onedrive_setup():
    for sub in ("SysWOW64", "System32"):
        p = os.path.join(WINDIR, sub, "OneDriveSetup.exe")
        if os.path.exists(p):
            return p
    return None


def onedrive_installed():
    spots = [os.path.join(PF, "Microsoft OneDrive", "OneDrive.exe"),
             os.path.join(PF86, "Microsoft OneDrive", "OneDrive.exe"),
             os.path.join(LOCAL, "Microsoft", "OneDrive", "OneDrive.exe")]
    return any(os.path.exists(p) for p in spots)


def onedrive_blocker():
    """Texto explicando por que NÃO dá pra remover agora, ou None se é seguro."""
    if winreg is None:
        return None
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders") as k:
            names = []
            for value in ("Desktop", "Personal", "My Pictures"):
                try:
                    if "onedrive" in str(winreg.QueryValueEx(k, value)[0]).lower():
                        names.append({"Desktop": "Área de Trabalho", "Personal": "Documentos",
                                      "My Pictures": "Imagens"}[value])
                except OSError:
                    pass
    except OSError:
        return None
    if names:
        return ("Suas pastas " + ", ".join(names) + " estão sendo salvas dentro do OneDrive. Se remover agora, "
                "seus arquivos vão parecer sumir (continuam na pasta OneDrive). Desligue antes o backup: ícone "
                "do OneDrive > Configurações > Sincronização e backup.")
    return None


def onedrive_remove():
    if not onedrive_installed():
        return True, "O OneDrive já não está instalado."
    why = onedrive_blocker()
    if why:
        return False, why
    setup = onedrive_setup()
    if not setup:
        return False, "Não achei o desinstalador do OneDrive neste PC."
    run(["taskkill", "/F", "/IM", "OneDrive.exe"], timeout=30)
    run([setup, "/uninstall"], timeout=300)
    if not onedrive_installed():
        return True, "OneDrive removido. Os arquivos que estavam na pasta OneDrive continuam no PC."
    return False, "O desinstalador rodou, mas o OneDrive continua aí. Tente pelas Configurações do Windows > Aplicativos."


def onedrive_reinstall():
    setup = onedrive_setup()
    if setup:
        run([setup], timeout=300)
        if onedrive_installed():
            return True, "OneDrive instalado de novo."
    r = run(["winget", "install", "--id", "Microsoft.OneDrive", "-e", "--silent", "--source", "winget"] + WINGET,
            timeout=900)
    return (r.returncode == 0 or onedrive_installed()), (r.stderr or r.stdout or "").strip()[-200:]
