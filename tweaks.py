"""Ajustes do Windows do MelbyTune.

Todo ajuste de registro guarda o valor ORIGINAL em %APPDATA%\\MelbyTune\\backup.json
antes de mexer, então dá pra desfazer exatamente como estava.
"""
import json
import os
import re
import subprocess
from dataclasses import dataclass, field

try:
    import winreg
except ImportError:  # permite checar sintaxe fora do Windows
    winreg = None

APP_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "MelbyTune")
BACKUP_FILE = os.path.join(APP_DIR, "backup.json")
NOWIN = 0x08000000 if os.name == "nt" else 0  # esconde janela de console
os.makedirs(APP_DIR, exist_ok=True)


def run(cmd, timeout=60):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                          creationflags=NOWIN, errors="ignore")


# ----------------------------------------------------------------- registro
@dataclass
class Tweak:
    id: str
    name: str
    desc: str
    category: str
    values: list = field(default_factory=list)  # (hive, path, nome, tipo, valor)
    note: str = ""


def _hive(h):
    return {"HKLM": winreg.HKEY_LOCAL_MACHINE, "HKCU": winreg.HKEY_CURRENT_USER}[h]


def _rtype(t):
    return {"DWORD": winreg.REG_DWORD, "SZ": winreg.REG_SZ}[t]


