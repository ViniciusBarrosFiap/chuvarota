// Aprendizado por reforço (Q-learning) do carrinho. Sem dependência do Arduino: o mesmo código roda no ESP32 e na simulação do
// computador (maker/tinyml/simular_treino.py), que é onde ele foi testado.
//
// O robô olha a distância à frente, escolhe uma ação (seguir, curvar ou girar para um lado) e a MANTÉM por alguns ciclos
// (CICLOS_POR_ACAO), para o movimento não ficar picado. No fim recebe uma nota pelo que aconteceu (andou livre = ganha; chegou perto
// demais, girou à toa ou trocou de lado toda hora = perde) e atualiza uma tabela estado x ação (72 x 5 números).
//
// Além disso ele aprende o PRÓPRIO FREIO: a cada freada mede quanto espaço sobrou entre o carrinho parado e o obstáculo e ajusta a
// distância do freio (1 cm por vez), para ir chegando mais perto das paredes sem bater. Todas as distâncias do treino (faixas do
// estado, notas) são medidas a partir dessa distância do freio, por isso a tabela continua valendo quando ela muda.
//
// Limites: o carrinho tem um sensor só, olhando para frente, e nada que meça quanto andou. Por isso ele aprende reflexos para o
// ambiente em que está (o que fazer ao ver uma parede a tantos cm), e não um mapa do lugar.
#pragma once
#include <math.h>
#include <stdint.h>
#include <string.h>

#include "config.h"
#include "logica.h"

enum Acao { FRENTE = 0, CURVA_ESQ = 1, CURVA_DIR = 2, GIRAR_ESQ = 3, GIRAR_DIR = 4, N_ACOES = 5 };

// estado = faixa da distância (6) x tendência (3) x última ação (4: seguiu, virou à esquerda, virou à direita, outra)
enum { N_FAIXAS = 6, N_TENDENCIAS = 3, N_GIROS = 4, N_ESTADOS = N_FAIXAS * N_TENDENCIAS * N_GIROS };
enum { PASSOS_POR_BLOCO = 100, N_BLOCOS = 40, VERSAO_MEMORIA = 3, CICLOS_POR_ACAO = 3 };

constexpr float RL_ALFA = 0.15f;         // o quanto cada experiência nova pesa
constexpr float RL_GAMA = 0.90f;         // o quanto ele se importa com o que vem depois
constexpr float RL_EPS_INICIAL = 0.30f;  // chance de testar uma ação aleatória no começo
constexpr float RL_EPS_MINIMO = 0.05f;   // e depois de muito treino
constexpr float RL_EPS_TAU = 1200.0f;    // passos (cada um dura CICLOS_POR_ACAO ciclos) para a exploração cair a ~37% do valor inicial

// Freio adaptativo (os que você pode querer mudar estão no config.h: TREINO_MARGEM_MIN_CM, TREINO_ADAPTAR_MARGEM, TREINO_APITAR_ERRO)
constexpr float RL_FREIO_INICIAL_CM = 20;   // distância do freio no começo (o robô a ajusta depois)
constexpr float RL_MARGEM_MAX_CM = 30;      // e nunca passa disso
constexpr float RL_FOLGA_MIN_CM = 6;        // depois de freado, quer ficar pelo menos a esta distância do obstáculo
constexpr float RL_FOLGA_MAX_CM = 10;       // se sobrar mais que isso, pode chegar mais perto da próxima vez
constexpr float RL_PERIGO_EXTRA_CM = 10;    // perde pontos quando chega a menos de (distância do freio + isto)
constexpr bool RL_PALPITE_INICIAL = true;   // começa com a regra antiga como palpite fraco: aprende bem mais rápido
// "mandou andar e a distância não mudou": quanto a distância tem que mudar em 3 ciclos andando para não contar como preso
constexpr float RL_TRAVADO_CM = (0.12f * CARRINHO_CM_S_LENTO) > 1.5f ? (0.12f * CARRINHO_CM_S_LENTO) : 1.5f;

inline const char* nome_acao(int a) {
  static const char* nomes[] = {"seguir em frente", "curva à esquerda", "curva à direita", "girar à esquerda", "girar à direita"};
  return nomes[a];
}

// 0 = seguiu em frente, 1 = virou à esquerda, 2 = virou à direita
inline int codigo_giro(Acao a) { return a == FRENTE ? 0 : ((a == CURVA_ESQ || a == GIRAR_ESQ) ? 1 : 2); }

