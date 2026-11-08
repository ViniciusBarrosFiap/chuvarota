/*
  ============================================================
  CARRINHO CHUVAROTA  -  ESP32 + Dabble + sensor de distância + LDR + IA (TinyML)
  ============================================================
  Tudo o que você pode ajustar está na SEÇÃO 1 (logo abaixo). O resto do arquivo é a lógica, explicada em comentários.
  Nenhum outro arquivo de configuração: só este, mais os dois arquivos do TinyML (caracteristicas.h e modelo_tinyml.h).

  O QUE O CARRINHO FAZ
    1) MANUAL (padrão): você dirige com as SETAS do Gamepad no app Dabble.
       Seta para cima = frente, baixo = ré, esquerda/direita = gira no lugar. Soltou = para.
       Ele NÃO deixa andar para frente se tiver algo a menos de DIST_PARAR_CM.
    2) AUTÔNOMO (botão TRIÂNGULO liga; X ou o triângulo de novo desligam): anda sozinho e, ao chegar perto de uma parede, gira para o lado
       até ter caminho livre (e dá uma ré se ficar preso).
    3) IA (sempre ligada, em qualquer modo): a cada 0,1 s o carrinho lê a luz (LDR) e a distância, e um modelo TinyML (rede neural
       pequena, treinada em maker/tinyml) olha as últimas 8 leituras e diz em qual situação ele está:

         situação da IA          como ver no carrinho
         ok                      nada de especial (LED apagado, velocidade normal)
         pouca_luz               LDR coberto / ambiente escuro: o LED acende (farol) e o carrinho anda mais DEVAGAR
         obstaculo               algo a menos de ~30 cm (o carrinho já para na frente por regra, ver DIST_PARAR_CM)
         escuro_e_obstaculo      escuro E algo à frente: para, apita 3 vezes e o LED fica aceso (alerta)
         luz_piscando            a luz oscila (lanterna ligando e desligando sobre o LDR): o LED pisca e apita 2 vezes
         objeto_se_aproximando   algo (a sua mão) vem rápido na direção do carrinho PARADO: apita uma vez e ele não anda para frente por 1,5 s

       A parada diante de obstáculo usa a distância medida direto (regra), não a IA: assim a segurança não depende do modelo.

  BOTÕES DO DABBLE (módulo Gamepad)
    setas = dirigir | TRIÂNGULO = liga/desliga o autônomo | X = volta ao manual | QUADRADO = buzina

  MONITOR SERIAL (115200): a cada meio segundo mostra  luz, valor bruto do LDR, distância, situação da IA, modo e o que os motores fazem.
  Use isso para ver o que o carrinho "enxerga" e para calibrar o LDR (seção 1).

  LIGAÇÃO (ESP32 DevKit)
    L298N: ENA=25  IN1=26  IN2=27  (motor esquerdo)    ENB=13  IN3=32  IN4=33  (motor direito)
    HC-SR04: TRIG=5  ECHO=18   (sensor em 3,3 V: ECHO direto. Sensor em 5 V: ECHO precisa de divisor 1k/2k, senão queima o ESP32)
    LDR: 3,3 V -> LDR -> GPIO 34 -> resistor 10 kΩ -> GND       Buzzer ativo: GPIO 23 e GND       LED: o da própria placa (GPIO 2)
    GND de tudo junto. Bateria no 12V do L298N e a saída 5V do L298N no VIN do ESP32.

  ARDUINO IDE: placa "ESP32 Dev Module" (pacote esp32 da Espressif, versão 3.x), Partition Scheme "Huge APP (3MB No OTA/1MB SPIFFS)",
  biblioteca "DabbleESP32" (da STEMpedia, NÃO a "Dabble" comum). Abra este arquivo (robo.ino) e clique em Upload.
  ============================================================
*/

#include <Arduino.h>
#define CUSTOM_SETTINGS
#define INCLUDE_GAMEPAD_MODULE
#include <DabbleESP32.h>

#include "caracteristicas.h"  // TinyML: calcula as 5 características das últimas 8 leituras
#include "modelo_tinyml.h"    // TinyML: a rede neural treinada (gerado por maker/tinyml/treinar.py)

// ================================================================================================================================
// SEÇÃO 1: PARÂMETROS (é aqui que você mexe)
// ================================================================================================================================