def read_value(hive, path, name):
    try:
        with winreg.OpenKey(_hive(hive), path, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as k:
            return winreg.QueryValueEx(k, name)[0]
    except OSError:
        return None


def write_value(hive, path, name, vtype, value):
    with winreg.CreateKeyEx(_hive(hive), path, 0,
                            winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as k:
        winreg.SetValueEx(k, name, 0, _rtype(vtype), value)


def delete_value(hive, path, name):
    try:
        with winreg.OpenKey(_hive(hive), path, 0,
                            winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as k:
            winreg.DeleteValue(k, name)
    except OSError:
        pass


def _load():
    try:
        with open(BACKUP_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save(data):
    with open(BACKUP_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def is_applied(t: Tweak):
    return all(str(read_value(h, p, n)) == str(v) for h, p, n, _, v in t.values)


def apply(t: Tweak):
    bkp = _load()
    if t.id not in bkp:  # só guarda o original na primeira vez
        bkp[t.id] = [{"hive": h, "path": p, "name": n, "type": ty,
                      "original": read_value(h, p, n)} for h, p, n, ty, _ in t.values]
        _save(bkp)
    for h, p, n, ty, v in t.values:
        write_value(h, p, n, ty, v)


def revert(t: Tweak):
    bkp = _load()
    for e in bkp.get(t.id, []):
        if e["original"] is None:
            delete_value(e["hive"], e["path"], e["name"])
        else:
            write_value(e["hive"], e["path"], e["name"], e["type"], e["original"])
    bkp.pop(t.id, None)
    _save(bkp)


def preview(t: Tweak):
    """Comandos equivalentes, pra mostrar antes de rodar."""
    lines = []
    for h, p, n, ty, v in t.values:
        full = ("HKEY_LOCAL_MACHINE" if h == "HKLM" else "HKEY_CURRENT_USER") + "\\" + p
        lines.append(f'reg add "{full}" /v "{n}" /t REG_{ty} /d {v} /f')
    return "\n".join(lines)


def revert_all():
    bkp = _load()
    by_id = {t.id: t for t in TWEAKS}
    for tid in list(bkp.keys()):
        if tid in by_id:
            revert(by_id[tid])
    if "_power" in _load():
        power_revert()


# ------------------------------------------------------------ plano de energia
HIGH_PERF = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
ULTIMATE = "e9a42b02-d5df-448d-aa00-03f14749eb61"
_GUID = re.compile(r"([0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12})")


def active_scheme():
    m = _GUID.search(run(["powercfg", "/getactivescheme"]).stdout)
    return m.group(1) if m else None


def power_applied():
    return "_power" in _load()


def power_apply():
    bkp = _load()
    if "_power" not in bkp:
        bkp["_power"] = active_scheme()
        _save(bkp)
    m = _GUID.search(run(["powercfg", "-duplicatescheme", ULTIMATE]).stdout)
    new = m.group(1) if m else HIGH_PERF  # fallback: Alto desempenho
    run(["powercfg", "/setactive", new])


def power_revert():
    bkp = _load()
    orig = bkp.pop("_power", None)
    if orig:
        run(["powercfg", "/setactive", orig])
    _save(bkp)


# --------------------------------------------------------- ponto de restauração
def create_restore_point():
    r = run(["powershell", "-NoProfile", "-Command",
             "Checkpoint-Computer -Description 'MelbyTune' -RestorePointType MODIFY_SETTINGS"],
            timeout=180)
    return r.returncode == 0, (r.stderr or r.stdout).strip()


# ------------------------------------------------------------------- lista
CV = r"Software\Microsoft\Windows\CurrentVersion"
MM = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile"

TWEAKS = [
    # ---- Jogos
    Tweak("game_mode", "Modo Jogo ligado",
          "Prioriza o jogo em primeiro plano e evita atualizações no meio da partida.", "Jogos",
          [("HKCU", r"Software\Microsoft\GameBar", "AutoGameModeEnabled", "DWORD", 1)]),
    Tweak("game_dvr", "Desligar captura em segundo plano (Game DVR)",
          "Para de gravar clipes em background, que consome CPU/GPU.", "Jogos",
          [("HKCU", r"System\GameConfigStore", "GameDVR_Enabled", "DWORD", 0),
           ("HKCU", CV + r"\GameDVR", "AppCaptureEnabled", "DWORD", 0)]),
    Tweak("game_priority", "Prioridade alta pra jogos",
          "Aumenta prioridade de CPU/GPU da tarefa 'Games' e tira o limite de rede do multimídia.",
          "Jogos",
          [("HKLM", MM + r"\Tasks\Games", "GPU Priority", "DWORD", 8),
           ("HKLM", MM + r"\Tasks\Games", "Priority", "DWORD", 6),
           ("HKLM", MM + r"\Tasks\Games", "Scheduling Category", "SZ", "High"),
           ("HKLM", MM + r"\Tasks\Games", "SFIO Priority", "SZ", "High"),
           ("HKLM", MM, "NetworkThrottlingIndex", "DWORD", 4294967295),
           ("HKLM", MM, "SystemResponsiveness", "DWORD", 0)]),
    Tweak("hags", "Agendamento de GPU acelerado por hardware",
          "Deixa a placa gerenciar a própria memória de vídeo. Só em GPUs/drivers recentes.",
          "Jogos",
          [("HKLM", r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers", "HwSchMode", "DWORD", 2)],
          note="Precisa reiniciar o PC."),
    Tweak("mouse_accel", "Desligar aceleração do mouse",
          "Mira 1:1, o movimento da mão vira o movimento do cursor.", "Jogos",
          [("HKCU", r"Control Panel\Mouse", "MouseSpeed", "SZ", "0"),
           ("HKCU", r"Control Panel\Mouse", "MouseThreshold1", "SZ", "0"),
           ("HKCU", r"Control Panel\Mouse", "MouseThreshold2", "SZ", "0")],
          note="Vale depois de sair e entrar na conta."),
    # ---- Privacidade e processos
    Tweak("telemetry", "Reduzir telemetria",
          "Limita o envio de dados de diagnóstico e desativa o serviço DiagTrack.", "Privacidade",
          [("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\DataCollection", "AllowTelemetry", "DWORD", 0),
           ("HKLM", r"SYSTEM\CurrentControlSet\Services\DiagTrack", "Start", "DWORD", 4)],
          note="Serviço só para no próximo boot."),
    Tweak("ads", "Tirar anúncios e sugestões do Windows",
          "Remove sugestões no Iniciar e dicas que aparecem sozinhas.", "Privacidade",
          [("HKCU", CV + r"\ContentDeliveryManager", "SystemPaneSuggestionsEnabled", "DWORD", 0),
           ("HKCU", CV + r"\ContentDeliveryManager", "SubscribedContent-338388Enabled", "DWORD", 0),
           ("HKCU", CV + r"\ContentDeliveryManager", "SubscribedContent-338389Enabled", "DWORD", 0),
           ("HKCU", CV + r"\ContentDeliveryManager", "SoftLandingEnabled", "DWORD", 0)]),
    Tweak("bg_apps", "Bloquear apps em segundo plano",
          "Apps da Store param de rodar escondidos consumindo RAM e CPU.", "Privacidade",
          [("HKCU", CV + r"\BackgroundAccessApplications", "GlobalUserDisabled", "DWORD", 1)]),
    Tweak("delivery_opt", "Desligar Otimização de Entrega",
          "O Windows para de usar sua internet pra enviar updates a outros PCs.", "Privacidade",
          [("HKLM", CV + r"\DeliveryOptimization\Config", "DODownloadMode", "DWORD", 0)]),
    # ---- Sistema
    Tweak("sysmain", "Desligar SysMain (Superfetch)",
          "Menos uso de disco/RAM em segundo plano. Use só se o Windows estiver em SSD.", "Sistema",
          [("HKLM", r"SYSTEM\CurrentControlSet\Services\SysMain", "Start", "DWORD", 4)],
          note="Não use em HD. Vale no próximo boot."),
    Tweak("startup_delay", "Tirar atraso dos apps de inicialização",
          "Programas do startup abrem sem esperar o Windows 'respirar'.", "Sistema",
          [("HKCU", CV + r"\Explorer\Serialize", "StartupDelayInMSec", "DWORD", 0)]),
    Tweak("menu_delay", "Menus mais rápidos",
          "Zera o atraso pra abrir menus.", "Sistema",
          [("HKCU", r"Control Panel\Desktop", "MenuShowDelay", "SZ", "0")]),
    Tweak("transparency", "Desligar transparência",
          "Menos efeito visual, ganha um pouco de GPU em PC fraco.", "Sistema",
          [("HKCU", CV + r"\Themes\Personalize", "EnableTransparency", "DWORD", 0)]),
]
