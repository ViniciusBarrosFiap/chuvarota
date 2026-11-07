"""Simula o modo treino do carrinho no computador: o MESMO código do robô (aprendizado.h e seguranca.h) aprendendo em salas
simuladas, sem o carrinho. Gera treino_simulado.png e confere que o robô que aprendeu erra menos que as regras fixas.

Os números valem para a SIMULAÇÃO (salas retangulares com obstáculos redondos, sensor com ruído e movimento com erro), não para o
carrinho de verdade. Uso: python maker/tinyml/simular_treino.py [passos_de_treino] [numero_de_sementes]"""
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

AQUI = Path(__file__).parent
FW = AQUI.parent / "firmware" / "robo"
PASSOS = int(sys.argv[1]) if len(sys.argv) > 1 else 60000
SEMENTES = int(sys.argv[2]) if len(sys.argv) > 2 else 3
POR_SALA = 600

treino = defaultdict(list)  # nome -> [semente][sala] = (quase, freios, batidas, andou, células, epsilon)
avaliacao = defaultdict(list)  # nome -> [semente][sala] = (quase, freios, batidas, andou, células)

with tempfile.TemporaryDirectory() as tmp:
    exe = Path(tmp) / "mundo"
    subprocess.run(["c++", "-std=c++14", "-O2", "-I", str(FW), str(AQUI / "mundo_treino.cpp"), "-o", str(exe)], check=True)
    for semente in range(1, SEMENTES + 1):
        saida = subprocess.run([str(exe), str(PASSOS), str(semente)], capture_output=True, text=True, check=True).stdout
        t, a = defaultdict(list), defaultdict(list)
        for linha in saida.strip().splitlines():
            tipo, nome, _, *v = linha.split(",")
            (t if tipo == "treino" else a)[nome].append([float(x) for x in (v if tipo == "treino" else v[:5])])
        for nome in t:
            treino[nome].append(np.array(t[nome]))
        for nome in a:
            avaliacao[nome].append(np.array(a[nome]))

ORDEM = ["aleatoria", "regras_antigas", "regras_com_detector", "agente_sem_treino", "agente_do_zero", "agente_com_palpite"]
LEGENDA = {
    "aleatoria": "ações aleatórias",
    "regras_antigas": "regras fixas (modo autônomo antigo)",
    "regras_com_detector": "regras fixas + detector de travamento",
    "agente_sem_treino": "agente sem treino",
    "agente_do_zero": "agente treinado (do zero)",
    "agente_com_palpite": "agente treinado (com palpite inicial)",
}
medias = {n: np.mean([m.mean(axis=0) for m in avaliacao[n]], axis=0) for n in ORDEM}  # por sala de 600 passos
print(f"AVALIAÇÃO em {len(avaliacao['aleatoria'][0])} salas novas x {SEMENTES} treinos, por sala de {POR_SALA} ciclos (0,13 s cada):")
print(f"{'':42s} {'quase(<30cm)':>12s} {'freios(<20)':>12s} {'batidas':>8s} {'andou(cm)':>10s} {'células':>8s}")
for n in ORDEM:
    q, f, b, an, c = medias[n]
    print(f"{LEGENDA[n]:42s} {q:12.1f} {f:12.1f} {b:8.1f} {an:10.0f} {c:8.1f}")

# ---- gráfico ------------------------------------------------------------------------------------------------------------------
fig, eixos = plt.subplots(1, 3, figsize=(17, 4.6))
ax = eixos[0]
for nome, cor in [("do_zero", "#1f77b4"), ("com_palpite_inicial", "#d62728")]:
    curva = np.mean([m[:, 0] for m in treino[nome]], axis=0)  # quase batidas por sala, média das sementes
    janela = 10
    suave = np.convolve(curva, np.ones(janela) / janela, mode="valid")
    ax.plot(np.arange(len(suave)) * POR_SALA / 1000, suave, color=cor, label={"do_zero": "começando do zero", "com_palpite_inicial": "começando com palpite"}[nome])
ax.axhline(medias["regras_antigas"][0], color="gray", ls="--", label="regras fixas (modo autônomo antigo)")
ax.set_xlabel("passos de treino (milhares)")
ax.set_ylabel("ciclos com algo a menos de 30 cm\n(por sala de 600 ciclos)")
ax.set_title("O robô aprende a ficar longe das paredes")
ax.legend(fontsize=8)

cores = ["#bbbbbb", "#888888", "#555555", "#9ecae1", "#1f77b4", "#d62728"]
for ax, indice, titulo in [(eixos[1], 1, "Freios de segurança (< 20 cm) — menos é melhor"), (eixos[2], 3, "Distância andando para frente (cm) — mais é melhor")]:
    ax.bar(range(len(ORDEM)), [medias[n][indice] for n in ORDEM], color=cores)
    ax.set_xticks(range(len(ORDEM)))
    ax.set_xticklabels(["aleatória", "regras\nantigas", "regras +\ndetector", "agente\nsem treino", "agente\ndo zero", "agente\ncom palpite"], fontsize=8)
    ax.set_title(titulo, fontsize=10)
fig.suptitle("Simulação: modo treino (Q-learning) em salas que ele nunca viu — não são dados do carrinho real", fontsize=11)
fig.tight_layout()
fig.savefig(AQUI / "treino_simulado.png", dpi=130)
print(f"gráfico salvo em {AQUI / 'treino_simulado.png'}")

# ---- o que precisa ser verdade --------------------------------------------------------------------------------------------------
antigas, agente = medias["regras_antigas"], medias["agente_com_palpite"]
assert agente[1] < 0.25 * antigas[1], "o agente treinado deveria precisar de bem menos freios de segurança que as regras antigas"
assert agente[2] < antigas[2], "o agente treinado deveria raspar/bater menos que as regras antigas"
assert agente[3] > antigas[3], "o agente treinado deveria andar mais que as regras antigas"
assert agente[4] > antigas[4], "o agente treinado deveria visitar mais cantos da sala que as regras antigas"
assert agente[0] < 0.25 * medias["agente_sem_treino"][0], "o treino deveria reduzir bastante as quase-batidas"
print("o agente treinado erra menos e anda mais que as regras antigas, na simulação")
