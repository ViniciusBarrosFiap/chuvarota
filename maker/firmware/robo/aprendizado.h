// Aprendizado por reforço (Q-learning) do carrinho. Sem dependência do Arduino: o mesmo código roda no ESP32 e na simulação do
// computador (maker/tinyml/simular_treino.py), que é onde ele foi testado.
//
// A cada ciclo (~0,1 s) o robô olha a distância à frente, escolhe uma ação (frente, frente devagar, girar, ré) e, no ciclo seguinte,
// recebe uma nota pelo que aconteceu (andou livre = ganha; chegou perto demais = perde). Com as notas ele atualiza uma tabela
// estado x ação (72 x 5 números) e passa a escolher cada vez mais as ações que deram nota boa.
//
// Limites: o carrinho tem um sensor só, olhando para frente, e nada que meça quanto andou. Por isso ele aprende reflexos para o
// ambiente em que está (o que fazer ao ver uma parede a tantos cm), e não um mapa do lugar.
#pragma once
#include <math.h>
#include <stdint.h>
#include <string.h>

#include "config.h"
#include "seguranca.h"

enum Acao { FRENTE = 0, FRENTE_LENTO = 1, GIRAR_ESQ = 2, GIRAR_DIR = 3, RE = 4, N_ACOES = 5 };

// estado = faixa da distância (6) x tendência (3) x última ação (4: andou, girou esquerda, girou direita, outra)
enum { N_FAIXAS = 6, N_TENDENCIAS = 3, N_GIROS = 4, N_ESTADOS = N_FAIXAS * N_TENDENCIAS * N_GIROS };
enum { PASSOS_POR_BLOCO = 300, N_BLOCOS = 40, VERSAO_MEMORIA = 1 };

constexpr float RL_ALFA = 0.15f;         // o quanto cada experiência nova pesa
constexpr float RL_GAMA = 0.90f;         // o quanto ele se importa com o que vem depois
constexpr float RL_EPS_INICIAL = 0.30f;  // chance de testar uma ação aleatória no começo
constexpr float RL_EPS_MINIMO = 0.05f;   // e depois de muito treino
constexpr float RL_EPS_TAU = 2500.0f;    // passos para a exploração cair a ~37% do valor inicial

inline const char* nome_acao(int a) {
  static const char* nomes[] = {"frente", "frente devagar", "girar esquerda", "girar direita", "ré"};
  return nomes[a];
}

// ---- como o robô enxerga o mundo -------------------------------------------------------------------------------------------
inline int faixa_dist(float d) {
  if (d < TREINO_DIST_FREIO_CM) return 0;   // freio de segurança
  if (d < TREINO_DIST_PERIGO_CM) return 1;  // perigo
  if (d < 50) return 2;                     // perto
  if (d < 90) return 3;                     // médio
  if (d < 190) return 4;                    // longe, com eco
  return 5;                                 // sem eco (nada à frente ou o sensor não pegou nada)
}
inline int faixa_tend(float delta_cm) { return delta_cm < -3 ? 0 : (delta_cm > 3 ? 2 : 1); }  // 0 aproximando, 1 estável, 2 afastando
inline int codigo_estado(float d, float delta_cm, int giro) { return (faixa_dist(d) * N_TENDENCIAS + faixa_tend(delta_cm)) * N_GIROS + giro; }

// ---- a nota que o robô recebe: d0 = distância antes da ação, d1 = depois -----------------------------------------------------
inline float recompensa(Acao a, float d0, float d1) {
  float r = -0.05f;  // custo de cada passo: não vale ficar parado
  if (d1 < TREINO_DIST_FREIO_CM) r -= 10;        // o freio de segurança teve que agir: erro grave
  else if (d1 < TREINO_DIST_PERIGO_CM) r -= 3;   // quase batida
  if (a == FRENTE || a == FRENTE_LENTO) {
    float bom = (a == FRENTE) ? 1.0f : 0.6f;     // andar rápido rende mais, desde que o caminho esteja livre
    if (d1 >= 50) r += bom;
    else if (d1 >= TREINO_DIST_PERIGO_CM) r += bom * 0.3f;
    if (d0 < 190 && fabsf(d1 - d0) < 1.5f) r -= 2.0f;  // mandou andar e não saiu do lugar: está raspando ou preso em uma parede
  } else if (a == GIRAR_ESQ || a == GIRAR_DIR) {
    r -= 0.1f;
    if (d0 >= 90) r -= 0.5f;                     // girar à toa com o caminho livre
    if (d0 < 50) r += (d1 > d0 + 8) ? 1.0f : 0.1f;  // girou e abriu espaço
  } else {  // RE: o carrinho não tem sensor atrás, então recuar é às cegas e só vale em último caso
    r -= 1.0f;
    if (d0 >= 50) r -= 1.0f;                     // recuar à toa
    else if (d0 < TREINO_DIST_PERIGO_CM && d1 > d0 + 5) r += 0.5f;
  }
  return r;
}

