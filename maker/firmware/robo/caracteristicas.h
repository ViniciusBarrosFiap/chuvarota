// as mesmas contas de maker/tinyml/caracteristicas.py (o testar_c.py confere que dão o mesmo resultado)
#pragma once
#include <math.h>

#define JANELA 8
#define PASSO_S 0.1f  // uma leitura a cada 100 ms

static inline float mediana(const float* v, int n) {
  float t[JANELA];
  for (int i = 0; i < n; i++) t[i] = v[i];
  for (int i = 1; i < n; i++) {  // ordenação por inserção: n é pequeno
    float x = t[i];
    int j = i - 1;
    while (j >= 0 && t[j] > x) {
      t[j + 1] = t[j];
      j--;
    }
    t[j + 1] = x;
  }
  return (n % 2) ? t[n / 2] : (t[n / 2 - 1] + t[n / 2]) / 2;
}

// luz e dist: as últimas JANELA leituras, da mais antiga para a mais nova; x: 5 saídas
inline void caracteristicas(const float* luz, const float* dist, float* x) {
  float soma = 0, maior = luz[0], menor = luz[0];
  for (int i = 0; i < JANELA; i++) {
    soma += luz[i];
    if (luz[i] > maior) maior = luz[i];
    if (luz[i] < menor) menor = luz[i];
  }
  float media = soma / JANELA, var = 0;
  for (int i = 0; i < JANELA; i++) var += (luz[i] - media) * (luz[i] - media);
  int metade = JANELA / 2;
  float tendencia = (mediana(dist + metade, metade) - mediana(dist, metade)) / (metade * PASSO_S);  // cm/s, negativo = aproximando
  x[0] = media;
  x[1] = 3 * sqrtf(var / JANELA);
  x[2] = maior - menor;
  x[3] = mediana(dist, JANELA) / 200;
  x[4] = tendencia / 100;
}