// O que cada ação manda para as rodas (-1 a 1). A velocidade acompanha a distância (perfil_velocidade): mais devagar perto do obstáculo,
// sem degrau. escuro: no escuro anda um pouco mais devagar. Usado pelo robô e pela simulação.
inline Rodas rodas_da_acao(Acao a, float d, float margem, bool escuro) {
  float v = perfil_velocidade(d, margem) * (escuro ? 0.85f : 1.0f);
  switch (a) {
    case FRENTE: return misturar(v, 0);
    case CURVA_ESQ: return misturar(0.6f * v, -0.45f);
    case CURVA_DIR: return misturar(0.6f * v, 0.45f);
    case GIRAR_ESQ: return misturar(0, -0.6f);
    default: return misturar(0, 0.6f);
  }
}

// ---- como o robô enxerga o mundo -------------------------------------------------------------------------------------------
// margem = distância do freio no momento (ela muda com o aprendizado). "Folga" = distância - margem.
inline int faixa_dist(float d, float margem) {
  if (d >= 190) return 5;  // sem eco (nada à frente ou o sensor não pegou nada)
  float folga = d - margem;
  if (folga < 0) return 0;                      // freio de segurança
  if (folga < RL_PERIGO_EXTRA_CM) return 1;     // perigo
  if (folga < 30) return 2;                     // perto
  if (folga < 70) return 3;                     // médio
  return 4;                                     // longe, com eco
}
inline int faixa_tend(float delta_cm) { return delta_cm < -3 ? 0 : (delta_cm > 3 ? 2 : 1); }  // 0 aproximando, 1 estável, 2 afastando
inline int codigo_estado(float d, float delta_cm, int giro, float margem) {
  return (faixa_dist(d, margem) * N_TENDENCIAS + faixa_tend(delta_cm)) * N_GIROS + giro;
}

// ---- a nota que o robô recebe: d0 = distância antes da ação, d1 = depois; ultimo = ação anterior a esta (codigo_giro) --------
inline float recompensa(Acao a, float d0, float d1, float margem, int ultimo = 3) {
  float perigo = margem + RL_PERIGO_EXTRA_CM, perto = margem + 30, longe = margem + 70;
  float r = -0.05f;  // custo de cada passo: não vale ficar parado
  if (d1 < margem) r -= 10;        // o freio de segurança teve que agir: erro grave
  else if (d1 < perigo) r -= 3;    // quase batida
  int lado = codigo_giro(a);
  if (a == FRENTE || a == CURVA_ESQ || a == CURVA_DIR) {
    float bom = (a == FRENTE) ? 1.0f : 0.5f;  // seguir reto rende mais, desde que o caminho esteja livre
    if (d1 >= perto) r += bom;
    else if (d1 >= perigo) r += bom * 0.3f;
    if (d0 < 190 && fabsf(d1 - d0) < RL_TRAVADO_CM / 2) r -= 2.0f;  // mandou andar e não saiu do lugar: raspando ou preso em uma parede
    if (a != FRENTE && d0 >= longe) r -= 0.3f;                      // curvar à toa com o caminho livre
  } else {  // GIRAR no lugar
    r -= 0.1f;
    if (d0 >= longe) r -= 0.5f;                    // girar à toa com o caminho livre
    if (d0 < perto) r += (d1 > d0 + 8) ? 1.0f : 0.1f;  // girou e abriu espaço
  }
  if (lado != 0 && ultimo != 0 && ultimo != 3 && ultimo != lado) r -= 0.5f;  // trocou de lado: vai e volta, o carrinho fica "tremendo"
  return r;
}

// ---- o que fica salvo na memória flash --------------------------------------------------------------------------------------
struct Bloco {  // resumo de PASSOS_POR_BLOCO passos de treino (um ponto da curva de aprendizado)
  float recompensa_media;
  uint16_t quase_batidas;  // passos com algo mais perto que a distância do freio + RL_PERIGO_EXTRA_CM
  uint16_t freios;         // passos em que o freio de segurança agiu
  uint8_t margem_cm;       // distância do freio (andando rápido) no fim do bloco
};

struct Memoria {
  uint32_t versao;
  uint32_t passos;  // passos de treino já feitos (define o quanto ele ainda explora)
  uint32_t blocos;  // blocos já fechados (o histórico guarda os últimos N_BLOCOS)
  float freio_cm[2];  // distância do freio aprendida: [0] andando rápido, [1] andando devagar (ou parado)
  float q[N_ESTADOS][N_ACOES];
  Bloco historico[N_BLOCOS];
};

