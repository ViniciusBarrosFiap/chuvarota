"""Compila o modelo em C e confere se ele decide igual ao scikit-learn."""
import subprocess
import tempfile
from pathlib import Path

import numpy as np

AQUI = Path(__file__).parent
X = np.loadtxt(AQUI / "teste_X.csv", delimiter=",")
esperado = np.loadtxt(AQUI / "teste_pred.csv", dtype=int)

main = '#include <stdio.h>\n#include "modelo_tinyml.h"\nint main(){float l,d;while(scanf("%f,%f",&l,&d)==2)printf("%d\\n",classificar(l,d));}\n'
with tempfile.TemporaryDirectory() as tmp:
    (Path(tmp) / "main.cpp").write_text(main)
    subprocess.run(["c++", "-O2", "-I", str(AQUI.parent / "firmware" / "robo"), str(Path(tmp) / "main.cpp"), "-o", str(Path(tmp) / "teste")], check=True)
    saida = subprocess.run([str(Path(tmp) / "teste")], input="\n".join(f"{a:.6f},{b:.6f}" for a, b in X), capture_output=True, text=True, check=True).stdout
obtido = np.array(saida.split(), dtype=int)
iguais = float((obtido == esperado).mean())
print(f"o código C decide igual ao Python em {iguais:.1%} de {len(X)} amostras")
assert iguais >= 0.999, "o código C diverge do modelo treinado"
