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
#include "logica.h"

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

struct Robo {
  float x, y, th;
  float se = 0, sd = 0;  // velocidade real de cada roda (cm/s): o motor demora a acelerar e a frear
};

static Mundo sala_aleatoria(Robo& r, bool apertada = false) {
  for (;;) {
    Mundo w;
    w.W = apertada ? uniforme(130, 220) : uniforme(200, 400);
    w.H = apertada ? uniforme(130, 220) : uniforme(200, 400);
    int n = apertada ? 4 + gen() % 4 : 2 + gen() % 5;
    for (int i = 0; i < n; i++) w.o.push_back({uniforme(25, w.W - 25), uniforme(25, w.H - 25), apertada ? uniforme(8, 16) : uniforme(6, 18)});
    for (int tentativa = 0; tentativa < 200; tentativa++) {
      r.x = uniforme(R, w.W - R);
      r.y = uniforme(R, w.H - R);
      if (w.livre(r.x, r.y)) {
        r.th = uniforme(0, 2 * PI_);
        r.se = r.sd = 0;
        return w;
      }
    }
  }
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

// 3 leituras e, se não concordam, até 5, com descarte das falsas: o mesmo código do robô (logica.h)
static float medir(const Mundo& w, const Robo& r) {
  return medir_adaptativo([&] { return medir_uma(w, r); }, 3, 5);
}

struct Contagem {
  int quase = 0, freios = 0, batidas = 0, passos = 0, muito_perto = 0;
  float andou = 0, recompensa = 0;
  std::set<std::pair<int, int>> celulas;  // células de 20 cm que o robô visitou
  // fluidez do movimento (ponderada pelo tempo)
  float t = 0, t_preso = 0, t_giro = 0, t_re = 0, u_esq = 0, u_dir = 0;
  int trocas = 0, sinal_giro = 0, abruptos = 0;
};

// devolve quanto o carrinho andou de verdade (0 se encostou)
static float mover(const Mundo& w, Robo& r, float v, float giro, float tempo, Contagem& c) {
  float th = r.th + giro * tempo;
  float nx = r.x + v * cosf(th) * tempo, ny = r.y + v * sinf(th) * tempo;
  r.th = th;
  if (!w.livre(nx, ny)) {
    c.batidas++;  // encostou: não anda
    return 0;
  }
  float andou = hypotf(nx - r.x, ny - r.y);
  r.x = nx;
  r.y = ny;
  if (v > 0) c.andou += v * tempo;
  c.celulas.insert({(int)(r.x / 20), (int)(r.y / 20)});
  return andou;
}

// velocidade de regime de uma roda para um comando de -1 a 1: abaixo de 5% fica parada; senão vai de metade da velocidade cheia até a cheia
// (o motor só vence o atrito a partir do PWM_MINIMO, por isso não existe velocidade bem baixa)
static float cmd_para_cm_s(float x) {
  float a = fabsf(x);
  if (a < 0.05f) return 0;
  float v = (0.5f + 0.5f * std::min(a, 1.0f)) * CARRINHO_CM_S_NORMAL;
  return x < 0 ? -v : v;
}
static const float K_GIRO = CARRINHO_GRAUS_S / (0.8f * CARRINHO_CM_S_NORMAL);  // graus/s por cm/s de diferença entre as rodas

// um pedaço de tempo andando com os comandos das rodas (já depois da rampa do robô)
static void aplicar(const Mundo& w, Robo& r, Rodas cmd, float dt, Contagem& c) {
  float alfa = 1 - expf(-dt / 0.12f);  // a roda leva ~0,12 s para chegar na velocidade (a freada tem ~5 cm de deslize)
  r.se += (cmd_para_cm_s(cmd.esq) - r.se) * alfa;
  r.sd += (cmd_para_cm_s(cmd.dir) - r.sd) * alfa;
  float v = (r.se + r.sd) / 2, om = (r.se - r.sd) / 2 * K_GIRO;  // om > 0 = vira para a direita (graus/s)
  float real = mover(w, r, v * (1 + normal(0.1f)), -om * (1 + normal(0.3f)) * PI_ / 180, dt, c) / std::max(dt, 1e-3f);  // velocidade de verdade (cm/s)
  c.t += dt;
  if ((cmd.esq + cmd.dir) / 2 > 0.3f && real < 3) c.t_preso += dt;  // mandou andar e não saiu do lugar: empurrando uma parede
  if (fabsf(v) < 6 && fabsf(om) > 30) c.t_giro += dt;
  if (v < -3) c.t_re += dt;
  int sinal = om > 20 ? 1 : (om < -20 ? -1 : 0);
  if (sinal != 0) {
    if (c.sinal_giro != 0 && sinal != c.sinal_giro) c.trocas++;
    c.sinal_giro = sinal;
  }
  if (fabsf(cmd.esq - c.u_esq) > 0.3f || fabsf(cmd.dir - c.u_dir) > 0.3f) c.abruptos++;  // degrau nos motores (solavanco)
  c.u_esq = cmd.esq;
  c.u_dir = cmd.dir;
}

// freio de segurança do robô: para, espera 0,08 s (o carrinho ainda desliza um pouco)
static void parar_e_esperar(const Mundo& w, Robo& r, Contagem& c) { aplicar(w, r, Rodas{0, 0}, 0.08f, c); }
static void re_curta(const Mundo& w, Robo& r, Contagem& c) { aplicar(w, r, Rodas{-0.15f, -0.15f}, 0.25f, c); }
// fuga de um canto: ré de 0,5 s e giro de 0,7 s (a mesma do robo.ino)
static void fuga(const Mundo& w, Robo& r, int lado, Contagem& c) {
  aplicar(w, r, Rodas{-0.15f, -0.15f}, 0.5f, c);
  aplicar(w, r, misturar(0, 0.6f * lado), 0.7f, c);
}

// o que conta como erro: a distância VERDADEIRA ficar dentro da zona de perigo
static void contar(const Mundo& w, const Robo& r, Contagem& c) {
  float t = distancia_real(w, r);
  if (t < 30) c.quase++;           // as métricas usam distâncias fixas (as do agente mudam com o aprendizado)
  if (t < 20) c.freios++;
  if (t < 8) c.muito_perto++;      // perto demais: quase encostando
  c.passos++;
}

// ---- políticas ------------------------------------------------------------------------------------------------------------
struct Politica {
  RampaMotor rampa;
  bool usa_rampa = true;  // o robô novo manda os motores em rampa; o modo autônomo antigo mandava em degrau
  virtual ~Politica() {}
  virtual void nova_sala() { rampa.parar(); }
  virtual void passo(const Mundo& w, Robo& r, float d, Contagem& c) = 0;
  // um ciclo (DT) andando com o alvo das rodas
  void rodar(const Mundo& w, Robo& r, Rodas alvo, Contagem& c) {
    Rodas cmd = usa_rampa ? rampa.seguir(alvo, 0.2f) : alvo;
    if (!usa_rampa) rampa.esq = alvo.esq, rampa.dir = alvo.dir;
    aplicar(w, r, cmd, DT, c);
  }
  // freio de segurança das políticas de comparação (o do agente é outro, com medição da folga)
  bool freio_seguranca(const Mundo& w, Robo& r, float d, Contagem& c) {
    if (d >= RL_FREIO_INICIAL_CM) return false;
    rampa.parar();
    parar_e_esperar(w, r, c);
    re_curta(w, r, c);
    return true;
  }
};

struct Aleatoria : Politica {
  void passo(const Mundo& w, Robo& r, float d, Contagem& c) override {
    if (freio_seguranca(w, r, d, c)) return;
    rodar(w, r, rodas_da_acao((Acao)(gen() % N_ACOES), d, RL_FREIO_INICIAL_CM, false), c);
  }
};

// o modo autônomo ANTIGO do robo.ino: anda na velocidade cheia até 25 cm, recua, gira (alternando o lado) até ter 40 cm livres.
// Mandava os motores em degrau (0 -> 180 -> ré -> giro).
struct Regras : Politica {
  int fase = 0, n = 0, lado = 1;
  bool com_detector;
  DetectorTravado detector;
  FiltroDistancia filtro;
  bool andou_antes = false;
  explicit Regras(bool com_detector_) : com_detector(com_detector_) { usa_rampa = false; }
  void nova_sala() override { Politica::nova_sala(); fase = 0; n = 0; detector.esquecer(); filtro.esquecer(); andou_antes = false; }
  void passo(const Mundo& w, Robo& r, float d, Contagem& c) override {
    if (com_detector) {
      d = filtro.filtrar(d, 2 * DIST_MINIMA_CM, DIST_MINIMA_CM - 1);
      bool preso = detector.atualizar(andou_antes && fase == 0, d, RL_TRAVADO_CM);
      andou_antes = false;
      if (preso && fase == 0) { fase = 1; n = 3; lado = -lado; }
    }
    if (fase == 0 && d < 25) {
      fase = 1;
      n = 3;
      lado = -lado;
    }
    if (fase == 1) {
      if (n-- > 0) { rodar(w, r, Rodas{-0.15f, -0.15f}, c); return; }
      fase = 2;
      n = 0;
    }
    if (fase == 2) {
      n++;
      if ((n > 4 && d >= 40) || n >= 11) fase = 0;
      else { rodar(w, r, misturar(0, 0.6f * lado), c); return; }
    }
    if (freio_seguranca(w, r, d, c)) return;
    rodar(w, r, Rodas{1, 1}, c);
    andou_antes = true;
  }
};

// o modo autônomo NOVO (Navegador do logica.h): velocidade pela distância, curva antes da parede, gira no lugar só se precisar
struct Suave : Politica {
  Navegador nav;
  DetectorTravado detector;
  FiltroDistancia filtro;
  bool seguiu_antes = false;
  void nova_sala() override { Politica::nova_sala(); nav.esquecer(); detector.esquecer(); filtro.esquecer(); seguiu_antes = false; }
  void passo(const Mundo& w, Robo& r, float d, Contagem& c) override {
    d = filtro.filtrar(d, 2 * DIST_MINIMA_CM, DIST_MINIMA_CM - 1);
    if (d < DIST_MINIMA_CM - 10) rampa.parar();  // algo muito perto: tira a velocidade na hora
    Navegador::Saida n = nav.passo(d, DIST_MINIMA_CM, DIST_MINIMA_CM + 50, DIST_MINIMA_CM + 20);
    if (n.preso || detector.atualizar(seguiu_antes, d, RL_TRAVADO_CM)) {
      fuga(w, r, nav.lado, c);
      if (!n.preso) nav.lado = -nav.lado;
      nav.esquecer(); detector.esquecer(); filtro.esquecer(); rampa.parar();
      seguiu_antes = false;
      return;
    }
    seguiu_antes = (n.v > 0.5f && fabsf(n.w) < 0.05f);
    rodar(w, r, misturar(n.v, n.w), c);
  }
};

struct Aprendiz : Politica {
  Agente ag;
  FiltroDistancia filtro;
  bool explorar, aprender;
  Aprendiz(bool explorar_, bool aprender_) : explorar(explorar_), aprender(aprender_) {}
  void nova_sala() override { Politica::nova_sala(); ag.recomecar(); filtro.esquecer(); }
  void passo(const Mundo& w, Robo& r, float d, Contagem& c) override {
    d = filtro.filtrar(d, 2 * DIST_MINIMA_CM, DIST_MINIMA_CM - 1);
    Decisao x = ag.decidir(d, explorar, aprender, false);
    if (x.escapar) { rampa.parar(); fuga(w, r, x.lado, c); filtro.esquecer(); return; }
    if (x.freio) {
      rampa.parar();
      parar_e_esperar(w, r, c);          // o carrinho ainda anda um pouco depois de decidir parar
      ag.freou(medir(w, r), aprender);   // mede quanto espaço sobrou e ajusta a distância do freio
      re_curta(w, r, c);
      filtro.esquecer();
      return;
    }
    rodar(w, r, rodas_da_acao(x.acao, d, ag.m.freio_cm[0], false), c);
  }
};

// roda uma sala de `passos` ciclos
static Contagem sala(Politica& p, int passos, bool apertada = false) {
  Robo r;
  Mundo w = sala_aleatoria(r, apertada);
  p.nova_sala();
  Contagem c;
  for (int i = 0; i < passos; i++) {
    contar(w, r, c);
    p.passo(w, r, medir(w, r), c);
  }
  return c;
}

static void imprimir(const char* tipo, const std::string& nome, int idx, const Contagem& c, float eps = 0) {
  float t = std::max(c.t, 1e-3f), min = t / 60;
  printf("%s,%s,%d,%d,%d,%d,%.1f,%zu,%d,%.1f,%.1f,%.1f,%.1f,%.1f,%.4f\n", tipo, nome.c_str(), idx, c.quase, c.freios, c.batidas, c.andou, c.celulas.size(),
         c.muito_perto, 100 * c.t_preso / t, 100 * c.t_giro / t, 100 * c.t_re / t, c.trocas / min, c.abruptos / min, eps);
}

int main(int argc, char** argv) {
  int passos_treino = argc > 1 ? atoi(argv[1]) : 60000;
  int semente = argc > 2 ? atoi(argv[2]) : 1;
  gen.seed(semente);
  const int POR_SALA = 600;

  // 1) curva de aprendizado: treina de 2 jeitos (do zero e partindo da regra antiga) em salas sempre novas
  Aprendiz frio(true, true), quente(true, true), fixo(true, true);
  frio.ag.zerar(false);
  quente.ag.zerar(true);
  fixo.ag.zerar(true);
  fixo.ag.adaptar_margem = false;  // mesmo treino, mas o freio fica sempre a 20 cm
  frio.ag.semear(11 + semente);
  quente.ag.semear(22 + semente);
  fixo.ag.semear(33 + semente);
  for (int i = 0; i < passos_treino / POR_SALA; i++) {
    imprimir("treino", "do_zero", i, sala(frio, POR_SALA, uniforme(0, 1) < 0.35f), frio.ag.epsilon());
    imprimir("treino", "com_palpite_inicial", i, sala(quente, POR_SALA, uniforme(0, 1) < 0.35f), quente.ag.epsilon());
    imprimir("treino", "margem_fixa", i, sala(fixo, POR_SALA, uniforme(0, 1) < 0.35f), fixo.ag.epsilon());
  }

  printf("margem,do_zero,%.1f,%.1f\n", frio.ag.m.freio_cm[0], frio.ag.m.freio_cm[1]);
  printf("margem,com_palpite_inicial,%.1f,%.1f\n", quente.ag.m.freio_cm[0], quente.ag.m.freio_cm[1]);
  printf("margem,margem_fixa,%.1f,%.1f\n", fixo.ag.m.freio_cm[0], fixo.ag.m.freio_cm[1]);

  // 2) avaliação em salas que ele nunca viu (sem explorar e sem aprender), contra as outras políticas
  Aleatoria aleatoria;
  Regras regras(false), regras_novas(true);
  Suave suave;
  Aprendiz a_frio(false, false), a_quente(false, false), a_fixo(false, false), nada(false, false);
  a_frio.ag = frio.ag;
  a_quente.ag = quente.ag;
  a_fixo.ag = fixo.ag;
  nada.ag.zerar(false);  // agente sem treino nenhum, só a tabela zerada
  struct { const char* nome; Politica* p; } todos[] = {
      {"aleatoria", &aleatoria}, {"regras_antigas", &regras}, {"regras_com_detector", &regras_novas}, {"autonomo_suave", &suave}, {"agente_sem_treino", &nada},
      {"agente_do_zero", &a_frio}, {"agente_margem_fixa", &a_fixo}, {"agente_com_palpite", &a_quente}};
  for (auto& t : todos) {
    gen.seed(1000);  // as mesmas salas para todos
    for (int i = 0; i < 100; i++) imprimir("avaliacao", t.nome, i, sala(*t.p, POR_SALA));
    gen.seed(2000);
    for (int i = 0; i < 100; i++) imprimir("apertada", t.nome, i, sala(*t.p, POR_SALA, true));
  }
  return 0;
}
