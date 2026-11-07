// Configuração do robô. Este arquivo vai para o GitHub, então NÃO coloque aqui a senha do seu Wi-Fi:
// copie wifi_local.example.h para wifi_local.h (o Git ignora esse arquivo) e preencha o Wi-Fi lá.
#pragma once

#define WIFI_SSID "nome-da-rede"   // troque em wifi_local.h
#define WIFI_SENHA "senha-da-rede"  // troque em wifi_local.h
#define URL_MVP "https://chuvarota-85ixn.azurewebsites.net/robo"
// Token de DEMONSTRAÇÃO, público de propósito: só deixa o robô enviar leituras de teste ao MVP de demonstração.
// Para usar o seu próprio MVP, defina ROBO_TOKEN lá (infra/variables.tf) e troque o valor aqui.
#define TOKEN_ROBO "6wsbYPEzUPxyJsi3S_4fvnyJDnlBjxCo"  // gitleaks:allow

// 1 = controle pelo app Dabble (Bluetooth); 0 = sem Bluetooth, o robô só anda sozinho (sobra mais memória para o envio ao MVP)
#define USAR_DABBLE 1
// nome que aparece no Bluetooth: no app Dabble, toque em Connect e escolha este nome
#define NOME_BLUETOOTH "ChuvaRota"
// 0 = o robô começa dirigido pelo Dabble (triângulo alterna para o modo autônomo); 1 = começa sozinho
#define MODO_INICIAL 0
// se "para frente" no joystick do Dabble fizer o robô ir para trás, troque 0 por 1
#define INVERTE_JOYSTICK_Y 0

// LDR: valores de partida (0 a 4095). O robô se autocalibra: guarda na memória o mais escuro e o mais claro que já viu
#define LDR_ESCURO 300
#define LDR_CLARO 3200

// motores: se uma roda girar ao contrário do esperado, troque 0 por 1 aqui (em vez de mexer nos fios)
#define INVERTE_ESQUERDO 0
#define INVERTE_DIREITO 0
#define VELOCIDADE_NORMAL 180  // 0 a 255
#define VELOCIDADE_LENTA 120
#define PWM_MINIMO 110  // abaixo disso os motores TT não vencem o atrito e só zumbem
#define TEMPO_RE_MS 400
#define TEMPO_GIRO_MS 450  // ajuste para o robô virar uns 90 graus

#define DIST_MINIMA_CM 8  // abaixo disso o robô para, mesmo que o modelo erre

// 1 = robô parado só imprimindo "luz,distancia_cm,classe" a cada 100 ms para coletar dados reais (ver docs/teste_pecas.md)
#define MODO_COLETA 0

// o Wi-Fi de verdade fica em wifi_local.h, que não vai para o Git
#if __has_include("wifi_local.h")
#undef WIFI_SSID
#undef WIFI_SENHA
#include "wifi_local.h"
#endif
