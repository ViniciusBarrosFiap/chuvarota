import csv
import random
from pathlib import Path

CLASSES = ["ok", "pouca_luz", "obstaculo", "escuro_e_obstaculo"]
LUZ_ESCURO = 0.30  # abaixo disso o ponto é considerado mal iluminado
DIST_OBSTACULO = 30  # cm


def rotular(luz, dist_cm):
    escuro, perto = luz < LUZ_ESCURO, dist_cm < DIST_OBSTACULO
    return 3 if escuro and perto else 2 if perto else 1 if escuro else 0


def gerar(n=4000, semente=42):
    sorteio = random.Random(semente)
    linhas = []
    for _ in range(n):
        luz = sorteio.random()
        dist = sorteio.choice([sorteio.uniform(2, 60), sorteio.uniform(2, 200)])  # metade dos casos com algo por perto
        # o sensor erra um pouco: o rótulo vem do valor real, o modelo vê o valor com ruído
        luz_lida = min(max(luz + sorteio.gauss(0, 0.03), 0), 1)
        dist_lida = min(max(dist + sorteio.gauss(0, 2), 2), 200)
        linhas.append((round(luz_lida, 3), round(dist_lida, 1), rotular(luz, dist)))
    return linhas


if __name__ == "__main__":
    saida = Path(__file__).parent / "dados_sinteticos.csv"
    with open(saida, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["luz", "distancia_cm", "classe"])
        w.writerows(gerar())
    print("gerado", saida)