// --- Geral ---
#define NOME_BLUETOOTH "ChuvaRota"  // nome que aparece no app Dabble (toque em Connect)
#define MODO_INICIAL 0              // 0 = começa no manual (dirija pelo Dabble); 1 = já começa andando sozinho (não precisa do celular)
#define USAR_IA 1                   // 1 = a IA reage (farol, devagar, alertas, freio); 0 = carrinho comum, só setas e sensor (para comparar)

// --- Motores: se com a seta para CIMA uma roda gira para trás, troque 0 por 1 no lado dessa roda ---
#define INVERTE_ESQUERDO 0
#define INVERTE_DIREITO 0
#define VELOCIDADE_NORMAL 230  // 0 a 255. Abaixo de uns 140 os motores TT só zumbem e não andam
#define VELOCIDADE_LENTA 170   // usada com pouca luz (a IA manda andar devagar no escuro)
#define VELOCIDADE_GIRO 200    // ao girar no lugar
#define PWM_FREQ_HZ 5000       // frequência do PWM (em 1000 os motores chiam)

// --- Distâncias (cm) ---
#define PROTECAO_FRENTE 1   // 1 = não anda para frente com obstáculo perto; 0 = desliga (se o sensor estiver dando leitura errada)
#define DIST_PARAR_CM 12    // a menos disso não anda para frente (manual e autônomo)
#define DIST_DESVIO_CM 18   // autônomo: começa a girar a esta distância
#define DIST_LIVRE_CM 20    // autônomo: volta a andar quando houver pelo menos isto livre

// --- LDR (leitura de 0 a 4095; olhe o valor "ldr=" no Monitor Serial) ---
#define LDR_ESCURO 300   // valor com o LDR coberto com o dedo (luz = 0%)
#define LDR_CLARO 3200   // valor com o ambiente bem claro ou com a lanterna (luz = 100%). A IA considera "pouca luz" abaixo de 30%

// --- Pinos ---
const int ENA = 25, IN1 = 26, IN2 = 27;  // motor esquerdo
const int ENB = 13, IN3 = 32, IN4 = 33;  // motor direito
const int TRIG = 5, ECHO = 18;           // sensor de distância HC-SR04
const int LDR = 34;                      // sensor de luz
const int BUZZER = 23, LED = 2;          // buzzer ativo e LED da placa

// --- Ajustes internos (normalmente não precisam mudar) ---
#define PERIODO_MS 100          // o modelo foi treinado com uma leitura a cada 100 ms: não mude
#define CICLOS_CONFIRMACAO 3    // a IA só muda de situação depois de 3 respostas iguais seguidas (0,3 s): evita piscar à toa
#define FREIO_IA_MS 1500        // quanto tempo o carrinho freia quando a IA vê algo se aproximando
#define SEM_ECO_CM 200          // "nada à frente" (o sensor não recebeu eco)

// ================================================================================================================================
// SEÇÃO 2: ESTADO
// ================================================================================================================================

enum Classe { CLASSE_OK, CLASSE_POUCA_LUZ, CLASSE_OBSTACULO, CLASSE_ESCURO_E_OBSTACULO, CLASSE_LUZ_PISCANDO, CLASSE_OBJETO_SE_APROXIMANDO };
const char* NOMES_CLASSE[] = {"ok", "pouca_luz", "obstaculo", "escuro_e_obstaculo", "luz_piscando", "objeto_se_aproximando"};

enum Fase { ANDAR, GIRAR, RE };  // fases do modo autônomo

bool autonomo = (MODO_INICIAL == 1);
Fase fase = ANDAR;
int lado_giro = 1;  // 1 = gira para a direita, -1 = para a esquerda (alterna a cada desvio)
unsigned long fase_inicio = 0;

float luz = 1, dist = SEM_ECO_CM;  // última leitura: luz de 0 a 1, distância em cm
int ldr_bruto = 0;                 // última leitura crua do LDR (0 a 4095)
float janela_luz[JANELA], janela_dist[JANELA];  // últimas 8 leituras, a mais antiga primeiro
int preenchidas = 0;

int classe = CLASSE_OK;         // situação confirmada pela IA
int candidata = CLASSE_OK;      // situação que o modelo disse agora
int repeticoes = 0;             // quantas vezes seguidas o modelo disse a candidata
unsigned long freio_ia_ate = 0; // enquanto millis() < isso, a IA segura o carrinho
unsigned long ultimo_movimento = 0;  // última vez que os motores foram mandados andar

