// Carro robô ChuvaRota: dirigido pelo app Dabble (Bluetooth) ou sozinho; desvia de obstáculos, mede a luz com o LDR
// e classifica a situação com um modelo TinyML. Placa: ESP32 DevKit (pacote "esp32" 3.x; partição "Huge APP").
#include <Arduino.h>
#include "config.h"
#if USAR_DABBLE
#define CUSTOM_SETTINGS
#define INCLUDE_GAMEPAD_MODULE
#include <DabbleESP32.h>  // biblioteca "DabbleESP32" (app Dabble)
#include "esp_bt.h"
#endif
#include <HTTPClient.h>
#include <Preferences.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>

#include "aprendizado.h"
#include "caracteristicas.h"
#include "modelo_tinyml.h"
#include "logica.h"

// motores (ponte H L298N)
const int ENA = 25, IN1 = 26, IN2 = 27;
const int ENB = 13, IN3 = 32, IN4 = 33;
// sensores e saídas
const int TRIG = 5, ECHO = 18;  // sensor a 5 V: o ECHO passa por um divisor de tensão (5 V -> 3,3 V); sensor a 3,3 V: ligado direto
const int LDR = 34;
const int BUZZER = 23, LED = 2;

// ajustes internos (não precisam mudar)
const float PASSO_RAMPA = 0.2f;                // o quanto cada roda pode mudar por ciclo (0 a 1): aceleração suave
const int SENSOR_INTERVALO_MS = 5;             // pausa entre uma leitura e outra do sensor, para o eco anterior sumir
const float SENSOR_DIST_EIXO_CM = 8;           // distância do sensor ao eixo do carrinho (usada no comando g)

const char* NOMES[] = {"ok", "pouca_luz", "obstaculo", "escuro_e_obstaculo", "luz_piscando", "objeto_se_aproximando"};
const unsigned long PERIODO_MS = 100;  // o modelo foi treinado com uma leitura a cada 100 ms

struct Leitura {
  float luz;
  float dist;
  int classe;
};
volatile Leitura atual = {1, 200, 0};
volatile bool urgente = false;
FiltroDistancia filtro;  // sem eco logo depois de uma leitura perto = obstáculo colado, e não caminho livre
enum Modo { MANUAL = 0, AUTONOMO = 1, TREINO = 2, IA = 3 };
const char* NOMES_MODO[] = {"manual (Dabble)", "autônomo (regras + TinyML)", "treino (aprendendo por tentativa e erro)", "IA (usa o que aprendeu)"};
int modo = USAR_DABBLE ? MODO_INICIAL : (MODO_INICIAL > 0 ? MODO_INICIAL : AUTONOMO);  // sem Dabble não há como dirigir: começa sozinho
RampaMotor rampa;          // aceleração suave dos motores
Navegador navegador;       // modo autônomo: velocidade pela distância e curvas antes da parede
DetectorTravado detector;  // modo autônomo: mandou andar e a distância não mudou = preso raspando em uma parede
Agente agente;             // aprendizado por reforço (modos treino e IA): a tabela fica na memória flash
MetaTreino meta;           // meta do treino, definida pelo painel (cfg meta_passos / meta_minutos)
unsigned long treino_inicio_ms = 0;  // quando esta sessão de treino começou
bool painel = false;       // true = imprime uma linha de telemetria por ciclo para o painel (comando "painel 1")
int acao_atual = -1;       // última ação do agente: 0 a 4; 5 = freio de segurança; 6 = fuga; -1 = nenhuma (manual ou autônomo)
bool explorando_atual = false;
int rotulo_coleta = 0;     // MODO_COLETA: classe digitada no Monitor Serial (0 a 5)

// janela das últimas leituras (a mais antiga primeiro)
float janela_luz[JANELA], janela_dist[JANELA];
int preenchidas = 0;

// calibração automática do LDR: o mais escuro e o mais claro já vistos, salvos na memória flash
Preferences memoria;
float ldr_min = LDR_ESCURO, ldr_max = LDR_CLARO;
bool calibracao_mudou = false;

void motor(int esq, int dir) {
  if (INVERTE_ESQUERDO) esq = -esq;
  if (INVERTE_DIREITO) dir = -dir;
  digitalWrite(IN1, esq > 0);
  digitalWrite(IN2, esq < 0);
  digitalWrite(IN3, dir > 0);
  digitalWrite(IN4, dir < 0);
  ledcWrite(ENA, esq == 0 ? 0 : constrain(max(abs(esq), PWM_MINIMO), 0, 255));
  ledcWrite(ENB, dir == 0 ? 0 : constrain(max(abs(dir), PWM_MINIMO), 0, 255));
}

void parar() {
  rampa.parar();
  motor(0, 0);
}

// manda as rodas em rampa (o motor acelera e freia aos poucos, em vez de pular de 0 a 180)
void motor_suave(Rodas alvo) {
  Rodas r = rampa.seguir(alvo, PASSO_RAMPA);
  motor(pwm_de(r.esq, PWM_MINIMO, VELOCIDADE_NORMAL), pwm_de(r.dir, PWM_MINIMO, VELOCIDADE_NORMAL));
}

