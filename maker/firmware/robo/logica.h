// Lógica do carrinho sem dependência do Arduino: roda no ESP32 e é testada no computador (python maker/tinyml/testar_tudo.py).
// Três partes: 1) setas e joystick do Dabble -> rodas, 2) filtro da distância e detector de travamento, 3) leitura do sensor e calibração.
#pragma once
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

// ================================================================================================================================
// 1) Dabble -> rodas
// ================================================================================================================================
// Converte o comando do Dabble (setas ou joystick) na velocidade das duas rodas.

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

// ================================================================================================================================
// 2) Segurança: filtro da distância e detector de travamento
// ================================================================================================================================
// O HC-SR04 devolve "sem eco" (200) quando não há nada à frente, mas também quando o obstáculo está perto demais (menos de uns
// 2 cm) ou é uma parede em ângulo que desvia o som. Se a leitura anterior era perto e agora ficou sem eco, o mais seguro é achar
// que o obstáculo continua ali, e não que o caminho abriu.
struct FiltroDistancia {
  enum { MAX_SEM_ECO = 20 };  // por no máximo 20 leituras (2 s); depois disso vale o "sem eco"
  float ultima = 200;         // última leitura com eco
  int sem_eco = 0;            // quantas leituras "sem eco" seguidas foram trocadas por "obstáculo colado"

  // d: leitura nova (200 = sem eco). perto_cm: abaixo disso a leitura anterior conta como "perto".
  // colado_cm: valor devolvido quando um "sem eco" é trocado por obstáculo (deve ser menor que a distância de parada).
  float filtrar(float d, float perto_cm, float colado_cm) {
    if (d >= 200 && ultima < perto_cm && sem_eco < MAX_SEM_ECO) {
      sem_eco++;
      return colado_cm;
    }
    sem_eco = 0;
    ultima = d;
    return d;
  }

  // depois de uma manobra as leituras de antes não valem mais
  void esquecer() {
    ultima = 200;
    sem_eco = 0;
  }
};

// O sensor só enxerga reto, mas o corpo do carrinho é largo: ao passar de raspão por uma parede ele encosta, as rodas patinam e a
// distância lida quase não muda enquanto o robô "anda". Andando livre, a distância muda uns 15 cm a cada 3 ciclos. Se mandou andar
// por 3 ciclos seguidos e a distância mudou menos de 3 cm, ele está preso. Só vale com eco (abaixo de 190 cm).
struct DetectorTravado {
  float hist[4] = {200, 200, 200, 200};  // as últimas 4 leituras, a mais antiga primeiro
  int andando = 0;                       // ciclos seguidos andando para frente
  void esquecer() {
    for (int i = 0; i < 4; i++) hist[i] = 200;
    andando = 0;
  }
  // andando: mandou andar para frente neste ciclo. Devolve true quando está preso (e recomeça a contagem).
  bool atualizar(bool andando_agora, float d, float limite_cm = 3.0f) {
    for (int i = 0; i < 3; i++) hist[i] = hist[i + 1];
    hist[3] = d;
    andando = andando_agora ? andando + 1 : 0;
    if (andando >= 4 && d < 190 && hist[0] < 190) {
      float mudou = hist[3] - hist[0];
      if (mudou > -limite_cm && mudou < limite_cm) {
        esquecer();
        return true;
      }
    }
    return false;
  }
};

// ================================================================================================================================
// 3) Sensor de distância: leituras, calibração e giro
// ================================================================================================================================
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

// ================================================================================================================================
// 4) Movimento suave: velocidade pela distância, curvas, rampa nos motores e o navegador do modo autônomo
// ================================================================================================================================
// Por que existe: antes o carrinho trocava de ação a cada ciclo, os motores iam de 0 a 180 em um degrau e as manobras eram "parar, ré,
// girar, parar". Agora a velocidade muda aos poucos, as curvas começam antes da parede e o motor sobe e desce em rampa.

// aleatório simples (xorshift), para não depender do Arduino
inline uint32_t proximo_aleatorio(uint32_t& s) {
  s ^= s << 13;
  s ^= s >> 17;
  s ^= s << 5;
  return s;
}
inline float aleatorio01(uint32_t& s) { return (proximo_aleatorio(s) >> 8) * (1.0f / 16777216.0f); }

struct Rodas {
  float esq, dir;  // -1 a 1 (positivo = para frente)
};

// andar (v) e virar (w, positivo = direita) misturados nas duas rodas
inline Rodas misturar(float v, float w) {
  Rodas r;
  r.esq = fmaxf(-1.0f, fminf(1.0f, v + w));
  r.dir = fmaxf(-1.0f, fminf(1.0f, v - w));
  return r;
}

// velocidade pela distância até o obstáculo: 1 (livre, a partir de 'cruzeiro' cm) até 0,45 (perto do freio), sem degrau
inline float perfil_velocidade(float d, float margem, float cruzeiro = 90) {
  float t = (d - margem) / (cruzeiro - margem);
  return fmaxf(0.45f, fminf(1.0f, t));
}

