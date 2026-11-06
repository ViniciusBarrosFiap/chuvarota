import csv
import itertools
import json
import time
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support
from sklearn.neural_network import MLPClassifier

from caracteristicas import CLASSES, JANELA, caracteristicas
from simular_sensores import conjunto

warnings.filterwarnings("ignore")
AQUI = Path(__file__).parent
SAIDA_C = AQUI.parent / "firmware" / "robo" / "modelo_tinyml.h"
SEMENTES = {"treino": range(0, 3500), "val": range(3500, 4250), "teste": range(4250, 5000)}


def janelas_reais(arq):
    """Monta janelas com os dados coletados no robô (luz,distancia_cm,classe, uma linha por leitura)."""
    linhas = [(float(a["luz"]), float(a["distancia_cm"]), int(a["classe"])) for a in csv.DictReader(open(arq))]
    X, y, brutas, bloco = [], [], [], []
    for i in range(JANELA - 1, len(linhas)):
        j = linhas[i - JANELA + 1:i + 1]
        if len({c for _, _, c in j}) == 1:  # só janelas dentro de uma mesma situação
            l, d = [a for a, _, _ in j], [b for _, b, _ in j]
            X.append(caracteristicas(l, d))
            y.append(j[-1][2])
            brutas.append(np.concatenate([l, d]))
            bloco.append(i // 400)
    return np.array(X), np.array(y), np.array(brutas), np.array(bloco)


def regras(X, lim_tend, lim_amp):
    """A solução clássica: limites fixos sobre as mesmas características da janela."""
    luz, amp, dist, tend = X[:, 0], X[:, 2], X[:, 3] * 200, X[:, 4] * 100
    r = np.zeros(len(X), int)
    r[luz < 0.30] = 1
    r[amp > lim_amp] = 4
    r[(tend < -lim_tend) & (dist < 100)] = 5
    r[(dist < 30) & (luz >= 0.30)] = 2
    r[(dist < 30) & (luz < 0.30)] = 3
    return r


def uma_leitura(brutas):
    """Decide só com a última leitura, sem olhar o tempo: não consegue ver luz piscando nem objeto se aproximando."""
    luz, dist = brutas[:, JANELA - 1], brutas[:, 2 * JANELA - 1]
    r = np.zeros(len(brutas), int)
    r[luz < 0.30] = 1
    r[(dist < 30) & (luz >= 0.30)] = 2
    r[(dist < 30) & (luz < 0.30)] = 3
    return r


def macro(y, p):
    return float(f1_score(y, p, average="macro", labels=range(6)))


def balancear(X, y, semente=0):
    """Repete as classes raras para o modelo não ignorá-las."""
    r = np.random.default_rng(semente)
    alvo = int(0.12 * len(y))
    idx = [np.where(y == k)[0] for k in range(6)]
    extra = [r.choice(i, max(0, alvo - len(i))) for i in idx if len(i)]
    sel = np.concatenate([np.arange(len(y))] + extra)
    return X[sel], y[sel]


t0 = time.time()
real = AQUI / "dados_reais.csv"
if real.exists():
    Xr, yr, Br, bloco = janelas_reais(real)
    fonte = "reais"
    corte = np.quantile(bloco, [0.7, 0.85])
    sel = {"treino": bloco <= corte[0], "val": (bloco > corte[0]) & (bloco <= corte[1]), "teste": bloco > corte[1]}
    D = {k: (Xr[m], yr[m], Br[m]) for k, m in sel.items()}
else:
    fonte = "simulados"
    D = {"treino": conjunto(SEMENTES["treino"], None), "val": conjunto(SEMENTES["val"], None), "teste": conjunto(SEMENTES["teste"], 1.0)}  # treino e validação com ruído variado; o teste principal com o ruído previsto
Xt, yt, _ = D["treino"]
Xv, yv, _ = D["val"]
Xe, ye, Be = D["teste"]
print(f"dados {fonte}: treino {len(yt)}, validação {len(yv)}, teste {len(ye)} janelas")

# 1) o melhor conjunto de limites para a solução clássica, escolhido no treino
melhor_regra = max(itertools.product(range(20, 90, 10), np.arange(0.15, 0.7, 0.05)), key=lambda p: macro(yt, regras(Xt, *p)))
print("limites da solução clássica:", melhor_regra)

# 2) busca de hiperparâmetros do MLP pela validação
Xb, yb = balancear(Xt, yt)
resultados = []
ARQUITETURAS = [(16, 8), (24, 12), (32, 16), (32, 16, 8)]
for oculta, alpha in itertools.product(ARQUITETURAS, [1e-3, 1e-2]):
    t, notas = time.time(), []
    for semente in (0, 1):
        m = MLPClassifier(oculta, alpha=alpha, max_iter=800, early_stopping=True, n_iter_no_change=20, random_state=semente).fit(Xb, yb)
        notas.append(macro(yv, m.predict(Xv)))
    n_par = sum(c.size for c in m.coefs_) + sum(i.size for i in m.intercepts_)
    f1 = float(np.mean(notas))
    resultados.append({"camadas": list(oculta), "alpha": alpha, "f1_macro_val": round(f1, 4), "parametros": int(n_par), "segundos": round(time.time() - t)})
    print(f"  {oculta} alpha={alpha}: F1 macro (validação, média de 2 sementes) {f1:.4f}, {n_par} parâmetros, {time.time() - t:.0f}s", flush=True)
topo = max(r["f1_macro_val"] for r in resultados)
melhor = min((r for r in resultados if r["f1_macro_val"] >= topo - 0.003), key=lambda r: r["parametros"])  # dentro de 0,003 do melhor é empate: fica o menor modelo
print("escolhido:", melhor["camadas"], melhor["alpha"], flush=True)

# 3) modelo final: treino + validação
Xf, yf = balancear(np.vstack([Xt, Xv]), np.concatenate([yt, yv]), 1)
modelo = MLPClassifier(tuple(melhor["camadas"]), alpha=melhor["alpha"], max_iter=1500, early_stopping=True, n_iter_no_change=30, random_state=0).fit(Xf, yf)
pred = modelo.predict(Xe)
prec, rev, f1c, sup = precision_recall_fscore_support(ye, pred, labels=range(6), zero_division=0)
n_par = int(sum(c.size for c in modelo.coefs_) + sum(i.size for i in modelo.intercepts_))

# 4) comparação com as soluções clássicas
comparacao = {
    "uma_leitura_sem_janela": {"acerto": round(accuracy_score(ye, uma_leitura(Be)), 4), "f1_macro": round(macro(ye, uma_leitura(Be)), 4)},
    "regras_sobre_a_janela": {"acerto": round(accuracy_score(ye, regras(Xe, *melhor_regra)), 4), "f1_macro": round(macro(ye, regras(Xe, *melhor_regra)), 4)},
    "modelo_tinyml": {"acerto": round(accuracy_score(ye, pred), 4), "f1_macro": round(macro(ye, pred), 4)},
}
for k, v in comparacao.items():
    print(f"{k:26s} acerto {v['acerto']:.3f}  F1 macro {v['f1_macro']:.3f}")

# 5) robustez: o mesmo modelo com sensores mais ruidosos que o previsto
robustez = []
if fonte == "simulados":
    for mult in (0.5, 1, 2, 3):  # sensores de 0,5 a 3 vezes mais ruidosos que o previsto
        Xr_, yr_, _ = conjunto(SEMENTES["teste"], ruido=mult)
        robustez.append({"ruido": mult, "modelo": round(macro(yr_, modelo.predict(Xr_)), 4), "regras": round(macro(yr_, regras(Xr_, *melhor_regra)), 4)})
    print("robustez (F1 macro):", robustez)

# 6) relatórios
matriz = confusion_matrix(ye, pred, labels=range(6), normalize="true")
fig, ax = plt.subplots(figsize=(7, 6))
ax.imshow(matriz, cmap="Blues", vmin=0, vmax=1)
ax.set_xticks(range(6), CLASSES, rotation=45, ha="right")
ax.set_yticks(range(6), CLASSES)
for i, j in itertools.product(range(6), range(6)):
    ax.text(j, i, f"{matriz[i, j]:.2f}", ha="center", va="center", color="white" if matriz[i, j] > 0.5 else "black", fontsize=8)
ax.set_xlabel("previsto")
ax.set_ylabel("real")
ax.set_title(f"Matriz de confusão no teste ({fonte})")
fig.tight_layout()
fig.savefig(AQUI / "matriz_confusao.png", dpi=130)
if robustez:
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot([r["ruido"] for r in robustez], [r["modelo"] for r in robustez], "o-", label="modelo TinyML")
    ax.plot([r["ruido"] for r in robustez], [r["regras"] for r in robustez], "s--", label="regras sobre a janela")
    ax.set_xlabel("ruído dos sensores (1 = o previsto)")
    ax.set_ylabel("F1 macro no teste")
    ax.set_ylim(0, 1)
    ax.legend()
    fig.tight_layout()
    fig.savefig(AQUI / "robustez.png", dpi=130)

(AQUI / "metricas.json").write_text(json.dumps({
    "dados": fonte, "janelas": {"treino": len(yt), "validacao": len(yv), "teste": len(ye)}, "janela_leituras": JANELA,
    "busca_de_hiperparametros": resultados, "escolhido": melhor, "parametros": n_par, "limites_da_solucao_classica": {"tendencia_cm_s": float(melhor_regra[0]), "amplitude_luz": round(float(melhor_regra[1]), 2)},
    "comparacao": comparacao, "robustez": robustez,
    "por_classe": {CLASSES[k]: {"precisao": round(float(prec[k]), 3), "recall": round(float(rev[k]), 3), "f1": round(float(f1c[k]), 3), "amostras": int(sup[k])} for k in range(6)},
    "segundos_de_treino": round(time.time() - t0)}, indent=1, ensure_ascii=False))

# janelas de conferência para o teste do código C++
idx = np.random.default_rng(0).choice(len(ye), min(400, len(ye)), replace=False)
np.savetxt(AQUI / "teste_janelas.csv", Be[idx], delimiter=",", fmt="%.6f")
np.savetxt(AQUI / "teste_classes.csv", modelo.predict(Xe[idx]), fmt="%d")


# 7) exporta o modelo para C++ (qualquer número de camadas)
def vetor(nome, a):
    return f"static const float {nome}[{a.size}] = {{" + ", ".join(f"{(0.0 if abs(v) < 1e-30 else v):.7g}f" for v in a.ravel()) + "};\n"


camadas = [modelo.coefs_[0].shape[0]] + [c.shape[1] for c in modelo.coefs_]
corpo = "".join(vetor(f"PESO_{k + 1}", w) + vetor(f"VIES_{k + 1}", b) for k, (w, b) in enumerate(zip(modelo.coefs_, modelo.intercepts_)))
tamanhos = ", ".join(str(c) for c in camadas)
SAIDA_C.write_text(f"""// gerado por maker/tinyml/treinar.py, não edite à mão
#pragma once

#define N_CAMADAS {len(camadas) - 1}
#define N_ENTRADAS {camadas[0]}
#define N_CLASSES {camadas[-1]}
#define MAIOR_CAMADA {max(camadas)}
static const int TAMANHOS[{len(camadas)}] = {{{tamanhos}}};

{corpo}
static const float* PESOS[N_CAMADAS] = {{{", ".join(f"PESO_{k + 1}" for k in range(len(camadas) - 1))}}};
static const float* VIESES[N_CAMADAS] = {{{", ".join(f"VIES_{k + 1}" for k in range(len(camadas) - 1))}}};

// entrada: as {camadas[0]} características (ver caracteristicas.h); saída: índice da classe
inline int classificar(const float* x) {{
  float a[MAIOR_CAMADA], b[MAIOR_CAMADA];
  for (int i = 0; i < N_ENTRADAS; i++) a[i] = x[i];
  for (int k = 0; k < N_CAMADAS; k++) {{
    int n_in = TAMANHOS[k], n_out = TAMANHOS[k + 1];
    for (int j = 0; j < n_out; j++) {{
      float s = VIESES[k][j];
      for (int i = 0; i < n_in; i++) s += a[i] * PESOS[k][i * n_out + j];
      b[j] = (k < N_CAMADAS - 1 && s < 0) ? 0 : s;  // ReLU nas camadas escondidas
    }}
    for (int j = 0; j < n_out; j++) a[j] = b[j];
  }}
  int melhor = 0;
  for (int k = 1; k < N_CLASSES; k++) if (a[k] > a[melhor]) melhor = k;
  return melhor;
}}
""")
print(f"modelo com {n_par} parâmetros escrito em {SAIDA_C} | tempo total {time.time() - t0:.0f}s")
