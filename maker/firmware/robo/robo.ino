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

#include "caracteristicas.h"
#include "cert_raiz.h"
#include "modelo_tinyml.h"

// motores (ponte H L298N)
const int ENA = 25, IN1 = 26, IN2 = 27;
const int ENB = 13, IN3 = 32, IN4 = 33;
// sensores e saídas
const int TRIG = 5, ECHO = 18;  // o ECHO passa por um divisor de tensão (5 V -> 3,3 V)
const int LDR = 34;
const int BUZZER = 23, LED = 2;

const char* NOMES[] = {"ok", "pouca_luz", "obstaculo", "escuro_e_obstaculo", "luz_piscando", "objeto_se_aproximando"};
const unsigned long PERIODO_MS = 100;  // o modelo foi treinado com uma leitura a cada 100 ms

struct Leitura {
  float luz;
  float dist;
  int classe;
};
volatile Leitura atual = {1, 200, 0};
volatile bool urgente = false;
bool autonomo = USAR_DABBLE ? MODO_INICIAL : 1;  // 0 = dirigido pelo Dabble, 1 = sozinho (triângulo alterna)

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

void parar() { motor(0, 0); }

void apitar(int vezes) {
  for (int i = 0; i < vezes; i++) {
    digitalWrite(BUZZER, HIGH);
    delay(120);
    digitalWrite(BUZZER, LOW);
    delay(120);
  }
}

float uma_distancia() {
  digitalWrite(TRIG, LOW);
  delayMicroseconds(3);
  digitalWrite(TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG, LOW);
  long us = pulseIn(ECHO, HIGH, 12000);
  return us == 0 ? 200 : min(200.0f, us / 58.0f);  // sem eco = nada à frente
}

float distancia() {
  float a = uma_distancia(), b = uma_distancia(), c = uma_distancia();
  return max(min(a, b), min(max(a, b), c));  // mediana de 3
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

void manobra() {
  parar();
  delay(150);
  motor(-VELOCIDADE_LENTA, -VELOCIDADE_LENTA);
  delay(TEMPO_RE_MS);
  motor(VELOCIDADE_LENTA + 30, -(VELOCIDADE_LENTA + 30));
  delay(TEMPO_GIRO_MS);
  parar();
  preenchidas = 0;  // as leituras de antes da manobra não valem mais
}

// diagnóstico: conecta sem validar só para mostrar a cadeia que o ESP32 recebe (roda uma vez)
void mostrar_cadeia() {
  WiFiClientSecure c;
  c.setInsecure();
  c.setHandshakeTimeout(30);
  if (!c.connect("chuvarota-85ixn.azurewebsites.net", 443)) { Serial.println("  cadeia: não conectou"); return; }
  int n = 0;
  for (const mbedtls_x509_crt *p = c.getPeerCertificate(); p && n < 6; p = p->next, n++) {
    char dono[120], emissor[120];
    mbedtls_x509_dn_gets(dono, sizeof(dono), &p->subject);
    mbedtls_x509_dn_gets(emissor, sizeof(emissor), &p->issuer);
    Serial.printf("  cadeia %d: %s <- %s\n", n, dono, emissor);
  }
  c.stop();
}

bool cadeia_mostrada = false;

void enviar(Leitura l) {
  if (WiFi.status() != WL_CONNECTED) return;
  if (ESP.getMaxAllocHeap() < 45000) {  // o Bluetooth e o HTTPS dividem a memória; sem folga o TLS falha
    Serial.printf("envio adiado: pouca memória livre (%u bytes)\n", ESP.getMaxAllocHeap());
    return;
  }
  WiFiClientSecure cliente;
  cliente.setCACert(CERT_RAIZ);
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
  if (codigo <= 0 && !cadeia_mostrada) { cadeia_mostrada = true; mostrar_cadeia(); }
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
// joystick do Dabble: valores de -7 a 7; as setas valem 1
void dirigir_manual() {
  float jx = GamePad.getXaxisData(), jy = GamePad.getYaxisData() * (INVERTE_JOYSTICK_Y ? -1 : 1);
  float giro = abs(jx) < 1 ? 0 : jx / 7.0f, frente = abs(jy) < 1 ? 0 : jy / 7.0f;
  if (GamePad.isUpPressed()) frente = 1;
  if (GamePad.isDownPressed()) frente = -1;
  if (GamePad.isLeftPressed()) giro = -1;
  if (GamePad.isRightPressed()) giro = 1;
  if (frente > 0 && atual.dist < DIST_MINIMA_CM) frente = 0;  // proteção: não deixa bater de frente
  motor((int)constrain((frente + giro) * VELOCIDADE_NORMAL, -255.0f, 255.0f), (int)constrain((frente - giro) * VELOCIDADE_NORMAL, -255.0f, 255.0f));
}

void botoes() {
  static bool triangulo_antes = false;
  bool triangulo = GamePad.isTrianglePressed();
  if (triangulo && !triangulo_antes) {  // triângulo: alterna entre dirigir e andar sozinho
    autonomo = !autonomo;
    parar();
    preenchidas = 0;
    apitar(autonomo ? 2 : 1);
  }
  triangulo_antes = triangulo;
  if (GamePad.isCrossPressed() && autonomo) {  // X: freia e volta para o controle manual
    autonomo = false;
    parar();
  }
  digitalWrite(BUZZER, GamePad.isSquarePressed());  // quadrado: buzina
}
#endif

void comandos_serial() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == 'r') {  // apaga a calibração do LDR
      ldr_min = LDR_ESCURO;
      ldr_max = LDR_CLARO;
      calibracao_mudou = true;
      salvar_calibracao();
      Serial.println("calibração do LDR apagada");
    } else if (c == 'i') {
      Serial.printf("LDR: mais escuro visto %.0f, mais claro visto %.0f\n", ldr_min, ldr_max);
    }
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

#if MODO_COLETA
  Serial.println("luz,distancia_cm,classe  (digite 0 a 5 para escolher a classe)");
#else
#if USAR_DABBLE
  // o Dabble só usa Bluetooth de baixa energia: devolve a memória do Bluetooth clássico para o HTTPS do envio
  esp_bt_controller_mem_release(ESP_BT_MODE_CLASSIC_BT);
  Dabble.begin(NOME_BLUETOOTH);
#endif
  Serial.printf("memória livre na partida: %u bytes (maior bloco %u)\n", ESP.getFreeHeap(), ESP.getMaxAllocHeap());
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_SENHA);
  xTaskCreatePinnedToCore(tarefa_rede, "rede", 20480, NULL, 1, NULL, 0);
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
  if (!autonomo) dirigir_manual();