// de -1..1 para PWM: abaixo de 5% fica parado; senão vai de pwm_min (onde o motor vence o atrito) até pwm_max
inline int pwm_de(float x, int pwm_min, int pwm_max) {
  float a = fabsf(x);
  if (a < 0.05f) return 0;
  int p = pwm_min + (int)((pwm_max - pwm_min) * fminf(a, 1.0f));
  return x < 0 ? -p : p;
}

// Rampa: limita o quanto cada roda pode mudar por ciclo (aceleração suave). Para frear de verdade use parar().
struct RampaMotor {
  float esq = 0, dir = 0;
  Rodas seguir(Rodas alvo, float passo = 0.2f) {
    esq += fmaxf(-passo, fminf(passo, alvo.esq - esq));
    dir += fmaxf(-passo, fminf(passo, alvo.dir - dir));
    Rodas r = {esq, dir};
    return r;
  }
  void parar() { esq = dir = 0; }
};

// Navegador do modo autônomo. Roda a cada ciclo com a distância à frente e devolve o quanto andar (v, 0 a 1) e virar (w, -1 a 1).
//  - longe (mais que curva_cm): segue reto na velocidade cheia;
//  - entre curva_cm e parar_cm: vai diminuindo a velocidade e CURVANDO para o lado preferido, cada vez mais forte;
//  - a menos de parar_cm: gira no lugar até haver saida_cm livres (2 ciclos seguidos), sem ré.
// O lado da curva é escolhido por realimentação: se depois de uns 5 ciclos curvando a distância continua caindo (mais de 8 cm), o lado
// estava errado e ele troca. Depois de cada desvio ele às vezes troca o lado, para não andar sempre em círculo.
struct Navegador {
  struct Saida {
    float v, w;
    bool preso;  // girou por 5 s sem abrir espaço: fazer uma fuga
  };
  int lado = 1;  // 1 = direita, -1 = esquerda
  uint32_t rng = 1234567u;

  void esquecer() {
    girando = false;
    ticks_giro = claros = ticks_curva = 0;
  }

  Saida passo(float d, float parar_cm, float curva_cm, float saida_cm) {
    Saida s = {0, 0, false};
    if (!girando && d < parar_cm) {
      girando = true;
      ticks_giro = claros = 0;
    }
    if (girando) {
      ticks_giro++;
      claros = (d >= saida_cm) ? claros + 1 : 0;
      if (claros >= 2) {  // abriu espaço: volta a andar
        girando = false;
        ticks_curva = 0;
        if (aleatorio01(rng) < 0.5f) lado = -lado;
      } else {
        if (ticks_giro == 25) lado = -lado;  // 2,5 s sem abrir: tenta o outro lado
        if (ticks_giro >= 50) {
          s.preso = true;
          girando = false;
          ticks_giro = 0;
        }
        s.w = 0.6f * lado;
        return s;
      }
    }
    float t = fmaxf(0.0f, fminf(1.0f, (curva_cm - d) / (curva_cm - parar_cm)));
    s.v = 1.0f - 0.45f * t;
    s.w = lado * 0.7f * t;
    if (t > 0.15f) {  // curvando: confere se a distância está melhorando
      if (ticks_curva == 0) d_curva = d;
      if (++ticks_curva >= 5) {
        if (d < d_curva - 8) lado = -lado;
        ticks_curva = 0;
      }
    } else {
      ticks_curva = 0;
    }
    return s;
  }

 private:
  bool girando = false;
  int ticks_giro = 0, claros = 0, ticks_curva = 0;
  float d_curva = 200;
};

// ================================================================================================================================
// 5) Protocolo do painel: uma linha vinda da porta serial
// ================================================================================================================================
// Uma letra é um comando de sempre ("a", "q", "z"...). O painel manda linhas: "cfg nome valor", "cfg?", "modo treino" e "painel 1".
struct LinhaSerial {
  enum Tipo { VAZIA, LETRA, CFG, CFG_LISTA, MODO, PAINEL, DESCONHECIDA } tipo = VAZIA;
  char letra = 0;
  char nome[32] = "";
  float valor = 0;
};

inline LinhaSerial interpretar_linha(const char* l) {
  LinhaSerial r;
  char b[64];
  while (*l == ' ' || *l == '\t') l++;
  strncpy(b, l, sizeof(b) - 1);
  b[sizeof(b) - 1] = 0;
  int n = (int)strlen(b);
  while (n > 0 && (b[n - 1] == ' ' || b[n - 1] == '\t' || b[n - 1] == '\r' || b[n - 1] == '\n')) b[--n] = 0;
  if (n == 0) return r;
  r.tipo = LinhaSerial::DESCONHECIDA;
  if (n == 1) {
    r.tipo = LinhaSerial::LETRA;
    r.letra = b[0];
  } else if (!strcmp(b, "cfg?")) {
    r.tipo = LinhaSerial::CFG_LISTA;
  } else if (sscanf(b, "cfg %31s %f", r.nome, &r.valor) == 2) {
    r.tipo = LinhaSerial::CFG;
  } else if (sscanf(b, "modo %31s", r.nome) == 1) {
    r.tipo = LinhaSerial::MODO;
  } else if (sscanf(b, "painel %f", &r.valor) == 1) {
    r.tipo = LinhaSerial::PAINEL;
  }
  return r;
}
