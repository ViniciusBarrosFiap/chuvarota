"""Compila logica.h no computador e confere o movimento suave: velocidade pela distância, tradução para PWM, rampa nos motores e o
navegador do modo autônomo (segue reto, curva antes da parede, gira no lugar só a menos de 25 cm, troca de lado se a curva piora)."""
import subprocess
import tempfile
from pathlib import Path

FW = Path(__file__).parent.parent / "firmware" / "robo"

main = r"""#include <stdio.h>
#include "logica.h"
#define SAIDA(nome, valor) printf("%s=%g\n", nome, (double)(valor))
int main() {
  // perfil de velocidade (margem 20, cruzeiro 90)
  SAIDA("perfil_livre", perfil_velocidade(200, 20));
  SAIDA("perfil_meio", perfil_velocidade(55, 20));
  SAIDA("perfil_no_freio", perfil_velocidade(20, 20));
  SAIDA("perfil_antes_do_freio", perfil_velocidade(5, 20));
  // PWM
  SAIDA("pwm_zero", pwm_de(0, 110, 180)); SAIDA("pwm_deadband", pwm_de(0.04f, 110, 180));
  SAIDA("pwm_cheio", pwm_de(1, 110, 180)); SAIDA("pwm_meio", pwm_de(0.5f, 110, 180));
  SAIDA("pwm_re", pwm_de(-1, 110, 180)); SAIDA("pwm_minimo", pwm_de(0.06f, 110, 180));
  // mistura
  Rodas m = misturar(0.5f, 0.3f), mc = misturar(1, 1);
  SAIDA("mistura_esq", m.esq); SAIDA("mistura_dir", m.dir); SAIDA("mistura_clamp", mc.esq);
  // rampa: de parado a velocidade cheia em 5 ciclos; inversão passa por zero
  RampaMotor r;
  float sobe[6];
  for (int i = 0; i < 6; i++) sobe[i] = r.seguir(Rodas{1, 1}, 0.2f).esq;
  SAIDA("rampa_1", sobe[0]); SAIDA("rampa_3", sobe[2]); SAIDA("rampa_5", sobe[4]); SAIDA("rampa_6", sobe[5]);
  float max_degrau = 0, antes = r.esq;
  for (int i = 0; i < 12; i++) { float agora = r.seguir(Rodas{-1, -1}, 0.2f).esq; max_degrau = fmaxf(max_degrau, fabsf(agora - antes)); antes = agora; }
  SAIDA("rampa_maior_degrau", max_degrau);
  SAIDA("rampa_chegou_na_re", r.esq);
  r.parar();
  SAIDA("rampa_parar", r.esq);
  // navegador
  Navegador n;
  Navegador::Saida s = n.passo(150, 25, 75, 45);
  SAIDA("nav_longe_v", s.v); SAIDA("nav_longe_w", s.w);
  s = n.passo(50, 25, 75, 45);
  SAIDA("nav_meio_v", s.v); SAIDA("nav_meio_w", s.w);   // lado = 1 (direita): w positivo
  s = n.passo(27, 25, 75, 45);
  SAIDA("nav_perto_v", s.v); SAIDA("nav_perto_w", s.w);
  s = n.passo(24, 25, 75, 45);                          // a menos de 25: gira no lugar
  SAIDA("nav_gira_v", s.v); SAIDA("nav_gira_w", s.w);
  // continua girando até 2 ciclos com 45 cm ou mais
  s = n.passo(40, 25, 75, 45); SAIDA("nav_ainda_gira", s.v == 0 && s.w != 0);
  s = n.passo(46, 25, 75, 45); SAIDA("nav_um_claro_ainda_gira", s.v == 0 && s.w != 0);
  s = n.passo(47, 25, 75, 45); SAIDA("nav_dois_claros_volta", s.v > 0);
  // preso: 60 ciclos a 24 cm
  Navegador p;
  int lado0 = p.lado, tick_troca = 0, tick_preso = 0;
  for (int i = 1; i <= 60; i++) {
    Navegador::Saida q = p.passo(24, 25, 75, 45);
    if (!tick_troca && p.lado != lado0) tick_troca = i;
    if (!tick_preso && q.preso) tick_preso = i;
  }
  SAIDA("nav_troca_de_lado_no_ciclo", tick_troca); SAIDA("nav_preso_no_ciclo", tick_preso);
  // realimentação: curvando e a distância continua caindo 3 cm por ciclo = lado errado, troca
  Navegador f;
  int lado1 = f.lado;
  for (int i = 0; i < 7; i++) f.passo(70 - 3 * i, 25, 75, 45);
  SAIDA("nav_lado_errado_troca", f.lado != lado1);
  // e se a distância melhora, mantém o lado
  Navegador g;
  int lado2 = g.lado;
  for (int i = 0; i < 7; i++) g.passo(40 + 4 * i, 25, 75, 45);
  SAIDA("nav_lado_certo_mantem", g.lado == lado2);
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


confere("velocidade: cheia em campo livre, diminui aos poucos e nunca cai abaixo de 45%", v["perfil_livre"] == 1 and abs(v["perfil_meio"] - 0.5) < 0.01 and abs(v["perfil_no_freio"] - 0.45) < 1e-6 and abs(v["perfil_antes_do_freio"] - 0.45) < 1e-6)
confere("PWM: parado abaixo de 5%, começa em 110 (onde o motor vence o atrito) e vai a 180", v["pwm_zero"] == 0 and v["pwm_deadband"] == 0 and v["pwm_minimo"] >= 110 and v["pwm_cheio"] == 180 and v["pwm_meio"] == 145 and v["pwm_re"] == -180)
confere("mistura de andar e virar, limitada a 1", abs(v["mistura_esq"] - 0.8) < 1e-6 and abs(v["mistura_dir"] - 0.2) < 1e-6 and v["mistura_clamp"] == 1)
confere("rampa: de parado a velocidade cheia em 5 ciclos, sem degrau maior que 0,2", abs(v["rampa_1"] - 0.2) < 1e-6 and abs(v["rampa_3"] - 0.6) < 1e-6 and abs(v["rampa_5"] - 1.0) < 1e-6 and v["rampa_6"] == 1 and v["rampa_maior_degrau"] <= 0.2 + 1e-6 and v["rampa_chegou_na_re"] == -1)
confere("rampa: parar() zera na hora", v["rampa_parar"] == 0)
confere("navegador: longe segue reto na velocidade cheia", v["nav_longe_v"] == 1 and v["nav_longe_w"] == 0)
confere("navegador: no meio do caminho diminui e já curva", 0.7 < v["nav_meio_v"] < 0.85 and 0.2 < v["nav_meio_w"] < 0.5, f"(v {v['nav_meio_v']:.2f}, w {v['nav_meio_w']:.2f})")
confere("navegador: perto da parede curva mais forte e mais devagar", v["nav_perto_w"] > v["nav_meio_w"] and v["nav_perto_v"] < v["nav_meio_v"] and v["nav_perto_v"] >= 0.55)
confere("navegador: a menos de 25 cm gira no lugar (sem ré)", v["nav_gira_v"] == 0 and abs(abs(v["nav_gira_w"]) - 0.6) < 1e-5)
confere("navegador: só volta a andar com 2 ciclos seguidos de espaço livre", v["nav_ainda_gira"] == 1 and v["nav_um_claro_ainda_gira"] == 1 and v["nav_dois_claros_volta"] == 1)
confere("navegador: preso a 24 cm troca de lado aos 2,5 s e pede fuga aos 5 s", v["nav_troca_de_lado_no_ciclo"] == 25 and v["nav_preso_no_ciclo"] == 50)
confere("navegador: se a curva piora a distância, troca de lado; se melhora, mantém", v["nav_lado_errado_troca"] == 1 and v["nav_lado_certo_mantem"] == 1)
assert erros == 0, f"{erros} verificação(ões) do movimento falharam"
print("o movimento suave está certo")
