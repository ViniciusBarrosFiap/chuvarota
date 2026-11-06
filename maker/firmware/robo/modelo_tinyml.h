// gerado por maker/tinyml/treinar.py, não edite à mão
#pragma once
#include <math.h>

#define N_ENTRADAS 2
#define N_ESCONDIDOS 8
#define N_CLASSES 4

static const float PESO_1[16] = {0.000000f, 3.017038f, 0.803695f, 2.530209f, -4.528324f, 0.000000f, -0.000000f, 0.364857f, -0.000000f, 3.487066f, -7.422310f, 1.366491f, 2.181750f, -0.000000f, 0.000000f, -0.298836f};
static const float VIES_1[8] = {-0.303267f, 0.215620f, 1.438938f, -0.374837f, 2.073243f, -0.558494f, -0.322008f, -0.373924f};
static const float PESO_2[32] = {-0.000000f, 0.000000f, -0.000000f, -0.000000f, 2.115512f, -1.030988f, -0.558572f, -3.336272f, -6.276996f, -6.012752f, 5.779879f, 4.887151f, 1.368478f, -1.760821f, 0.228504f, -4.138613f, -3.675622f, 3.047185f, -4.819357f, 2.089956f, 0.000000f, 0.000000f, -0.000000f, 0.000000f, -0.000000f, -0.000000f, -0.000000f, 0.000000f, 0.551070f, 0.392999f, 0.243910f, 0.444398f};
static const float VIES_2[4] = {-0.304969f, -0.195438f, -1.121700f, -0.231580f};

// luz: 0 (escuro) a 1 (claro); dist: distância em cm dividida por 200
inline int classificar(float luz, float dist) {
  float x[N_ENTRADAS] = {luz, dist};
  float h[N_ESCONDIDOS];
  for (int j = 0; j < N_ESCONDIDOS; j++) {
    float s = VIES_1[j];
    for (int i = 0; i < N_ENTRADAS; i++) s += x[i] * PESO_1[i * N_ESCONDIDOS + j];
    h[j] = s > 0 ? s : 0;
  }
  int melhor = 0;
  float maior = -1e30f;
  for (int k = 0; k < N_CLASSES; k++) {
    float s = VIES_2[k];
    for (int j = 0; j < N_ESCONDIDOS; j++) s += h[j] * PESO_2[j * N_CLASSES + k];
    if (s > maior) { maior = s; melhor = k; }
  }
  return melhor;
}
