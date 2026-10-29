"""Instalar vários apps de uma vez usando o winget (já vem no Windows 10/11 atualizado)."""
import shutil
import subprocess

from tweaks import NOWIN

# categoria -> [(id no winget, nome)]
CATALOG = {
    "Navegadores": [
        ("Google.Chrome", "Google Chrome"), ("Mozilla.Firefox", "Firefox"),
        ("Brave.Brave", "Brave"), ("Opera.OperaGX", "Opera GX"),
    ],
    "Comunicação": [
        ("Discord.Discord", "Discord"), ("WhatsApp.WhatsApp", "WhatsApp"),
        ("Telegram.TelegramDesktop", "Telegram"), ("Zoom.Zoom", "Zoom"),
    ],
    "Jogos": [
        ("Valve.Steam", "Steam"), ("EpicGames.EpicGamesLauncher", "Epic Games"),
        ("GOG.Galaxy", "GOG Galaxy"), ("Ubisoft.Connect", "Ubisoft Connect"),
        ("ElectronicArts.EADesktop", "EA app"), ("Blizzard.BattleNet", "Battle.net"),
        ("PrismLauncher.PrismLauncher", "Prism Launcher (Minecraft)"),
        ("Guru3D.Afterburner", "MSI Afterburner"),
    ],
    "Mídia": [
        ("VideoLAN.VLC", "VLC"), ("Spotify.Spotify", "Spotify"),
        ("OBSProject.OBSStudio", "OBS Studio"), ("Audacity.Audacity", "Audacity"),
        ("HandBrake.HandBrake", "HandBrake"), ("ShareX.ShareX", "ShareX (prints e gravação)"),
    ],
    "Utilitários": [
        ("7zip.7zip", "7-Zip"), ("voidtools.Everything", "Everything (busca rápida)"),
        ("Notepad++.Notepad++", "Notepad++"), ("Microsoft.PowerToys", "PowerToys"),
        ("RevoUninstaller.RevoUninstaller", "Revo Uninstaller"), ("WinDirStat.WinDirStat", "WinDirStat"),
        ("qBittorrent.qBittorrent", "qBittorrent"), ("AnyDesk.AnyDesk", "AnyDesk"),
        ("Rufus.Rufus", "Rufus"),
    ],
    "Hardware": [
        ("CPUID.CPU-Z", "CPU-Z"), ("TechPowerUp.GPU-Z", "GPU-Z"),
        ("CPUID.HWMonitor", "HWMonitor"), ("CrystalDewWorld.CrystalDiskInfo", "CrystalDiskInfo"),
    ],
    "Programação": [
        ("Python.Python.3.12", "Python 3.12"), ("Microsoft.VisualStudioCode", "VS Code"),
        ("Git.Git", "Git"), ("OpenJS.NodeJS.LTS", "Node.js LTS"),
        ("GitHub.GitHubDesktop", "GitHub Desktop"), ("EclipseAdoptium.Temurin.21.JDK", "Java 21 (JDK)"),
    ],
    "Documentos": [
        ("Adobe.Acrobat.Reader.64-bit", "Adobe Acrobat Reader"),
        ("TheDocumentFoundation.LibreOffice", "LibreOffice"), ("SumatraPDF.SumatraPDF", "SumatraPDF"),
    ],
    "Runtimes (jogos pedem)": [
        ("Microsoft.VCRedist.2015+.x64", "Visual C++ Redistributable"),
        ("Microsoft.DotNet.DesktopRuntime.8", ".NET Desktop Runtime 8"),
        ("Microsoft.DirectX", "DirectX"),
    ],
}

_COMMON = ["--accept-package-agreements", "--accept-source-agreements", "--disable-interactivity"]


def has_winget():
    return shutil.which("winget") is not None


def _run(cmd, timeout):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=timeout, creationflags=NOWIN)


def installed_ids():
    """Quais itens do catálogo já estão instalados (uma consulta só)."""
    try:
        text = _run(["winget", "list", "--accept-source-agreements", "--disable-interactivity"], 180).stdout.lower()
    except Exception:
        return set()
    return {pid for apps in CATALOG.values() for pid, _ in apps if pid.lower() in text}


def install(pid):
    """Retorna (ok, mensagem)."""
    cmd = ["winget", "install", "--id", pid, "-e", "--silent", "--source", "winget"] + _COMMON
    try:
        r = _run(cmd, 1800)
    except subprocess.TimeoutExpired:
        return False, "demorou demais"
    rc = r.returncode & 0xFFFFFFFF
    if rc == 0:
        return True, "instalado"
    if rc == 3010:
        return True, "instalado (precisa reiniciar o PC)"
    if rc in (0x8A15002B, 0x8A150061):
        return True, "já estava instalado"
    if rc == 0x8A150014:
        return False, "não encontrado no winget"
    return False, f"falhou (código 0x{rc:X})"


def upgrade_all():
    r = _run(["winget", "upgrade", "--all", "--silent", "--source", "winget"] + _COMMON, 3600)
    return r.returncode == 0
