// Configuração do robô. Este arquivo vai para o GitHub, então NÃO coloque aqui a senha do seu Wi-Fi:
// copie wifi_local.example.h para wifi_local.h (o Git ignora esse arquivo) e preencha o Wi-Fi lá.
#pragma once

#define WIFI_SSID "nome-da-rede"   // troque em wifi_local.h
#define WIFI_SENHA "senha-da-rede"  // troque em wifi_local.h
#define URL_MVP "https://chuvarota-85ixn.azurewebsites.net/robo"
// Token de DEMONSTRAÇÃO, público de propósito: só deixa o robô enviar leituras de teste ao MVP de demonstração.
// Para usar o seu próprio MVP, defina ROBO_TOKEN lá (infra/variables.tf) e troque o valor aqui.
#define TOKEN_ROBO "6wsbYPEzUPxyJsi3S_4fvnyJDnlBjxCo"  // gitleaks:allow

// ===== 1. O que você pode querer mudar ==========================================================================================
// 1 = controle pelo app Dabble (Bluetooth); 0 = sem Bluetooth, o robô só anda sozinho (sobra mais memória para o envio ao MVP)
#define USAR_DABBLE 1
// nome que aparece no Bluetooth: no app Dabble, toque em Connect e escolha este nome
#define NOME_BLUETOOTH "ChuvaRota"
// modo em que o robô começa: 0 = dirigido pelo Dabble, 1 = autônomo (regras + TinyML), 2 = treino (aprende por tentativa e erro),
// 3 = IA (usa o que aprendeu, sem explorar). No Dabble: triângulo = autônomo, círculo = treino, Start = IA, X = volta ao manual
#define MODO_INICIAL 0
// se "para frente" no joystick do Dabble fizer o robô ir para trás, troque 0 por 1
#define INVERTE_JOYSTICK_Y 0


// motores: se uma roda girar ao contrário do esperado, troque 0 por 1 aqui (em vez de mexer nos fios)
#define INVERTE_ESQUERDO 0
#define INVERTE_DIREITO 0
#define VELOCIDADE_NORMAL 180  // 0 a 255
#define VELOCIDADE_LENTA 120
#define PWM_MINIMO 110  // abaixo disso os motores TT não vencem o atrito e só zumbem
#define TEMPO_RE_MS 400
#define TEMPO_GIRO_MS 450  // giro mínimo da manobra: ajuste para o robô virar uns 90 graus

// Anti-colisão (modo autônomo e Dabble). Se ainda bater na parede, aumente DIST_MINIMA_CM ou diminua VELOCIDADE_NORMAL.
#define DIST_MINIMA_CM 25  // algo mais perto que isso à frente: o robô para e (no autônomo) recua e vira para o lado

// Modo treino (o robô ajusta sozinho a distância do freio entre TREINO_MARGEM_MIN_CM e 30 cm; ver docs/ia.md)
#define TREINO_MARGEM_MIN_CM 12  // o freio nunca chega mais perto que isso. É o limite de segurança: só diminua depois de testar
#define TREINO_ADAPTAR_MARGEM 1  // 0 = a distância do freio fica sempre em 20 cm
#define TREINO_APITAR_ERRO 1     // 1 = um "bip" curto a cada freio de segurança, para você ouvir os erros acontecendo

// ===== 2. Calibração: não escreva aqui, deixe os comandos p, k, v e g do Monitor Serial dizerem os valores (docs/teste_pecas.md) ====
// Sensor de distância: leitura = tempo do eco x velocidade do som (pela temperatura) x SENSOR_ESCALA + SENSOR_OFFSET_CM
#define TEMPERATURA_C 25  // temperatura do ambiente: o som é ~0,6 m/s mais rápido a cada grau
#define SENSOR_ESCALA 1.000f
#define SENSOR_OFFSET_CM 0.0f
// O carrinho de verdade (só a simulação do treino usa estes números)
#define CARRINHO_CM_S_NORMAL 42  // velocidade andando em VELOCIDADE_NORMAL
#define CARRINHO_CM_S_LENTO 26   // velocidade andando em VELOCIDADE_LENTA
#define CARRINHO_GRAUS_S 110     // giro no lugar, em graus por segundo
// LDR: valores de partida (0 a 4095). O robô se autocalibra: guarda na memória o mais escuro e o mais claro que já viu
#define LDR_ESCURO 300
#define LDR_CLARO 3200

// 1 = robô parado só imprimindo "luz,distancia_cm,classe" a cada 100 ms para coletar dados reais (ver docs/teste_pecas.md)
#define MODO_COLETA 0

// o Wi-Fi de verdade fica em wifi_local.h, que não vai para o Git
#if __has_include("wifi_local.h")
#undef WIFI_SSID
#undef WIFI_SENHA
#include "wifi_local.h"
#endif
