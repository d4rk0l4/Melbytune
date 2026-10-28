"""Limpeza de arquivos temporários (só pastas seguras, tudo se regenera)."""
import os
import shutil

from tweaks import run

ENV = os.environ
TARGETS = [
    ("Temporários do usuário", ENV.get("TEMP", "")),
    ("Temporários do Windows", os.path.join(ENV.get("WINDIR", r"C:\Windows"), "Temp")),
    ("Relatórios de erro do Windows",
     os.path.join(ENV.get("PROGRAMDATA", r"C:\ProgramData"), r"Microsoft\Windows\WER")),
    ("Cache de shaders (DirectX)", os.path.join(ENV.get("LOCALAPPDATA", ""), "D3DSCache")),
]


def folder_size(path):
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total


def scan():
    """Retorna [(nome, caminho, bytes)]."""
    return [(n, p, folder_size(p)) for n, p in TARGETS if p and os.path.isdir(p)]


def clean_folder(path):
    """Apaga o conteúdo (não a pasta). Ignora o que estiver em uso. Retorna bytes liberados."""
    before = folder_size(path)
    for entry in os.scandir(path):
        try:
            if entry.is_dir(follow_symlinks=False):
                shutil.rmtree(entry.path, ignore_errors=True)
            else:
                os.remove(entry.path)
        except OSError:
            pass
    return max(0, before - folder_size(path))


def empty_recycle_bin():
    run(["powershell", "-NoProfile", "-Command",
         "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"])


def fmt(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
