"""'Roda esse jogo?': compara os requisitos de um jogo com o hardware do PC.

É uma ESTIMATIVA. Os requisitos vêm da lista do app ou da Steam (que quem publica o jogo escreve), a
placa de vídeo é comparada pela tabela de gpus.py e o processador por uma conta aproximada
(geração, núcleos e clock). Serve pra saber "dá ou não dá"; não prevê FPS.
"""
import html
import json
import re
import urllib.parse
import urllib.request

from gpus import find_gpu, is_integrated

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MelbyTune/2.1"}
STEAM = "https://store.steampowered.com"


# ============================================================== processador
_IPC_INTEL = {1: 0.85, 2: 1.0, 3: 1.07, 4: 1.15, 5: 1.2, 6: 1.27, 7: 1.3, 8: 1.35, 9: 1.4, 10: 1.45,
              11: 1.65, 12: 1.95, 13: 2.1, 14: 2.15}
_BOOST_INTEL = {1: 3.2, 2: 3.6, 3: 3.8, 4: 3.9, 5: 3.5, 6: 3.8, 7: 4.1, 8: 4.3, 9: 4.6, 10: 4.6, 11: 4.7,
                12: 4.7, 13: 5.0, 14: 5.2}
_IPC_RYZEN = {1: 1.25, 2: 1.35, 3: 1.6, 4: 1.65, 5: 1.9, 6: 1.95, 7: 2.15, 8: 2.2, 9: 2.4}
_BOOST_RYZEN = {1: 3.6, 2: 4.1, 3: 4.3, 4: 4.2, 5: 4.5, 6: 4.6, 7: 5.2, 8: 5.0, 9: 5.3}

_CORE_WORDS = {"single": 1, "dual": 2, "tri": 3, "triple": 3, "quad": 4, "hexa": 6, "six": 6, "octa": 8, "eight": 8}


def _clean(s):
    s = (s or "").lower()
    for junk in ("(r)", "(tm)", "(c)", "®", "™"):
        s = s.replace(junk, " ")
    return re.sub(r"\s+", " ", s)


def _intel_cores(tier, gen, mobile, high_power):
    if mobile and gen <= 7:
        return 2, 4
    if mobile and 8 <= gen <= 9:
        return (2, 4) if tier == 3 else (4, 8)
    if mobile and 10 <= gen <= 11:
        return (2, 4) if tier == 3 else (4, 8)
    if mobile and gen >= 12:
        return (6, 8) if tier == 3 else (10, 12)
    if high_power:
        return {3: (4, 8), 5: (6, 12), 7: (8, 16), 9: (8, 16)}[tier] if gen < 12 else {3: (4, 8), 5: (12, 16), 7: (14, 20), 9: (16, 24)}[tier]
    if tier == 3:
        return (2, 4) if gen <= 7 else ((4, 4) if gen <= 9 else (4, 8))
    if tier == 5:
        if gen <= 7:
            return 4, 4
        if gen <= 9:
            return 6, 6
        return (6, 12) if gen <= 12 else (10, 16)
    if tier == 7:
        if gen <= 7:
            return 4, 8
        if gen == 8:
            return 6, 12
        if gen == 9:
            return 8, 8
        if gen <= 11:
            return 8, 16
        return (12, 20) if gen == 12 else (16, 24)
    # i9
    if gen <= 9:
        return 8, 16
    if gen == 10:
        return 10, 20
    if gen == 11:
        return 8, 16
    return (16, 24) if gen == 12 else (24, 32)


