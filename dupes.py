"""Arquivos duplicados e arquivos grandes (só lê; quem apaga é a interface, via Lixeira)."""
import hashlib
import heapq
import os
import stat

SKIP_DIRS = {"windows", "program files", "program files (x86)", "programdata", "$recycle.bin",
             "system volume information", "appdata", "node_modules", ".git", "__pycache__"}


def iter_files(roots, stop=None):
    seen = set()
    for root in roots:
        for dp, dns, fns in os.walk(root, followlinks=False):
            if stop is not None and stop.is_set():
                return
            dns[:] = [d for d in dns if d.lower() not in SKIP_DIRS and not d.startswith("$")]
            for fn in fns:
                p = os.path.join(dp, fn)
                key = os.path.normcase(os.path.abspath(p))
                if key in seen:  # pastas sobrepostas
                    continue
                seen.add(key)
                yield p


def _hash(path, limit=None):
    h = hashlib.blake2b(digest_size=20)
    try:
        with open(path, "rb") as f:
            if limit:
                h.update(f.read(limit))
            else:
                while True:
                    chunk = f.read(1 << 20)
                    if not chunk:
                        break
                    h.update(chunk)
    except OSError:
        return None
    return h.digest()


def find_duplicates(roots, min_size=1 << 20, progress=None, stop=None):
    """Retorna [{'size': int, 'files': [(caminho, mtime), ...]}], mais antigo primeiro."""
    by_size = {}
    n = 0
    for p in iter_files(roots, stop):
        try:
            st = os.lstat(p)
        except OSError:
            continue
        if not stat.S_ISREG(st.st_mode) or st.st_size < min_size:
            continue
        by_size.setdefault(st.st_size, []).append((p, st.st_mtime))
        n += 1
        if progress and n % 300 == 0:
            progress(f"Lendo arquivos... {n}")

    cand = {s: v for s, v in by_size.items() if len(v) > 1}
    total = sum(len(v) for v in cand.values())
    done = 0
    groups = []
    for size, files in cand.items():
        if stop is not None and stop.is_set():
            break
        partial = {}
        for p, m in files:
            h = _hash(p, 65536)
            done += 1
            if progress and done % 20 == 0:
                progress(f"Comparando... {done}/{total}")
            if h is not None:
                partial.setdefault(h, []).append((p, m))
        for plist in partial.values():
            if len(plist) < 2:
                continue
            if size <= 65536:
                full = {b"x": plist}
            else:
                full = {}
                for p, m in plist:
                    h = _hash(p)
                    if h is not None:
                        full.setdefault(h, []).append((p, m))
            for flist in full.values():
                if len(flist) > 1:
                    groups.append({"size": size, "files": sorted(flist, key=lambda x: x[1])})
    groups.sort(key=lambda g: g["size"] * (len(g["files"]) - 1), reverse=True)
    return groups


def biggest(root, n=40, progress=None, stop=None):
    """Os n maiores arquivos dentro de root: [(tamanho, caminho)]."""
    heap = []
    count = 0
    for p in iter_files([root], stop):
        try:
            st = os.lstat(p)
        except OSError:
            continue
        if not stat.S_ISREG(st.st_mode):
            continue
        count += 1
        if progress and count % 500 == 0:
            progress(f"Lendo arquivos... {count}")
        item = (st.st_size, p)
        if len(heap) < n:
            heapq.heappush(heap, item)
        elif item > heap[0]:
            heapq.heapreplace(heap, item)
    return sorted(heap, reverse=True)


def recycle(paths):
    """Manda pra Lixeira do Windows (dá pra restaurar). Retorna (enviados, [falhas])."""
    import tempfile
    from tweaks import run
    if not paths:
        return 0, []
    fd, lst = tempfile.mkstemp(suffix=".txt")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("\n".join(paths))
    safe = lst.replace("'", "''")
    ps = ("Add-Type -AssemblyName Microsoft.VisualBasic; "
          f"Get-Content -LiteralPath '{safe}' -Encoding UTF8 | ForEach-Object {{ "
          "try { [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile($_,'OnlyErrorDialogs','SendToRecycleBin') } "
          "catch { Write-Output \"FAIL:$_\" } }")
    try:
        r = run(["powershell", "-NoProfile", "-Command", ps], timeout=900)
        if r.returncode == 127:  # sem PowerShell (fora do Windows)
            return 0, [f"FAIL:{p}" for p in paths]
        fails = [ln for ln in r.stdout.splitlines() if ln.startswith("FAIL:")]
    finally:
        try:
            os.remove(lst)
        except OSError:
            pass
    return len(paths) - len(fails), fails