void apitar(int vezes) {
  for (int i = 0; i < vezes; i++) {
    digitalWrite(BUZZER, HIGH);
    delay(120);
    digitalWrite(BUZZER, LOW);
    delay(120);
  }
}

// uma leitura do HC-SR04, só com o tempo do eco e a velocidade do som (sem a calibração do config.h)
float uma_distancia_bruta() {
  digitalWrite(TRIG, LOW);
  delayMicroseconds(3);
  digitalWrite(TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG, LOW);
  long us = pulseIn(ECHO, HIGH, 12000);
  delay(SENSOR_INTERVALO_MS);  // deixa o eco anterior sumir antes da próxima leitura
  return us == 0 ? SEM_ECO_CM : min(SEM_ECO_CM, us * cm_por_us(TEMPERATURA_C));  // sem eco = nada à frente
}

float uma_distancia() {
  float cm = uma_distancia_bruta();
  if (cm >= SEM_ECO_CM - 0.5f) return SEM_ECO_CM;
  return constrain(cm * SENSOR_ESCALA + SENSOR_OFFSET_CM, 0.0f, SEM_ECO_CM);
}

// 3 leituras; se não concordam, até 5. Média das que concordam, sem as leituras falsas (ver sensor.h)
float distancia() {
  return medir_adaptativo([] { return uma_distancia(); }, 3, 5);
}

// 7 leituras: para quando o carrinho está parado e dá tempo de medir com calma (depois de frear, nas calibrações)
float distancia_precisa() {
  return medir_adaptativo([] { return uma_distancia(); }, 7, 7);
}

float luz() {
  long soma = 0;
  for (int i = 0; i < 8; i++) soma += analogRead(LDR);
  float bruto = soma / 8.0f;
  if (bruto < ldr_min) { ldr_min = bruto; calibracao_mudou = true; }
  if (bruto > ldr_max) { ldr_max = bruto; calibracao_mudou = true; }
  float faixa = ldr_max - ldr_min;
  if (faixa < 800) return constrain((bruto - LDR_ESCURO) / (float)(LDR_CLARO - LDR_ESCURO), 0.0f, 1.0f);  // ainda sem faixa confiável
  return constrain((bruto - ldr_min) / faixa, 0.0f, 1.0f);
}

void salvar_calibracao() {
  if (!calibracao_mudou) return;
  memoria.putFloat("ldr_min", ldr_min);
  memoria.putFloat("ldr_max", ldr_max);
  calibracao_mudou = false;
}

// Fuga de um canto: ré maior e giro para o lado (lado: 1 = direita, -1 = esquerda). Só quando está preso; no resto o carrinho curva.
void fuga(int lado) {
  parar();
  delay(100);
  motor(-VELOCIDADE_LENTA, -VELOCIDADE_LENTA);
  delay(500);
  int v = VELOCIDADE_LENTA + 30;
  motor(lado * v, -lado * v);
  delay(700);
  parar();
  filtro.esquecer();
  detector.esquecer();
  navegador.esquecer();
  preenchidas = 0;
}

// ---- modos treino e IA (aprendizado por reforço, ver aprendizado.h) --------------------------------------------------------------
void salvar_agente() { memoria.putBytes("agente", &agente.m, sizeof(agente.m)); }

void carregar_agente() {
  agente.semear(esp_random());
  if (memoria.getBytesLength("agente") == sizeof(agente.m)) {
    memoria.getBytes("agente", &agente.m, sizeof(agente.m));
    if (agente.m.versao != VERSAO_MEMORIA) agente.zerar();  // memória de uma versão antiga: recomeça
  }
  Serial.printf("aprendizado: %u passos de treino já feitos (exploração %.0f%%, distância do freio %.0f cm)\n", (unsigned)agente.m.passos, agente.epsilon() * 100,
                agente.m.freio_cm[0]);
}

// o que o robô faz em cada ação do agente: a velocidade acompanha a distância (mais devagar perto do obstáculo) e vai em rampa
void executar_acao(Acao a, float d, bool escuro) {
  motor_suave(rodas_da_acao(a, d, agente.m.freio_cm[0], escuro));
}

void imprimir_bloco() {
  const Bloco& b = agente.m.historico[(agente.m.blocos - 1) % N_BLOCOS];
  Serial.printf("treino: bloco %u | passos %u | exploração %.0f%% | nota média %.2f | quase-batidas %u | freios %u | distância do freio %u cm\n", (unsigned)agente.m.blocos,
                (unsigned)agente.m.passos, agente.epsilon() * 100, b.recompensa_media, b.quase_batidas, b.freios, b.margem_cm);
}