def cpu_profile(name):
    """Do nome do processador tira uma estimativa: núcleos, threads, clock máximo e eficiência por clock.
    Retorna um dict ou None quando não reconhece o modelo."""
    t = _clean(name)
    if not t.strip():
        return None
    # ---- Intel Core iN
    m = re.search(r"\bi([3579])[\s-]?(\d{3,5})([a-z]{0,2}\d?)\b", t)
    if m and ("core" in t or "intel" in t or True):
        tier, num, suf = int(m.group(1)), m.group(2), m.group(3)
        if len(num) == 5:
            gen = int(num[:2])
        elif len(num) == 4:
            gen = int(num[:2]) if (10 <= int(num[:2]) <= 14 and suf) else int(num[0])
        else:
            gen = 1
        mobile = bool(re.match(r"^(u|y|g\d|p)", suf)) if suf else False
        high = bool(re.match(r"^(h|hk|hx|hq)", suf)) if suf else False
        cores, threads = _intel_cores(tier, gen, mobile, high)
        boost = _BOOST_INTEL.get(gen, 4.5) * {3: 0.88, 5: 1.0, 7: 1.05, 9: 1.1}[tier]
        if mobile:
            boost *= 0.82
        return {"family": f"Intel Core i{tier} (geração {gen})", "cores": cores, "threads": threads,
                "boost": boost, "ipc": _IPC_INTEL.get(gen, 2.0), "shared": 1.0}
    # ---- Intel Core Ultra
    if "core ultra" in t:
        return {"family": "Intel Core Ultra", "cores": 14, "threads": 20, "boost": 5.0, "ipc": 2.3, "shared": 1.0}
    # ---- AMD Ryzen
    m = re.search(r"ryzen\s*(?:ai\s*)?([3579])\s*(?:pro\s*)?(\d)(\d{3})([a-z0-9]{0,3})\b", t)
    if m:
        tier, gen, suf = int(m.group(1)), int(m.group(2)), m.group(4)
        mobile = bool(re.match(r"^(u|c|h|hs|hx)", suf)) if suf else False
        base = {3: (4, 8), 5: (6, 12), 7: (8, 16), 9: (12, 24)}[tier]
        cores, threads = base
        if gen == 1 and tier in (3,):
            cores, threads = 4, 4
        if tier == 5 and gen == 1 and m.group(3).startswith("4"):  # Ryzen 5 1400
            cores, threads = 4, 8
        if gen == 4 and tier == 3:
            cores, threads = 4, 8
        boost = _BOOST_RYZEN.get(gen, 5.0) * {3: 0.93, 5: 1.0, 7: 1.03, 9: 1.06}[tier] * (0.85 if mobile else 1.0)
        return {"family": f"AMD Ryzen {tier} (série {gen}000)", "cores": cores, "threads": threads,
                "boost": boost, "ipc": _IPC_RYZEN.get(gen, 2.2), "shared": 1.0}
    # ---- AMD antigos
    m = re.search(r"\bfx[\s-]?(\d)(\d{3})\b", t)
    if m:
        cores = int(m.group(1))
        return {"family": "AMD FX", "cores": cores, "threads": cores, "boost": 4.0, "ipc": 0.75, "shared": 0.8}
    if re.search(r"phenom ii", t):
        m = re.search(r"x(\d)", t)
        cores = int(m.group(1)) if m else 4
        return {"family": "AMD Phenom II", "cores": cores, "threads": cores, "boost": 3.4, "ipc": 0.85, "shared": 1.0}
    if "phenom" in t:
        return {"family": "AMD Phenom", "cores": 4, "threads": 4, "boost": 2.5, "ipc": 0.75, "shared": 1.0}
    if re.search(r"athlon\s*(\d{3}ge|\d{4}g|silver|gold)", t):
        return {"family": "AMD Athlon (Zen)", "cores": 2, "threads": 4, "boost": 3.2, "ipc": 1.3, "shared": 1.0}
    if re.search(r"athlon", t):
        return {"family": "AMD Athlon", "cores": 2, "threads": 2, "boost": 2.8, "ipc": 0.7, "shared": 1.0}
    m = re.search(r"\ba(4|6|8|10|12)[\s-]?(\d{4})", t)
    if m:
        return {"family": "AMD série A", "cores": 4, "threads": 4, "boost": 3.8, "ipc": 0.85, "shared": 0.85}
    # ---- Intel antigos / básicos
    if re.search(r"core\s*2\s*quad|\bq[69]\d{3}\b", t):
        return {"family": "Intel Core 2 Quad", "cores": 4, "threads": 4, "boost": 2.7, "ipc": 0.8, "shared": 1.0}
    if re.search(r"core\s*2\s*duo|\be[78]\d{3}\b", t):
        return {"family": "Intel Core 2 Duo", "cores": 2, "threads": 2, "boost": 2.9, "ipc": 0.8, "shared": 1.0}
    if re.search(r"pentium|celeron", t):
        if re.search(r"\bn\d{4}\b|silver|\bj\d{4}\b", t):
            return {"family": "Intel Pentium/Celeron (baixo consumo)", "cores": 4, "threads": 4, "boost": 2.6,
                    "ipc": 0.8, "shared": 1.0}
        if re.search(r"gold|\bg[4-7]\d{3}\b", t):
            return {"family": "Intel Pentium Gold", "cores": 2, "threads": 4, "boost": 3.6, "ipc": 1.3, "shared": 1.0}
        return {"family": "Intel Pentium/Celeron", "cores": 2, "threads": 2, "boost": 2.8, "ipc": 1.0, "shared": 1.0}
    # ---- só "N núcleos e X GHz" no texto
    ghz = re.search(r"(\d+(?:[.,]\d+)?)\s*ghz", t)
    cw = re.search(r"\b(single|dual|tri|triple|quad|hexa|six|octa|eight)[\s-]*core", t)
    n = re.search(r"\b(\d{1,2})[\s-]*(?:core|cores|cpus?)\b", t)
    if ghz and (cw or n):
        cores = _CORE_WORDS[cw.group(1)] if cw else int(n.group(1))
        return {"family": "genérico", "cores": cores, "threads": cores,
                "boost": float(ghz.group(1).replace(",", ".")) * 1.1, "ipc": 1.0, "shared": 1.0}
    return None