int bipes = 0;                  // bipes que faltam tocar (o buzzer toca sem travar o resto do programa)
bool bipe_ligado = false;
unsigned long bipe_marca = 0;

const char* acao = "parado";    // o que os motores estão fazendo (só para o Monitor Serial)
bool app_conectado = false;

// ================================================================================================================================
// SEÇÃO 3: MOTORES
// ================================================================================================================================
// esq e dir: -255 (ré toda) a 255 (frente toda); 0 = freia.

void motor_um(int pwm_pino, int in_a, int in_b, int v) {
  if (v == 0) {  // freio: as duas entradas iguais e o enable ligado (a ponte H "segura" o motor)
    digitalWrite(in_a, HIGH);
    digitalWrite(in_b, HIGH);
    ledcWrite(pwm_pino, 255);
    return;
  }
  digitalWrite(in_a, v > 0);
  digitalWrite(in_b, v < 0);
  ledcWrite(pwm_pino, constrain(abs(v), 0, 255));
}

void motor(int esq, int dir) {
  if (esq != 0 || dir != 0) ultimo_movimento = millis();
  if (INVERTE_ESQUERDO) esq = -esq;
  if (INVERTE_DIREITO) dir = -dir;
  motor_um(ENA, IN1, IN2, esq);
  motor_um(ENB, IN3, IN4, dir);
}

void parar() {
  motor(0, 0);
  acao = "parado";
}

void andar(int velocidade) {  // positivo = frente, negativo = ré
  motor(velocidade, velocidade);
  acao = velocidade > 0 ? "frente" : "ré";
}

void girar(int lado) {  // 1 = direita, -1 = esquerda (gira no lugar)
  motor(lado * VELOCIDADE_GIRO, -lado * VELOCIDADE_GIRO);
  acao = lado > 0 ? "gira à direita" : "gira à esquerda";
}

// ================================================================================================================================
// SEÇÃO 4: SENSORES
// ================================================================================================================================

// uma medida do HC-SR04: dispara um pulso e mede quanto o eco demora. Som: ~0,0343 cm/µs, e o eco vai e volta (÷2).
float uma_medida() {
  digitalWrite(TRIG, LOW);
  delayMicroseconds(3);
  digitalWrite(TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG, LOW);
  long us = pulseIn(ECHO, HIGH, 12000);  // espera até 12 ms (uns 2 m); sem eco devolve 0
  if (us == 0) return SEM_ECO_CM;
  return fminf(SEM_ECO_CM, us * 0.01715f);
}

// mediana de 3 medidas: descarta uma leitura falsa isolada. Se a leitura anterior era "muito perto" e agora veio "sem eco", é
// quase certo que o obstáculo está colado no sensor (o HC-SR04 não enxerga a menos de ~2 cm): então mantém "perto" por até 2 s.
float medir_distancia() {
  static int sem_eco_seguidos = 0;
  float a = uma_medida();
  delay(5);  // deixa o eco anterior sumir
  float b = uma_medida();
  delay(5);
  float c = uma_medida();
  float m = fmaxf(fminf(a, b), fminf(fmaxf(a, b), c));
  if (m >= SEM_ECO_CM && dist < 10 && sem_eco_seguidos < 20) {
    sem_eco_seguidos++;
    return dist;
  }
  sem_eco_seguidos = 0;
  return m;
}

// luz de 0 (escuro) a 1 (claro): média de 8 leituras do LDR, ajustada entre LDR_ESCURO e LDR_CLARO
float medir_luz() {
  long soma = 0;
  for (int i = 0; i < 8; i++) soma += analogRead(LDR);
  ldr_bruto = soma / 8;
  return constrain((ldr_bruto - LDR_ESCURO) / (float)(LDR_CLARO - LDR_ESCURO), 0.0f, 1.0f);
}

// ================================================================================================================================
// SEÇÃO 5: IA (TinyML) E ALERTAS
// ================================================================================================================================

void apitar(int vezes) { bipes = vezes; }

// roda a cada volta do loop: toca os bipes pendentes (120 ms ligado, 120 ms desligado) e a buzina do Dabble
void atualizar_buzzer(bool buzina) {
  if ((bipes > 0 || bipe_ligado) && millis() - bipe_marca >= 120) {
    bipe_marca = millis();
    if (bipe_ligado) {
      bipe_ligado = false;
    } else {
      bipes--;
      bipe_ligado = true;
    }
  }
  digitalWrite(BUZZER, buzina || bipe_ligado);
}