// um ciclo dos modos treino e IA: o agente escolhe a ação; o freio de segurança e a fuga valem mais que ele
void passo_ia(float d, bool escuro, bool treinando) {
  Decisao x = agente.decidir(d, treinando, treinando, escuro);
  digitalWrite(LED, x.explorou);  // acende nos ciclos em que ele testa uma ação aleatória (explorando)
  acao_atual = x.escapar ? 6 : (x.freio ? 5 : (int)x.acao);
  explorando_atual = x.explorou;
  if (x.escapar) {  // preso: ré maior e giro para o lado
    Serial.println("preso: fuga");
    fuga(x.lado);
  } else if (x.freio) {  // chegou perto demais: freio de segurança (um erro, que o agente aprende a evitar)
    parar();
    delay(80);  // espera o carrinho parar de verdade
    float depois = distancia_precisa();  // quanto espaço sobrou entre o carrinho parado e o obstáculo
    agente.freou(depois, treinando);  // ajusta a distância do freio: parou perto demais = freia mais longe; sobrou espaço = pode chegar mais perto
    if (agente.margem_depois != agente.margem_antes)
      Serial.printf("freio: parou a %.0f cm do obstáculo | distância do freio %.0f -> %.0f cm\n", depois, agente.margem_antes, agente.margem_depois);
    if (TREINO_APITAR_ERRO && treinando) {
      digitalWrite(BUZZER, HIGH);
      delay(40);
      digitalWrite(BUZZER, LOW);
    }
    motor(-VELOCIDADE_LENTA, -VELOCIDADE_LENTA);
    delay(250);
    parar();
    filtro.esquecer();
  } else {
    executar_acao(x.acao, d, escuro);
  }
  if (agente.fechou_bloco) {
    agente.fechou_bloco = false;
    imprimir_bloco();
  }
}

// troca o modo: freia, esquece as leituras de antes e apita o número do modo (1 manual, 2 autônomo, 3 treino, 4 IA)
void trocar_modo(int novo) {
  if (modo == TREINO) salvar_agente();
  modo = novo;
  parar();
  preenchidas = 0;
  filtro.esquecer();
  detector.esquecer();
  navegador.esquecer();
  agente.recomecar();
  acao_atual = -1;
  explorando_atual = false;
  if (novo == TREINO) treino_inicio_ms = millis();
  apitar(novo + 1);
  Serial.printf("modo: %s\n", NOMES_MODO[novo]);
}

// A meta do treino foi atingida? (total de passos ou tempo desta sessão, o que vier primeiro)
bool meta_atingida() {
  if (meta.passos > 0 && agente.m.passos >= meta.passos) return true;
  if (meta.minutos > 0 && (millis() - treino_inicio_ms) / 60000.0f >= meta.minutos) return true;
  return false;
}

// o que ele aprendeu: a melhor ação para cada situação (depois de uma ação de andar)
void imprimir_politica() {
  static const char* TENDENCIAS[] = {"aproximando", "estável", "afastando"};
  float mg = agente.m.freio_cm[0], lim[5] = {mg, mg + RL_PERIGO_EXTRA_CM, mg + 30, mg + 70, 190};  // as faixas andam com a distância do freio
  Serial.printf("política aprendida (%u passos de treino; distância do freio: %.0f cm andando rápido, %.0f cm devagar). Melhor ação quando a distância está...\n",
                (unsigned)agente.m.passos, agente.m.freio_cm[0], agente.m.freio_cm[1]);
  for (int f = 0; f < N_FAIXAS; f++) {
    char faixa[24];
    if (f == 0) snprintf(faixa, sizeof(faixa), "< %.0f cm (freio)", lim[0]);
    else if (f == N_FAIXAS - 1) snprintf(faixa, sizeof(faixa), "sem eco");
    else snprintf(faixa, sizeof(faixa), "%.0f a %.0f cm", lim[f - 1], lim[f]);
    for (int t = 0; t < N_TENDENCIAS; t++) {
      int s = (f * N_TENDENCIAS + t) * N_GIROS;  // última ação = andou
      Serial.printf("  %-18s %-12s -> %s\n", faixa, TENDENCIAS[t], nome_acao(agente.melhor_acao(s)));
    }
  }
  // as mesmas informações, em linhas para o painel: POL,faixa,tendência,ação (0 seguir, 1 curva esq, 2 curva dir, 3 girar esq, 4 girar dir)
  for (int f = 0; f < N_FAIXAS; f++)
    for (int t = 0; t < N_TENDENCIAS; t++) Serial.printf("POL,%d,%d,%d\n", f, t, (int)agente.melhor_acao((f * N_TENDENCIAS + t) * N_GIROS));
  Serial.printf("POL_FREIO,%.0f,%.0f\n", agente.m.freio_cm[0], agente.m.freio_cm[1]);
}

// ---- painel: configuração e estado em linhas "CFG nome=valor" -------------------------------------------------------------------
void descrever_config() {
  Serial.printf("CFG eps_inicial=%.3f\nCFG eps_minimo=%.3f\nCFG eps_tau=%.0f\nCFG ciclos_por_acao=%d\nCFG margem_min=%.0f\n", agente.eps_inicial, agente.eps_minimo,
                agente.eps_tau, agente.ciclos_por_acao, agente.margem_min);
  Serial.printf("CFG adaptar_margem=%d\nCFG palpite=%d\nCFG meta_passos=%u\nCFG meta_minutos=%.0f\n", agente.adaptar_margem, agente.palpite, (unsigned)meta.passos, meta.minutos);
  Serial.printf("ESTADO modo=%d passos=%u eps=%.3f margem=%.0f margem_lento=%.0f painel=%d\n", modo, (unsigned)agente.m.passos, agente.epsilon(), agente.m.freio_cm[0],
                agente.m.freio_cm[1], painel);
}

