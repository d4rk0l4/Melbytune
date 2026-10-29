"""Teste de velocidade da internet (sem programa extra; usa os servidores públicos da Cloudflare)."""
import statistics
import threading
import time
import urllib.request

BASE = "https://speed.cloudflare.com"
UA = {"User-Agent": "MelbyTune/2.0"}


def _ping(n=6):
    times = []
    for _ in range(n):
        t = time.perf_counter()
        with urllib.request.urlopen(urllib.request.Request(BASE + "/__down?bytes=0", headers=UA), timeout=8) as r:
            r.read()
        times.append((time.perf_counter() - t) * 1000)
    return statistics.median(times[1:] or times)  # o 1º inclui o handshake


def _transfer(worker, seconds, threads, live):
    total = [0]
    lock = threading.Lock()
    start = time.perf_counter()
    deadline = start + seconds

    def add(n):
        with lock:
            total[0] += n

    ts = [threading.Thread(target=worker, args=(deadline, add), daemon=True) for _ in range(threads)]
    for t in ts:
        t.start()
    while any(t.is_alive() for t in ts):
        time.sleep(0.25)
        el = max(time.perf_counter() - start, 0.1)
        live(total[0] * 8 / 1e6 / el)
    el = max(time.perf_counter() - start, 0.1)
    if total[0] == 0:
        raise RuntimeError("Sem resposta do servidor de teste. Confira sua conexão.")
    return total[0] * 8 / 1e6 / el


def _download_worker(deadline, add):
    while time.perf_counter() < deadline:
        try:
            req = urllib.request.Request(BASE + "/__down?bytes=25000000", headers=UA)
            with urllib.request.urlopen(req, timeout=10) as r:
                while time.perf_counter() < deadline:
                    b = r.read(65536)
                    if not b:
                        break
                    add(len(b))
        except Exception:
            time.sleep(0.3)


def _upload_worker(deadline, add):
    payload = bytes(1_000_000)
    hdr = dict(UA)
    hdr["Content-Type"] = "application/octet-stream"
    while time.perf_counter() < deadline:
        try:
            req = urllib.request.Request(BASE + "/__up", data=payload, headers=hdr, method="POST")
            with urllib.request.urlopen(req, timeout=15) as r:
                r.read()
            add(len(payload))
        except Exception:
            time.sleep(0.3)


def run(cb):
    """cb(etapa, valor, final). Etapas: ping (ms), download e upload (Mbps)."""
    ms = _ping()
    cb("ping", ms, True)
    d = _transfer(_download_worker, 8, 4, lambda v: cb("download", v, False))
    cb("download", d, True)
    u = _transfer(_upload_worker, 6, 3, lambda v: cb("upload", v, False))
    cb("upload", u, True)
