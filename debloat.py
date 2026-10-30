"""Debloat: remove apps que vêm pré-instalados no Windows (só da conta atual).

Lista conservadora. NÃO inclui Microsoft Store, Calculadora, Fotos, Paint, Xbox nem Edge (o Edge
tem tratamento próprio em programs.py). Só aparecem na tela os apps que existem no PC.
"""
import json
import os

from tweaks import APP_DIR, run

REMOVED_FILE = os.path.join(APP_DIR, "debloat_removidos.json")

# (grupo, [(nome exato do pacote, rótulo, marcado em "recomendados")])
GROUPS = [
    ("Lixo do Windows", [
        ("Microsoft.MicrosoftSolitaireCollection", "Microsoft Solitaire Collection", True),
        ("Microsoft.BingNews", "Notícias (Bing News)", True),
        ("Microsoft.BingFinance", "Finanças (Bing)", True),
        ("Microsoft.BingSports", "Esportes (Bing)", True),
        ("Microsoft.BingSearch", "Pesquisa do Bing", True),
        ("Microsoft.MicrosoftOfficeHub", "Office (atalho que só abre propaganda)", True),
        ("Microsoft.GetHelp", "Obter Ajuda", True),
        ("Microsoft.Getstarted", "Dicas", True),
        ("Microsoft.WindowsFeedbackHub", "Central de Comentários", True),
        ("Microsoft.ZuneVideo", "Filmes e TV", True),
        ("Microsoft.People", "Pessoas", True),
        ("Microsoft.SkypeApp", "Skype", True),
        ("Microsoft.MixedReality.Portal", "Portal de Realidade Misturada", True),
        ("Microsoft.Microsoft3DViewer", "Visualizador 3D", True),
        ("Microsoft.Print3D", "Print 3D", True),
        ("Microsoft.OneConnect", "Planos Móveis", True),
        ("Microsoft.Wallet", "Microsoft Pay", True),
        ("Microsoft.Windows.DevHome", "Dev Home", True),
        ("MicrosoftCorporationII.MicrosoftFamily", "Microsoft Family", True),
        ("Clipchamp.Clipchamp", "Clipchamp (editor de vídeo)", True),
        ("Microsoft.549981C3F5F10", "Cortana", True),
    ]),
    ("Jogos e apps de terceiros que vêm instalados", [
        ("king.com.CandyCrushSaga", "Candy Crush Saga", True),
        ("king.com.CandyCrushSodaSaga", "Candy Crush Soda Saga", True),
        ("king.com.FarmHeroesSaga", "Farm Heroes Saga", True),
        ("king.com.BubbleWitch3Saga", "Bubble Witch 3 Saga", True),
        ("A278AB0D.MarchofEmpires", "March of Empires", True),
        ("A278AB0D.DisneyMagicKingdoms", "Disney Magic Kingdoms", True),
        ("flaregamesGmbH.RoyalRevolt2", "Royal Revolt 2", True),
        ("828B5831.HiddenCityMysteryofShadows", "Hidden City", True),
        ("4DF9E0F8.Netflix", "Netflix", True),
        ("AmazonVideo.PrimeVideo", "Prime Video", True),
        ("Disney.37853FC22B2CE", "Disney+", True),
        ("BytedancePte.Ltd.TikTok", "TikTok", True),
        ("Facebook.Facebook", "Facebook", True),
        ("Facebook.InstagramBeta", "Instagram", True),
        ("9E2F88E3.Twitter", "Twitter / X", True),
        ("D5EA27B7.Duolingo-LearnLanguagesforFree", "Duolingo", True),
        ("ShazamEntertainmentLtd.Shazam", "Shazam", True),
        ("PandoraMediaInc.29680B314EFC2", "Pandora", True),
    ]),
    ("HP (só aparece em PC da HP)", [
        ("AD2F1837.HPJumpStarts", "HP JumpStarts (dicas e propaganda)", True),
        ("AD2F1837.HPPrivacySettings", "HP Privacy Settings", True),
        ("AD2F1837.HPWorkWell", "HP WorkWell", True),
        ("AD2F1837.HPSupportAssistant", "HP Support Assistant (suporte e drivers)", False),
        ("AD2F1837.myHP", "myHP", False),
        ("AD2F1837.HPQuickDrop", "HP QuickDrop", False),
        ("AD2F1837.HPEasyClean", "HP Easy Clean", False),
        ("AD2F1837.HPSystemInformation", "HP System Information", False),
    ]),
    ("Opcionais (algumas pessoas usam)", [
        ("Microsoft.BingWeather", "Clima", False),
        ("Microsoft.WindowsMaps", "Mapas", False),
        ("Microsoft.WindowsAlarms", "Alarmes e Relógio", False),
        ("Microsoft.WindowsSoundRecorder", "Gravador de Voz", False),
        ("Microsoft.YourPhone", "Vincular ao Celular (Phone Link)", False),
        ("MicrosoftTeams", "Microsoft Teams (versão pessoal)", False),
        ("MSTeams", "Microsoft Teams (versão pessoal, Win 11)", False),
        ("Microsoft.Copilot", "Copilot", False),
        ("Microsoft.Todos", "Microsoft To Do", False),
        ("Microsoft.PowerAutomateDesktop", "Power Automate", False),
        ("Microsoft.Office.OneNote", "OneNote", False),
        ("Microsoft.OutlookForWindows", "Novo Outlook", False),
        ("microsoft.windowscommunicationsapps", "Email e Calendário", False),
        ("Microsoft.Whiteboard", "Whiteboard", False),
        ("SpotifyAB.SpotifyMusic", "Spotify (versão da Store)", False),
        ("5319275A.WhatsAppDesktop", "WhatsApp (versão da Store)", False),
    ]),
]

