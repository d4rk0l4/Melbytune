"""Debloat: remove apps que vêm pré-instalados no Windows (só da conta atual).

Lista conservadora: nada que o sistema precise pra funcionar. NÃO inclui Microsoft Store,
Calculadora, Fotos, Paint, Xbox nem Edge. Se algum app removido não voltar pelo botão
"Reinstalar", é só baixar de novo pela Microsoft Store.
"""
from tweaks import run

# (nome exato do pacote, rótulo mostrado no app)
APPS = [
    ("Microsoft.MicrosoftSolitaireCollection", "Microsoft Solitaire Collection"),
    ("king.com.CandyCrushSaga", "Candy Crush Saga"),
    ("king.com.CandyCrushSodaSaga", "Candy Crush Soda Saga"),
    ("Microsoft.BingNews", "Notícias (Bing News)"),
    ("Microsoft.BingWeather", "Clima"),
    ("Microsoft.MicrosoftOfficeHub", "Office (atalho que só abre propaganda)"),
    ("Microsoft.GetHelp", "Obter Ajuda"),
    ("Microsoft.Getstarted", "Dicas"),
    ("Microsoft.WindowsFeedbackHub", "Central de Comentários"),
    ("Microsoft.WindowsMaps", "Mapas"),
    ("Microsoft.ZuneVideo", "Filmes e TV"),
    ("Microsoft.People", "Pessoas"),
    ("Microsoft.SkypeApp", "Skype"),
    ("Microsoft.MixedReality.Portal", "Portal de Realidade Misturada"),
    ("Microsoft.Microsoft3DViewer", "Visualizador 3D"),
    ("Clipchamp.Clipchamp", "Clipchamp (editor de vídeo)"),
    ("Microsoft.549981C3F5F10", "Cortana"),
    ("Microsoft.YourPhone", "Vincular ao Celular (Phone Link)"),
    ("Microsoft.Copilot", "Copilot"),
    ("Microsoft.Todos", "Microsoft To Do"),
    ("Microsoft.PowerAutomateDesktop", "Power Automate"),
    ("MicrosoftTeams", "Microsoft Teams (versão pessoal)"),
    ("MSTeams", "Microsoft Teams (versão pessoal, Win 11)"),
]

_VALID = {pkg for pkg, _ in APPS}


def installed():
    """Conjunto com os nomes dos pacotes instalados na conta atual."""
    r = run(["powershell", "-NoProfile", "-Command",
             "Get-AppxPackage | Select-Object -ExpandProperty Name"], timeout=90)
    return {ln.strip() for ln in r.stdout.splitlines() if ln.strip()}


def command(pkg):
    return f'Get-AppxPackage -Name "{pkg}" | Remove-AppxPackage'


def remove(pkg):
    """Só aceita pacotes da lista APPS. Retorna (ok, mensagem de erro)."""
    if pkg not in _VALID:
        return False, "Item fora da lista."
    r = run(["powershell", "-NoProfile", "-Command", command(pkg)], timeout=240)
    return r.returncode == 0, (r.stderr or "").strip()


def reinstall(pkg):
    """Tenta registrar de novo o app a partir dos arquivos que o Windows ainda guarda."""
    if pkg not in _VALID:
        return False, "Item fora da lista."
    ps = (f'Get-AppxPackage -AllUsers -Name "{pkg}" | ForEach-Object '
          '{ Add-AppxPackage -DisableDevelopmentMode -Register "$($_.InstallLocation)\\AppxManifest.xml" }')
    r = run(["powershell", "-NoProfile", "-Command", ps], timeout=240)
    return r.returncode == 0, (r.stderr or "").strip()
