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
// modo em que o robô começa: 0 = dirigido pelo Dabble, 1 = autônomo (regras + TinyML), 2 = treino (aprende por tentativa e erro),
// 3 = IA (usa o que aprendeu, sem explorar). No Dabble: triângulo = autônomo, círculo = treino, Start = IA, X = volta ao manual
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
#define TEMPO_GIRO_MS 450  // giro mínimo da manobra: ajuste para o robô virar uns 90 graus
#define TEMPO_GIRO_MAX_MS 1500  // depois do giro mínimo ele continua girando até achar espaço livre, no máximo até aqui

// Anti-colisão (vale no modo autônomo e no Dabble). Com o carrinho a ~0,4 m/s, a leitura a cada 0,1 s e a freada levam uns 10 a 15 cm:
// por isso a parada é bem antes da parede. Se ainda bater, aumente DIST_MINIMA_CM ou diminua VELOCIDADE_NORMAL.
#define DIST_MINIMA_CM 25  // algo mais perto que isso à frente: o robô para e (no autônomo) recua e vira para o lado, mesmo que o modelo erre
#define DIST_LIVRE_CM 40  // na manobra, só para de girar quando houver pelo menos esta distância livre à frente

// Modo treino (aprendizado por reforço, ver aprendizado.h). A "quase batida" é o único erro que ele pode cometer: o freio de segurança
// sempre age antes de bater. Dentro de TREINO_DIST_PERIGO_CM ele perde pontos; dentro de TREINO_DIST_FREIO_CM o freio recua o carrinho.
#define TREINO_DIST_PERIGO_CM 30
#define TREINO_DIST_FREIO_CM 20
#define TREINO_CONHECIMENTO_INICIAL 1  // 1 = começa com a regra antiga como palpite fraco (aprende bem mais rápido); 0 = começa do zero
#define TREINO_APITAR_ERRO 1  // 1 = um "bip" curto a cada freio de segurança, para você ouvir os erros acontecendo

// 1 = robô parado só imprimindo "luz,distancia_cm,classe" a cada 100 ms para coletar dados reais (ver docs/teste_pecas.md)
#define MODO_COLETA 0

// o Wi-Fi de verdade fica em wifi_local.h, que não vai para o Git
#if __has_include("wifi_local.h")
#undef WIFI_SSID
#undef WIFI_SENHA
#include "wifi_local.h"
#endif
