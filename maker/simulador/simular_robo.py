"""Finge ser o robô: manda leituras ao MVP para testar o endpoint antes de o carrinho chegar.
Só para teste: apague as leituras (reinicie o app) antes de gravar o vídeo com o robô de verdade."""
import os
import random
import re
import sys
import time
from pathlib import Path

import numpy as np
import requests

CABECALHO = Path(__file__).resolve().parents[1] / "firmware" / "robo" / "modelo_tinyml.h"
NOMES = ["ok", "pouca_luz", "obstaculo", "escuro_e_obstaculo"]


def carregar_modelo():
    texto = CABECALHO.read_text()
    pesos = {n: np.array([float(v.rstrip("f")) for v in re.search(rf"{n}\[\d+\] = \{{([^}}]*)\}}", texto).group(1).split(",")]) for n in ("PESO_1", "VIES_1", "PESO_2", "VIES_2")}
    h = int(re.search(r"N_ESCONDIDOS (\d+)", texto).group(1))
    return pesos["PESO_1"].reshape(2, h), pesos["VIES_1"], pesos["PESO_2"].reshape(h, 4), pesos["VIES_2"]


def classificar(modelo, luz, dist):
    W1, B1, W2, B2 = modelo
    oculta = np.maximum(np.array([luz, dist]) @ W1 + B1, 0)
    return int(np.argmax(oculta @ W2 + B2))


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/robo"
    token = os.environ["ROBO_TOKEN"]
    modelo = carregar_modelo()
    sorteio = random.Random(1)
    for i in range(int(sys.argv[2]) if len(sys.argv) > 2 else 8):
        luz, dist = sorteio.uniform(0, 1), sorteio.choice([sorteio.uniform(5, 40), sorteio.uniform(40, 200)])
        situacao = NOMES[classificar(modelo, luz, dist / 200)]
        r = requests.post(url, json={"luz_pct": round(luz * 100), "distancia_cm": round(dist), "situacao": situacao}, headers={"X-Token": token}, timeout=15)
        print(i + 1, f"luz {luz:.0%} dist {dist:.0f} cm ->", situacao, r.status_code)
        time.sleep(1)
