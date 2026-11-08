// Leitura do HC-SR04 e calibração, sem dependência do Arduino (testado no computador em maker/tinyml/testar_sensor.py).
#pragma once
#include <math.h>

constexpr float SEM_ECO_CM = 200;  // valor que as leituras usam quando o sensor não ouviu eco

// centímetros por microssegundo de eco (ida e volta), pela temperatura: o som viaja a 331,3 + 0,606 x T m/s
inline float cm_por_us(float temperatura_c) { return (331.3f + 0.606f * temperatura_c) / 20000.0f; }

// Junta várias leituras brutas (em cm; SEM_ECO_CM = sem eco) em uma distância confiável:
//  - se menos da metade das leituras teve eco, devolve SEM_ECO_CM;
//  - descarta as que se afastam da mediana (ruído e leituras falsas) e devolve a média das que concordam.
// Assim o ruído cai com a raiz do número de leituras e uma leitura falsa não passa. n no máximo 16.
inline float combinar_leituras(const float* v, int n) {
  float ok[16];
  int k = 0;
  for (int i = 0; i < n && i < 16; i++)
    if (v[i] < SEM_ECO_CM - 0.5f) ok[k++] = v[i];
  if (k * 2 <= n) return SEM_ECO_CM;
  for (int i = 1; i < k; i++) {  // ordena
    float x = ok[i];
    int j = i - 1;
    while (j >= 0 && ok[j] > x) {
      ok[j + 1] = ok[j];
      j--;
    }
    ok[j + 1] = x;
  }
  float mediana = (k % 2) ? ok[k / 2] : (ok[k / 2 - 1] + ok[k / 2]) / 2;
  float tolerancia = fmaxf(3.0f, 0.05f * mediana);
  float soma = 0;
  int usadas = 0;
  for (int i = 0; i < k; i++)
    if (fabsf(ok[i] - mediana) <= tolerancia) {
      soma += ok[i];
      usadas++;
    }
  return usadas ? soma / usadas : mediana;
}

// as leituras concordam entre si (não precisa medir mais)?
inline bool leituras_concordam(const float* v, int n) {
  int k = 0;
  float menor = 1e9f, maior = -1e9f, soma = 0;
  for (int i = 0; i < n; i++)
    if (v[i] < SEM_ECO_CM - 0.5f) {
      k++;
      menor = fminf(menor, v[i]);
      maior = fmaxf(maior, v[i]);
      soma += v[i];
    }
  if (k == 0) return true;  // nenhuma teve eco: concordam em "nada à frente"
  if (k < n) return false;  // misturou com e sem eco
  return (maior - menor) <= fmaxf(2.5f, 0.04f * soma / k);
}

// Mede de 'minimo' a 'maximo' vezes: para assim que as leituras concordam (rápido quando está tudo calmo, mais leituras quando duvida).
// leitura: função sem argumentos que devolve uma leitura bruta em cm.
template <class Leitura>
inline float medir_adaptativo(Leitura leitura, int minimo = 3, int maximo = 5) {
  float v[16];
  int n = 0;
  while (n < maximo && n < 16) {
    v[n++] = leitura();
    if (n >= minimo && leituras_concordam(v, n)) break;
  }
  return combinar_leituras(v, n);
}

// Calibração do sensor: acha escala e offset tais que real ~= escala x medido + offset (mínimos quadrados).
inline bool ajustar_reta(const float* medido, const float* real, int n, float* escala, float* offset) {
  if (n < 2) return false;
  float sx = 0, sy = 0, sxx = 0, sxy = 0;
  for (int i = 0; i < n; i++) {
    sx += medido[i];
    sy += real[i];
    sxx += medido[i] * medido[i];
    sxy += medido[i] * real[i];
  }
  float den = n * sxx - sx * sx;
  if (fabsf(den) < 1e-6f) return false;
  *escala = (n * sxy - sx * sy) / den;
  *offset = (sy - *escala * sx) / n;
  return true;
}

// Quanto o carrinho girou, medido por uma parede lisa à frente: d0 = distância antes, d1 = depois, r_eixo = distância do sensor ao eixo
// de giro. Com o sensor a r do eixo, d1 + r = (d0 + r) / cos(ângulo). Vale para ângulos de uns 10 a 60 graus.
inline float angulo_giro_graus(float d0, float d1, float r_eixo) {
  float c = (d0 + r_eixo) / (d1 + r_eixo);
  if (c > 1) c = 1;
  if (c < -1) c = -1;
  return acosf(c) * 180.0f / 3.14159265f;
}
