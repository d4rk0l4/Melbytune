"""Lista local de placas de vídeo com pontuação relativa APROXIMADA.

Os números são estimativas de desempenho geral em jogos, numa escala parecida com a de benchmarks
públicos (G3D Mark). Foram reunidos à mão e podem errar uns 20%: servem pra COMPARAR placas e pra
estimar se um jogo roda, não pra medir. Dá pra editar à vontade (mude o valor ou adicione linhas).
Nada é consultado na internet.
"""
import re

GPUS = {
    # ---- NVIDIA RTX 50
    "GeForce RTX 5090": 39000, "GeForce RTX 5080": 34500, "GeForce RTX 5070 Ti": 31000,
    "GeForce RTX 5070": 27000,
    # ---- NVIDIA RTX 40
    "GeForce RTX 4090": 38000, "GeForce RTX 4080 SUPER": 34500, "GeForce RTX 4080": 34000,
    "GeForce RTX 4070 Ti SUPER": 31500, "GeForce RTX 4070 Ti": 28000,
    "GeForce RTX 4070 SUPER": 27500, "GeForce RTX 4070": 25500,
    "GeForce RTX 4060 Ti": 22500, "GeForce RTX 4060": 19500,
    # ---- NVIDIA RTX 30
    "GeForce RTX 3090 Ti": 27000, "GeForce RTX 3090": 26500, "GeForce RTX 3080 Ti": 26000,
    "GeForce RTX 3080": 25000, "GeForce RTX 3070 Ti": 23500, "GeForce RTX 3070": 22000,
    "GeForce RTX 3060 Ti": 20000, "GeForce RTX 3060": 17000, "GeForce RTX 3050": 12800,
    # ---- NVIDIA RTX 20 / GTX 16
    "GeForce RTX 2080 Ti": 21500, "GeForce RTX 2080 SUPER": 20000, "GeForce RTX 2080": 19500,
    "GeForce RTX 2070 SUPER": 18000, "GeForce RTX 2070": 16000, "GeForce RTX 2060 SUPER": 16500,
    "GeForce RTX 2060": 14000, "GeForce GTX 1660 Ti": 13000, "GeForce GTX 1660 SUPER": 12500,
    "GeForce GTX 1660": 11800, "GeForce GTX 1650 SUPER": 10000, "GeForce GTX 1650": 7800,
    # ---- NVIDIA GTX 10
    "GeForce GTX 1080 Ti": 18500, "GeForce GTX 1080": 15500, "GeForce GTX 1070 Ti": 14800,
    "GeForce GTX 1070": 14000, "GeForce GTX 1060 6GB": 10000, "GeForce GTX 1060 3GB": 9300,
    "GeForce GTX 1050 Ti": 6300, "GeForce GTX 1050": 5000, "GeForce GT 1030": 2700,
    # ---- NVIDIA GTX 9 / 7 / 6 / 5 e mais antigas
    "GeForce GTX 980 Ti": 12500, "GeForce GTX 980": 10000, "GeForce GTX 970": 8800,
    "GeForce GTX 960": 5400, "GeForce GTX 950": 4300,
    "GeForce GTX 780 Ti": 7500, "GeForce GTX 780": 6500, "GeForce GTX 770": 4900,
    "GeForce GTX 760": 4000, "GeForce GTX 750 Ti": 3900, "GeForce GTX 750": 3300,
    "GeForce GTX 680": 4000, "GeForce GTX 670": 3800, "GeForce GTX 660 Ti": 3900, "GeForce GTX 660": 3400,
    "GeForce GTX 650 Ti": 2100, "GeForce GTX 650": 1500, "GeForce GTX 560 Ti": 2300,
    "GeForce GTX 560": 1900, "GeForce GTX 550 Ti": 900, "GeForce GTX 460": 1400,
    "GeForce GT 730": 650, "GeForce GT 710": 380, "GeForce GT 640": 700,
    "GeForce 9800 GT": 550, "GeForce 8800 GT": 500,
    # ---- NVIDIA de notebook (MX)
    "GeForce MX350": 3000, "GeForce MX330": 2300, "GeForce MX250": 2500, "GeForce MX150": 2000,
    "GeForce MX130": 1300, "GeForce MX110": 1100,
    # ---- AMD RX 9000 / 7000
    "Radeon RX 9070 XT": 31000, "Radeon RX 9070": 28000,
    "Radeon RX 7900 XTX": 31000, "Radeon RX 7900 XT": 28500, "Radeon RX 7800 XT": 24500,
    "Radeon RX 7700 XT": 22000, "Radeon RX 7600 XT": 17500, "Radeon RX 7600": 16500,
    # ---- AMD RX 6000
    "Radeon RX 6950 XT": 29500, "Radeon RX 6900 XT": 28000, "Radeon RX 6800 XT": 25000,
    "Radeon RX 6800": 24000, "Radeon RX 6750 XT": 21800, "Radeon RX 6700 XT": 20500,
    "Radeon RX 6650 XT": 17000, "Radeon RX 6600 XT": 16800, "Radeon RX 6600": 14500,
    "Radeon RX 6500 XT": 7600, "Radeon RX 6400": 6200,
    # ---- AMD RX 5000 / Vega / 500 / 400
    "Radeon RX 5700 XT": 17500, "Radeon RX 5700": 16000, "Radeon RX 5600 XT": 13500,
    "Radeon RX 5500 XT": 9800, "Radeon RX Vega 64": 13000, "Radeon RX Vega 56": 12000,
    "Radeon RX 590": 9500, "Radeon RX 580": 8800, "Radeon RX 570": 7600, "Radeon RX 560": 4600,
    "Radeon RX 550": 2700, "Radeon RX 480": 8000, "Radeon RX 470": 7000, "Radeon RX 460": 4300,
    # ---- AMD R9 / R7 / HD
    "Radeon R9 390": 7500, "Radeon R9 380": 4900, "Radeon R9 290": 7300, "Radeon R9 280X": 5000,
    "Radeon R9 280": 4300, "Radeon R9 270X": 3800, "Radeon R9 270": 3000, "Radeon R7 370": 2800,
    "Radeon R7 260X": 2300, "Radeon R7 250": 1200, "Radeon R7 240": 700,
    "Radeon HD 7970": 5000, "Radeon HD 7950": 4300, "Radeon HD 7870": 3500, "Radeon HD 7850": 2800,
    "Radeon HD 7770": 1800, "Radeon HD 6950": 2200, "Radeon HD 6870": 2100, "Radeon HD 5870": 2000,
    "Radeon HD 5770": 1000, "Radeon HD 5670": 550, "Radeon HD 4870": 900,
    # ---- Intel Arc
    "Intel Arc A770": 15500, "Intel Arc A750": 14000, "Intel Arc A580": 10500, "Intel Arc A380": 4800,
    # ---- Gráficos integrados (placa de vídeo dividida com a memória RAM)
    "Intel UHD Graphics 770": 2300, "Intel UHD Graphics 730": 1500, "Intel UHD Graphics 630": 1300,
    "Intel UHD Graphics 620": 1000, "Intel UHD Graphics 610": 600, "Intel UHD Graphics 600": 550,
    "Intel UHD Graphics": 900, "Intel Iris Xe Graphics": 2200, "Intel Iris Plus Graphics": 1300,
    "Intel HD Graphics 630": 1200, "Intel HD Graphics 620": 900, "Intel HD Graphics 530": 850,
    "Intel HD Graphics 520": 800, "Intel HD Graphics 4600": 700, "Intel HD Graphics 4400": 560,
    "Intel HD Graphics 4000": 400, "Intel HD Graphics 3000": 250,
    "Radeon Vega 11": 2500, "Radeon Vega 10": 2300, "Radeon Vega 8": 2000, "Radeon Vega 7": 1800,
    "Radeon Vega 6": 1400, "Radeon Vega 3": 800, "Radeon 780M": 5500, "Radeon 680M": 4600,
    "Radeon 660M": 2800, "Radeon 610M": 800, "Radeon Graphics (integrada)": 1800,
}