// a curva de aprendizado, em CSV (copie do Monitor Serial): o treino melhora se as quase-batidas e os freios caem
void imprimir_historico() {
  uint32_t total = agente.m.blocos, primeiro = total > N_BLOCOS ? total - N_BLOCOS : 0;
  Serial.printf("bloco,passos_de_treino,nota_media,quase_batidas,freios,distancia_do_freio_cm  (cada bloco = %d passos)\n", (int)PASSOS_POR_BLOCO);
  for (uint32_t i = primeiro; i < total; i++) {
    const Bloco& b = agente.m.historico[i % N_BLOCOS];
    Serial.printf("%u,%u,%.3f,%u,%u,%u\n", (unsigned)(i + 1), (unsigned)((i + 1) * PASSOS_POR_BLOCO), b.recompensa_media, b.quase_batidas, b.freios, b.margem_cm);
  }
}

void enviar(Leitura l) {
  if (WiFi.status() != WL_CONNECTED) return;
  if (ESP.getMaxAllocHeap() < 25000) {  // sem validar o certificado o TLS precisa de bem menos memória
    Serial.printf("envio adiado: pouca memória livre (%u bytes)\n", ESP.getMaxAllocHeap());
    return;
  }
  WiFiClientSecure cliente;
  cliente.setInsecure();  // criptografa, mas não confere o certificado: o ESP32 recusava a cadeia do Azure (erro -9984)
  cliente.setHandshakeTimeout(30);  // a cadeia de certificados do Azure é pesada e o Bluetooth divide a antena: dá tempo
  HTTPClient http;
  http.setConnectTimeout(15000);
  http.setTimeout(15000);
  if (!http.begin(cliente, URL_MVP)) return;
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Token", TOKEN_ROBO);
  char corpo[160];
  snprintf(corpo, sizeof(corpo), "{\"luz_pct\":%.0f,\"distancia_cm\":%.0f,\"situacao\":\"%s\"}", l.luz * 100, l.dist, NOMES[l.classe]);
  int codigo = http.POST(corpo);
  Serial.printf("envio: %s -> %d\n", corpo, codigo);
  if (codigo <= 0) {  // explica a falha: erro do TLS, memória e hora
    char erro[100] = "";
    int e = cliente.lastError(erro, sizeof(erro));
    Serial.printf("  falha: %s | erro TLS %d (%s) | memória livre %u, maior bloco %u | hora %ld | Wi-Fi %d dBm\n", HTTPClient::errorToString(codigo).c_str(), e, erro, ESP.getFreeHeap(), ESP.getMaxAllocHeap(), (long)time(nullptr), WiFi.RSSI());
  }
  http.end();
}

// o envio roda em outra tarefa para não deixar o robô parado esperando a rede
void tarefa_rede(void*) {
  unsigned long ultimo = 0;
  bool hora_pedida = false;
  for (;;) {
    if (WiFi.status() != WL_CONNECTED) {
      WiFi.reconnect();
      vTaskDelay(5000 / portTICK_PERIOD_MS);
      continue;
    }
    if (!hora_pedida) {  // sem a data certa o ESP32 acha que é 1970 e recusa o certificado do MVP
      configTime(0, 0, "pool.ntp.org", "time.google.com");
      hora_pedida = true;
    }
    if (time(nullptr) < 1700000000) {
      vTaskDelay(500 / portTICK_PERIOD_MS);
      continue;
    }
    if (urgente || millis() - ultimo > 5000) {
      urgente = false;
      ultimo = millis();
      Leitura copia = {atual.luz, atual.dist, atual.classe};  // shortcut: sem trava; no pior caso lê um valor de 100 ms atrás
      enviar(copia);
    }
    vTaskDelay(200 / portTICK_PERIOD_MS);
  }
}

#if USAR_DABBLE
// seta para cima = frente, baixo = trás, esquerda/direita = vira para o lado (modo digital); no modo joystick, ângulo e raio (0 a 7)
void dirigir_manual() {
  Comando c = ler_comando(GamePad.isUpPressed(), GamePad.isDownPressed(), GamePad.isLeftPressed(), GamePad.isRightPressed(),
                          GamePad.getAngle(), GamePad.getRadius(), INVERTE_JOYSTICK_Y);
  if (c.frente > 0 && atual.dist < DIST_MINIMA_CM) c.frente = 0;  // proteção: não deixa bater de frente
  int esq, dir;
  misturar_rodas(c.frente, c.giro, VELOCIDADE_NORMAL, &esq, &dir);
  motor(esq, dir);
}

void botoes() {
  static bool triangulo_antes = false, circulo_antes = false, start_antes = false;
  bool triangulo = GamePad.isTrianglePressed(), circulo = GamePad.isCirclePressed(), start = GamePad.isStartPressed();
  if (triangulo && !triangulo_antes) trocar_modo(modo == AUTONOMO ? MANUAL : AUTONOMO);  // triângulo: anda sozinho (regras + TinyML)
  if (circulo && !circulo_antes) trocar_modo(modo == TREINO ? MANUAL : TREINO);          // círculo: modo treino (aprende)
  if (start && !start_antes) trocar_modo(modo == IA ? MANUAL : IA);                      // start: modo IA (usa o que aprendeu)
  triangulo_antes = triangulo;
  circulo_antes = circulo;
  start_antes = start;
  if (GamePad.isCrossPressed() && modo != MANUAL) trocar_modo(MANUAL);  // X: freia e volta para o controle manual
  digitalWrite(BUZZER, GamePad.isSquarePressed());  // quadrado: buzina
}
#endif

