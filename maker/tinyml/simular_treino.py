"""Simula o carrinho no computador, sem o robô: o MESMO código do firmware (aprendizado.h e logica.h) andando e aprendendo em salas
simuladas. Compara o modo autônomo antigo, o novo (movimento suave) e o agente que aprende, e confere que o novo erra menos, trava menos e
anda de forma mais contínua. Gera treino_simulado.png.

Os números valem para a SIMULAÇÃO (salas retangulares com obstáculos redondos, sensor com ruído, motor com inércia e movimento com erro),
não para o carrinho de verdade. Para usar os números do SEU carrinho, rode os comandos v e g no Monitor Serial e cole os valores no config.h.
Uso: python maker/tinyml/simular_treino.py [passos_de_treino] [numero_de_sementes]"""
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

# colunas por sala: quase(<30 cm), freios(<20), batidas, andou(cm), células, <8 cm, preso%, giro no lugar%, ré%, viradas de lado/min, solavancos/min
COLUNAS = ["quase(<30cm)", "freios(<20)", "batidas", "andou(cm)", "células", "<8 cm", "preso%", "giro%", "ré%", "vira/min", "solav/min"]
treino = defaultdict(list)  # nome -> [semente][sala] = (11 colunas, epsilon)
avaliacao = defaultdict(list)  # nome -> [semente][sala] = 11 colunas
apertada = defaultdict(list)  # o mesmo, em salas pequenas e cheias de obstáculos
margens = defaultdict(list)  # nome -> [semente] = distância do freio aprendida (andando rápido)

with tempfile.TemporaryDirectory() as tmp:
    exe = Path(tmp) / "mundo"
    subprocess.run(["c++", "-std=c++14", "-O2", "-I", str(FW), str(AQUI / "mundo_treino.cpp"), "-o", str(exe)], check=True)
    for semente in range(1, SEMENTES + 1):
        saida = subprocess.run([str(exe), str(PASSOS), str(semente)], capture_output=True, text=True, check=True).stdout
        t, a, ap = defaultdict(list), defaultdict(list), defaultdict(list)
        for linha in saida.strip().splitlines():
            tipo, nome, primeiro, *v = linha.split(",")
            if tipo == "margem":
                margens[nome].append(float(primeiro))
                continue
            valores = [float(x) for x in v]
            {"treino": t, "avaliacao": a, "apertada": ap}[tipo][nome].append(valores if tipo == "treino" else valores[:11])
        for nome in t:
            treino[nome].append(np.array(t[nome]))
        for nome in a:
            avaliacao[nome].append(np.array(a[nome]))
        for nome in ap:
            apertada[nome].append(np.array(ap[nome]))

ORDEM = ["aleatoria", "regras_antigas", "regras_com_detector", "autonomo_suave", "agente_sem_treino", "agente_do_zero", "agente_margem_fixa", "agente_com_palpite"]
LEGENDA = {
    "aleatoria": "ações aleatórias",
    "regras_antigas": "autônomo ANTIGO (degraus, ré, giro)",
    "regras_com_detector": "autônomo antigo + detector de travamento",
    "autonomo_suave": "autônomo NOVO (movimento suave)",
    "agente_sem_treino": "agente sem treino",
    "agente_do_zero": "agente treinado (do zero)",
    "agente_margem_fixa": "agente treinado (freio fixo em 20 cm)",
    "agente_com_palpite": "agente treinado (freio adaptativo)",
}


def tabela(titulo, dados):
    medias = {n: np.mean([m.mean(axis=0) for m in dados[n]], axis=0) for n in ORDEM}
    print(titulo)
    print(f"{'':42s}" + "".join(f"{c:>13s}" for c in COLUNAS))
    for n in ORDEM:
        print(f"{LEGENDA[n]:42s}" + "".join(f"{x:13.1f}" for x in medias[n]))
    return medias


print(f"AVALIAÇÃO em {len(avaliacao['aleatoria'][0])} salas novas x {SEMENTES} treinos, por sala de {POR_SALA} ciclos (0,13 s cada).")
print("'preso%' = tempo empurrando a parede sem sair do lugar; 'giro%' = tempo girando no lugar; 'solav/min' = degraus nos motores por minuto.\n")
medias = tabela("SALAS NORMAIS", avaliacao)
print()
medias_apertada = tabela("SALAS APERTADAS (pequenas e cheias de obstáculos)", apertada)
print("\ndistância do freio aprendida (andando rápido, cm), por treino:")
for n, rotulo in [("do_zero", "do zero"), ("com_palpite_inicial", "freio adaptativo"), ("margem_fixa", "freio fixo")]:
    print(f"  {rotulo:18s} {margens[n]}")

# ---- gráfico ------------------------------------------------------------------------------------------------------------------
fig, eixos = plt.subplots(1, 3, figsize=(17, 4.6))
ax = eixos[0]
for nome, cor in [("do_zero", "#1f77b4"), ("com_palpite_inicial", "#d62728")]:
    curva = np.mean([m[:, 0] for m in treino[nome]], axis=0)  # quase batidas por sala, média das sementes
    suave = np.convolve(curva, np.ones(10) / 10, mode="valid")
    ax.plot(np.arange(len(suave)) * POR_SALA / 1000, suave, color=cor, label={"do_zero": "começando do zero", "com_palpite_inicial": "começando com palpite"}[nome])
