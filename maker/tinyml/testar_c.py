"""Compila o C++ do robô no computador e confere se ele decide igual ao Python, partindo das leituras brutas."""
import subprocess
import tempfile
from pathlib import Path

import numpy as np

AQUI = Path(__file__).parent
FW = AQUI.parent / "firmware" / "robo"
janelas = np.loadtxt(AQUI / "teste_janelas.csv", delimiter=",")
esperado = np.loadtxt(AQUI / "teste_classes.csv", dtype=int)

main = r"""#include <stdio.h>
#include "caracteristicas.h"
#include "modelo_tinyml.h"
int main() {
  float l[JANELA], d[JANELA], x[N_ENTRADAS];
  while (true) {
    for (int i = 0; i < JANELA; i++) if (scanf("%f,", &l[i]) != 1) return 0;
    for (int i = 0; i < JANELA; i++) if (scanf("%f,", &d[i]) != 1) return 0;
    caracteristicas(l, d, x);
    printf("%d\n", classificar(x));
  }
}
"""
with tempfile.TemporaryDirectory() as tmp:
    (Path(tmp) / "main.cpp").write_text(main)
    subprocess.run(["c++", "-std=c++11", "-O2", "-I", str(FW), str(Path(tmp) / "main.cpp"), "-o", str(Path(tmp) / "teste")], check=True)
    entrada = "\n".join(",".join(f"{v:.6f}" for v in linha) for linha in janelas)
    saida = subprocess.run([str(Path(tmp) / "teste")], input=entrada, capture_output=True, text=True, check=True).stdout
obtido = np.array(saida.split(), dtype=int)
iguais = float((obtido == esperado).mean())
print(f"o C++ decide igual ao Python em {iguais:.1%} de {len(esperado)} janelas")
assert len(obtido) == len(esperado) and iguais >= 0.99, "o C++ diverge do modelo treinado"
