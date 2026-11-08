"""Compila logica.h no computador e confere: a combinação das leituras (descarte de leituras falsas, "sem eco"), o quanto ela reduz o
ruído contra a mediana de 3 antiga, a calibração por reta e o cálculo do ângulo de giro. O ruído é simulado (a placa real é medida
pelo comando p no Monitor Serial)."""
import subprocess
import tempfile
from pathlib import Path

FW = Path(__file__).parent.parent / "firmware" / "robo"

main = r"""#include <stdio.h>
#include <algorithm>
#include <random>
#include "logica.h"
#define SAIDA(nome, valor) printf("%s=%g\n", nome, (double)(valor))
static std::mt19937 gen(7);
static float normal(float d) { return std::normal_distribution<float>(0, d)(gen); }
static float uni() { return std::uniform_real_distribution<float>(0, 1)(gen); }
// uma leitura simulada de um alvo a `real` cm: ruído, 3% sem eco, 1% de leitura falsa
static float leitura(float real) {
  float u = uni();
  if (u < 0.03f) return 200;
  if (u < 0.04f) return 5 + uni() * 190;
  return real + normal(1.0f + 0.005f * real);
}
static float mediana3(float a, float b, float c) { return std::max(std::min(a, b), std::min(std::max(a, b), c)); }
int main() {
  // combinar leituras
  float v1[] = {30, 31, 200};      SAIDA("duas_de_tres", combinar_leituras(v1, 3));
  float v2[] = {200, 200, 31};     SAIDA("uma_de_tres", combinar_leituras(v2, 3));
  float v3[] = {30, 31, 29, 52, 30}; SAIDA("descarta_falsa", combinar_leituras(v3, 5));
  float v4[] = {200, 200, 200};    SAIDA("todas_sem_eco", combinar_leituras(v4, 3));
  float v5[] = {30, 31, 200, 200, 32}; SAIDA("tres_de_cinco", combinar_leituras(v5, 5));
  float c1[] = {50, 50.5f, 49.8f};  SAIDA("concordam_3_perto", leituras_concordam(c1, 3));
  float c2[] = {50, 58, 49.8f};     SAIDA("concordam_dispersas", leituras_concordam(c2, 3));
  float c3[] = {200, 200, 200};     SAIDA("concordam_sem_eco", leituras_concordam(c3, 3));
  float c4[] = {50, 200, 50};       SAIDA("concordam_misturadas", leituras_concordam(c4, 3));
  // ruído: 20000 medidas de um alvo a 50 cm e a 120 cm, método antigo (mediana de 3) contra o novo (3 a 5 leituras com descarte)
  for (float real : {50.0f, 120.0f}) {
    double soma_a = 0, soma2_a = 0, soma_n = 0, soma2_n = 0;
    int ok_a = 0, ok_n = 0, leituras_novo = 0, falsas_a = 0, falsas_n = 0;
    for (int i = 0; i < 20000; i++) {
      float a = mediana3(leitura(real), leitura(real), leitura(real));
      int usadas = 0;
      float n = medir_adaptativo([&] { usadas++; return leitura(real); }, 3, 5);
      leituras_novo += usadas;
      if (a < 199.5f) { if (fabsf(a - real) > 6) falsas_a++; else { soma_a += a; soma2_a += (double)a * a; ok_a++; } }
      if (n < 199.5f) { if (fabsf(n - real) > 6) falsas_n++; else { soma_n += n; soma2_n += (double)n * n; ok_n++; } }
    }
    double ma = soma_a / ok_a, mn = soma_n / ok_n;
    char nome[40];
    snprintf(nome, sizeof nome, "desvio_antigo_%.0f", real); SAIDA(nome, sqrt(soma2_a / ok_a - ma * ma));
    snprintf(nome, sizeof nome, "desvio_novo_%.0f", real);   SAIDA(nome, sqrt(soma2_n / ok_n - mn * mn));
    snprintf(nome, sizeof nome, "falsas_antigo_%.0f", real); SAIDA(nome, falsas_a);
    snprintf(nome, sizeof nome, "falsas_novo_%.0f", real);   SAIDA(nome, falsas_n);
    snprintf(nome, sizeof nome, "leituras_novo_%.0f", real); SAIDA(nome, leituras_novo / 20000.0);
  }
  // calibração: um sensor que lê 3% a mais e 1,5 cm de sobra
  float real[3] = {20, 50, 100}, medido[3], escala, offset;
  for (int i = 0; i < 3; i++) medido[i] = real[i] * 1.03f + 1.5f;
  ajustar_reta(medido, real, 3, &escala, &offset);
  SAIDA("escala", escala); SAIDA("offset", offset);
  // ângulo de giro: parede reta a 50 cm, sensor a 8 cm do eixo, giro de 30 graus
  float d0 = 50, r = 8, ang = 30, d1 = (d0 + r) / cosf(ang * 3.14159265f / 180) - r;
  SAIDA("angulo_giro", angulo_giro_graus(d0, d1, r));
  SAIDA("cm_por_us_20c", 1.0 / cm_por_us(20));
  SAIDA("cm_por_us_35c", 1.0 / cm_por_us(35));
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


confere("2 de 3 leituras com eco: média das duas", abs(v["duas_de_tres"] - 30.5) < 0.01)
confere("1 de 3 com eco: sem eco", v["uma_de_tres"] == 200)
confere("uma leitura falsa (52 entre 30) é descartada", abs(v["descarta_falsa"] - 30) < 0.01)
confere("nenhuma com eco: sem eco", v["todas_sem_eco"] == 200)
confere("3 de 5 com eco já vale", abs(v["tres_de_cinco"] - 31) < 0.01)
confere("leituras que concordam param a medição; dispersas ou misturadas pedem mais", v["concordam_3_perto"] == 1 and v["concordam_dispersas"] == 0 and v["concordam_misturadas"] == 0 and v["concordam_sem_eco"] == 1)
for real in (50, 120):
    confere(f"alvo a {real} cm: menos oscilação que a mediana de 3", v[f"desvio_novo_{real}"] < 0.85 * v[f"desvio_antigo_{real}"],
            f"(desvio {v[f'desvio_antigo_{real}']:.2f} -> {v[f'desvio_novo_{real}']:.2f} cm, com {v[f'leituras_novo_{real}']:.2f} leituras por medida em média)")
    confere(f"alvo a {real} cm: menos leituras falsas passando", v[f"falsas_novo_{real}"] <= v[f"falsas_antigo_{real}"],
            f"({v[f'falsas_antigo_{real}']:.0f} -> {v[f'falsas_novo_{real}']:.0f} em 20000)")
    confere(f"alvo a {real} cm: no máximo 5 leituras por medida", v[f"leituras_novo_{real}"] <= 5)
confere("calibração por reta recupera o erro de 3% e 1,5 cm", abs(v["escala"] - 1 / 1.03) < 0.002 and abs(v["offset"] - (-1.5 / 1.03)) < 0.1, f"(escala {v['escala']:.3f}, offset {v['offset']:.1f})")
confere("ângulo de giro medido pela parede", abs(v["angulo_giro"] - 30) < 0.1, f"({v['angulo_giro']:.1f} graus)")
confere("a velocidade do som muda com a temperatura (58,2 cm/ms a 20 °C)", 58.0 < v["cm_por_us_20c"] < 58.4 and v["cm_por_us_35c"] < v["cm_por_us_20c"])
assert erros == 0, f"{erros} verificação(ões) do sensor falharam"
print("o sensor está certo")
