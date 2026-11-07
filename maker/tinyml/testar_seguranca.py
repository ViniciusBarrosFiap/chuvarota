"""Compila seguranca.h no computador e confere o filtro da distância: "sem eco" logo depois de uma leitura perto vira obstáculo."""
import subprocess
import tempfile
from pathlib import Path

FW = Path(__file__).parent.parent / "firmware" / "robo"
DIST_MINIMA = 25  # o mesmo valor do config.h
COLADO = DIST_MINIMA - 1

main = r"""#include <stdio.h>
#include "seguranca.h"
int main() {
  FiltroDistancia f;
  float d;
  char c;
  while (scanf(" %c", &c) == 1) {
    if (c == 'e') { f.esquecer(); continue; }  // 'e' = depois de uma manobra
    if (scanf("%f", &d) != 1) return 1;       // 'l' valor = leitura
    printf("%.0f\n", f.filtrar(d, 2 * 25, 24));
  }
}
"""


def rodar(passos):
    """passos: lista de números (leituras) ou 'e' (esquecer). Devolve o que o filtro devolveu para cada leitura."""
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "main.cpp").write_text(main)
        subprocess.run(["c++", "-std=c++11", "-O2", "-I", str(FW), str(Path(tmp) / "main.cpp"), "-o", str(Path(tmp) / "teste")], check=True)
        entrada = "\n".join("e" if p == "e" else f"l {p}" for p in passos)
        saida = subprocess.run([str(Path(tmp) / "teste")], input=entrada, capture_output=True, text=True, check=True).stdout.split()
    return [int(v) for v in saida]


erros = 0


def confere(nome, passos, esperado):
    global erros
    obtido = rodar(passos)
    ok = obtido == esperado
    erros += not ok
    print(f"{'ok  ' if ok else 'ERRO'} {nome}: {obtido}")


confere("leituras normais passam sem mudar", [150, 80, 60, 30, 20], [150, 80, 60, 30, 20])
confere("sem eco logo depois de algo perto (45 cm) vira obstáculo colado", [100, 45, 200, 200], [100, 45, COLADO, COLADO])
confere("sem eco com o caminho longe (100 cm) continua sem eco", [100, 200, 200], [100, 200, 200])
confere("quando o eco volta, o filtro solta", [45, 200, 200, 60, 200], [45, COLADO, COLADO, 60, 200])
confere("depois de 20 leituras sem eco o 'sem eco' volta a valer (sensor desligado não trava o carrinho)", [40] + [200] * 22, [40] + [COLADO] * 20 + [200, 200])
confere("depois da manobra o filtro esquece", [30, "e", 200], [30, 200])
assert erros == 0, f"{erros} caso(s) do filtro com resultado errado"
print("o filtro da distância está certo")