struct Decisao {
  Acao acao;      // o que fazer neste ciclo (se não houver freio nem fuga)
  bool explorou;  // true = foi uma ação aleatória, de teste
  bool freio;     // true = algo mais perto que a distância do freio: parar, medir a folga (Agente::freou) e recuar um pouco
  bool escapar;   // true = freou várias vezes seguidas ou está preso raspando: fazer uma fuga maior
  int lado;       // lado da fuga: 1 = direita, -1 = esquerda
};

struct Agente {
  Memoria m;
  uint32_t rng = 2463534242u;
  bool fechou_bloco = false;  // ligado quando um bloco acabou de fechar (o robô imprime o resumo e desliga)
  float folga_medida = 0;     // folga da última freada (cm entre o carrinho parado e o obstáculo)
  float margem_antes = 0;     // distância do freio antes e depois do último ajuste, para o robô contar o que mudou
  float margem_depois = 0;
  bool adaptar_margem = TREINO_ADAPTAR_MARGEM;  // false = a distância do freio fica fixa

  Agente() { zerar(); }

  void semear(uint32_t s) { rng = s ? s : 1; }

  // apaga o aprendizado. Com RL_PALPITE_INICIAL, parte da regra antiga (anda se livre, vira se perto) como palpite fraco
  void zerar(bool com_conhecimento = RL_PALPITE_INICIAL) {
    memset(&m, 0, sizeof(m));
    m.versao = VERSAO_MEMORIA;
    m.freio_cm[0] = m.freio_cm[1] = RL_FREIO_INICIAL_CM;
    if (com_conhecimento) {
      for (int s = 0; s < N_ESTADOS; s++) {
        int f = s / (N_TENDENCIAS * N_GIROS), t = (s / N_GIROS) % N_TENDENCIAS;
        float* q = m.q[s];
        if (f >= 3) {  // médio ou longe: seguir
          q[FRENTE] = 0.5f; q[CURVA_ESQ] = q[CURVA_DIR] = -0.1f; q[GIRAR_ESQ] = q[GIRAR_DIR] = -0.3f;
        } else if (f == 2) {  // perto: se está se aproximando, melhor curvar
          bool aprox = (t == 0);
          q[FRENTE] = aprox ? -0.2f : 0.3f; q[CURVA_ESQ] = q[CURVA_DIR] = aprox ? 0.35f : 0.1f; q[GIRAR_ESQ] = q[GIRAR_DIR] = aprox ? 0.0f : -0.1f;
        } else {  // perigo ou freio: girar
          q[FRENTE] = -1.0f; q[CURVA_ESQ] = q[CURVA_DIR] = -0.2f; q[GIRAR_ESQ] = q[GIRAR_DIR] = 0.4f;
        }
        if (f <= 4 && t == 1 && (s % N_GIROS) == 0) {  // acabou de seguir e a distância não mudou: está preso, melhor girar
          q[FRENTE] -= 0.8f; q[CURVA_ESQ] -= 0.2f; q[CURVA_DIR] -= 0.2f; q[GIRAR_ESQ] += 0.5f; q[GIRAR_DIR] += 0.5f;
        }
      }
    }
    recomecar();
  }

