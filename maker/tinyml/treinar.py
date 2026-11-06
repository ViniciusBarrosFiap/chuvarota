import csv
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.metrics import confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier

AQUI = Path(__file__).parent
SAIDA_C = AQUI.parent / "firmware" / "robo" / "modelo_tinyml.h"
CLASSES = ["ok", "pouca_luz", "obstaculo", "escuro_e_obstaculo"]

# usa os dados coletados no robô se existirem; senão, os sintéticos
arq = AQUI / "dados_reais.csv"
if not arq.exists():
    arq = AQUI / "dados_sinteticos.csv"
fonte = "reais" if arq.name == "dados_reais.csv" else "sintéticos"
linhas = list(csv.DictReader(open(arq)))
X = np.array([[float(l["luz"]), float(l["distancia_cm"]) / 200] for l in linhas])
y = np.array([int(l["classe"]) for l in linhas])

Xt, Xv, yt, yv = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
modelo = MLPClassifier(hidden_layer_sizes=(8,), activation="relu", max_iter=3000, random_state=42).fit(Xt, yt)
pred = modelo.predict(Xv)
acc = float((pred == yv).mean())
print(f"dados {fonte}: {len(X)} amostras | acerto no teste: {acc:.3f}")
print(confusion_matrix(yv, pred))

np.savetxt(AQUI / "teste_X.csv", Xv, delimiter=",", fmt="%.6f")
np.savetxt(AQUI / "teste_pred.csv", pred, fmt="%d")
(AQUI / "metricas.json").write_text(json.dumps({"dados": fonte, "amostras": len(X), "acerto_teste": round(acc, 3),
    "parametros": int(sum(c.size for c in modelo.coefs_) + sum(i.size for i in modelo.intercepts_))}, indent=1))


def vetor(nome, a):
    return f"static const float {nome}[{a.size}] = {{" + ", ".join(f"{v:.6f}f" for v in a.ravel()) + "};\n"


W1, W2 = modelo.coefs_  # W1: 2x8, W2: 8x4
b1, b2 = modelo.intercepts_
SAIDA_C.write_text(f"""// gerado por maker/tinyml/treinar.py, não edite à mão
#pragma once
#include <math.h>

#define N_ENTRADAS 2
#define N_ESCONDIDOS {W1.shape[1]}
#define N_CLASSES {W2.shape[1]}

{vetor("PESO_1", W1)}{vetor("VIES_1", b1)}{vetor("PESO_2", W2)}{vetor("VIES_2", b2)}
// luz: 0 (escuro) a 1 (claro); dist: distância em cm dividida por 200
inline int classificar(float luz, float dist) {{
  float x[N_ENTRADAS] = {{luz, dist}};
  float h[N_ESCONDIDOS];
  for (int j = 0; j < N_ESCONDIDOS; j++) {{
    float s = VIES_1[j];
    for (int i = 0; i < N_ENTRADAS; i++) s += x[i] * PESO_1[i * N_ESCONDIDOS + j];
    h[j] = s > 0 ? s : 0;
  }}
  int melhor = 0;
  float maior = -1e30f;
  for (int k = 0; k < N_CLASSES; k++) {{
    float s = VIES_2[k];
    for (int j = 0; j < N_ESCONDIDOS; j++) s += h[j] * PESO_2[j * N_CLASSES + k];
    if (s > maior) {{ maior = s; melhor = k; }}
  }}
  return melhor;
}}
""")
print("escrito", SAIDA_C)
