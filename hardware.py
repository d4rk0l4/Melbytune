"""Escaneia o PC: processador, memória, placa(s) de vídeo, disco, sistema e temperatura.

No Windows usa o PowerShell (CIM) e o registro. Fora do Windows (só pra testes) cai pro psutil.
"""
import json
import os
import platform
import re
import shutil
import subprocess

import psutil

from gpus import is_integrated
from tweaks import NOWIN, run

try:
    import winreg
except ImportError:
    winreg = None

GB = 1024 ** 3
_CLASS_GPU = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11cd-bfc1-08002be10318}"

_SCAN_PS = r"""
$ErrorActionPreference = 'SilentlyContinue'
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1 Name,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed
$gpu = @(Get-CimInstance Win32_VideoController | Select-Object Name,AdapterRAM)
$os  = Get-CimInstance Win32_OperatingSystem | Select-Object Caption,BuildNumber
$cs  = Get-CimInstance Win32_ComputerSystem | Select-Object Manufacturer,Model,PCSystemType,TotalPhysicalMemory
$mem = @(Get-CimInstance Win32_PhysicalMemory | Select-Object Capacity,Speed)
$disk = $null
try { $disk = Get-Partition -DriveLetter ($env:SystemDrive.Substring(0,1)) | Get-Disk | Get-PhysicalDisk | Select-Object -First 1 @{n='MediaType';e={[string]$_.MediaType}},@{n='BusType';e={[string]$_.BusType}},FriendlyName,Size } catch {}
[pscustomobject]@{cpu=$cpu;gpu=$gpu;os=$os;cs=$cs;mem=$mem;disk=$disk} | ConvertTo-Json -Depth 4 -Compress
"""


def _list(x):
    if x is None:
        return []
    return x if isinstance(x, list) else [x]


def clean_cpu_name(name):
    """'Intel(R) Core(TM) i5-10400F CPU @ 2.90GHz' -> 'Intel Core i5-10400F'."""
    n = (name or "").replace("(R)", "").replace("(TM)", "").replace("(tm)", "").replace("(r)", "")
    n = re.sub(r"\s*@\s*[\d.]+\s*GHz", "", n)
    n = re.sub(r"\b(CPU|Processor)\b", "", n)
    n = re.sub(r"\s*\d+-Core\b", "", n)
    n = re.sub(r"\bwith Radeon.*$", "", n, flags=re.I)
    return re.sub(r"\s+", " ", n).strip()


def _vram_registry():
    """VRAM dedicada por placa, lida do registro (a leitura do WMI trava em 4 GB)."""
    out = {}
    if winreg is None:
        return out
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, _CLASS_GPU, 0,
                            winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as root:
            i = 0
            while True:
                try:
                    sub = winreg.EnumKey(root, i)
                except OSError:
                    break
                i += 1
                if not sub.isdigit():
                    continue
                try:
                    with winreg.OpenKey(root, sub) as k:
                        desc = winreg.QueryValueEx(k, "DriverDesc")[0]
                        mem = winreg.QueryValueEx(k, "HardwareInformation.qwMemorySize")[0]
                        if isinstance(mem, (bytes, bytearray)):
                            mem = int.from_bytes(mem[:8], "little")
                        out[str(desc)] = int(mem)
                except OSError:
                    continue
    except OSError:
        pass
    return out


def _nvidia():
    """{nome: VRAM em GB} lido do nvidia-smi (que vem junto com o driver)."""
    if not shutil.which("nvidia-smi"):
        return {}
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=5, creationflags=NOWIN).stdout
        res = {}
        for ln in out.splitlines():
            if "," in ln:
                name, mib = ln.rsplit(",", 1)
                res[name.strip()] = round(float(mib) / 1024, 1)
        return res
    except Exception:
        return {}


def _disk_kind(disk):
    """'SSD', 'HDD' ou None (quando o Windows não informa). Aceita texto ou o número do enum."""
    media = str((disk or {}).get("MediaType") or "").strip().upper()
    bus = str((disk or {}).get("BusType") or "").strip().upper()
    if media in ("SSD", "4"):
        return "SSD"
    if media in ("HDD", "3"):
        return "HDD"
    if bus in ("NVME", "17"):
        return "SSD"
    return None


def _drive_info():
    drive = os.environ.get("SystemDrive", "C:") + "\\" if os.name == "nt" else "/"
    try:
        u = psutil.disk_usage(drive)
        total, free = u.total / GB, u.free / GB
    except OSError:
        total = free = 0.0
    best = free
    try:
        for p in psutil.disk_partitions(all=False):
            if "cdrom" in (p.opts or "").lower():
                continue
            try:
                best = max(best, psutil.disk_usage(p.mountpoint).free / GB)
            except OSError:
                pass
    except Exception:
        pass
    return drive.rstrip("\\"), total, free, best


