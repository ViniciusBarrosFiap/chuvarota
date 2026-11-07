// Converte o comando do Dabble na velocidade das duas rodas. Sem nenhuma dependência do Arduino,
// para poder ser testado no computador (maker/tinyml/testar_direcao.py).
#pragma once
#include <math.h>

struct Comando {
  float frente;  // -1 (para trás) a 1 (para frente)
  float giro;    // -1 (vira à esquerda) a 1 (vira à direita)
};

// cima, baixo, esquerda e direita: setas do Dabble (modo digital).
// angulo (graus) e raio (0 a 7): joystick do Dabble (modo joystick). No modo digital o raio é sempre 0.
// Não use getXaxisData()/getYaxisData() do Dabble: eles não olham o modo e, com as setas, leem os bits dos botões como se
// fossem um joystick (para frente saía levemente para a direita, para trás saía torto).
inline Comando ler_comando(bool cima, bool baixo, bool esquerda, bool direita, int angulo, int raio, bool inverte_y) {
  const float PI_ = 3.14159265f;
  float jx = raio * cosf(angulo * PI_ / 180.0f);
  float jy = raio * sinf(angulo * PI_ / 180.0f) * (inverte_y ? -1 : 1);
  Comando c;
  c.giro = fabsf(jx) < 1 ? 0 : jx / 7.0f;
  c.frente = fabsf(jy) < 1 ? 0 : jy / 7.0f;
  if (cima) c.frente = 1;
  if (baixo) c.frente = -1;
  if (esquerda) c.giro = -1;
  if (direita) c.giro = 1;
  return c;
}

// roda esquerda = frente + giro; roda direita = frente - giro. Resultado de -255 a 255 (positivo = para frente).
inline void misturar_rodas(float frente, float giro, int velocidade, int* esq, int* dir) {
  float e = (frente + giro) * velocidade, d = (frente - giro) * velocidade;
  *esq = (int)(e > 255 ? 255 : (e < -255 ? -255 : e));
  *dir = (int)(d > 255 ? 255 : (d < -255 ? -255 : d));
}
