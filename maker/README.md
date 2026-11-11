# Carro robô ChuvaRota (Project-Based Maker Lab)

Vinicius Barros, RM 97824

Vídeo de demonstração: https://youtu.be/e_pNHcq62Pw

## O que é
Um carrinho com ESP32 que eu dirijo pelo app **Dabble** (Bluetooth). Ele tem um sensor de distância (HC-SR04), um **LDR** (sensor de luz) e uma **IA pequena (TinyML)** rodando no próprio ESP32. A IA olha a luz e a distância e reage na hora: acende o LED no escuro, apita em alerta e freia se algo vem na direção dele.

A ideia vem do problema do projeto: ponto de ônibus, calçada e rua mal iluminados, ainda mais na chuva e à noite, causam acidente e crime, e a prefeitura só fica sabendo quando alguém reclama. O robô passaria pelo local medindo luz e obstáculos e avisaria onde tem lâmpada queimada ou piscando. Ajuda nos ODS 11 e 9.

## Peças
ESP32 DevKit, driver L298N, chassi com 2 motores, HC-SR04, LDR + resistor de 10 kΩ, buzzer ativo, bateria e protoboard.

| Peça | Pino do ESP32 |
|---|---|
| Motor esquerdo (ENA, IN1, IN2) | 25, 26, 27 |
| Motor direito (ENB, IN3, IN4) | 13, 32, 33 |
| HC-SR04 (TRIG, ECHO) | 5, 18 |
| LDR | 3,3 V, LDR, GPIO 34, 10 kΩ, GND |
| Buzzer | GPIO 23 e GND |
| LED | o da placa (GPIO 2) |

Cuidado com o ECHO: se o sensor está em 5 V ele manda 5 V no pino, e o ESP32 só aguenta 3,3 V. Nesse caso precisa de um divisor (1 kΩ do ECHO até o GPIO 18 e 2 kΩ do GPIO 18 ao GND). O GND de tudo tem que ser o mesmo. Na minha montagem o ESP32 ficou no power bank (USB) e a bateria só nos motores, porque o regulador do L298N não aguentou alimentar o ESP32.

## Como colocar para rodar
1. Arduino IDE 2. Em Settings, nas URLs adicionais, ponha `https://espressif.github.io/arduino-esp32/package_esp32_index.json` e instale **esp32 (Espressif) 3.x**. Em Bibliotecas, instale **DabbleESP32** (STEMpedia).
2. Placa **ESP32 Dev Module** e Partition Scheme **Huge APP (3MB No OTA/1MB SPIFFS)**, senão o programa não cabe.
3. Abra `maker/robo/robo.ino` e dê Upload (se aparecer `Connecting....`, segure o botão BOOT).
4. Monitor Serial em 115200 mostra o que o carrinho está lendo.
5. No celular: Dabble, Connect, **ChuvaRota**, módulo **Gamepad**.

Todos os ajustes (pinos, distâncias, calibração do LDR, roda invertida) ficam na seção 1 do `robo.ino`.

## Controles (Gamepad do Dabble)
| Botão | O que faz |
|---|---|
| Seta cima / baixo | frente / ré (a frente trava a menos de 12 cm de um obstáculo) |
| Seta esquerda / direita | gira no lugar |
| Triângulo | liga ou desliga o modo autônomo (anda sozinho e desvia de parede) |
| X | volta para o manual |
| Quadrado | buzina |

## O que a IA faz
A cada 0,1 s o carrinho lê luz e distância. O modelo olha as últimas 8 leituras (0,8 s) e diz em qual de 6 situações ele está:

| Situação | Como provocar | Reação |
|---|---|---|
| `ok` | luz normal, nada na frente | nada |
| `pouca_luz` | tapar o LDR com o dedo | LED acende |
| `obstaculo` | mão parada a menos de 30 cm | frente já travada pela regra de distância |
| `escuro_e_obstaculo` | tapar o LDR e por a mão perto | para, apita 3 vezes, LED aceso |
| `luz_piscando` | lanterna do celular ligando e desligando sobre o LDR | LED pisca e apita 2 vezes (lâmpada com defeito) |
| `objeto_se_aproximando` | mão indo rápido na direção do carrinho parado | apita 1 vez e ele não vai para frente por 1,5 s |

Parar diante de obstáculo é regra com a distância medida, não é a IA. Assim a segurança não depende do modelo. Para comparar, `USAR_IA 0` no `robo.ino` vira um carrinho comum.

## TinyML (pasta `tinyml/`)
- `simular_sensores.py` gera leituras de luz e distância com defeito de sensor de verdade (ruído, eco falso, sem eco) para as 6 situações. **Os dados de treino são simulados**, eu não tinha como coletar milhares de leituras reais de cada situação.
- `treinar.py` treina uma rede pequena (5 entradas, camadas de 16 e 8, 6 saídas, 286 parâmetros) e escreve o `robo/modelo_tinyml.h`. Em dado simulado deu **95,1% de acerto e F1 de 0,93**, contra 87,1% de regras fixas. Os gráficos estão em `matriz_confusao.png` e `robustez.png`.
- `caracteristicas.py` e `robo/caracteristicas.h` fazem a mesma conta em Python e em C++. O `testar_c.py` compila o C++ e confere que ele decide igual ao Python nas 400 janelas de teste (100% iguais).

```
pip install numpy scikit-learn matplotlib
python maker/tinyml/treinar.py
python maker/tinyml/testar_c.py
```

## Resultados e limites
- Montado e funcionando: o carrinho conecta no Dabble e anda, o programa compila e o C++ da IA bate com o Python. Está tudo no vídeo.
- **Não medi a taxa de acerto da IA com dados reais do carrinho.** Os 95,1% são de dado simulado, então no carrinho real pode ser menos.
- O LDR precisa de calibração em cada ambiente (valores `LDR_ESCURO` e `LDR_CLARO` no `robo.ino`).
- O carrinho não manda dados para o MVP. O MVP tem uma rota `/robo` pronta para isso, mas o robô só reage por conta própria.