def _scan_windows():
    r = run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
             "[Console]::OutputEncoding=[Text.Encoding]::UTF8; " + _SCAN_PS], timeout=40)
    try:
        return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else {}
    except ValueError:
        return {}


def _linux_cpu_name():
    try:
        with open("/proc/cpuinfo", encoding="utf-8") as f:
            for ln in f:
                if ln.lower().startswith("model name"):
                    return ln.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or "Processador desconhecido"


def scan():
    """Retorna um dicionário com o hardware do PC (valores que não deu pra ler ficam None)."""
    data = _scan_windows() if os.name == "nt" else {}
    cpu = data.get("cpu") or {}
    cs = data.get("cs") or {}
    osd = data.get("os") or {}
    disk = data.get("disk") or {}

    cores = cpu.get("NumberOfCores") or psutil.cpu_count(logical=False) or 1
    threads = cpu.get("NumberOfLogicalProcessors") or psutil.cpu_count(logical=True) or cores
    mhz = cpu.get("MaxClockSpeed")
    if not mhz:
        try:
            mhz = psutil.cpu_freq().max or psutil.cpu_freq().current
        except Exception:
            mhz = 0
    ram_gb = round(psutil.virtual_memory().total / GB, 1)

    # --- placas de vídeo
    nv = _nvidia()
    vram_reg = _vram_registry()
    gpus = []
    for g in _list(data.get("gpu")):
        name = (g.get("Name") or "").strip()
        if not name:
            continue
        integrated = is_integrated(name)
        vram = None
        for k, v in nv.items():
            if k.lower() in name.lower() or name.lower() in k.lower():
                vram = v
        if vram is None and name in vram_reg and vram_reg[name] > 0:
            vram = round(vram_reg[name] / GB, 1)
        if vram is None:
            ar = g.get("AdapterRAM") or 0
            if 0 < ar < 4 * GB - 1024 ** 2:  # abaixo do teto de 4 GB do WMI o valor é confiável
                vram = round(ar / GB, 1)
        gpus.append({"name": name, "vram_gb": vram, "integrated": integrated})
    if not gpus and nv:
        gpus = [{"name": n, "vram_gb": v, "integrated": False} for n, v in nv.items()]
    discrete = [g for g in gpus if not g["integrated"]]
    main = (discrete or gpus or [None])[0]

    drive, total, free, best = _drive_info()
    kind = _disk_kind(disk)

    cs_model = " ".join(x for x in (cs.get("Manufacturer"), cs.get("Model")) if x)
    return {
        "cpu_name": clean_cpu_name(cpu.get("Name") or _linux_cpu_name()),
        "cores": int(cores), "threads": int(threads), "ghz": round((mhz or 0) / 1000, 2),
        "ram_gb": ram_gb,
        "gpus": gpus, "gpu_main": main,
        "os": re.sub(r"^Microsoft\s+", "", osd.get("Caption") or f"{platform.system()} {platform.release()}"),
        "os_build": int(osd["BuildNumber"]) if str(osd.get("BuildNumber") or "").isdigit() else None,
        "machine": cs_model or None,
        "laptop": cs.get("PCSystemType") == 2,
        "disk_drive": drive, "disk_total_gb": round(total, 1), "disk_free_gb": round(free, 1),
        "disk_free_best_gb": round(best, 1), "disk_kind": kind,
    }


_acpi_misses = 0  # leituras seguidas sem sensor: depois de 2, não gasta mais um PowerShell à toa


def read_temps():
    """{'cpu': °C ou None, 'gpu': °C ou None}. A do processador vem da zona térmica do ACPI,
    que existe em muitos notebooks mas não em todos os PCs."""
    global _acpi_misses
    cpu = gpu = None
    if os.name == "nt" and _acpi_misses < 2:
        try:
            r = run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                     "Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature "
                     "-ErrorAction SilentlyContinue | Select-Object -ExpandProperty CurrentTemperature"], timeout=15)
            vals = [(int(x) / 10.0) - 273.15 for x in r.stdout.split() if x.strip().isdigit()]
            vals = [v for v in vals if 5 < v < 120]
            cpu = round(max(vals)) if vals else None
        except Exception:
            cpu = None
        _acpi_misses = 0 if cpu is not None else _acpi_misses + 1
    if shutil.which("nvidia-smi"):
        try:
            out = subprocess.run(["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"],
                                 capture_output=True, text=True, timeout=3, creationflags=NOWIN).stdout
            gpu = int(out.split()[0])
        except Exception:
            gpu = None
    return {"cpu": cpu, "gpu": gpu}