// ---- calibração do carrinho (comandos no Monitor Serial, com o carrinho no modo manual) ---------------------------------------------
void esperar_tecla(const char* mensagem) {
  Serial.println(mensagem);
  while (Serial.available()) Serial.read();
  while (!Serial.available()) delay(10);
  delay(50);
  while (Serial.available()) Serial.read();
}

void estatistica(const float* v, int n, float* media, float* desvio, int* sem_eco) {
  float soma = 0, soma2 = 0;
  int k = 0;
  *sem_eco = 0;
  for (int i = 0; i < n; i++) {
    if (v[i] >= SEM_ECO_CM - 0.5f) {
      (*sem_eco)++;
      continue;
    }
    soma += v[i];
    soma2 += v[i] * v[i];
    k++;
  }
  *media = k ? soma / k : 0;
  *desvio = k > 1 ? sqrtf(fmaxf(0, soma2 / k - *media * *media)) : 0;
}

// p: o quanto o sensor oscila medindo um alvo parado, com uma leitura, com a mediana de 3 (antigo) e com as 5 leituras com descarte (novo)
void teste_precisao() {
  esperar_tecla("Precisão: ponha uma parede ou caixa lisa de frente para o sensor, a uns 50 cm, SEM mexer nela. Envie qualquer tecla.");
  float bruto[90], mediana3[30], novo[18];
  for (int i = 0; i < 90; i++) bruto[i] = uma_distancia();
  for (int g = 0; g < 30; g++) {
    float a = bruto[3 * g], b = bruto[3 * g + 1], c = bruto[3 * g + 2];
    mediana3[g] = max(min(a, b), min(max(a, b), c));
  }
  for (int g = 0; g < 18; g++) novo[g] = combinar_leituras(&bruto[5 * g], 5);
  float m, d;
  int se;
  estatistica(bruto, 90, &m, &d, &se);
  Serial.printf("  uma leitura:            média %.1f cm | oscilação (desvio) %.2f cm | sem eco %d de 90\n", m, d, se);
  estatistica(mediana3, 30, &m, &d, &se);
  Serial.printf("  mediana de 3 (antigo):  média %.1f cm | oscilação (desvio) %.2f cm | sem eco %d de 30\n", m, d, se);
  estatistica(novo, 18, &m, &d, &se);
  Serial.printf("  5 com descarte (novo):  média %.1f cm | oscilação (desvio) %.2f cm | sem eco %d de 18\n", m, d, se);
  Serial.println("Se a média não bate com a régua, rode o comando k para calibrar escala e offset.");
}

// k: mede a parede a 20, 50 e 100 cm (com régua) e calcula SENSOR_ESCALA e SENSOR_OFFSET_CM
void calibrar_sensor() {
  const float alvos[3] = {20, 50, 100};
  float medido[3];
  for (int i = 0; i < 3; i++) {
    char mensagem[140];
    snprintf(mensagem, sizeof(mensagem), "Calibração do sensor (%d de 3): parede lisa, de frente, a EXATOS %.0f cm do sensor (meça com régua). Envie qualquer tecla.", i + 1, alvos[i]);
    esperar_tecla(mensagem);
    float v[15];
    for (int j = 0; j < 15; j++) v[j] = uma_distancia_bruta();
    medido[i] = combinar_leituras(v, 15);
    Serial.printf("  o sensor mediu %.1f cm\n", medido[i]);
    if (medido[i] >= SEM_ECO_CM - 0.5f) {
      Serial.println("  sem eco: confira a parede e o sensor e rode k de novo");
      return;
    }
  }
  float escala, offset;
  if (!ajustar_reta(medido, alvos, 3, &escala, &offset)) {
    Serial.println("não deu para calcular: as 3 medidas ficaram iguais");
    return;
  }
  Serial.println("Cole no config.h (substituindo os valores de SENSOR_ESCALA e SENSOR_OFFSET_CM) e grave de novo:");
  Serial.printf("#define SENSOR_ESCALA %.3ff\n#define SENSOR_OFFSET_CM %.1ff\n", escala, offset);
  for (int i = 0; i < 3; i++) Serial.printf("  com isso: %.0f cm -> %.1f cm\n", alvos[i], medido[i] * escala + offset);
}

