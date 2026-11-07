// Simulador de salas para testar o aprendizado do carrinho (aprendizado.h) no computador, sem o robô.
// Compilado e executado por simular_treino.py. Uso: mundo_treino <passos_de_treino> <semente>
//
// O mundo: sala retangular com 2 a 6 obstáculos redondos. O robô é um disco de 10 cm com UM sensor de distância na frente, com os
// defeitos do HC-SR04 (ruído, falha de eco, leitura falsa, mediana de 3). Os movimentos têm erro, porque o carrinho de verdade
// não tem nada que meça o quanto andou ou girou.
#include <stdio.h>

#include <algorithm>
#include <cmath>
#include <random>
#include <set>
#include <string>
#include <utility>
#include <vector>

#include "aprendizado.h"
#include "seguranca.h"

static std::mt19937 gen(1);
static float normal(float desvio) { return std::normal_distribution<float>(0, desvio)(gen); }
static float uniforme(float a, float b) { return std::uniform_real_distribution<float>(a, b)(gen); }

const float R = 10;    // raio do robô (cm)
const float DT = 0.13f;  // um ciclo do robô: 0,1 s de espera + a medição
const float PI_ = 3.14159265f;

struct Obstaculo { float x, y, r; };
struct Mundo {
  float W, H;
  std::vector<Obstaculo> o;

  bool livre(float x, float y) const {
    if (x < R || y < R || x > W - R || y > H - R) return false;
    for (auto& b : o)
      if (hypotf(x - b.x, y - b.y) < b.r + R) return false;
    return true;
  }

  // distância verdadeira, do ponto (px,py) na direção th, até a parede ou obstáculo mais próximo
  float raio(float px, float py, float th) const {
    float dx = cosf(th), dy = sinf(th), melhor = 1e9f;
    if (dx > 1e-6f) melhor = std::min(melhor, (W - px) / dx);
    if (dx < -1e-6f) melhor = std::min(melhor, (0 - px) / dx);
    if (dy > 1e-6f) melhor = std::min(melhor, (H - py) / dy);
    if (dy < -1e-6f) melhor = std::min(melhor, (0 - py) / dy);
    for (auto& b : o) {
      float ox = px - b.x, oy = py - b.y, bb = dx * ox + dy * oy, cc = ox * ox + oy * oy - b.r * b.r;
      float disc = bb * bb - cc;
      if (disc >= 0) {
        float t = -bb - sqrtf(disc);
        if (t > 0) melhor = std::min(melhor, t);
      }
    }
    return std::max(melhor, 0.0f);
  }
};

struct Robo { float x, y, th; };

static Mundo sala_aleatoria(Robo& r) {
  Mundo w;
  w.W = uniforme(200, 400);
  w.H = uniforme(200, 400);
  int n = 2 + gen() % 5;
  for (int i = 0; i < n; i++) w.o.push_back({uniforme(30, w.W - 30), uniforme(30, w.H - 30), uniforme(6, 18)});
  do {
    r.x = uniforme(R, w.W - R);
    r.y = uniforme(R, w.H - R);
  } while (!w.livre(r.x, r.y));
  r.th = uniforme(0, 2 * PI_);
  return w;
}

// uma leitura do HC-SR04 simulado
static float distancia_real(const Mundo& w, const Robo& r) {  // o HC-SR04 enxerga um cone de uns 15 graus: o mais perto de 3 raios
  float t = 1e9f;
  for (float desvio : {-0.14f, 0.0f, 0.14f}) t = std::min(t, w.raio(r.x + R * cosf(r.th), r.y + R * sinf(r.th), r.th + desvio));
  return t;
}

static float medir_uma(const Mundo& w, const Robo& r) {
  float t = distancia_real(w, r);
  if (t > 200 || t < 2) return 200;      // sem eco: longe demais ou perto demais
  if (uniforme(0, 1) < 0.03f) return 200;  // falha de eco
  if (uniforme(0, 1) < 0.01f) return uniforme(5, 200);  // leitura falsa
  return std::min(200.0f, std::max(0.0f, t + normal(1.0f + 0.005f * t)));
}

