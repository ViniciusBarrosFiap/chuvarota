"""Confere o protocolo entre o carrinho e o painel: (1) a leitura das linhas que o painel manda (cfg, modo, painel) e (2) que os formatos das
linhas que o carrinho imprime (telemetria, blocos, política, ajustes) são os mesmos que a demonstração do painel usa e que o painel sabe ler."""
import re
import subprocess
import tempfile
from pathlib import Path

AQUI = Path(__file__).parent
FW = AQUI.parent / "firmware" / "robo"

main = r"""#include <stdio.h>
#include "logica.h"
static const char* nomes[] = {"vazia", "letra", "cfg", "cfg_lista", "modo", "painel", "desconhecida"};
int main() {
  const char* casos[] = {"a", " q ", "cfg?", "cfg? ", "cfg meta_passos 5000", "cfg eps_inicial 0.35", "cfg margem_min 16\r", "modo treino", "painel 1", "painel 0",
                         "cfg", "cfg x", "modo", "xyz", "   ", "", "treino"};
  for (const char* c : casos) {
    LinhaSerial l = interpretar_linha(c);
    printf("%s|%c|%s|%g\n", nomes[l.tipo], l.letra ? l.letra : '-', l.nome[0] ? l.nome : "-", l.valor);
  }
}
"""
with tempfile.TemporaryDirectory() as tmp:
    (Path(tmp) / "main.cpp").write_text(main)
    subprocess.run(["c++", "-std=c++14", "-O2", "-I", str(FW), str(Path(tmp) / "main.cpp"), "-o", str(Path(tmp) / "teste")], check=True)
    saida = subprocess.run([str(Path(tmp) / "teste")], capture_output=True, text=True, check=True).stdout.splitlines()

esperado = ["letra|a|-|0", "letra|q|-|0", "cfg_lista|-|-|0", "cfg_lista|-|-|0", "cfg|-|meta_passos|5000", "cfg|-|eps_inicial|0.35", "cfg|-|margem_min|16",
            "modo|-|treino|0", "painel|-|-|1", "painel|-|-|0", "desconhecida|-|-|0", "desconhecida|-|x|0", "desconhecida|-|-|0", "desconhecida|-|-|0",
            "vazia|-|-|0", "vazia|-|-|0", "desconhecida|-|-|0"]
erros = 0
for entrada, obtido, esp in zip(["a", " q ", "cfg?", "cfg? ", "cfg meta_passos 5000", "cfg eps_inicial 0.35", "cfg margem_min 16\\r", "modo treino", "painel 1", "painel 0", "cfg", "cfg x", "modo", "xyz", "   ", "", "treino"], saida, esperado):
    ok = obtido == esp
    erros += not ok
    print(f"{'ok  ' if ok else 'ERRO'} linha {entrada!r}: {obtido}" + ("" if ok else f" (esperado {esp})"))

# ---- formatos: o carrinho (robo.ino) e a demonstração (mundo_treino.cpp) têm que imprimir o mesmo -----------------------------------------
robo = (FW / "robo.ino").read_text()
demo = (AQUI / "mundo_treino.cpp").read_text()


def formato(texto, prefixo):
    """O texto da primeira chamada printf/Serial.printf cujo formato começa com `prefixo` (sem aspas)."""
    m = re.search(r'printf\(\s*"(' + re.escape(prefixo) + r'(?:[^"\\]|\\.)*)"', texto)
    assert m, f"não achei o formato que começa com {prefixo!r}"
    return m.group(1)


pares = [("~", "telemetria"), ("treino: bloco", "linha de bloco"), ("POL,%d", "política"), ("POL_FREIO", "freio da política"), ("freio: parou a", "freio ajustado"),
         ("ESTADO modo=", "estado")]
for prefixo, nome in pares:
    f_robo, f_demo = formato(robo, prefixo), formato(demo, prefixo)
    # o robô usa %lu e %u para os mesmos números que a demonstração imprime com %.0f e %u: normaliza antes de comparar
    norm = lambda t: re.sub(r"%(?:l|\.\d)?[a-z]+|%g", "%", t)  # noqa: E731
    ok = norm(f_robo) == norm(f_demo)
    erros += not ok
    print(f"{'ok  ' if ok else 'ERRO'} formato '{nome}' igual no robô e na demonstração")
    if not ok:
        print("     robô:", f_robo, "\n     demo:", f_demo)

ok = '"preso: fuga"' in robo and '"preso: fuga' in demo
erros += not ok
print(f"{'ok  ' if ok else 'ERRO'} a mensagem de fuga é a mesma no robô e na demonstração")

# toda linha da demonstração tem que ser de um tipo que o painel entende
padroes = [r"^~\d+,[\d.]+,\d+,\d,\d,-?\d,[01],\d+,\d+,[\d.]+$", r"^CFG \w+=[\d.]+$", r"^ESTADO modo=\d passos=\d+ eps=[\d.]+ margem=\d+ margem_lento=\d+ painel=\d$",
           r"^treino: bloco \d+ \| passos \d+ \| exploração \d+% \| nota média -?[\d.]+ \| quase-batidas \d+ \| freios \d+ \| distância do freio \d+ cm$", r"^POL,\d,\d,\d$",
           r"^POL_FREIO,\d+,\d+$", r"^modo: ", r"^freio: parou a \d+ cm do obstáculo \| distância do freio \d+ -> \d+ cm$", r"^preso: fuga$", r"^aprendizado: "]
import json
demo_js = (AQUI.parent / "painel" / "demo.js").read_text(encoding="utf-8")
linhas = json.loads(demo_js[demo_js.index("{"):demo_js.rindex("}") + 1])["linhas"]
desconhecidas = [l for l in linhas if not any(re.match(p, l) for p in padroes)]
ok = not desconhecidas
erros += not ok
print(f"{'ok  ' if ok else 'ERRO'} as {len(linhas)} linhas da demonstração são todas de tipos que o painel lê" + ("" if ok else f" (ex.: {desconhecidas[:3]})"))
assert erros == 0, f"{erros} verificação(ões) do protocolo falharam"
print("o protocolo do painel está certo")