// ---- aleatório simples (xorshift), para não depender do Arduino -------------------------------------------------------------
inline uint32_t proximo_aleatorio(uint32_t& s) {
  s ^= s << 13;
  s ^= s >> 17;
  s ^= s << 5;
  return s;
}
inline float aleatorio01(uint32_t& s) { return (proximo_aleatorio(s) >> 8) * (1.0f / 16777216.0f); }

// ---- o que fica salvo na memória flash --------------------------------------------------------------------------------------
struct Bloco {  // resumo de PASSOS_POR_BLOCO passos de treino (um ponto da curva de aprendizado)
  float recompensa_media;
  uint16_t quase_batidas;  // passos com algo mais perto que TREINO_DIST_PERIGO_CM
  uint16_t freios;         // passos em que o freio de segurança agiu
};

struct Memoria {
  uint32_t versao;
  uint32_t passos;  // passos de treino já feitos (define o quanto ele ainda explora)
  uint32_t blocos;  // blocos já fechados (o histórico guarda os últimos N_BLOCOS)
  float q[N_ESTADOS][N_ACOES];
  Bloco historico[N_BLOCOS];
};

struct Decisao {
  Acao acao;      // o que fazer neste ciclo (se não houver freio nem fuga)
  bool explorou;  // true = foi uma ação aleatória, de teste
  bool freio;     // true = algo a menos de TREINO_DIST_FREIO_CM: recuar um pouco (não é decisão do agente)
  bool escapar;   // true = freou várias vezes seguidas: está preso em um canto, fazer uma fuga maior
  int lado;       // lado da fuga: 1 = direita, -1 = esquerda
};

struct Agente {
  Memoria m;
  uint32_t rng = 2463534242u;
  bool fechou_bloco = false;  // ligado quando um bloco acabou de fechar (o robô imprime o resumo e desliga)

  Agente() { zerar(); }

  void semear(uint32_t s) { rng = s ? s : 1; }

  // apaga o aprendizado. Com TREINO_CONHECIMENTO_INICIAL, parte da regra antiga (anda se livre, vira se perto) como palpite fraco
  void zerar(bool com_conhecimento = TREINO_CONHECIMENTO_INICIAL) {
    memset(&m, 0, sizeof(m));
    m.versao = VERSAO_MEMORIA;
    if (com_conhecimento) {
      for (int s = 0; s < N_ESTADOS; s++) {
        int f = s / (N_TENDENCIAS * N_GIROS), t = (s / N_GIROS) % N_TENDENCIAS;
        float* q = m.q[s];
        if (f >= 3) {  // médio ou longe: andar
          q[FRENTE] = 0.5f; q[FRENTE_LENTO] = 0.3f; q[GIRAR_ESQ] = q[GIRAR_DIR] = -0.2f; q[RE] = -0.5f;
        } else if (f == 2) {  // perto: se está se aproximando, melhor virar
          bool aprox = (t == 0);
          q[FRENTE] = aprox ? -0.3f : 0.2f; q[FRENTE_LENTO] = 0.2f; q[GIRAR_ESQ] = q[GIRAR_DIR] = aprox ? 0.3f : 0.0f; q[RE] = -0.4f;
        } else {  // perigo ou freio: virar
          q[FRENTE] = -1.0f; q[FRENTE_LENTO] = -0.8f; q[GIRAR_ESQ] = q[GIRAR_DIR] = 0.3f; q[RE] = 0.0f;
        }
        if (f <= 4 && t == 1 && (s % N_GIROS) == 0) {  // acabou de andar e a distância não mudou: está preso, melhor virar
          q[FRENTE] -= 0.5f; q[FRENTE_LENTO] -= 0.5f; q[GIRAR_ESQ] += 0.3f; q[GIRAR_DIR] += 0.3f;
        }
      }
    }
    recomecar();
  }

