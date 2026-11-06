// Testa cada peça sozinha, antes de montar tudo. Abra o Monitor Serial (115200) e digite um comando:
//   m = gira os motores (um de cada vez, 1 s)   d = mede a distância   l = lê o LDR (para calibrar)
//   b = apita o buzzer   t = mostra a distância e a luz sem parar (digite qualquer coisa para sair)
#include <Arduino.h>
const int ENA = 25, IN1 = 26, IN2 = 27, ENB = 13, IN3 = 32, IN4 = 33;
const int TRIG = 5, ECHO = 18, LDR = 34, BUZZER = 23;

void motor(int a, int b, int c, int d, int pwmA, int pwmB) {
  digitalWrite(IN1, a);
  digitalWrite(IN2, b);
  digitalWrite(IN3, c);
  digitalWrite(IN4, d);
  ledcWrite(ENA, pwmA);
  ledcWrite(ENB, pwmB);
}

float distancia() {
  digitalWrite(TRIG, LOW);
  delayMicroseconds(3);
  digitalWrite(TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG, LOW);
  long us = pulseIn(ECHO, HIGH, 12000);
  return us == 0 ? -1 : us / 58.0f;
}

void setup() {
  Serial.begin(115200);
  int saidas[] = {IN1, IN2, IN3, IN4, TRIG, BUZZER};
  for (int p : saidas) pinMode(p, OUTPUT);
  pinMode(ECHO, INPUT);
  ledcAttach(ENA, 1000, 8);
  ledcAttach(ENB, 1000, 8);
  analogSetPinAttenuation(LDR, ADC_11db);
  Serial.println("pronto: m, d, l, b ou t");
}

void loop() {
  if (!Serial.available()) return;
  char c = Serial.read();
  if (c == 'm') {
    Serial.println("motor esquerdo para frente"); motor(1, 0, 0, 0, 180, 0); delay(1000);
    Serial.println("motor esquerdo para trás"); motor(0, 1, 0, 0, 180, 0); delay(1000);
    Serial.println("motor direito para frente"); motor(0, 0, 1, 0, 0, 180); delay(1000);
    Serial.println("motor direito para trás"); motor(0, 0, 0, 1, 0, 180); delay(1000);
    motor(0, 0, 0, 0, 0, 0);
  } else if (c == 'd') {
    Serial.printf("distância: %.1f cm (-1 = sem eco)\n", distancia());
  } else if (c == 'l') {
    Serial.printf("LDR bruto: %d (0 a 4095)\n", analogRead(LDR));
  } else if (c == 'b') {
    digitalWrite(BUZZER, HIGH); delay(300); digitalWrite(BUZZER, LOW);
  } else if (c == 't') {
    while (!Serial.available()) {
      Serial.printf("distância %.1f cm | LDR %d\n", distancia(), analogRead(LDR));
      delay(300);
    }
  }
}