// o que fazer no instante em que a IA muda de situação
void ao_mudar_de_classe(int nova) {
  Serial.printf(">>> IA: %s\n", NOMES_CLASSE[nova]);
  if (!USAR_IA) return;
  if (nova == CLASSE_ESCURO_E_OBSTACULO) apitar(3);
  if (nova == CLASSE_LUZ_PISCANDO) apitar(2);
  // "objeto se aproximando" só vale com o carrinho PARADO há mais de 1,5 s: andando, é ele mesmo que se aproxima da parede
  if (nova == CLASSE_OBJETO_SE_APROXIMANDO && millis() - ultimo_movimento > 1500) {
    freio_ia_ate = millis() + FREIO_IA_MS;
    apitar(1);
  }
}

// lê os sensores, atualiza a janela e pergunta ao modelo em que situação o carrinho está
void ler_sensores_e_classificar() {
  luz = medir_luz();
  dist = medir_distancia();

  for (int i = 0; i < JANELA - 1; i++) {  // empurra a janela uma posição e coloca a leitura nova no fim
    janela_luz[i] = janela_luz[i + 1];
    janela_dist[i] = janela_dist[i + 1];
  }
  janela_luz[JANELA - 1] = luz;
  janela_dist[JANELA - 1] = dist;
  if (preenchidas < JANELA) {
    preenchidas++;
    return;  // ainda juntando as 8 primeiras leituras (0,8 s)
  }

  float x[N_ENTRADAS];
  caracteristicas(janela_luz, janela_dist, x);  // média e oscilação da luz, distância, tendência da distância
  int dito = classificar(x);                    // a rede neural escolhe uma das 6 situações

  repeticoes = (dito == candidata) ? repeticoes + 1 : 1;
  candidata = dito;
  if (repeticoes >= CICLOS_CONFIRMACAO && candidata != classe) {
    classe = candidata;
    ao_mudar_de_classe(classe);
  }
}

// ================================================================================================================================
// SEÇÃO 6: COMO O CARRINHO SE MOVE
// ================================================================================================================================

// quando a frente está bloqueada: pela distância (regra) ou, se a IA estiver ligada, pela IA (freio de aproximação / escuro com obstáculo)
bool frente_bloqueada() {
  if (PROTECAO_FRENTE && dist < DIST_PARAR_CM) return true;
  if (USAR_IA && millis() < freio_ia_ate) return true;
  if (USAR_IA && classe == CLASSE_ESCURO_E_OBSTACULO && dist < 30) return true;  // só se a distância medida concorda com a IA
  return false;
}

// velocidade de passeio: a IA manda andar devagar quando está escuro ou a luz está piscando
int velocidade_atual() {
  bool devagar = USAR_IA && (classe == CLASSE_POUCA_LUZ || classe == CLASSE_ESCURO_E_OBSTACULO || classe == CLASSE_LUZ_PISCANDO);
  return devagar ? VELOCIDADE_LENTA : VELOCIDADE_NORMAL;
}

void dirigir_manual() {
  if (!app_conectado) {  // sem o app não há ninguém dirigindo
    parar();
    return;
  }
  if (GamePad.isUpPressed()) {
    if (frente_bloqueada()) {
      parar();
      acao = "frente bloqueada";
    } else {
      andar(velocidade_atual());
    }
  } else if (GamePad.isDownPressed()) {
    andar(-VELOCIDADE_LENTA);
  } else if (GamePad.isRightPressed()) {
    girar(1);
  } else if (GamePad.isLeftPressed()) {
    girar(-1);
  } else {
    parar();
  }
}

void mudar_fase(Fase nova) {
  fase = nova;
  fase_inicio = millis();
}