  // esquece o ciclo anterior (depois de trocar de modo ou de uma manobra), sem apagar o que aprendeu
  void recomecar() {
    tem_ant = false;
    giro = 3;
    mascara_freio = 0;
    detector.esquecer();
  }

  float epsilon() const { return RL_EPS_MINIMO + (RL_EPS_INICIAL - RL_EPS_MINIMO) * expf(-(float)m.passos / RL_EPS_TAU); }

  Acao melhor_acao(int s) const {
    int melhor = 0;
    for (int a = 1; a < N_ACOES; a++)
      if (m.q[s][a] > m.q[s][melhor]) melhor = a;
    return (Acao)melhor;
  }

  // Chamado a cada ciclo com a distância medida (já filtrada).
  //   explorar: pode testar ações aleatórias (modo treino). aprender: atualiza a tabela (modo treino).
  // Devolve o que o robô deve fazer. O freio de segurança e a fuga valem mais que o agente e não entram no aprendizado.
  Decisao decidir(float d, bool explorar, bool aprender) {
    bool andou = tem_ant && (a_ant == FRENTE || a_ant == FRENTE_LENTO);
    bool raspando = detector.atualizar(andou, d);  // mandou andar e a distância não mudou: preso em uma parede
    float delta = tem_ant ? d - d_ant : 0;
    int s2 = codigo_estado(d, delta, giro);
    if (tem_ant && aprender) {  // fecha o ciclo anterior: a nota da ação que ele tomou
      float r = recompensa(a_ant, d_ant, d);
      float melhor = m.q[s2][0];
      for (int a = 1; a < N_ACOES; a++)
        if (m.q[s2][a] > melhor) melhor = m.q[s2][a];
      m.q[s_ant][a_ant] += RL_ALFA * (r + RL_GAMA * melhor - m.q[s_ant][a_ant]);
      m.passos++;
      registrar(r, d);
    }
    mascara_freio = (mascara_freio << 1) | (d < TREINO_DIST_FREIO_CM ? 1u : 0u);

    Decisao x = {FRENTE, false, false, false, 0};
    bool testar = explorar && aleatorio01(rng) < epsilon();
    x.acao = testar ? (Acao)(proximo_aleatorio(rng) % N_ACOES) : melhor_acao(s2);
    x.explorou = testar;
    s_ant = s2;
    a_ant = x.acao;
    d_ant = d;
    tem_ant = true;
    giro = (x.acao == GIRAR_ESQ) ? 1 : (x.acao == GIRAR_DIR ? 2 : (x.acao == RE ? 3 : 0));

    if (d < TREINO_DIST_FREIO_CM) {  // o freio de segurança assume: a ação do agente não vai ser executada
      tem_ant = false;
      giro = 3;
      if (preso()) {
        x.escapar = true;
        x.lado = lado_fuga;
        lado_fuga = -lado_fuga;
        mascara_freio = 0;
      } else {
        x.freio = true;
      }
    } else if (raspando) {  // preso sem ter chegado perto o bastante para o freio: fuga
      tem_ant = false;
      giro = 3;
      x.escapar = true;
      x.lado = lado_fuga;
      lado_fuga = -lado_fuga;
    }
    return x;
  }

 private:
  bool tem_ant = false;
  int s_ant = 0, giro = 0, lado_fuga = 1;
  Acao a_ant = FRENTE;
  float d_ant = 200;
  uint32_t mascara_freio = 0;  // um bit por ciclo: 1 = o freio agiu
  DetectorTravado detector;
  float bloco_r = 0;
  int bloco_passos = 0, bloco_quase = 0, bloco_freios = 0;

  // 5 freios nos últimos 30 ciclos: está preso
  bool preso() const {
    uint32_t v = mascara_freio & 0x3FFFFFFFu;
    int n = 0;
    for (; v; v &= v - 1) n++;
    return n >= 5;
  }

  void registrar(float r, float d) {
    bloco_r += r;
    bloco_passos++;
    if (d < TREINO_DIST_PERIGO_CM) bloco_quase++;
    if (d < TREINO_DIST_FREIO_CM) bloco_freios++;
    if (bloco_passos >= PASSOS_POR_BLOCO) {
      Bloco& b = m.historico[m.blocos % N_BLOCOS];
      b.recompensa_media = bloco_r / bloco_passos;
      b.quase_batidas = bloco_quase;
      b.freios = bloco_freios;
      m.blocos++;
      bloco_r = 0;
      bloco_passos = bloco_quase = bloco_freios = 0;
      fechou_bloco = true;
    }
  }
};
