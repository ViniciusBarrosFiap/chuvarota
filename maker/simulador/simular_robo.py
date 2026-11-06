"""Finge ser o robô: gera leituras de sensores com os defeitos de verdade, calcula a janela e o modelo igual ao firmware
e manda o resultado ao MVP. Serve para testar o endpoint antes de o carrinho chegar.
Só para teste: reinicie o app (az webapp restart) antes de gravar o vídeo com o robô de verdade, para apagar estas leituras.
Uso: ROBO_TOKEN=... python simular_robo.py [url] [quantas_leituras] [semente]"""
import os
import re
import sys
import time
from pathlib import Path

import numpy as np
import requests

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent / "tinyml"))
from caracteristicas import CLASSES, JANELA, caracteristicas  # noqa: E402
from simular_sensores import leituras  # noqa: E402

CABECALHO = AQUI.parent / "firmware" / "robo" / "modelo_tinyml.h"


def carregar_modelo():
    texto = CABECALHO.read_text()
    tam = [int(v) for v in re.search(r"TAMANHOS\[\d+\] = \{([^}]*)\}", texto).group(1).split(",")]
    pegar = lambda n: np.array([float(v.rstrip("f")) for v in re.search(rf"{n}\[\d+\] = \{{([^}}]*)\}}", texto).group(1).split(",")])
    return [(pegar(f"PESO_{k + 1}").reshape(tam[k], tam[k + 1]), pegar(f"VIES_{k + 1}")) for k in range(len(tam) - 1)]


def classificar(modelo, x):
    for k, (w, b) in enumerate(modelo):
        x = x @ w + b
        if k < len(modelo) - 1:
            x = np.maximum(x, 0)
    return int(np.argmax(x))


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/robo"
    quantas = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    semente = int(sys.argv[3]) if len(sys.argv) > 3 else 7
    token = os.environ["ROBO_TOKEN"]
    modelo = carregar_modelo()
    luz, dist, real = leituras(semente)
    janelas = range(JANELA - 1, len(luz), max(1, (len(luz) - JANELA) // quantas))
    for n, t in enumerate(list(janelas)[:quantas], 1):
        x = caracteristicas(luz[t - JANELA + 1:t + 1], dist[t - JANELA + 1:t + 1])
        situacao = CLASSES[classificar(modelo, x)]
        r = requests.post(url, json={"luz_pct": round(float(luz[t]) * 100), "distancia_cm": round(float(dist[t])), "situacao": situacao}, headers={"X-Token": token}, timeout=15)
        print(n, f"luz {luz[t]:.0%} dist {dist[t]:.0f} cm -> {situacao} (certo: {CLASSES[real[t]]}) {r.status_code}")
        time.sleep(1)