def cpu_score(profile, cores=None, threads=None):
    """Índice aproximado de desempenho do processador (maior = mais rápido)."""
    cores = cores or profile["cores"]
    threads = threads or profile["threads"]
    eff = (cores + 0.3 * max(0, threads - cores)) * profile["shared"]
    return profile["boost"] * profile["ipc"] * (eff ** 0.8)


def pc_cpu_score(name, cores, threads, ghz):
    """Índice do processador do PC: usa os núcleos reais e, se o modelo não for reconhecido, o clock lido."""
    prof = cpu_profile(name)
    if prof:
        return cpu_score(prof, cores, threads), prof["family"]
    if cores and ghz:
        generic = {"cores": cores, "threads": threads or cores, "boost": ghz * 1.3, "ipc": 1.0, "shared": 1.0}
        return cpu_score(generic), "modelo não reconhecido (estimado por núcleos e clock)"
    return None, ""


def _alternatives(text):
    return [a.strip() for a in re.split(r"\s*(?:/|\||\bor\b|\bou\b)\s*", text or "", flags=re.I) if a.strip()]


def req_cpu_score(text):
    best = None
    for alt in _alternatives(text):
        prof = cpu_profile(alt)
        if prof:
            s = cpu_score(prof)
            best = s if best is None else min(best, s)
    return best


def req_gpu(text):
    """(pontuação, VRAM em GB) pedidos no texto da placa de vídeo. Cada parte pode ser None."""
    score, vram = None, None
    for alt in _alternatives(text):
        f = find_gpu(alt)
        if f:
            score = f[1] if score is None else min(score, f[1])
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(gb|mb)\b", text or "", flags=re.I)
    if m:
        v = float(m.group(1).replace(",", "."))
        vram = v if m.group(2).lower() == "gb" else v / 1024
    return score, vram


# ============================================================= requisitos (texto)
def _gb(text):
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(tb|gb|mb|g)\b", text or "", flags=re.I)
    if not m:
        return None
    v = float(m.group(1).replace(",", "."))
    u = m.group(2).lower()
    return v * 1024 if u == "tb" else (v / 1024 if u == "mb" else v)


def _slot(label):
    l = label.lower().strip()
    if "processor" in l or l.startswith("cpu") or "processador" in l:
        return "cpu"
    if ("video" in l and "memory" in l) or "vram" in l:
        return "vram"
    if any(k in l for k in ("graphic", "video", "gpu", "placa de v", "vga")):
        return "gpu"
    if any(k in l for k in ("storage", "hard", "disk", "space", "armazen", "hdd", "drive")):
        return "disk"
    if any(k in l for k in ("memory", "ram", "mem")):
        return "ram"
    if l.startswith("os") or "operating" in l or "sistema" in l:
        return "os"
    return None


def parse_requirements(raw_html):
    """Lê o texto de requisitos da Steam. Retorna {'cpu','gpu','ram','vram','disk','os','lines'} ou None."""
    if not raw_html or not isinstance(raw_html, str):
        return None
    text = re.sub(r"(?i)<br\s*/?>|</li>|</p>|</ul>|</div>", "\n", raw_html)
    text = html.unescape(re.sub(r"<[^>]+>", "", text))
    spec = {"cpu": None, "gpu": None, "ram": None, "vram": None, "disk": None, "os": None, "lines": []}
    for line in (ln.strip() for ln in text.splitlines()):
        if not line:
            continue
        m = re.match(r"^([^:]{2,40}):\s*(.*)$", line)
        if not m:
            continue
        label, value = m.group(1), m.group(2).strip()
        if label.lower() in ("minimum", "recommended", "mínimo", "mínimos", "recomendado", "recomendados"):
            continue
        slot = _slot(label)
        if not slot or not value:
            continue
        spec["lines"].append(f"{label.strip()}: {value[:140]}")
        if slot in ("cpu", "gpu", "os") and not spec[slot]:
            spec[slot] = value
        elif slot in ("ram", "vram", "disk") and spec[slot] is None:
            spec[slot] = _gb(value)
    if not any(spec[k] for k in ("cpu", "gpu", "ram", "disk", "vram")):
        return None
    return spec


# ============================================================== lista do app
def _spec(cpu, gpu, ram, disk, vram=None):
    lines = [f"Processador: {cpu}", f"Placa de vídeo: {gpu}", f"Memória: {ram} GB", f"Espaço em disco: {disk} GB"]
    return {"cpu": cpu, "gpu": gpu, "ram": ram, "vram": vram, "disk": disk, "os": None, "lines": lines}


