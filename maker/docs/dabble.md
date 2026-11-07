# Controlando o carrinho pelo app Dabble

O Dabble é um app gratuito (Android e iOS) que transforma o celular em um controle por Bluetooth. O robô aparece como **ChuvaRota** (nome em `NOME_BLUETOOTH`, no `config.h`).

## Preparar o código (uma vez)
1. No Arduino IDE: **Ferramentas > Gerenciar Bibliotecas**, busque **DabbleESP32** (de STEMpedia) e instale.
2. **Ferramentas > Partition Scheme > "Huge APP (3MB No OTA/1MB SPIFFS)"**. É obrigatório: com o Bluetooth o programa tem 1,8 MB e não cabe na partição padrão (o IDE avisa "Sketch too big"). O arquivo `sketch.json` da pasta já tenta escolher isso sozinho; confira de qualquer jeito.
3. Grave o `robo.ino` normalmente.

## Conectar o celular
1. Instale o **Dabble** ("Dabble - Bluetooth Controller", de STEMpedia).
2. Ligue o Bluetooth do celular (no Android, a localização precisa estar ligada para o app achar o robô).
3. Abra o Dabble, toque no ícone de **Bluetooth (Connect)** e escolha **ChuvaRota**. Não pareie pelas configurações do celular: é só dentro do app.
4. Abra o módulo **Gamepad**. Toque na engrenagem do módulo para escolher o modo: **Digital** (setas e botões) ou **Joystick**.

## Botões
| Botão | O que faz |
|---|---|
| Setas ou joystick | dirigir (para frente, para trás, virar; no joystick a velocidade acompanha o quanto você empurra) |
| **Quadrado** | buzina enquanto estiver apertado |
| **Triângulo** | alterna entre **dirigir pelo Dabble** e **andar sozinho** (apita 1 vez ao ir para manual e 2 vezes ao ir para o autônomo) |
| **X** | freia e volta para o controle manual |

## O que o robô faz enquanto você dirige
- **Proteção:** se houver algo a menos de 8 cm à frente, ele não deixa avançar (você ainda pode recuar e virar).
- **IA e sensores continuam ligados:** o LDR e o modelo TinyML classificam o ambiente e enviam as leituras ao MVP. Se detectar **escuro com obstáculo**, apita uma vez e manda o alerta na hora; se a luz estiver **piscando**, avisa o MVP.
- No modo **autônomo** o robô decide sozinho (anda, desvia, freia diante de algo que se aproxima) até você apertar o X ou o triângulo.

## Ajustes no `config.h`
- `MODO_INICIAL`: `0` começa dirigido pelo Dabble, `1` começa sozinho.
- `INVERTE_JOYSTICK_Y`: se empurrar o joystick para frente fizer o robô ir para trás, troque para `1`.
- `NOME_BLUETOOTH`: nome que aparece no app.

## Se não funcionar
- **O app não acha o robô:** confira se o código foi gravado com a partição Huge APP, se o Monitor Serial não mostra reinício em loop e se a localização do Android está ligada.
- **Conecta e cai:** o Bluetooth e o Wi-Fi dividem a antena e a memória do ESP32. Se o Monitor Serial mostrar `envio adiado: pouca memória livre`, o robô não está conseguindo enviar ao MVP, mas continua dirigindo.
- **O robô vai ao contrário do joystick:** `INVERTE_JOYSTICK_Y`.