// v: anda 0,8 s de frente para uma parede e mede quanto se aproximou
void teste_velocidade() {
  esperar_tecla("Velocidade: carrinho no chão, de frente para uma parede lisa a uns 100 cm, com o caminho livre (ele anda uns 30 cm). Envie qualquer tecla.");
  const int tempo_ms = 800;
  const int pwm[2] = {VELOCIDADE_NORMAL, VELOCIDADE_LENTA};
  const char* nomes[2] = {"NORMAL", "LENTO"};
  float resultado[2] = {0, 0};
  for (int i = 0; i < 2; i++) {
    float antes = distancia_precisa();
    if (antes < 70 || antes >= SEM_ECO_CM - 0.5f) {
      Serial.printf("  preciso de 70 a 190 cm de parede à frente (medi %.0f). Afaste o carrinho e rode v de novo\n", antes);
      return;
    }
    motor(pwm[i], pwm[i]);
    delay(tempo_ms);
    parar();
    delay(400);
    float depois = distancia_precisa();
    resultado[i] = (antes - depois) / (tempo_ms / 1000.0f);
    Serial.printf("  %s (PWM %d): foi de %.0f para %.0f cm = %.0f cm/s\n", nomes[i], pwm[i], antes, depois, resultado[i]);
    if (i == 0) esperar_tecla("  Leve o carrinho de volta a uns 100 cm da parede e envie qualquer tecla.");
  }
  Serial.println("Cole no config.h (só a simulação do treino usa) :");
  Serial.printf("#define CARRINHO_CM_S_NORMAL %.0f\n#define CARRINHO_CM_S_LENTO %.0f\n", resultado[0], resultado[1]);
}

// g: gira 0,3 s de frente para uma parede e calcula o ângulo pela mudança da distância
void teste_giro() {
  esperar_tecla("Giro: carrinho no chão, de frente (reto) para uma parede lisa e larga, a uns 50 cm. Ele vai girar um pouco no lugar. Envie qualquer tecla.");
  float antes = distancia_precisa();
  if (antes < 25 || antes > 120) {
    Serial.printf("  preciso da parede entre 25 e 120 cm (medi %.0f). Ajuste e rode g de novo\n", antes);
    return;
  }
  const int tempo_ms = 300;
  int v = VELOCIDADE_LENTA + 30;  // o mesmo giro das manobras
  motor(v, -v);
  delay(tempo_ms);
  parar();
  delay(400);
  float depois = distancia_precisa();
  if (depois >= SEM_ECO_CM - 0.5f) {
    Serial.println("  o sensor perdeu a parede (girou demais ou a parede é pequena). Use uma parede maior e rode g de novo");
    return;
  }
  float graus = angulo_giro_graus(antes, depois, SENSOR_DIST_EIXO_CM);
  Serial.printf("  a parede foi de %.0f para %.0f cm: girou uns %.0f graus em %d ms = %.0f graus/s\n", antes, depois, graus, tempo_ms, graus / (tempo_ms / 1000.0f));
  if (graus < 8 || graus > 60) Serial.println("  resultado pouco confiável (vale de 10 a 60 graus): ajuste a distância da parede e repita");
  Serial.printf("Cole no config.h (só a simulação do treino usa) :\n#define CARRINHO_GRAUS_S %.0f\n", graus / (tempo_ms / 1000.0f));
}

void ajuda() {
  Serial.println("comandos: a treino | u IA | x modo manual | q política aprendida | e curva de aprendizado | z apaga o aprendizado | i/r calibração do LDR");
  Serial.println("          p precisão do sensor | k calibrar o sensor | v medir a velocidade | g medir o giro (estes 4 só no modo manual)");
  Serial.println("painel:   painel 1 (telemetria) | modo manual/autonomo/treino/ia | cfg? (mostra os ajustes) | cfg nome valor");
  Serial.println("          nomes: eps_inicial eps_minimo eps_tau ciclos_por_acao margem_min adaptar_margem palpite meta_passos meta_minutos");
}

// um comando de uma letra (os de sempre)
void executar_comando(char c) {
  if (c == 'r') {  // apaga a calibração do LDR
    ldr_min = LDR_ESCURO;
    ldr_max = LDR_CLARO;
    calibracao_mudou = true;
    salvar_calibracao();
    Serial.println("calibração do LDR apagada");
  } else if (c == 'i') {
    Serial.printf("LDR: mais escuro visto %.0f, mais claro visto %.0f\n", ldr_min, ldr_max);
  } else if (c == 'a') {  // liga e desliga o modo treino (sem precisar do Dabble)
    trocar_modo(modo == TREINO ? MANUAL : TREINO);
  } else if (c == 'u') {  // liga e desliga o modo IA
    trocar_modo(modo == IA ? MANUAL : IA);
  } else if (c == 'x') {  // volta ao modo manual (o carrinho para)
    trocar_modo(MANUAL);
  } else if (c == 'q') {
    imprimir_politica();
  } else if (c == 'e') {
    imprimir_historico();
  } else if (c == 'z') {  // apaga o que ele aprendeu (use ao levar o carrinho para um ambiente novo)
    agente.zerar(agente.palpite);
    salvar_agente();
    Serial.println("aprendizado apagado");
  } else if (c == 'p' || c == 'k' || c == 'v' || c == 'g') {  // calibrações: bloqueiam o robô por alguns segundos
    if (modo != MANUAL) {
      Serial.println("estes comandos só funcionam no modo manual (aperte X no Dabble)");
    } else if (c == 'p') {
      teste_precisao();
    } else if (c == 'k') {
      calibrar_sensor();
    } else if (c == 'v') {
      teste_velocidade();
    } else {
      teste_giro();
    }
  } else if (c == '?') {
    ajuda();
  }
#if MODO_COLETA
  if (c >= '0' && c <= '5') rotulo_coleta = c - '0';
#endif
}

