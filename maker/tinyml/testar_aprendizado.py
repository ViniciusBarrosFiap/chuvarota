"""Compila aprendizado.h no computador e confere as regras do Q-learning do carrinho: estados, notas, ações que duram alguns ciclos,
freio de segurança, fuga, freio adaptativo e o tamanho do que vai para a memória flash."""
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
  SAIDA("estado_min", codigo_estado(0, -50, 0, 20));
  SAIDA("estado_max", codigo_estado(200, 50, 3, 20));
  SAIDA("faixa_15", faixa_dist(15, 20)); SAIDA("faixa_25", faixa_dist(25, 20)); SAIDA("faixa_40", faixa_dist(40, 20));
  SAIDA("faixa_70", faixa_dist(70, 20)); SAIDA("faixa_150", faixa_dist(150, 20)); SAIDA("faixa_200", faixa_dist(200, 20));
  SAIDA("faixa_25_freio12", faixa_dist(25, 12));  // com o freio mais perto, 25 cm já é "perto", e não "perigo"
  // notas
  SAIDA("nota_frente_livre", recompensa(FRENTE, 150, 144, 20));
  SAIDA("nota_curva_livre", recompensa(CURVA_ESQ, 60, 55, 20));
  SAIDA("nota_frente_quase_batida", recompensa(FRENTE, 40, 27, 20));
  SAIDA("nota_frente_freio", recompensa(FRENTE, 30, 18, 20));
  SAIDA("nota_frente_travado", recompensa(FRENTE, 60, 60, 20));
  SAIDA("nota_girar_a_toa", recompensa(GIRAR_ESQ, 150, 150, 20));
  SAIDA("nota_curvar_a_toa", recompensa(CURVA_DIR, 150, 150, 20));
  SAIDA("nota_girar_e_abriu", recompensa(GIRAR_DIR, 35, 70, 20));
  SAIDA("nota_virar_mesmo_lado", recompensa(GIRAR_DIR, 35, 70, 20, 2));
  SAIDA("nota_virar_lado_oposto", recompensa(GIRAR_DIR, 35, 70, 20, 1));
  // as rodas de cada ação
  Rodas f = rodas_da_acao(FRENTE, 150, 20, false), fp = rodas_da_acao(FRENTE, 30, 20, false), fe = rodas_da_acao(FRENTE, 150, 20, true);
  SAIDA("frente_livre_esq", f.esq); SAIDA("frente_livre_dir", f.dir);
  SAIDA("frente_perto_esq", fp.esq);  // mais devagar perto do obstáculo
  SAIDA("frente_escuro_esq", fe.esq);
  Rodas ce = rodas_da_acao(CURVA_ESQ, 150, 20, false), cd = rodas_da_acao(CURVA_DIR, 150, 20, false);
  SAIDA("curva_esq_esq", ce.esq); SAIDA("curva_esq_dir", ce.dir); SAIDA("curva_dir_esq", cd.esq); SAIDA("curva_dir_dir", cd.dir);
  Rodas ge = rodas_da_acao(GIRAR_ESQ, 150, 20, false), gd = rodas_da_acao(GIRAR_DIR, 150, 20, false);
  SAIDA("girar_esq_esq", ge.esq); SAIDA("girar_esq_dir", ge.dir); SAIDA("girar_dir_esq", gd.esq); SAIDA("girar_dir_dir", gd.dir);
  // a ação dura CICLOS_POR_ACAO ciclos; só o freio interrompe
  Agente a;
  a.zerar(false);
  SAIDA("q_inicial_zero", a.m.q[5][FRENTE]);
  Decisao primeira = a.decidir(150, false, true);
  int iguais = 0;
  for (int i = 1; i < CICLOS_POR_ACAO; i++) iguais += (a.decidir(150 - 5 * i, false, true).acao == primeira.acao);
  SAIDA("ciclos_com_a_mesma_acao", iguais + 1);
  SAIDA("passos_no_meio_da_acao", a.m.passos);
  a.decidir(130, false, true);  // fecha a ação: agora conta o passo
  SAIDA("passos_ao_fechar_a_acao", a.m.passos);
  // freio: perto demais interrompe a ação, não entra no aprendizado e manda recuar
  Agente b;
  b.zerar(false);
  b.decidir(150, true, true);
  Decisao x = b.decidir(15, true, true);
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
  // blocos: depois de PASSOS_POR_BLOCO passos (cada um com CICLOS_POR_ACAO ciclos), o histórico ganha um bloco
  Agente g;
  g.zerar(false);
  for (int i = 0; i < (PASSOS_POR_BLOCO + 2) * CICLOS_POR_ACAO; i++) g.decidir(190 - (i % 30) * 4, false, true);  // a distância sempre muda: não conta como preso
  SAIDA("blocos_fechados", g.m.blocos);
  SAIDA("bloco_fechou_flag", g.fechou_bloco);
  // distância do freio adaptativa
  Agente h;
  h.zerar(false);
  SAIDA("freio_inicial", h.m.freio_cm[0]);
  h.decidir(150, false, false);
  h.decidir(15, false, false);        // freio: guarda que foi uma andada rápida
  h.freou(30, true);                  // parou a 30 cm: sobrou espaço
  SAIDA("freio_apos_sobrar_espaco", h.m.freio_cm[0]);
  h.freou(30, false);                 // sem permissão de diminuir (modo IA): não muda
  SAIDA("freio_sem_permissao", h.m.freio_cm[0]);
  h.freou(3, true);                   // parou a 3 cm: perto demais
  SAIDA("freio_apos_parar_perto", h.m.freio_cm[0]);
  h.freou(200, true);                 // sumiu o eco
  SAIDA("freio_apos_perder_eco", h.m.freio_cm[0]);
  for (int i = 0; i < 100; i++) h.freou(30, true);
  SAIDA("freio_minimo", h.m.freio_cm[0]);
  SAIDA("margem_min_config", TREINO_MARGEM_MIN_CM);
  for (int i = 0; i < 100; i++) h.freou(2, true);
  SAIDA("freio_maximo", h.m.freio_cm[0]);
  Agente fixo;
  fixo.zerar(false);
  fixo.adaptar_margem = false;
  fixo.decidir(150, false, false);
  fixo.decidir(15, false, false);
  fixo.freou(30, true);
  SAIDA("freio_fixo", fixo.m.freio_cm[0]);
  // ajustes vindos do painel
  Agente k;
  MetaTreino meta;
  const char* erro;
  SAIDA("cfg_ok", aplicar_config(k, meta, "eps_tau", 2000, &erro));
  SAIDA("cfg_eps_tau", k.eps_tau);
  SAIDA("cfg_fora_da_faixa", aplicar_config(k, meta, "eps_tau", 5, &erro));
  SAIDA("cfg_fora_da_faixa_mudou", k.eps_tau);
  SAIDA("cfg_nome_ruim", aplicar_config(k, meta, "xyz", 1, &erro));
  SAIDA("cfg_erro_nome", !strcmp(erro, "nome desconhecido"));
  aplicar_config(k, meta, "eps_inicial", 0.1f, &erro);
  SAIDA("cfg_eps_inicial", k.epsilon());
  aplicar_config(k, meta, "meta_passos", 5000, &erro);
  aplicar_config(k, meta, "meta_minutos", 30, &erro);
  SAIDA("cfg_meta_passos", meta.passos); SAIDA("cfg_meta_minutos", meta.minutos);
  aplicar_config(k, meta, "ciclos_por_acao", 4, &erro);
  k.zerar(false);
  for (int i = 0; i < 4; i++) k.decidir(150 - 6 * i, false, true);
  SAIDA("cfg_passos_em_4_ciclos", k.m.passos);   // a ação ainda não terminou: nenhum passo contado
  k.decidir(100, false, true);
  SAIDA("cfg_passos_no_5o_ciclo", k.m.passos);   // terminou: um passo
  aplicar_config(k, meta, "margem_min", 18, &erro);
  k.decidir(150, false, false); k.decidir(15, false, false);
  for (int i = 0; i < 100; i++) k.freou(30, true);
  SAIDA("cfg_margem_min_respeitada", k.m.freio_cm[0]);
  SAIDA("epsilon_em_zero", Agente().epsilon_em(0)); SAIDA("epsilon_em_infinito", Agente().epsilon_em(1e6f));
  // tamanho do que vai para a memória flash
  SAIDA("bytes_memoria", sizeof(Memoria));
  // com o palpite inicial: longe segue, perto gira, preso gira
  Agente p;
  p.zerar(true);
  SAIDA("palpite_longe", p.melhor_acao(codigo_estado(150, -5.5f, 0, 20)));
  SAIDA("palpite_perto", p.melhor_acao(codigo_estado(25, -5, 0, 20)));
  SAIDA("palpite_travado", p.melhor_acao(codigo_estado(60, 0, 0, 20)));
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
confere("as faixas andam com a distância do freio", v["faixa_25_freio12"] == 2 and v["faixa_25"] == 1)
confere("seguir livre rende mais que curvar livre", v["nota_frente_livre"] > v["nota_curva_livre"] > 0)
confere("quase batida e freio são notas ruins, o freio pior", v["nota_frente_freio"] < v["nota_frente_quase_batida"] < 0)
confere("mandar seguir e não sair do lugar é nota ruim", v["nota_frente_travado"] < 0)
confere("girar ou curvar à toa são notas ruins", v["nota_girar_a_toa"] < 0 and v["nota_curvar_a_toa"] < 0)
confere("girar e abrir espaço é nota boa", v["nota_girar_e_abriu"] > 0)
confere("trocar de lado (vai e volta) perde pontos", v["nota_virar_lado_oposto"] < v["nota_virar_mesmo_lado"])
confere("seguir livre: as duas rodas iguais e na velocidade cheia", v["frente_livre_esq"] == 1 and v["frente_livre_dir"] == 1)
confere("seguir perto do obstáculo é mais devagar, sem parar", 0.4 < v["frente_perto_esq"] < v["frente_livre_esq"])
confere("no escuro anda um pouco mais devagar", v["frente_escuro_esq"] < v["frente_livre_esq"])
confere("curva à esquerda: roda esquerda mais devagar, as duas para frente", 0 < v["curva_esq_esq"] < v["curva_esq_dir"])
confere("curva à direita: roda direita mais devagar, as duas para frente", 0 < v["curva_dir_dir"] < v["curva_dir_esq"])
confere("girar à esquerda: esquerda para trás, direita para frente", v["girar_esq_esq"] < 0 < v["girar_esq_dir"])
confere("girar à direita: esquerda para frente, direita para trás", v["girar_dir_dir"] < 0 < v["girar_dir_esq"])
confere("a ação dura vários ciclos sem mudar e só conta o passo no fim", v["ciclos_com_a_mesma_acao"] == 3 and v["passos_no_meio_da_acao"] == 0 and v["passos_ao_fechar_a_acao"] == 1)
confere("freio de segurança interrompe a ação, sem fuga na primeira vez", v["freio_perto"] == 1 and v["escapar_no_primeiro"] == 0)
confere("5 freios seguidos viram uma fuga", v["fugas_em_5_freios"] >= 1)
confere("a exploração cai com o treino", v["epsilon_apos_10000"] < v["epsilon_inicio"] and v["epsilon_apos_10000"] >= 0.05)
confere("o histórico fecha um bloco a cada 100 passos", v["blocos_fechados"] == 1 and v["bloco_fechou_flag"] == 1)
confere("freio adaptativo: sobrou espaço = freia 1 cm mais perto", v["freio_inicial"] == 20 and v["freio_apos_sobrar_espaco"] == 19)
confere("freio adaptativo: sem permissão (modo IA) ele não diminui", v["freio_sem_permissao"] == 19)
confere("freio adaptativo: parou perto demais = +2, perdeu o eco = +3", v["freio_apos_parar_perto"] == 21 and v["freio_apos_perder_eco"] == 24)
confere("freio adaptativo: respeita o mínimo do config.h e o máximo de 30", v["freio_minimo"] == v["margem_min_config"] and v["freio_maximo"] == 30)
confere("freio fixo (adaptar_margem desligado) não muda", v["freio_fixo"] == 20)
confere("ajuste do painel: valor dentro da faixa vale e fora da faixa é recusado sem mudar nada", v["cfg_ok"] == 1 and v["cfg_eps_tau"] == 2000 and v["cfg_fora_da_faixa"] == 0 and v["cfg_fora_da_faixa_mudou"] == 2000)
confere("ajuste do painel: nome desconhecido é recusado com o motivo", v["cfg_nome_ruim"] == 0 and v["cfg_erro_nome"] == 1)
confere("ajuste do painel: a exploração inicial e as metas mudam", abs(v["cfg_eps_inicial"] - 0.1) < 1e-4 and v["cfg_meta_passos"] == 5000 and v["cfg_meta_minutos"] == 30)
confere("ajuste do painel: a ação dura o número de ciclos configurado", v["cfg_passos_em_4_ciclos"] == 0 and v["cfg_passos_no_5o_ciclo"] == 1)
confere("ajuste do painel: o mínimo do freio configurado é respeitado", v["cfg_margem_min_respeitada"] == 18)
confere("a exploração vai de eps_inicial a eps_minimo", abs(v["epsilon_em_zero"] - 0.30) < 1e-4 and abs(v["epsilon_em_infinito"] - 0.05) < 1e-4)
confere("o que vai para a memória flash cabe com folga (limite de 4000 bytes por valor)", v["bytes_memoria"] < 4000, f"({v['bytes_memoria']:.0f} bytes)")
confere("palpite inicial: longe segue, perto gira, preso gira", v["palpite_longe"] == 0 and v["palpite_perto"] in (3, 4) and v["palpite_travado"] in (3, 4))
assert erros == 0, f"{erros} verificação(ões) do aprendizado falharam"
print("o Q-learning do carrinho está certo")