# Valores aproximados reunidos à mão a partir das páginas oficiais; confira no site do jogo.
CURATED = [
    {"id": "curated:minecraft", "name": "Minecraft (Java)", "aliases": ["minecraft", "mine"],
     "min": _spec("Intel Core i3-3210 / AMD A8-7600", "Intel HD Graphics 4000 / AMD Radeon R5", 4, 1),
     "rec": _spec("Intel Core i5-4690 / AMD A10-7800", "GeForce GTX 750 / Radeon R7 260X", 8, 4),
     "note": "Com mods e shaders pesa bem mais que isso. A placa da linha recomendada é a equivalente às séries GeForce 700 / Radeon Rx 200."},
    {"id": "curated:fortnite", "name": "Fortnite", "aliases": ["fortnite"],
     "min": _spec("Intel Core i3-3225", "Intel HD Graphics 4000", 8, 30),
     "rec": _spec("Intel Core i5-7300U / AMD Ryzen 3 3300U", "GeForce GTX 960 / Radeon R9 280", 16, 30),
     "note": "A Epic atualiza os requisitos a cada temporada."},
    {"id": "curated:valorant", "name": "Valorant", "aliases": ["valorant", "valo"],
     "min": _spec("Intel Core 2 Duo E8400 / AMD Athlon 200GE", "Intel HD Graphics 4000 / AMD Radeon R5", 4, 8),
     "rec": _spec("Intel Core i3-4150 / AMD Ryzen 3 1200", "GeForce GT 730 / Radeon R7 240", 4, 8),
     "note": "Mínimo = 30 fps, recomendado = 60 fps. Pra 144 fps ou mais a Riot pede Core i5-9400F e GTX 1050 Ti."},
    {"id": "curated:lol", "name": "League of Legends", "aliases": ["league of legends", "lol", "league"],
     "min": _spec("Intel Core i3-530 / AMD A6-3650", "GeForce 9800 GT / Radeon HD 5670", 2, 16),
     "rec": _spec("Intel Core i5-3300 / AMD Phenom II X4", "GeForce GTX 560 / Radeon HD 6950", 4, 16),
     "note": "Valores aproximados. Jogo leve, roda em quase tudo."},
    {"id": "curated:roblox", "name": "Roblox", "aliases": ["roblox"],
     "min": _spec("Intel Core 2 Duo 1.6 GHz", "Intel HD Graphics 3000", 1, 1),
     "rec": _spec("Intel Core i3-3210", "Intel HD Graphics 4000", 4, 1),
     "note": "Depende muito do jogo (experiência) que você abrir dentro do Roblox."},
    {"id": "curated:gtav", "name": "Grand Theft Auto V", "aliases": ["gta", "gta v", "gta 5", "grand theft auto"],
     "min": _spec("Intel Core 2 Quad Q6600 / AMD Phenom 9850", "GeForce 9800 GT / Radeon HD 4870", 4, 125, vram=1),
     "rec": _spec("Intel Core i5-3470 / AMD FX-8350", "GeForce GTX 660 / Radeon HD 7870", 8, 125, vram=2),
     "note": "Dados da página da Steam. O espaço de 125 GB é o da versão atual."},
    {"id": "curated:cs2", "name": "Counter-Strike 2", "aliases": ["cs2", "cs", "counter strike", "csgo", "cs go"],
     "min": _spec("Intel Core i5-750", "Placa DirectX 11 com 1 GB de vídeo", 8, 85, vram=1),
     "rec": None,
     "note": "A Valve só publica o requisito mínimo. Pra jogar competitivo, mire bem acima dele."},
    {"id": "curated:rocketleague", "name": "Rocket League", "aliases": ["rocket league", "rl"],
     "min": _spec("Intel Core 2 Duo E8400 / AMD Phenom II X2", "GeForce GTX 760 / Radeon R7 270X", 4, 20),
     "rec": _spec("Intel Core i5-3470 / AMD FX-8350", "GeForce GTX 1060 / Radeon RX 470", 8, 20),
     "note": "Valores aproximados."},
    {"id": "curated:genshin", "name": "Genshin Impact", "aliases": ["genshin", "genshin impact"],
     "min": _spec("Intel Core i5-7400", "GeForce GT 1030", 8, 30),
     "rec": _spec("Intel Core i7-8700", "GeForce GTX 1060 6GB", 16, 30),
     "note": "Valores aproximados: o jogo pede 'Core i5 ou equivalente' e 'Core i7 ou equivalente'."},

    {"id": "curated:rdr2", "name": "Red Dead Redemption 2", "aliases": ["rdr2", "red dead", "red dead redemption"],
     "min": _spec("Intel Core i5-2500K / AMD FX-6300", "GeForce GTX 770 2GB / Radeon R9 280 3GB", 8, 150),
     "rec": _spec("Intel Core i7-4770K / AMD Ryzen 5 1500X", "GeForce GTX 1060 6GB / Radeon RX 480 4GB", 12, 150),
     "note": "Valores aproximados."},
    {"id": "curated:cyberpunk", "name": "Cyberpunk 2077", "aliases": ["cyberpunk", "cp2077"],
     "min": _spec("Intel Core i7-6700 / AMD Ryzen 5 1600", "GeForce GTX 1060 6GB / Radeon RX 580 8GB", 12, 70),
     "rec": _spec("Intel Core i7-12700 / AMD Ryzen 7 7800X3D", "GeForce RTX 2060 SUPER / Radeon RX 5700 XT", 16, 70),
     "note": "Pede SSD. Valores aproximados."},
    {"id": "curated:eldenring", "name": "Elden Ring", "aliases": ["elden ring", "eldenring"],
     "min": _spec("Intel Core i5-8400 / AMD Ryzen 3 3300X", "GeForce GTX 1060 3GB / Radeon RX 580 4GB", 12, 60),
     "rec": _spec("Intel Core i7-8700K / AMD Ryzen 5 3600X", "GeForce GTX 1070 8GB / Radeon RX Vega 56 8GB", 16, 60),
     "note": "Valores aproximados."},
    {"id": "curated:hogwarts", "name": "Hogwarts Legacy", "aliases": ["hogwarts", "harry potter"],
     "min": _spec("Intel Core i5-6600 / AMD Ryzen 5 1400", "GeForce GTX 960 4GB / Radeon RX 470 4GB", 16, 85),
     "rec": _spec("Intel Core i7-8700 / AMD Ryzen 5 3600", "GeForce GTX 1080 Ti / Radeon RX 5700 XT", 16, 85),
     "note": "Pede SSD. Valores aproximados."},
    {"id": "curated:apex", "name": "Apex Legends", "aliases": ["apex", "apex legends"],
     "min": _spec("Intel Core i3-6300 / AMD FX-4350", "GeForce GT 640 / Radeon HD 7730", 6, 56),
     "rec": _spec("Intel Core i5-3570K / AMD Ryzen 5", "GeForce GTX 970 / Radeon R9 290", 8, 56),
     "note": "Valores aproximados."},
    {"id": "curated:pubg", "name": "PUBG: Battlegrounds", "aliases": ["pubg", "battlegrounds"],
     "min": _spec("Intel Core i5-4430 / AMD FX-6300", "GeForce GTX 960 2GB / Radeon R7 370 2GB", 8, 40),
     "rec": _spec("Intel Core i5-6600K / AMD Ryzen 5 1600", "GeForce GTX 1060 3GB / Radeon RX 580 4GB", 16, 40),
     "note": "Valores aproximados."},
    {"id": "curated:r6", "name": "Rainbow Six Siege", "aliases": ["rainbow six", "r6", "siege"],
     "min": _spec("Intel Core i3-560 / AMD Phenom II X4 945", "GeForce GTX 460 / Radeon HD 5870", 6, 61),
     "rec": _spec("Intel Core i5-2500K / AMD FX-8120", "GeForce GTX 670 / Radeon HD 7970", 8, 61),
     "note": "Valores aproximados."},
    {"id": "curated:warzone", "name": "Call of Duty: Warzone", "aliases": ["warzone", "cod", "call of duty"],
     "min": _spec("Intel Core i5-6600K / AMD Ryzen 5 1400", "GeForce GTX 960 / Radeon RX 470", 8, 125),
     "rec": _spec("Intel Core i7-6700K / AMD Ryzen 5 1600X", "GeForce GTX 1060 / Radeon RX 580", 12, 125),
     "note": "A Activision muda isso com frequência e o tamanho do jogo cresce a cada atualização. Confira na página oficial."},
    {"id": "curated:fc25", "name": "EA Sports FC 25", "aliases": ["fc 25", "fc25", "fifa", "ea fc", "ea sports fc"],
     "min": _spec("Intel Core i5-6600K / AMD Ryzen 5 1600", "GeForce GTX 1050 Ti / Radeon RX 570", 8, 100),
     "rec": _spec("Intel Core i7-6700 / AMD Ryzen 7 2700X", "GeForce GTX 1660 / Radeon RX 5600 XT", 12, 100),
     "note": "Valores aproximados."},
    {"id": "curated:fh5", "name": "Forza Horizon 5", "aliases": ["forza", "forza horizon", "fh5"],
     "min": _spec("Intel Core i5-4460 / AMD Ryzen 3 1200", "GeForce GTX 970 / Radeon RX 470", 8, 110),
     "rec": _spec("Intel Core i5-8400 / AMD Ryzen 5 1500X", "GeForce GTX 1070 / Radeon RX 590", 16, 110),
     "note": "Valores aproximados."},
    {"id": "curated:bg3", "name": "Baldur's Gate 3", "aliases": ["baldur", "bg3", "baldurs gate"],
     "min": _spec("Intel Core i5-4690 / AMD FX-4350", "GeForce GTX 970 / Radeon RX 480", 8, 150),
     "rec": _spec("Intel Core i7-8700K / AMD Ryzen 5 3600", "GeForce RTX 2060 SUPER / Radeon RX 5700 XT", 16, 150),
     "note": "SSD recomendado. Valores aproximados."},
    {"id": "curated:starfield", "name": "Starfield", "aliases": ["starfield"],
     "min": _spec("Intel Core i7-6800K / AMD Ryzen 5 2600X", "GeForce GTX 1070 Ti / Radeon RX 5700", 16, 125),
     "rec": _spec("Intel Core i5-10600K / AMD Ryzen 5 3600X", "GeForce RTX 2080 / Radeon RX 6800 XT", 16, 125),
     "note": "Exige SSD. Valores aproximados."},
    {"id": "curated:gow", "name": "God of War", "aliases": ["god of war", "gow"],
     "min": _spec("Intel Core i5-2500K / AMD Ryzen 3 1200", "GeForce GTX 960 4GB / Radeon R9 290", 8, 70),
     "rec": _spec("Intel Core i5-6600K / AMD Ryzen 5 2400G", "GeForce GTX 1060 6GB / Radeon RX 570 4GB", 8, 70),
     "note": "Valores aproximados."},
    {"id": "curated:helldivers2", "name": "Helldivers 2", "aliases": ["helldivers", "hell divers"],
     "min": _spec("Intel Core i7-4790K / AMD Ryzen 5 1500X", "GeForce GTX 1050 Ti / Radeon RX 470", 8, 100),
     "rec": _spec("Intel Core i7-9700K / AMD Ryzen 7 3700X", "GeForce RTX 2060 / Radeon RX 6600 XT", 16, 100),
     "note": "Exige SSD. Valores aproximados."},
    {"id": "curated:wukong", "name": "Black Myth: Wukong", "aliases": ["wukong", "black myth"],
     "min": _spec("Intel Core i5-8400 / AMD Ryzen 5 1600", "GeForce GTX 1060 6GB / Radeon RX 580 8GB", 16, 130),
     "rec": _spec("Intel Core i7-9700 / AMD Ryzen 5 5500", "GeForce RTX 2060 / Radeon RX 5700 XT", 16, 130),
     "note": "Pede SSD. Valores aproximados."},
    {"id": "curated:palworld", "name": "Palworld", "aliases": ["palworld", "pal world"],
     "min": _spec("Intel Core i5-3570K", "GeForce GTX 1050", 16, 40),
     "rec": _spec("Intel Core i9-9900K", "GeForce RTX 2070", 32, 40),
     "note": "Valores aproximados."},
    {"id": "curated:diablo4", "name": "Diablo IV", "aliases": ["diablo", "diablo 4", "diablo iv"],
     "min": _spec("Intel Core i5-2500K / AMD FX-8350", "GeForce GTX 660 / Radeon R9 280", 8, 90),
     "rec": _spec("Intel Core i5-4670K / AMD Ryzen 3 1300X", "GeForce GTX 970 / Radeon RX 470", 16, 90),
     "note": "Exige SSD. Valores aproximados."},
    {"id": "curated:re4", "name": "Resident Evil 4 (2023)", "aliases": ["resident evil", "re4"],
     "min": _spec("Intel Core i5-7500 / AMD Ryzen 3 1200", "GeForce GTX 1050 Ti / Radeon RX 560", 8, 60),
     "rec": _spec("Intel Core i7-8700 / AMD Ryzen 5 3600", "GeForce GTX 1070 / Radeon RX 5700", 16, 60),
     "note": "Valores aproximados."},
    {"id": "curated:sims4", "name": "The Sims 4", "aliases": ["sims", "the sims", "sims 4"],
     "min": _spec("Intel Core 2 Duo E8400", "Intel HD Graphics 3000", 4, 26),
     "rec": _spec("Intel Core i5-2400", "GeForce GTX 650", 8, 26),
     "note": "Valores aproximados. Com muitas expansões instaladas pede mais espaço e mais RAM."},
]


