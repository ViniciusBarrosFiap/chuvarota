// copie para config.h (que não vai para o Git) ou rode maker/firmware/configurar.sh, que faz isso por você
#pragma once

#define WIFI_SSID "nome-da-rede"
#define WIFI_SENHA "senha-da-rede"
#define URL_MVP "https://chuvarota-85ixn.azurewebsites.net/robo"
#define TOKEN_ROBO "troque-pelo-token"

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