// mediana de 3, como o robô faz
static float medir(const Mundo& w, const Robo& r) {
  float a = medir_uma(w, r), b = medir_uma(w, r), c = medir_uma(w, r);
  return std::max(std::min(a, b), std::min(std::max(a, b), c));
}

struct Contagem {
  int quase = 0, freios = 0, batidas = 0, passos = 0;
  float andou = 0, recompensa = 0;
  std::set<std::pair<int, int>> celulas;  // células de 20 cm que o robô visitou
};

static void mover(const Mundo& w, Robo& r, float v, float giro, float tempo, Contagem& c) {
  float th = r.th + giro * tempo;
  float nx = r.x + v * cosf(th) * tempo, ny = r.y + v * sinf(th) * tempo;
  r.th = th;
  if (!w.livre(nx, ny)) {
    c.batidas++;  // encostou: não anda
    return;
  }
  r.x = nx;
  r.y = ny;
  if (v > 0) c.andou += v * tempo;
  c.celulas.insert({(int)(r.x / 20), (int)(r.y / 20)});
}

static void executar(const Mundo& w, Robo& r, Acao a, float tempo, Contagem& c) {
  const float GIRO = 110 * PI_ / 180;
  switch (a) {
    case FRENTE: mover(w, r, 42 * (1 + normal(0.1f)), 0, tempo, c); break;
    case FRENTE_LENTO: mover(w, r, 26 * (1 + normal(0.1f)), 0, tempo, c); break;
    case GIRAR_ESQ: mover(w, r, 0, GIRO * (1 + normal(0.3f)), tempo, c); break;
    case GIRAR_DIR: mover(w, r, 0, -GIRO * (1 + normal(0.3f)), tempo, c); break;
    case RE: mover(w, r, -22, 0, tempo, c); break;
    default: break;
  }
}

static void freio(const Mundo& w, Robo& r, Contagem& c) { executar(w, r, RE, 0.25f, c); }
static void fuga(const Mundo& w, Robo& r, int lado, Contagem& c) {
  executar(w, r, RE, 0.5f, c);
  executar(w, r, lado > 0 ? GIRAR_DIR : GIRAR_ESQ, 0.7f, c);
}

// o que conta como erro: a distância VERDADEIRA ficar dentro da zona de perigo
static void contar(const Mundo& w, const Robo& r, Contagem& c) {
  float t = distancia_real(w, r);
  if (t < TREINO_DIST_PERIGO_CM) c.quase++;
  if (t < TREINO_DIST_FREIO_CM) c.freios++;
  c.passos++;
}

// ---- políticas ------------------------------------------------------------------------------------------------------------
struct Politica {
  virtual ~Politica() {}
  virtual void nova_sala() {}
  virtual void passo(const Mundo& w, Robo& r, float d, Contagem& c) = 0;
};

// o freio de segurança é o mesmo para todas as políticas
static bool freio_de_seguranca(const Mundo& w, Robo& r, float d, Contagem& c) {
  if (d < TREINO_DIST_FREIO_CM) {
    freio(w, r, c);
    return true;
  }
  return false;
}

struct Aleatoria : Politica {
  void passo(const Mundo& w, Robo& r, float d, Contagem& c) override {
    if (freio_de_seguranca(w, r, d, c)) return;
    executar(w, r, (Acao)(gen() % N_ACOES), DT, c);
  }
};

// o modo autônomo antigo do robo.ino: anda até 25 cm, recua, vira para o lado (alternando) até ter 40 cm livres
struct Regras : Politica {
  int fase = 0, n = 0, lado = 1;
  bool com_detector;
  DetectorTravado detector;
  FiltroDistancia filtro;
  bool andou_antes = false;
  explicit Regras(bool com_detector_) : com_detector(com_detector_) {}
  void nova_sala() override { fase = 0; n = 0; detector.esquecer(); filtro.esquecer(); andou_antes = false; }
  void passo(const Mundo& w, Robo& r, float d, Contagem& c) override {
    if (com_detector) {
      d = filtro.filtrar(d, 2 * DIST_MINIMA_CM, DIST_MINIMA_CM - 1);
      bool preso = detector.atualizar(andou_antes && fase == 0, d);
      andou_antes = false;
      if (preso && fase == 0) { fase = 1; n = 3; lado = -lado; }
    }
    if (fase == 0 && d < 25) {
      fase = 1;
      n = 3;
      lado = -lado;
    }
    if (fase == 1) {
      if (n-- > 0) { executar(w, r, RE, DT, c); return; }
      fase = 2;
      n = 0;
    }
    if (fase == 2) {
      n++;
      if ((n > 4 && d >= 40) || n >= 11) fase = 0;
      else { executar(w, r, lado > 0 ? GIRAR_DIR : GIRAR_ESQ, DT, c); return; }
    }
    if (freio_de_seguranca(w, r, d, c)) return;
    executar(w, r, FRENTE, DT, c);
    andou_antes = true;
  }
};