# (pacote, rótulo): formato antigo, usado por outras partes do app
APPS = [(pkg, label) for _, items in GROUPS for pkg, label, _ in items]
RECOMMENDED = {pkg for _, items in GROUPS for pkg, _, rec in items if rec}

# Só o lixo mais óbvio (usado pelo pacote Davi Zone)
LEVE = [
    "Microsoft.MicrosoftSolitaireCollection", "king.com.CandyCrushSaga", "king.com.CandyCrushSodaSaga",
    "Microsoft.BingNews", "Microsoft.MicrosoftOfficeHub", "Microsoft.GetHelp", "Microsoft.Getstarted",
    "Microsoft.WindowsFeedbackHub", "Microsoft.ZuneVideo", "Microsoft.People", "Microsoft.SkypeApp",
    "Microsoft.MixedReality.Portal", "Microsoft.Microsoft3DViewer", "Clipchamp.Clipchamp",
    "Microsoft.549981C3F5F10", "AD2F1837.HPJumpStarts", "AD2F1837.HPPrivacySettings",
    "AD2F1837.HPWorkWell", "Microsoft.BingFinance", "Microsoft.BingSports", "Microsoft.Windows.DevHome",
]

_VALID = {pkg.lower() for pkg, _ in APPS}


def installed():
    """Conjunto (em minúsculas) com os nomes dos pacotes instalados na conta atual."""
    r = run(["powershell", "-NoProfile", "-Command",
             "Get-AppxPackage | Select-Object -ExpandProperty Name"], timeout=90)
    return {ln.strip().lower() for ln in r.stdout.splitlines() if ln.strip()}


def is_installed(pkg, have):
    return pkg.lower() in have


def removed_set():
    """Pacotes que o MelbyTune removeu (pra poder oferecer 'Reinstalar')."""
    try:
        with open(REMOVED_FILE, "r", encoding="utf-8") as f:
            return {p.lower() for p in json.load(f)}
    except (OSError, ValueError):
        return set()


def _save_removed(items):
    try:
        os.makedirs(APP_DIR, exist_ok=True)
        with open(REMOVED_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(items), f)
    except OSError:
        pass


def command(pkg):
    return f'Get-AppxPackage -Name "{pkg}" | Remove-AppxPackage'


def remove(pkg):
    """Só aceita pacotes da lista. Retorna (ok, mensagem de erro)."""
    if pkg.lower() not in _VALID:
        return False, "Item fora da lista."
    r = run(["powershell", "-NoProfile", "-Command", command(pkg)], timeout=240)
    ok = r.returncode == 0
    if ok:
        _save_removed(removed_set() | {pkg.lower()})
    return ok, (r.stderr or "").strip()


def reinstall(pkg):
    """Tenta registrar de novo o app a partir dos arquivos que o Windows ainda guarda."""
    if pkg.lower() not in _VALID:
        return False, "Item fora da lista."
    ps = (f'Get-AppxPackage -AllUsers -Name "{pkg}" | ForEach-Object '
          '{ Add-AppxPackage -DisableDevelopmentMode -Register "$($_.InstallLocation)\\AppxManifest.xml" }')
    r = run(["powershell", "-NoProfile", "-Command", ps], timeout=240)
    ok = r.returncode == 0
    if ok:
        _save_removed(removed_set() - {pkg.lower()})
    return ok, (r.stderr or "").strip()