#endif
  if (millis() < proxima) return;
  proxima = millis() + PERIODO_MS;

  float d = distancia();
  float l = luz();
  if (millis() - ultimo_salvar > 60000) {
    salvar_calibracao();
    ultimo_salvar = millis();
  }

#if MODO_COLETA
  static int rotulo = 0;
  while (Serial.available()) {
    int c = Serial.read() - '0';
    if (c >= 0 && c <= 5) rotulo = c;
  }
  Serial.printf("%.3f,%.1f,%d\n", l, d, rotulo);
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

  if (!autonomo) {  // dirigindo pelo Dabble: o robô só observa e avisa
    if (c == 3 && millis() - ultimo_alerta > 10000) {
      ultimo_alerta = millis();
      apitar(1);
      urgente = true;
    }
    if (c == 4 && millis() - ultima_luz_piscando > 30000) {
      ultima_luz_piscando = millis();
      urgente = true;
    }
    return;
  }

  switch (c) {
    case 0: motor(VELOCIDADE_NORMAL, VELOCIDADE_NORMAL); break;
    case 1: motor(VELOCIDADE_LENTA, VELOCIDADE_LENTA); break;  // pouca luz: anda devagar
    case 2: manobra(); em_vigor = 0; break;
    case 3:
      parar();
      apitar(3);
      urgente = true;
      manobra();
      em_vigor = 0;
      break;
    case 4:  // luz piscando: lâmpada com defeito; segue devagar e avisa uma vez a cada 30 s
      motor(VELOCIDADE_LENTA, VELOCIDADE_LENTA);
      if (millis() - ultima_luz_piscando > 30000) {
        ultima_luz_piscando = millis();
        urgente = true;
      }
      break;
    case 5:  // algo se aproxima rápido: freia e recua um pouco antes de chegar perto
      parar();
      motor(-VELOCIDADE_LENTA, -VELOCIDADE_LENTA);
      delay(250);
      parar();
      preenchidas = 0;
      em_vigor = 0;
      break;
  }
}