// uma linha completa: uma letra (comando de sempre) ou um comando do painel (cfg, modo, painel)
void executar_linha(const char* linha) {
  LinhaSerial l = interpretar_linha(linha);
  switch (l.tipo) {
    case LinhaSerial::VAZIA: break;
    case LinhaSerial::LETRA: executar_comando(l.letra); break;
    case LinhaSerial::CFG_LISTA: descrever_config(); break;
    case LinhaSerial::CFG: {
      const char* erro;
      if (aplicar_config(agente, meta, l.nome, l.valor, &erro)) Serial.printf("CFG %s=%g\n", l.nome, l.valor);
      else Serial.printf("CFG erro: %s (%s)\n", l.nome, erro);
      break;
    }
    case LinhaSerial::MODO:
      if (!strcmp(l.nome, "manual")) trocar_modo(MANUAL);
      else if (!strcmp(l.nome, "autonomo")) trocar_modo(AUTONOMO);
      else if (!strcmp(l.nome, "treino")) trocar_modo(TREINO);
      else if (!strcmp(l.nome, "ia")) trocar_modo(IA);
      else Serial.printf("modo desconhecido: %s\n", l.nome);
      break;
    case LinhaSerial::PAINEL:
      painel = l.valor > 0.5f;
      Serial.printf("painel: telemetria %s\n", painel ? "ligada" : "desligada");
      break;
    default: Serial.printf("comando desconhecido: %s (envie ? para a lista)\n", linha);
  }
}

// lê o que chegou pela porta serial: linhas terminadas em Enter ou, para os comandos de uma letra, a letra sozinha (sem Enter)
void comandos_serial() {
  static char linha[48];
  static int n = 0;
  static unsigned long ultimo = 0;
  while (Serial.available()) {
    char c = Serial.read();
    ultimo = millis();
    if (c == '\n' || c == '\r') {
      if (n) {
        linha[n] = 0;
        n = 0;
        executar_linha(linha);
      }
      continue;
    }
    if (n < (int)sizeof(linha) - 1) linha[n++] = c;
  }
  if (n == 1 && millis() - ultimo > 40) {  // uma letra sem Enter (Monitor Serial com "No Line Ending")
    linha[1] = 0;
    n = 0;
    executar_linha(linha);
  }
}

void setup() {
  Serial.begin(115200);
  int saidas[] = {IN1, IN2, IN3, IN4, TRIG, BUZZER, LED};
  for (int p : saidas) pinMode(p, OUTPUT);
  pinMode(ECHO, INPUT);
  ledcAttach(ENA, 1000, 8);
  ledcAttach(ENB, 1000, 8);
  analogSetPinAttenuation(LDR, ADC_11db);
  parar();

  memoria.begin("robo", false);
  ldr_min = memoria.getFloat("ldr_min", LDR_ESCURO);
  ldr_max = memoria.getFloat("ldr_max", LDR_CLARO);
  carregar_agente();

#if MODO_COLETA
  Serial.println("luz,distancia_cm,classe  (digite 0 a 5 para escolher a classe)");
#else
#if USAR_DABBLE
  // o Dabble só usa Bluetooth de baixa energia: devolve a memória do Bluetooth clássico para o HTTPS do envio
  esp_bt_controller_mem_release(ESP_BT_MODE_CLASSIC_BT);
  Dabble.begin(NOME_BLUETOOTH);
#endif
  Serial.printf("memória livre na partida: %u bytes (maior bloco %u)\n", ESP.getFreeHeap(), ESP.getMaxAllocHeap());
#if ENVIAR_AO_MVP
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_SENHA);
  xTaskCreatePinnedToCore(tarefa_rede, "rede", 20480, NULL, 1, NULL, 0);
#else
  Serial.println("envio ao MVP desligado (com o Bluetooth do Dabble não sobra memória para o HTTPS). Para enviar: USAR_DABBLE 0 no config.h");
#endif
  apitar(1);  // pronto
#endif
}

