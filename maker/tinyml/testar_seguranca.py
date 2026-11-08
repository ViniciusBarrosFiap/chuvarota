"""Compila logica.h no computador e confere (1) o filtro da distância ("sem eco" logo depois de uma leitura perto vira obstáculo)
e (2) o detector de travamento (mandou andar e a distância não mudou = preso raspando em uma parede)."""
import subprocess
import tempfile
from pathlib import Path

FW = Path(__file__).parent.parent / "firmware" / "robo"
DIST_MINIMA = 25  # o mesmo valor do config.h
COLADO = DIST_MINIMA - 1

main = r"""#include <stdio.h>
#include "logica.h"
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

# ---- detector de travamento -----------------------------------------------------------------------------------------------------
main_detector = r"""#include <stdio.h>
#include "logica.h"
int main() {
  DetectorTravado t;
  int andando;
  float d;
  while (scanf("%d %f", &andando, &d) == 2) printf("%d\n", t.atualizar(andando, d) ? 1 : 0);
}
"""


def detector(passos):
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "main.cpp").write_text(main_detector)
        subprocess.run(["c++", "-std=c++11", "-O2", "-I", str(FW), str(Path(tmp) / "main.cpp"), "-o", str(Path(tmp) / "teste")], check=True)
        entrada = "\n".join(f"{int(a)} {d}" for a, d in passos)
        return [int(v) for v in subprocess.run([str(Path(tmp) / "teste")], input=entrada, capture_output=True, text=True, check=True).stdout.split()]


def confere_detector(nome, passos, esperado):
    global erros
    obtido = detector(passos)
    ok = obtido == esperado
    erros += not ok
    print(f"{'ok  ' if ok else 'ERRO'} detector: {nome}: {obtido}")


confere_detector("andando livre (a distância cai ~5,5 cm por ciclo): nunca acusa", [(1, 150 - 5.5 * i) for i in range(20)], [0] * 20)
confere_detector("andando e a distância parada em 80 cm: acusa no 4º ciclo e de novo 4 ciclos depois", [(1, 80)] * 8, [0, 0, 0, 1, 0, 0, 0, 1])
confere_detector("ruído de 1 cm na distância parada também acusa", [(1, 80 + r) for r in [0.5, -0.8, 0.9, -0.4, 0.7, -1.0, 0.2, 0.6]], [0, 0, 0, 1, 0, 0, 0, 1])
confere_detector("sem eco (200) parado não acusa: é o caminho livre", [(1, 200)] * 8, [0] * 8)
confere_detector("parado de propósito (não mandou andar) não acusa", [(0, 80)] * 8, [0] * 8)
confere_detector("se parar de andar no meio, a contagem recomeça", [(1, 80)] * 3 + [(0, 80)] + [(1, 80)] * 3, [0] * 7)

assert erros == 0, f"{erros} caso(s) com resultado errado"
print("o filtro da distância e o detector de travamento estão certos")