  // esquece o ciclo anterior (depois de trocar de modo ou de uma manobra), sem apagar o que aprendeu
  void recomecar() {
    tem_ant = false;
    giro = 3;
    espera = 0;
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
  //   escuro: no escuro a ação FRENTE é um pouco mais devagar (conta como devagar para o freio).
  // A ação escolhida vale por CICLOS_POR_ACAO ciclos (movimento contínuo); só o freio de segurança e a fuga interrompem antes.
  // O freio e a fuga valem mais que o agente e não entram no aprendizado.
  Decisao decidir(float d, bool explorar, bool aprender, bool escuro = false) {
    float margem = m.freio_cm[0];  // referência das faixas e das notas
    // distância do freio que vale agora: a da velocidade que ele vinha. Sem saber (acabou de frear), a maior.
    float limite = tem_ant ? m.freio_cm[rapido_ant ? 0 : 1] : (m.freio_cm[0] > m.freio_cm[1] ? m.freio_cm[0] : m.freio_cm[1]);
    bool andou = tem_ant && a_ant == FRENTE;
    bool raspando = detector.atualizar(andou, d, RL_TRAVADO_CM);  // mandou seguir e a distância não mudou: preso em uma parede
    mascara_freio = (mascara_freio << 1) | (d < limite ? 1u : 0u);
    bool emergencia = (d < limite) || raspando;

    if (tem_ant && espera > 0 && !emergencia) {  // ainda no meio da ação: continua nela
      espera--;
      Decisao igual = {a_ant, explorou_ant, false, false, 0};
      return igual;
    }

    float delta = tem_ant ? d - d_ant : 0;
    int s2 = codigo_estado(d, delta, giro, margem);
    if (tem_ant && aprender) {  // fecha a ação anterior: a nota do que ele fez
      float r = recompensa(a_ant, d_ant, d, margem, s_ant % N_GIROS);
      float melhor = m.q[s2][0];
      for (int a = 1; a < N_ACOES; a++)
        if (m.q[s2][a] > melhor) melhor = m.q[s2][a];
      m.q[s_ant][a_ant] += RL_ALFA * (r + RL_GAMA * melhor - m.q[s_ant][a_ant]);
      m.passos++;
      registrar(r, d);
    }

    Decisao x = {FRENTE, false, false, false, 0};
    bool testar = explorar && aleatorio01(rng) < epsilon();
    x.acao = testar ? (Acao)(proximo_aleatorio(rng) % N_ACOES) : melhor_acao(s2);
    x.explorou = testar;
    s_ant = s2;
    a_ant = x.acao;
    explorou_ant = testar;
    rapido_ant = (x.acao == FRENTE && !escuro);
    d_ant = d;
    tem_ant = true;
    giro = codigo_giro(x.acao);
    espera = CICLOS_POR_ACAO - 1;

    if (d < limite) {  // o freio de segurança assume: a ação do agente não vai ser executada
      freio_rapido = rapido_ant_antes_do_freio(limite);
      tem_ant = false;
      giro = 3;
      espera = 0;
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
      espera = 0;
      x.escapar = true;
      x.lado = lado_fuga;
      lado_fuga = -lado_fuga;
    }
    return x;
  }

  // O robô chama depois de uma freada, já com o carrinho parado e a distância medida de novo (d_depois). Assim ele descobre se a
  // distância do freio está boa: parou perto demais (ou o sensor perdeu o eco) = freia mais longe da próxima vez; sobrou espaço de
  // sobra (e pode_diminuir) = freia 1 cm mais perto. Sempre dentro de [TREINO_MARGEM_MIN_CM, RL_MARGEM_MAX_CM].
  void freou(float d_depois, bool pode_diminuir) {
    folga_medida = d_depois;
    margem_antes = margem_depois = m.freio_cm[freio_rapido ? 0 : 1];
    if (!adaptar_margem) return;
    float& lim = m.freio_cm[freio_rapido ? 0 : 1];
    if (d_depois >= 190) lim += 3;                                       // sumiu o eco: ficou perto demais para o sensor
    else if (d_depois < RL_FOLGA_MIN_CM) lim += 2;                       // parou perto demais
    else if (d_depois > RL_FOLGA_MAX_CM && pode_diminuir) lim -= 1;      // sobrou espaço: pode chegar mais perto
    if (lim < TREINO_MARGEM_MIN_CM) lim = TREINO_MARGEM_MIN_CM;
    if (lim > RL_MARGEM_MAX_CM) lim = RL_MARGEM_MAX_CM;
    margem_depois = lim;
  }

 private:
  bool tem_ant = false;
  bool rapido_ant = false;    // a ação anterior era seguir na velocidade cheia
  bool freio_rapido = false;  // o freio atual foi de uma andada rápida
  bool explorou_ant = false;
  int s_ant = 0, giro = 0, lado_fuga = 1, espera = 0;
  Acao a_ant = FRENTE;
  float d_ant = 200;
  uint32_t mascara_freio = 0;  // um bit por ciclo: 1 = o freio agiu
  DetectorTravado detector;
  float bloco_r = 0;
  int bloco_passos = 0, bloco_quase = 0, bloco_freios = 0;

  // qual das duas distâncias de freio disparou: a rápida ou a devagar
  bool rapido_ant_antes_do_freio(float limite) const { return limite >= m.freio_cm[0]; }

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
    if (d < m.freio_cm[0] + RL_PERIGO_EXTRA_CM) bloco_quase++;
    if (d < m.freio_cm[0]) bloco_freios++;
    if (bloco_passos >= PASSOS_POR_BLOCO) {
      Bloco& b = m.historico[m.blocos % N_BLOCOS];
      b.recompensa_media = bloco_r / bloco_passos;
      b.quase_batidas = bloco_quase;
      b.freios = bloco_freios;
      b.margem_cm = (uint8_t)(m.freio_cm[0] + 0.5f);
      m.blocos++;
      bloco_r = 0;
      bloco_passos = bloco_quase = bloco_freios = 0;
      fechou_bloco = true;
    }
  }
};
