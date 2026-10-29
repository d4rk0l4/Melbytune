"""Apps de inicialização: lista e liga/desliga do mesmo jeito que o Gerenciador de Tarefas."""
import os
from dataclasses import dataclass

try:
    import winreg
except ImportError:  # permite testar fora do Windows
    winreg = None

RUN = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN32 = r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run"
APPROVED = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved"


@dataclass
class Entry:
    name: str
    command: str
    source: str
    hive: str           # "HKCU" ou "HKLM"
    approved_key: str   # subchave de StartupApproved: Run, Run32 ou StartupFolder
    enabled: bool = True


def _h(hive):
    return winreg.HKEY_CURRENT_USER if hive == "HKCU" else winreg.HKEY_LOCAL_MACHINE


def _state(hive, sub, name):
    """True = ligado. Sem registro em StartupApproved significa ligado."""
    try:
        with winreg.OpenKey(_h(hive), APPROVED + "\\" + sub, 0,
                            winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as k:
            data, _ = winreg.QueryValueEx(k, name)
            return not (data and data[0] & 1)
    except OSError:
        return True


def _run_values(hive, path, label, sub):
    out = []
    try:
        with winreg.OpenKey(_h(hive), path, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as k:
            i = 0
            while True:
                try:
                    name, val, _ = winreg.EnumValue(k, i)
                except OSError:
                    break
                i += 1
                out.append(Entry(name, str(val), label, hive, sub, _state(hive, sub, name)))
    except OSError:
        pass
    return out


def _folder_items(hive, folder, label):
    out = []
    if folder and os.path.isdir(folder):
        for fn in os.listdir(folder):
            if fn.lower() == "desktop.ini":
                continue
            out.append(Entry(fn, os.path.join(folder, fn), label, hive, "StartupFolder",
                             _state(hive, "StartupFolder", fn)))
    return out


def list_entries():
    if winreg is None:
        return []
    appdata = os.environ.get("APPDATA", "")
    common = os.path.join(os.environ.get("PROGRAMDATA", ""), r"Microsoft\Windows\Start Menu\Programs\StartUp")
    items = []
    items += _run_values("HKCU", RUN, "Registro (usuário)", "Run")
    items += _run_values("HKLM", RUN, "Registro (todos os usuários)", "Run")
    items += _run_values("HKLM", RUN32, "Registro (32 bits)", "Run32")
    items += _folder_items("HKCU", os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs\Startup"),
                           "Pasta Inicializar (usuário)")
    items += _folder_items("HKLM", common, "Pasta Inicializar (todos)")
    items.sort(key=lambda e: (not e.enabled, e.name.lower()))
    return items


def set_enabled(entry, enabled):
    if winreg is None:
        raise RuntimeError("Só funciona no Windows.")
    data = (b"\x02" if enabled else b"\x03") + b"\x00" * 11
    with winreg.CreateKeyEx(_h(entry.hive), APPROVED + "\\" + entry.approved_key, 0,
                            winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as k:
        winreg.SetValueEx(k, entry.name, 0, winreg.REG_BINARY, data)
    entry.enabled = enabled
