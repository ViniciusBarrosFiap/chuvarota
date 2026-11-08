"""Compila logica.h no computador e confere que as setas (e o joystick) do Dabble viram o movimento certo das rodas."""
import subprocess
import tempfile
from pathlib import Path

FW = Path(__file__).parent.parent / "firmware" / "robo"

main = r"""#include <stdio.h>
#include "logica.h"
int main() {
  int cima, baixo, esq, dir, ang, raio;
  while (scanf("%d %d %d %d %d %d", &cima, &baixo, &esq, &dir, &ang, &raio) == 6) {
    Comando c = ler_comando(cima, baixo, esq, dir, ang, raio, false);
    int e, d;
    misturar_rodas(c.frente, c.giro, 180, &e, &d);
    printf("%d %d\n", e, d);
  }
}
"""

# nome, (cima, baixo, esquerda, direita, ângulo, raio), condição sobre (roda esquerda, roda direita)
casos = [
    ("nada apertado", (0, 0, 0, 0, 0, 0), lambda e, d: e == 0 and d == 0),
    ("seta para CIMA: as duas rodas para frente, iguais (anda reto)", (1, 0, 0, 0, 0, 0), lambda e, d: e > 0 and e == d),
    ("seta para BAIXO: as duas rodas para trás, iguais (recua reto)", (0, 1, 0, 0, 0, 0), lambda e, d: e < 0 and e == d),
    ("seta ESQUERDA: gira no lugar para a esquerda (esquerda trás, direita frente)", (0, 0, 1, 0, 0, 0), lambda e, d: e < 0 < d and e == -d),
    ("seta DIREITA: gira no lugar para a direita (esquerda frente, direita trás)", (0, 0, 0, 1, 0, 0), lambda e, d: d < 0 < e and e == -d),
    ("cima + esquerda: anda para frente curvando para a esquerda", (1, 0, 1, 0, 0, 0), lambda e, d: 0 <= e < d),
    ("cima + direita: anda para frente curvando para a direita", (1, 0, 0, 1, 0, 0), lambda e, d: 0 <= d < e),
    ("joystick para cima (90 graus, raio 7)", (0, 0, 0, 0, 90, 7), lambda e, d: e > 0 and abs(e - d) <= 1),
    ("joystick para baixo (270 graus, raio 7)", (0, 0, 0, 0, 270, 7), lambda e, d: e < 0 and abs(e - d) <= 1),
    ("joystick para a esquerda (180 graus, raio 7)", (0, 0, 0, 0, 180, 7), lambda e, d: e < 0 < d),
    ("joystick para a direita (0 grau, raio 7)", (0, 0, 0, 0, 0, 7), lambda e, d: d < 0 < e),
    ("joystick solto (raio 0)", (0, 0, 0, 0, 0, 0), lambda e, d: e == 0 and d == 0),
]

with tempfile.TemporaryDirectory() as tmp:
    (Path(tmp) / "main.cpp").write_text(main)
    subprocess.run(["c++", "-std=c++11", "-O2", "-I", str(FW), str(Path(tmp) / "main.cpp"), "-o", str(Path(tmp) / "teste")], check=True)
    entrada = "\n".join(" ".join(str(v) for v in entradas) for _, entradas, _ in casos)
    saida = subprocess.run([str(Path(tmp) / "teste")], input=entrada, capture_output=True, text=True, check=True).stdout.split("\n")

erros = 0
for (nome, entradas, ok), linha in zip(casos, saida):
    esq, dir = (int(v) for v in linha.split())
    passou = ok(esq, dir)
    erros += not passou
    print(f"{'ok  ' if passou else 'ERRO'} {nome}: esquerda={esq} direita={dir}")
assert erros == 0, f"{erros} caso(s) com a direção errada"
print("todas as direções estão certas")
