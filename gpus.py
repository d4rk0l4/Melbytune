"""Lista local de placas de vídeo com pontuação relativa APROXIMADA.

Os números são estimativas de desempenho geral em jogos (escala parecida com
benchmarks públicos). Dá pra editar à vontade: é só mudar o valor ou adicionar linhas.
Nada é consultado na internet.
"""
import re

GPUS = {
    # NVIDIA RTX 50
    "GeForce RTX 5090": 39000, "GeForce RTX 5080": 34500, "GeForce RTX 5070 Ti": 31000,
    "GeForce RTX 5070": 27000,
    # NVIDIA RTX 40
    "GeForce RTX 4090": 38000, "GeForce RTX 4080 SUPER": 34500, "GeForce RTX 4080": 34000,
    "GeForce RTX 4070 Ti SUPER": 31500, "GeForce RTX 4070 Ti": 28000,
    "GeForce RTX 4070 SUPER": 27500, "GeForce RTX 4070": 25500,
    "GeForce RTX 4060 Ti": 22500, "GeForce RTX 4060": 19500,
    # NVIDIA RTX 30
    "GeForce RTX 3090 Ti": 27000, "GeForce RTX 3090": 26500, "GeForce RTX 3080 Ti": 26000,
    "GeForce RTX 3080": 25000, "GeForce RTX 3070 Ti": 23500, "GeForce RTX 3070": 22000,
    "GeForce RTX 3060 Ti": 20000, "GeForce RTX 3060": 17000, "GeForce RTX 3050": 12800,
    # NVIDIA RTX 20 / GTX
    "GeForce RTX 2080 Ti": 21500, "GeForce RTX 2070 SUPER": 18000, "GeForce RTX 2060": 14000,
    "GeForce GTX 1660 SUPER": 12500, "GeForce GTX 1650": 7800,
    "GeForce GTX 1080": 15500, "GeForce GTX 1070": 14000, "GeForce GTX 1060 6GB": 10000,
    # AMD
    "Radeon RX 9070 XT": 31000, "Radeon RX 9070": 28000,
    "Radeon RX 7900 XTX": 31000, "Radeon RX 7900 XT": 28500, "Radeon RX 7800 XT": 24500,
    "Radeon RX 7700 XT": 22000, "Radeon RX 7600": 16500,
    "Radeon RX 6800 XT": 25000, "Radeon RX 6700 XT": 20500, "Radeon RX 6600": 14500,
    "Radeon RX 580": 8800,
}


def detect_gpu(detected_name: str):
    """Tenta casar o nome que o Windows reporta com um item da lista."""
    if not detected_name:
        return None
    d = re.sub(r"[^a-z0-9 ]", "", detected_name.lower())
    best = None
    for name in GPUS:
        n = re.sub(r"[^a-z0-9 ]", "", name.lower())
        short = n.replace("geforce ", "").replace("radeon ", "")
        if short in d and (best is None or len(name) > len(best)):
            best = name
    return best
