// copie para config.h (que não vai para o Git) e preencha
#pragma once

#define WIFI_SSID "nome-da-rede"
#define WIFI_SENHA "senha-da-rede"
#define URL_MVP "https://chuvarota-85ixn.azurewebsites.net/robo"
#define TOKEN_ROBO "troque-pelo-token"

// calibração do LDR: valores brutos (0 a 4095) lidos no Monitor Serial no escuro e com luz forte
#define LDR_ESCURO 300
#define LDR_CLARO 3200

// 1 = robô parado só imprimindo "luz,distancia_cm,classe" para montar o conjunto de dados real
#define MODO_COLETA 0