ax.axhline(medias["regras_antigas"][0], color="gray", ls="--", label="autônomo antigo")
ax.set_xlabel("ciclos de treino (milhares)")
ax.set_ylabel("ciclos com algo a menos de 30 cm\n(por sala de 600 ciclos)")
ax.set_title("O robô aprende a ficar longe das paredes")
ax.legend(fontsize=8)

cores = ["#bbbbbb", "#888888", "#555555", "#2ca02c", "#9ecae1", "#1f77b4", "#17becf", "#d62728"]
rotulos = ["aleatória", "autôn.\nantigo", "antigo +\ndetector", "autôn.\nNOVO", "agente\nsem treino", "agente\ndo zero", "agente\nfreio fixo", "agente\nfreio adapt."]
for ax, indice, titulo in [(eixos[1], 10, "Solavancos nos motores por minuto — menos é melhor"), (eixos[2], 3, "Distância andada por sala (cm) — mais é melhor")]:
    ax.bar(range(len(ORDEM)), [medias[n][indice] for n in ORDEM], color=cores)
    ax.set_xticks(range(len(ORDEM)))
    ax.set_xticklabels(rotulos, fontsize=7)
    ax.set_title(titulo, fontsize=10)
fig.suptitle("Simulação, em salas que o robô nunca viu — não são dados do carrinho real", fontsize=11)
fig.tight_layout()
fig.savefig(AQUI / "treino_simulado.png", dpi=130)
print(f"\ngráfico salvo em {AQUI / 'treino_simulado.png'}")

# ---- o que precisa ser verdade --------------------------------------------------------------------------------------------------
I = {c: i for i, c in enumerate(COLUNAS)}
antigas, detector, suave, agente, sem_treino = (medias[n] for n in ["regras_antigas", "regras_com_detector", "autonomo_suave", "agente_com_palpite", "agente_sem_treino"])
# o autônomo novo contra o antigo (é isso que o usuário vê: travar, rodar no lugar, dar solavanco)
assert suave[I["preso%"]] < 0.2 * antigas[I["preso%"]], "o autônomo novo deveria passar bem menos tempo empurrando parede que o antigo"
assert suave[I["andou(cm)"]] > 3 * antigas[I["andou(cm)"]], "o autônomo novo deveria andar bem mais que o antigo"
assert suave[I["células"]] > 3 * antigas[I["células"]], "o autônomo novo deveria visitar bem mais cantos da sala que o antigo"
assert suave[I["solav/min"]] < 0.5 * detector[I["solav/min"]], "o autônomo novo deveria dar bem menos solavancos que o antigo com detector"
assert suave[I["giro%"]] < 0.6 * detector[I["giro%"]], "o autônomo novo deveria girar bem menos no lugar que o antigo com detector"
assert suave[I["ré%"]] < 0.3 * detector[I["ré%"]], "o autônomo novo deveria dar bem menos ré"
assert suave[I["batidas"]] < antigas[I["batidas"]], "o autônomo novo deveria raspar menos que o antigo"
# o agente que aprende
assert agente[I["freios(<20)"]] < 0.25 * antigas[I["freios(<20)"]], "o agente treinado deveria precisar de bem menos freios de segurança que o autônomo antigo"
assert agente[I["batidas"]] < antigas[I["batidas"]], "o agente treinado deveria raspar menos que o autônomo antigo"
assert agente[I["andou(cm)"]] > 3 * antigas[I["andou(cm)"]], "o agente treinado deveria andar bem mais que o autônomo antigo"
assert agente[I["solav/min"]] < 0.25 * sem_treino[I["solav/min"]], "o treino deveria acabar com os solavancos do agente sem treino"
assert agente[I["quase(<30cm)"]] < 0.25 * sem_treino[I["quase(<30cm)"]], "o treino deveria reduzir bastante as quase-batidas"
assert np.mean(margens["com_palpite_inicial"]) < 20, "o freio adaptativo deveria ter chegado mais perto que os 20 cm iniciais"
assert np.mean(margens["com_palpite_inicial"]) >= 12 and all(m == 20 for m in margens["margem_fixa"]), "a distância do freio saiu dos limites"
ap_adapt, ap_fixo = medias_apertada["agente_com_palpite"], medias_apertada["agente_margem_fixa"]
fixo = medias["agente_margem_fixa"]
# O freio adaptativo chega mais perto (era o objetivo), mas na simulação isso NÃO fez o robô andar mais; os números ficam aqui para consulta:
print(f"freio adaptativo contra freio fixo: salas normais andou {agente[I['andou(cm)']]:.0f} contra {fixo[I['andou(cm)']]:.0f} cm e {agente[I['<8 cm']]:.1f} contra {fixo[I['<8 cm']]:.1f} ciclos a menos de 8 cm;"
      f" salas apertadas andou {ap_adapt[I['andou(cm)']]:.0f} contra {ap_fixo[I['andou(cm)']]:.0f} cm e {ap_adapt[I['<8 cm']]:.1f} contra {ap_fixo[I['<8 cm']]:.1f} ciclos a menos de 8 cm")
print("o autônomo novo e o agente treinado travam menos, dão menos solavanco e andam mais que o autônomo antigo, na simulação")