void loop() {
  static unsigned long proxima = 0, ultimo_salvar = 0, ultima_luz_piscando = 0;
  static unsigned long ultimo_alerta = 0;
  static int candidata = 0, repeticoes = 0, em_vigor = 0;
  comandos_serial();
#if !MODO_COLETA && USAR_DABBLE
  Dabble.processInput();
  botoes();
  if (modo == MANUAL) dirigir_manual();
#endif
  if (millis() < proxima) return;
  proxima = millis() + PERIODO_MS;

  float d = filtro.filtrar(distancia(), 2 * DIST_MINIMA_CM, DIST_MINIMA_CM - 1);
  float l = luz();
  if (millis() - ultimo_salvar > 60000) {
    salvar_calibracao();
    if (modo == TREINO) salvar_agente();
    ultimo_salvar = millis();
  }

#if MODO_COLETA
  Serial.printf("%.3f,%.1f,%d\n", l, d, rotulo_coleta);
  return;
#endif

  // entra uma leitura nova na janela
  if (preenchidas == JANELA) {
    for (int i = 1; i < JANELA; i++) {
      janela_luz[i - 1] = janela_luz[i];
      janela_dist[i - 1] = janela_dist[i];
    }
    preenchidas--;
  }
  janela_luz[preenchidas] = l;
  janela_dist[preenchidas] = d;
  preenchidas++;

  int c = (d < 30) ? ((l < 0.30f) ? 3 : 2) : ((l < 0.30f) ? 1 : 0);  // regra simples enquanto a janela enche
  if (preenchidas == JANELA) {
    float x[N_ENTRADAS];
    caracteristicas(janela_luz, janela_dist, x);
    int nova = classificar(x);
    // só troca de comportamento se a mesma classe aparecer 2 vezes seguidas; situações de risco valem na hora
    repeticoes = (nova == candidata) ? repeticoes + 1 : 1;
    candidata = nova;
    bool risco = (nova == 2 || nova == 3 || nova == 5);
    if (risco || repeticoes >= 2) em_vigor = nova;
    c = em_vigor;
  }
  if (d < DIST_MINIMA_CM) c = (l < 0.30f) ? 3 : 2;  // regra de segurança acima do modelo

  atual.luz = l;
  atual.dist = d;
  atual.classe = c;
  digitalWrite(LED, c == 1 || c == 3 || c == 4);
  // telemetria para o painel: tempo, distância, luz, classe, modo, ação, explorando, freio, passos de treino, exploração
  if (painel) Serial.printf("~%lu,%.1f,%.0f,%d,%d,%d,%d,%.0f,%u,%.3f\n", millis(), d, l * 100, c, modo, acao_atual, explorando_atual ? 1 : 0, agente.m.freio_cm[0],
                            (unsigned)agente.m.passos, agente.epsilon());

  if (modo != AUTONOMO) {  // manual, treino ou IA: o robô observa e avisa (e, no treino e na IA, o agente dirige)
    if (c == 3 && millis() - ultimo_alerta > 10000) {
      ultimo_alerta = millis();
      if (modo == MANUAL) apitar(1);  // no treino e na IA não apita: o robô está andando e não pode parar para isso
      urgente = true;
    }
    if (c == 4 && millis() - ultima_luz_piscando > 30000) {
      ultima_luz_piscando = millis();
      urgente = true;
    }
    if (modo == TREINO && meta_atingida()) {  // meta do painel (passos ou minutos): salva, avisa e para
      Serial.printf("meta: treino concluído (%u passos, %.1f min)\n", (unsigned)agente.m.passos, (millis() - treino_inicio_ms) / 60000.0f);
      salvar_agente();
      apitar(5);
      trocar_modo(MANUAL);
      return;
    }
    if (modo == TREINO || modo == IA) passo_ia(d, c == 1 || c == 3, modo == TREINO);
    return;
  }

  // Modo autônomo. O navegador anda reto na velocidade cheia, vai diminuindo e CURVANDO antes da parede e só gira no lugar a menos de
  // DIST_MINIMA_CM (sem ré). O TinyML continua classificando: manda os alertas ao MVP e deixa o carrinho um pouco mais devagar no escuro.
  bool escuro = (c == 1 || c == 3);
  if (c == 3 && millis() - ultimo_alerta > 10000) {  // escuro com obstáculo: para, apita 3 vezes e avisa na hora
    ultimo_alerta = millis();
    parar();
    apitar(3);
    urgente = true;
    return;
  }
  if (c == 4 && millis() - ultima_luz_piscando > 30000) {  // luz piscando: lâmpada com defeito, avisa uma vez a cada 30 s
    ultima_luz_piscando = millis();
    urgente = true;
  }
  // classe 5 (algo se aproxima rápido): só vale com o carrinho parado. Andando, quem se aproxima da parede é ele mesmo, e a reação
  // (freiar e dar ré) interrompia o movimento toda vez que ele andava rápido em direção a uma parede.
  bool carrinho_parado = (fabsf(rampa.esq) + fabsf(rampa.dir)) < 0.3f;
  if (c == 5 && carrinho_parado && millis() - ultimo_alerta > 3000) {  // algo se aproxima rápido: freia e recua um pouco antes de chegar perto
    ultimo_alerta = millis();
    parar();
    motor(-VELOCIDADE_LENTA, -VELOCIDADE_LENTA);
    delay(250);
    parar();
    preenchidas = 0;
    filtro.esquecer();
    navegador.esquecer();
    return;
  }
  if (d < DIST_MINIMA_CM - 10) parar();  // algo apareceu muito perto: freio na hora, sem rampa
  Navegador::Saida n = navegador.passo(d, DIST_MINIMA_CM, DIST_MINIMA_CM + 50, DIST_MINIMA_CM + 20);
  if (n.preso) {  // girou por 5 s sem abrir espaço
    Serial.println("preso: fuga");
    fuga(navegador.lado);
    return;
  }
  // mandou seguir reto e a distância não mudou por 3 ciclos = preso raspando em uma parede (o sensor só enxerga reto)
  static bool seguiu_antes = false;
  if (detector.atualizar(seguiu_antes, d, RL_TRAVADO_CM)) {
    Serial.println("preso raspando: fuga");
    fuga(navegador.lado);
    navegador.lado = -navegador.lado;
    seguiu_antes = false;
    return;
  }
  seguiu_antes = (n.v > 0.5f && fabsf(n.w) < 0.05f);
  float fator = escuro ? 0.85f : 1.0f;
  motor_suave(misturar(n.v * fator, n.w));
}