def curated_search(term=""):
    t = (term or "").strip().lower()
    if not t:
        return list(CURATED)
    return [g for g in CURATED if t in g["name"].lower() or any(t in a or a in t for a in g["aliases"])]


# ============================================================== Steam (internet)
def _get_json(url, timeout=12):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", errors="replace"))


def steam_search(term, limit=8):
    """[{id, name}] de jogos de PC da Steam que combinam com o texto."""
    url = f"{STEAM}/api/storesearch/?" + urllib.parse.urlencode({"term": term, "l": "english", "cc": "us"})
    data = _get_json(url)
    out = []
    for it in data.get("items", []):
        if it.get("type") != "app" or not it.get("id"):
            continue
        if (it.get("platforms") or {}).get("windows") is False:
            continue
        out.append({"id": it["id"], "name": it.get("name", "?")})
    return out[:limit]


def steam_game(appid):
    """Baixa os requisitos de PC de um jogo da Steam. Retorna o mesmo formato da lista do app."""
    url = f"{STEAM}/api/appdetails?" + urllib.parse.urlencode(
        {"appids": appid, "l": "english", "cc": "us", "filters": "basic,pc_requirements"})
    data = _get_json(url).get(str(appid)) or {}
    if not data.get("success"):
        raise RuntimeError("A Steam não devolveu esse jogo.")
    d = data["data"]
    req = d.get("pc_requirements")
    mn = rc = None
    if isinstance(req, dict):
        mn, rc = parse_requirements(req.get("minimum")), parse_requirements(req.get("recommended"))
    return {"id": f"steam:{appid}", "name": d.get("name", str(appid)), "min": mn, "rec": rc, "aliases": [],
            "note": "" if (mn or rc) else "Esse item não tem requisitos de PC publicados na Steam (pode ser DLC ou trilha sonora)."}


