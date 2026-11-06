// Carro robô ChuvaRota: desvia de obstáculos, mede a luz do ambiente e classifica a situação com um modelo TinyML.
// Placa: ESP32 DevKit (pacote "esp32" 3.x do Arduino)
#include <Arduino.h>
#include <HTTPClient.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>

#include "cert_raiz.h"
#include "config.h"
#include "modelo_tinyml.h"

// motores (ponte H L298N)
const int ENA = 25, IN1 = 26, IN2 = 27;
const int ENB = 13, IN3 = 32, IN4 = 33;
// sensores e saídas
const int TRIG = 5, ECHO = 18;  // o ECHO passa por um divisor de tensão (5 V -> 3,3 V)
const int LDR = 34;
const int BUZZER = 23, LED = 2;

const char* NOMES[] = {"ok", "pouca_luz", "obstaculo", "escuro_e_obstaculo"};
const float DIST_MINIMA = 8;  // abaixo disso o robô para, mesmo que o modelo diga outra coisa

struct Leitura {
  float luz;
  float dist;
  int classe;
};
volatile Leitura atual = {1, 200, 0};
volatile bool urgente = false;

void motor(int esq, int dir) {
  digitalWrite(IN1, esq > 0);
  digitalWrite(IN2, esq < 0);
  digitalWrite(IN3, dir > 0);
  digitalWrite(IN4, dir < 0);
  ledcWrite(ENA, abs(esq));
  ledcWrite(ENB, abs(dir));
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
  long us = pulseIn(ECHO, HIGH, 25000);
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
  return constrain((bruto - LDR_ESCURO) / (float)(LDR_CLARO - LDR_ESCURO), 0.0f, 1.0f);
}

void manobra() {
  parar();
  delay(150);
  motor(-150, -150);
  delay(400);
  motor(150, -150);
  delay(450);
  parar();
}

void enviar(Leitura l) {
  if (WiFi.status() != WL_CONNECTED) return;
  WiFiClientSecure cliente;
  cliente.setCACert(CERT_RAIZ);
  HTTPClient http;
  http.setTimeout(5000);
  if (!http.begin(cliente, URL_MVP)) return;
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Token", TOKEN_ROBO);
  char corpo[128];
  snprintf(corpo, sizeof(corpo), "{\"luz_pct\":%.0f,\"distancia_cm\":%.0f,\"situacao\":\"%s\"}", l.luz * 100, l.dist, NOMES[l.classe]);
  int codigo = http.POST(corpo);
  Serial.printf("envio: %s -> %d\n", corpo, codigo);
  http.end();
}

// o envio roda em outra tarefa para não deixar o robô parado esperando a rede
void tarefa_rede(void*) {
  unsigned long ultimo = 0;
  for (;;) {
    if (WiFi.status() != WL_CONNECTED) {
      WiFi.reconnect();
      vTaskDelay(5000 / portTICK_PERIOD_MS);
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

void setup() {
  Serial.begin(115200);
  int saidas[] = {IN1, IN2, IN3, IN4, TRIG, BUZZER, LED};
  for (int p : saidas) pinMode(p, OUTPUT);
  pinMode(ECHO, INPUT);
  ledcAttach(ENA, 1000, 8);
  ledcAttach(ENB, 1000, 8);
  analogSetPinAttenuation(LDR, ADC_11db);
  parar();

#if MODO_COLETA
  Serial.println("luz,distancia_cm,classe  (digite 0, 1, 2 ou 3 para escolher a classe)");
#else
  WiFi.begin(WIFI_SSID, WIFI_SENHA);
  xTaskCreatePinnedToCore(tarefa_rede, "rede", 12288, NULL, 1, NULL, 0);
#endif
}

void loop() {
  float d = distancia();
  float l = luz();

#if MODO_COLETA
  static int rotulo = 0;
  while (Serial.available()) {
    int c = Serial.read() - '0';
    if (c >= 0 && c <= 3) rotulo = c;
  }
  Serial.printf("%.3f,%.1f,%d\n", l, d, rotulo);
  delay(200);
  return;
#endif

  int c = classificar(l, d / 200.0f);
  if (d < DIST_MINIMA) c = (l < 0.30f) ? 3 : 2;  // regra de segurança acima do modelo
  atual.luz = l;
  atual.dist = d;
  atual.classe = c;
  digitalWrite(LED, c == 1 || c == 3);

  switch (c) {
    case 0: motor(180, 180); break;
    case 1: motor(110, 110); break;  // pouca luz: anda devagar
    case 2: manobra(); break;
    case 3:
      parar();
      apitar(3);
      urgente = true;
      manobra();
      break;
  }
  delay(100);
}
