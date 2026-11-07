"""Compila aprendizado.h no computador e confere as regras do Q-learning do carrinho: estados, notas, atualização da tabela,
freio de segurança, fuga e o tamanho do que vai para a memória flash."""
import subprocess
import tempfile
from pathlib import Path

FW = Path(__file__).parent.parent / "firmware" / "robo"

main = r"""#include <stdio.h>
#include "aprendizado.h"
#define SAIDA(nome, valor) printf("%s=%g\n", nome, (double)(valor))
int main() {
  // estados
  SAIDA("estados", N_ESTADOS);
  SAIDA("estado_min", codigo_estado(0, -50, 0));
  SAIDA("estado_max", codigo_estado(200, 50, 3));
  SAIDA("faixa_15", faixa_dist(15)); SAIDA("faixa_25", faixa_dist(25)); SAIDA("faixa_40", faixa_dist(40));
  SAIDA("faixa_70", faixa_dist(70)); SAIDA("faixa_150", faixa_dist(150)); SAIDA("faixa_200", faixa_dist(200));
  // notas
  SAIDA("nota_frente_livre", recompensa(FRENTE, 150, 144));
  SAIDA("nota_frente_devagar_livre", recompensa(FRENTE_LENTO, 150, 144));
  SAIDA("nota_frente_quase_batida", recompensa(FRENTE, 40, 27));
  SAIDA("nota_frente_freio", recompensa(FRENTE, 30, 18));
  SAIDA("nota_frente_travado", recompensa(FRENTE, 60, 60));
  SAIDA("nota_girar_a_toa", recompensa(GIRAR_ESQ, 150, 150));
  SAIDA("nota_girar_e_abriu", recompensa(GIRAR_DIR, 35, 70));
  SAIDA("nota_re_a_toa", recompensa(RE, 150, 156));
  // aprendizado: sem palpite, uma ação com nota boa passa a ter valor positivo e a ruim, negativo
  Agente a;
  a.zerar(false);
  SAIDA("q_inicial_zero", a.m.q[5][FRENTE]);
  a.decidir(150, false, true);   // 1º ciclo: só escolhe
  a.decidir(144, false, true);   // 2º: fecha o 1º, com nota da ação FRENTE (padrão da tabela zerada)
  SAIDA("passos_depois_de_2_ciclos", a.m.passos);
  // freio: perto demais não entra no aprendizado e manda recuar
  Agente b;
  b.zerar(false);
  Decisao x = b.decidir(150, true, true);
  x = b.decidir(15, true, true);
  SAIDA("freio_perto", x.freio);
  SAIDA("escapar_no_primeiro", x.escapar);
  // 5 freios em 30 ciclos = preso: foge
  Agente c;
  c.zerar(false);
  int fugas = 0;
  for (int i = 0; i < 5; i++) fugas += c.decidir(15, false, false).escapar;
  SAIDA("fugas_em_5_freios", fugas);
  // exploração cai com o treino
  Agente e;
  float eps0 = e.epsilon();
  e.m.passos = 10000;
  SAIDA("epsilon_inicio", eps0);
  SAIDA("epsilon_apos_10000", e.epsilon());
  // blocos: depois de PASSOS_POR_BLOCO ciclos de aprendizado, o histórico ganha um bloco
  Agente f;
  f.zerar(false);
  for (int i = 0; i < PASSOS_POR_BLOCO + 5; i++) f.decidir(100, false, true);
  SAIDA("blocos_fechados", f.m.blocos);
  SAIDA("bloco_fechou_flag", f.fechou_bloco);
  // tamanho do que vai para a memória flash
  SAIDA("bytes_memoria", sizeof(Memoria));
  // com o palpite inicial, a regra antiga: longe anda, perto vira
  Agente g;
  g.zerar(true);
  SAIDA("palpite_longe", g.melhor_acao(codigo_estado(150, -5.5f, 0)));
  SAIDA("palpite_perto", g.melhor_acao(codigo_estado(25, -5, 0)));
  SAIDA("palpite_travado", g.melhor_acao(codigo_estado(60, 0, 0)));
}
"""

with tempfile.TemporaryDirectory() as tmp:
    (Path(tmp) / "main.cpp").write_text(main)
    subprocess.run(["c++", "-std=c++14", "-O2", "-I", str(FW), str(Path(tmp) / "main.cpp"), "-o", str(Path(tmp) / "teste")], check=True)
    saida = subprocess.run([str(Path(tmp) / "teste")], capture_output=True, text=True, check=True).stdout
v = {k: float(x) for k, x in (linha.split("=") for linha in saida.split())}

erros = 0


def confere(nome, condicao, detalhe=""):
    global erros
    erros += not condicao
    print(f"{'ok  ' if condicao else 'ERRO'} {nome} {detalhe}")


confere("os códigos de estado cabem na tabela", 0 <= v["estado_min"] and v["estado_max"] < v["estados"], f"(0 a {v['estado_max']:.0f} de {v['estados']:.0f})")
confere("faixas de distância: <20, <30, <50, <90, <190, sem eco", [v[f"faixa_{d}"] for d in (15, 25, 40, 70, 150, 200)] == [0, 1, 2, 3, 4, 5])
confere("andar livre rende mais que andar devagar livre", v["nota_frente_livre"] > v["nota_frente_devagar_livre"] > 0)
confere("quase batida e freio são notas ruins, o freio pior", v["nota_frente_freio"] < v["nota_frente_quase_batida"] < 0)
confere("mandar andar e não sair do lugar é nota ruim", v["nota_frente_travado"] < 0)
confere("girar à toa e recuar à toa são notas ruins", v["nota_girar_a_toa"] < 0 and v["nota_re_a_toa"] < 0)
confere("girar e abrir espaço é nota boa", v["nota_girar_e_abriu"] > 0)
confere("o aprendizado conta os ciclos fechados", v["passos_depois_de_2_ciclos"] == 1)
confere("freio de segurança perto demais, sem fuga na primeira vez", v["freio_perto"] == 1 and v["escapar_no_primeiro"] == 0)
confere("5 freios seguidos viram uma fuga", v["fugas_em_5_freios"] >= 1)
confere("a exploração cai com o treino", v["epsilon_apos_10000"] < v["epsilon_inicio"] and v["epsilon_apos_10000"] >= 0.05)
confere("o histórico fecha um bloco a cada 300 passos", v["blocos_fechados"] == 1 and v["bloco_fechou_flag"] == 1)
confere("o que vai para a memória flash cabe com folga (limite de 4000 bytes por valor)", v["bytes_memoria"] < 4000, f"({v['bytes_memoria']:.0f} bytes)")
confere("palpite inicial: longe anda, perto vira, travado vira", v["palpite_longe"] in (0, 1) and v["palpite_perto"] in (2, 3) and v["palpite_travado"] in (2, 3))
assert erros == 0, f"{erros} verificação(ões) do aprendizado falharam"
print("o Q-learning do carrinho está certo")