# ================================================================ comparação
LEVEL_TITLES = {
    "great": "Roda bem",
    "ok": "Roda, com gráficos reduzidos",
    "no": "Provavelmente não roda bem",
    "unknown": "Não deu pra concluir",
}


def _status(user, rmin, rrec, tol_min=0.85, tol_rec=0.9):
    """'ok' (atinge o recomendado), 'min' (só o mínimo), 'low' (abaixo do mínimo) ou 'unknown'."""
    if user is None or (rmin is None and rrec is None):
        return "unknown"
    if rrec is not None and user >= rrec * tol_rec:
        return "ok"
    if rmin is not None:
        if user >= rmin * tol_min:
            return "ok" if rrec is None and user >= rmin * 1.5 else "min"
        return "low"
    return "min" if user >= rrec * 0.6 else "low"  # só existe o recomendado


def _fmt_gb(v):
    if v is None:
        return "—"
    return f"{v:g} GB" if v >= 1 else f"{round(v * 1024)} MB"


def evaluate(hw, game):
    """hw: {'cpu_name','cores','threads','ghz','ram_gb','gpu_name','gpu_vram_gb','gpu_integrated','laptop',
    'disk_free_gb','disk_kind'}; game: um item de CURATED ou o retorno de steam_game()."""
    mn, rc = game.get("min"), game.get("rec")
    rows, tips = [], []

    def spec(key, which):
        s = mn if which == "min" else rc
        return s.get(key) if s else None

    # ---- placa de vídeo
    gname = hw.get("gpu_name") or ""
    found = find_gpu(gname) if gname else None
    integrated = bool(hw.get("gpu_integrated")) or (is_integrated(gname) if gname else False)
    user_gpu = found[1] if found else None
    if user_gpu is not None and hw.get("laptop") and not integrated:
        user_gpu *= 0.85  # versão de notebook costuma render menos que a de mesmo nome no desktop
    mn_gpu, mn_vram = req_gpu(spec("gpu", "min") or "")
    rc_gpu, rc_vram = req_gpu(spec("gpu", "rec") or "")
    mn_vram = spec("vram", "min") or mn_vram
    rc_vram = spec("vram", "rec") or rc_vram
    st_gpu = _status(user_gpu, mn_gpu, rc_gpu)
    rows.append({"key": "gpu", "label": "Placa de vídeo", "pc": (found[0] if found else gname) or "não detectada",
                 "min": spec("gpu", "min") or "—", "rec": spec("gpu", "rec") or "—", "status": st_gpu,
                 "note": "" if found else "Placa fora da lista: escolha uma parecida em 'Meu PC'."})

    # ---- VRAM
    vram = hw.get("gpu_vram_gb")
    if integrated:
        rows.append({"key": "vram", "label": "Memória de vídeo", "pc": "compartilhada com a RAM",
                     "min": _fmt_gb(mn_vram), "rec": _fmt_gb(rc_vram), "status": "unknown",
                     "note": "Placa integrada usa a RAM; a conta já está no item da placa de vídeo."})
        st_vram = "unknown"
    else:
        st_vram = _status(vram, mn_vram, rc_vram, 0.95, 0.95)
        rows.append({"key": "vram", "label": "Memória de vídeo", "pc": _fmt_gb(vram),
                     "min": _fmt_gb(mn_vram), "rec": _fmt_gb(rc_vram), "status": st_vram, "note": ""})

    # ---- processador
    uscore, ufam = pc_cpu_score(hw.get("cpu_name") or "", hw.get("cores"), hw.get("threads"), hw.get("ghz"))
    mn_cpu, rc_cpu = req_cpu_score(spec("cpu", "min") or ""), req_cpu_score(spec("cpu", "rec") or "")
    st_cpu = _status(uscore, mn_cpu, rc_cpu, 0.7, 0.85)
    rows.insert(0, {"key": "cpu", "label": "Processador", "pc": hw.get("cpu_name") or "não detectado",
                    "min": spec("cpu", "min") or "—", "rec": spec("cpu", "rec") or "—", "status": st_cpu,
                    "note": "Comparação aproximada (geração, núcleos e clock)."})

    # ---- RAM
    ram = hw.get("ram_gb")
    mn_ram, rc_ram = spec("ram", "min"), spec("ram", "rec")
    st_ram = _status(None if ram is None else ram + 0.7, mn_ram, rc_ram, 1.0, 1.0)
    rows.append({"key": "ram", "label": "Memória RAM", "pc": _fmt_gb(ram), "min": _fmt_gb(mn_ram),
                 "rec": _fmt_gb(rc_ram), "status": st_ram, "note": ""})

    # ---- disco
    need = max([x for x in (spec("disk", "min"), spec("disk", "rec")) if x] or [0]) or None
    free = hw.get("disk_free_gb")
    st_disk = "unknown" if (free is None or need is None) else ("ok" if free >= need else "low")
    rows.append({"key": "disk", "label": "Espaço livre", "pc": _fmt_gb(free) + (f" ({hw['disk_kind']})" if hw.get("disk_kind") else ""),
                 "min": _fmt_gb(need), "rec": _fmt_gb(need), "status": st_disk, "note": ""})

    # ---- veredito
    known = [r for r in rows if r["status"] != "unknown"]
    lows = [r for r in rows if r["status"] == "low"]
    if not known:
        level, sub = "unknown", "Não consegui comparar nenhum requisito. Confira os campos em 'Meu PC'."
    elif lows:
        level = "no"
        names = ", ".join(r["label"].lower() for r in lows)
        if all(r["key"] == "disk" for r in lows):
            sub = f"Hardware ok, mas falta espaço no disco ({_fmt_gb(need)} necessários)."
        elif all(r["key"] in ("cpu",) for r in lows):
            sub = "O processador parece abaixo do mínimo (comparação aproximada). Pode engasgar."
        else:
            sub = f"Abaixo do mínimo em: {names}."
    elif all(r["status"] == "ok" for r in known):
        level, sub = "great", "Seu PC atende ao recomendado." if rc else "Seu PC passa folgado do mínimo."
    else:
        level, sub = "ok", "Atende ao mínimo: espere gráficos baixos ou médios."
    if level in ("great", "ok", "no") and any(r["status"] == "unknown" and r["key"] in ("cpu", "gpu") for r in rows):
        sub += " Algum requisito não deu pra comparar."

    # ---- qualidade estimada
    quality = ""
    if user_gpu and (rc_gpu or mn_gpu) and level != "no":
        ref = rc_gpu or (mn_gpu * 1.6)
        r = user_gpu / ref
        quality = ("Alto ou Ultra" if r >= 1.4 else "Alto" if r >= 0.95 else "Médio" if r >= 0.6 else "Baixo")
        quality = f"Gráficos estimados: {quality}"

    # ---- dicas
    bykey = {r["key"]: r["status"] for r in rows}
    if bykey["ram"] in ("low", "min") and ram:
        tips.append("Pouca RAM: feche navegador e outros programas antes de jogar. Aumentar a RAM costuma ser o upgrade mais barato.")
    if bykey["gpu"] == "low" and integrated:
        tips.append("Placa de vídeo integrada: use resolução baixa (720p), gráficos no mínimo e desligue sombras e efeitos.")
    elif bykey["gpu"] == "low":
        tips.append("A placa de vídeo está abaixo do mínimo: baixe a resolução e os gráficos, ou escolha outro jogo mais leve.")
    if bykey["disk"] == "low" and need and free is not None:
        tips.append(f"Libere cerca de {max(1, round(need - free))} GB: veja a aba Limpeza (duplicados e arquivos grandes) ou instale em outra unidade.")
    if hw.get("disk_kind") == "HDD" and need and need >= 20:
        tips.append("Seu disco é HDD: o jogo vai carregar devagar. Um SSD faz mais diferença que quase qualquer ajuste.")
    if bykey["cpu"] == "low":
        tips.append("Processador abaixo do mínimo: feche programas em segundo plano e use o plano de energia de alto desempenho (aba Desempenho).")
    if level in ("great", "ok"):
        tips.append("Pra tirar mais do PC, ligue o Modo Jogo e os ajustes de input lag na aba Desempenho.")
    if game.get("note"):
        tips.append(game["note"])
    return {"level": level, "title": LEVEL_TITLES[level], "subtitle": sub, "quality": quality,
            "rows": rows, "tips": tips, "game": game.get("name", "")}


def hw_from_scan(scan):
    """Converte o retorno de hardware.scan() nos campos que evaluate() espera."""
    g = scan.get("gpu_main") or {}
    return {
        "cpu_name": scan.get("cpu_name"), "cores": scan.get("cores"), "threads": scan.get("threads"),
        "ghz": scan.get("ghz"), "ram_gb": scan.get("ram_gb"), "gpu_name": g.get("name"),
        "gpu_vram_gb": g.get("vram_gb"), "gpu_integrated": g.get("integrated", False),
        "laptop": scan.get("laptop"), "disk_free_gb": scan.get("disk_free_best_gb") or scan.get("disk_free_gb"),
        "disk_kind": scan.get("disk_kind"),
    }