struct Aprendiz : Politica {
  Agente ag;
  FiltroDistancia filtro;
  bool explorar, aprender;
  Aprendiz(bool explorar_, bool aprender_) : explorar(explorar_), aprender(aprender_) {}
  void nova_sala() override { ag.recomecar(); filtro.esquecer(); }
  void passo(const Mundo& w, Robo& r, float d, Contagem& c) override {
    d = filtro.filtrar(d, 2 * DIST_MINIMA_CM, DIST_MINIMA_CM - 1);
    int antes = ag.m.blocos;
    Decisao x = ag.decidir(d, explorar, aprender);
    (void)antes;
    if (x.escapar) { fuga(w, r, x.lado, c); filtro.esquecer(); return; }
    if (x.freio) { freio(w, r, c); filtro.esquecer(); return; }
    executar(w, r, x.acao, DT, c);
  }
};

// roda uma sala de `passos` ciclos
static Contagem sala(Politica& p, int passos) {
  Robo r;
  Mundo w = sala_aleatoria(r);
  p.nova_sala();
  Contagem c;
  for (int i = 0; i < passos; i++) {
    contar(w, r, c);
    p.passo(w, r, medir(w, r), c);
  }
  return c;
}

static void imprimir(const char* tipo, const std::string& nome, int idx, const Contagem& c, float eps = 0) {
  printf("%s,%s,%d,%d,%d,%d,%.1f,%zu,%.4f\n", tipo, nome.c_str(), idx, c.quase, c.freios, c.batidas, c.andou, c.celulas.size(), eps);
}

int main(int argc, char** argv) {
  int passos_treino = argc > 1 ? atoi(argv[1]) : 60000;
  int semente = argc > 2 ? atoi(argv[2]) : 1;
  gen.seed(semente);
  const int POR_SALA = 600;

  // 1) curva de aprendizado: treina de 2 jeitos (do zero e partindo da regra antiga) em salas sempre novas
  Aprendiz frio(true, true), quente(true, true);
  frio.ag.zerar(false);
  quente.ag.zerar(true);
  frio.ag.semear(11 + semente);
  quente.ag.semear(22 + semente);
  for (int i = 0; i < passos_treino / POR_SALA; i++) {
    imprimir("treino", "do_zero", i, sala(frio, POR_SALA), frio.ag.epsilon());
    imprimir("treino", "com_palpite_inicial", i, sala(quente, POR_SALA), quente.ag.epsilon());
  }

  // 2) avaliação em salas que ele nunca viu (sem explorar e sem aprender), contra as outras políticas
  Aleatoria aleatoria;
  Regras regras(false), regras_novas(true);
  Aprendiz a_frio(false, false), a_quente(false, false), nada(false, false);
  a_frio.ag = frio.ag;
  a_quente.ag = quente.ag;
  nada.ag.zerar(false);  // agente sem treino nenhum, só a tabela zerada
  struct { const char* nome; Politica* p; } todos[] = {
      {"aleatoria", &aleatoria}, {"regras_antigas", &regras}, {"regras_com_detector", &regras_novas}, {"agente_sem_treino", &nada},
      {"agente_do_zero", &a_frio}, {"agente_com_palpite", &a_quente}};
  for (auto& t : todos) {
    gen.seed(1000);  // as mesmas salas para todos
    for (int i = 0; i < 100; i++) imprimir("avaliacao", t.nome, i, sala(*t.p, POR_SALA));
  }
  return 0;
}