# Como reconhecer cada placa num texto. Por padrão vale o próprio nome sem "GeForce/Radeon/NVIDIA/AMD";
# aqui ficam os apelidos e as exceções.
_VENDOR_WORDS = {"nvidia", "geforce", "amd", "radeon"}
_EXTRA_KEYS = {
    "Intel HD Graphics 4000": [" hd 4000 "], "Intel HD Graphics 4600": [" hd 4600 "],
    "Intel HD Graphics 4400": [" hd 4400 "], "Intel HD Graphics 3000": [" hd 3000 "],
    "Intel HD Graphics 530": [" hd 530 "], "Intel HD Graphics 520": [" hd 520 "],
    "Intel HD Graphics 620": [" hd 620 "], "Intel HD Graphics 630": [" hd 630 "],
    "Intel UHD Graphics 620": [" uhd 620 "], "Intel UHD Graphics 630": [" uhd 630 "],
    "GeForce GTX 1060 6GB": [" gtx 1060 "],
    "Radeon Graphics (integrada)": [" radeon graphics "],
    "Intel Iris Xe Graphics": [" iris xe "],
}
_OWN_KEY = {"Radeon Graphics (integrada)": []}  # esse não usa o nome como chave


def _norm(s):
    s = (s or "").lower()
    for junk in ("(r)", "(tm)", "(c)", "®", "™"):
        s = s.replace(junk, " ")
    return " " + re.sub(r"[^a-z0-9]+", " ", s).strip() + " "


def _key(name):
    words = [w for w in _norm(name).split() if w not in _VENDOR_WORDS]
    return " " + " ".join(words) + " "


# chave de busca -> nome da placa
_KEYS = {}
for _n in GPUS:
    if _n in _OWN_KEY:
        continue
    _KEYS.setdefault(_key(_n), _n)
for _n, _alts in _EXTRA_KEYS.items():
    for _a in _alts:
        _KEYS.setdefault(_a, _n)
_ORDERED = sorted(_KEYS, key=len, reverse=True)  # chave mais longa primeiro (3060 Ti antes de 3060)


def find_gpu(text):
    """Procura no texto uma placa da lista. Retorna (nome, pontuação) ou None."""
    t = _norm(text)
    for k in _ORDERED:  # a chave mais longa vem primeiro: "RTX 3060 Ti" ganha de "RTX 3060"
        if k in t:
            name = _KEYS[k]
            return name, GPUS[name]
    return None


def detect_gpu(detected_name):
    """Nome (da lista) da placa que o Windows informou, ou None."""
    found = find_gpu(detected_name)
    return found[0] if found else None


_INTEGRATED = re.compile(
    r"uhd graphics|hd graphics|iris|radeon graphics|vega (3|6|7|8|10|11)\b|"
    r"radeon (610|660|680|740|760|780|880|890)m\b|microsoft basic|basic render")


def is_integrated(name):
    """True para gráficos integrados (usam a memória RAM). Intel Arc e Vega 56/64 são placas dedicadas."""
    n = _norm(name)
    if " arc " in n or re.search(r" rx vega (56|64) ", n):
        return False
    if " intel " in n and " hd " not in n and " uhd " not in n and " iris " not in n:
        return False  # "Intel ..." sem ser HD/UHD/Iris (ex.: Arc) não conta como integrada
    return bool(_INTEGRATED.search(n))