// anda; ao chegar perto de algo, gira para o lado (alternando) até ter caminho livre; se girar por muito tempo, dá uma ré e tenta de novo
void dirigir_autonomo() {
  unsigned long agora = millis();
  if (fase == ANDAR) {
    if (dist < DIST_DESVIO_CM) {
      lado_giro = -lado_giro;
      mudar_fase(GIRAR);
      parar();
    } else if (frente_bloqueada()) {
      parar();  // a IA mandou segurar (algo se aproximando)
      acao = "freio da IA";
    } else {
      andar(velocidade_atual());
    }
  } else if (fase == GIRAR) {
    girar(lado_giro);
    if (dist > DIST_LIVRE_CM) mudar_fase(ANDAR);
    else if (agora - fase_inicio > 3000) mudar_fase(RE);  // preso num canto
  } else {  // RE
    andar(-VELOCIDADE_LENTA);
    if (agora - fase_inicio > 700) mudar_fase(GIRAR);
  }
}

void mudar_modo(bool ligar_autonomo) {
  autonomo = ligar_autonomo;
  mudar_fase(ANDAR);
  parar();
  apitar(autonomo ? 2 : 1);
  Serial.printf("modo: %s\n", autonomo ? "AUTÔNOMO" : "MANUAL");
}

// lê os botões do Dabble que não são setas
bool ler_botoes() {  // devolve true se o QUADRADO (buzina) está apertado
  static bool triangulo_antes = false;
  bool triangulo = GamePad.isTrianglePressed();
  if (triangulo && !triangulo_antes) mudar_modo(!autonomo);
  triangulo_antes = triangulo;
  if (GamePad.isCrossPressed() && autonomo) mudar_modo(false);
  return GamePad.isSquarePressed();
}

// LED: aceso no escuro (farol) e no alerta; pisca quando a luz externa está piscando
void atualizar_led() {
  bool aceso = false;
  if (USAR_IA) {
    if (classe == CLASSE_POUCA_LUZ || classe == CLASSE_ESCURO_E_OBSTACULO) aceso = true;
    if (classe == CLASSE_LUZ_PISCANDO) aceso = (millis() / 150) % 2 == 0;
  }
  digitalWrite(LED, aceso);
}

// ================================================================================================================================
// SEÇÃO 7: SETUP E LOOP
// ================================================================================================================================

void setup() {
  Serial.begin(115200);
  int pinos_saida[] = {IN1, IN2, IN3, IN4, TRIG, BUZZER, LED};
  for (int p : pinos_saida) pinMode(p, OUTPUT);
  pinMode(ECHO, INPUT);
  pinMode(LDR, INPUT);
  digitalWrite(TRIG, LOW);
  ledcAttach(ENA, PWM_FREQ_HZ, 8);  // esp32 3.x: ledcAttach(pino, frequência, bits)
  ledcAttach(ENB, PWM_FREQ_HZ, 8);
  parar();

  Dabble.begin(NOME_BLUETOOTH);  // no app Dabble: Connect > "ChuvaRota" > módulo Gamepad
  Serial.println("============================================");
  Serial.printf("Carrinho ChuvaRota. IA: %s. Modo: %s.\n", USAR_IA ? "ligada" : "desligada", autonomo ? "autônomo" : "manual");
  Serial.printf("Bluetooth: procure \"%s\" no app Dabble.\n", NOME_BLUETOOTH);
  Serial.println("============================================");
  apitar(1);
}

void loop() {
  static unsigned long ultima_leitura = 0, ultimo_texto = 0;
  Dabble.processInput();  // atualiza os botões do app (chame sempre, sem demora)

  // conexão do app
  bool conectado = Dabble.isAppConnected();
  if (conectado != app_conectado) {
    app_conectado = conectado;
    Serial.println(conectado ? "[Bluetooth] app Dabble CONECTADO" : "[Bluetooth] app Dabble DESCONECTADO");
  }

  // sensores + IA: uma vez a cada 100 ms
  if (millis() - ultima_leitura >= PERIODO_MS) {
    ultima_leitura = millis();
    ler_sensores_e_classificar();
  }

  // botões e movimento
  bool buzina = app_conectado ? ler_botoes() : false;
  if (autonomo) dirigir_autonomo();
  else dirigir_manual();

  atualizar_led();
  atualizar_buzzer(buzina);

  // resumo no Monitor Serial a cada meio segundo
  if (millis() - ultimo_texto >= 500) {
    ultimo_texto = millis();
    Serial.printf("luz %3.0f%% (ldr=%4d) | dist %3.0f cm | IA: %-21s | %s | %s\n", luz * 100, ldr_bruto, dist, NOMES_CLASSE[classe],
                  autonomo ? "autônomo" : "manual  ", acao);
  }
}
