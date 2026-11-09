# Carro robô ChuvaRota (Project-Based Maker Lab)

Integrante: **Vinicius Barros, RM 97824**

Carro com ESP32 **dirigido pelo app Dabble** (Bluetooth), com sensor de distância (HC-SR04), um **LDR (sensor de luz novo)** e uma **IA (TinyML)** que olha a luz e a distância e reage no próprio carrinho: acende o farol no escuro, apita em alertas e freia quando algo vem na direção dele.

O projeto tem só isto:

```
maker/
  robo/
    robo.ino            <- TODO o programa do carrinho e TODOS os parâmetros (seção 1 do arquivo)
    caracteristicas.h   <- TinyML: as contas que viram a entrada do modelo
    modelo_tinyml.h     <- TinyML: a rede neural treinada (gerado, não edite)
  tinyml/               <- como o modelo foi treinado e testado (Python)
```

## Colocar para funcionar
1. **Arduino IDE 2**: em Settings, adicione em "URLs adicionais" `https://espressif.github.io/arduino-esp32/package_esp32_index.json`. Em Placas, instale **esp32 by Espressif Systems 3.x**. Em Bibliotecas, instale **DabbleESP32** (STEMpedia).
2. **Ferramentas**: placa **ESP32 Dev Module**, Partition Scheme **Huge APP (3MB No OTA/1MB SPIFFS)**, a porta COM do ESP32.
3. Abra `maker/robo/robo.ino` (o arquivo) e clique em **Upload** (segure o botão BOOT se aparecer `Connecting....`).
4. Abra o **Monitor Serial em 115200**: ele mostra o que o carrinho "vê".
5. No celular, abra o **Dabble**, toque em Connect, escolha **ChuvaRota** e entre no módulo **Gamepad**.

## Ligação
| Peça | Pino do ESP32 |
|---|---|
| L298N motor esquerdo: ENA, IN1, IN2 | 25, 26, 27 |
| L298N motor direito: ENB, IN3, IN4 | 13, 32, 33 |
| HC-SR04: TRIG, ECHO | 5, 18 (ECHO direto se o sensor está em 3,3 V; em 5 V precisa de divisor 1k/2k) |
| LDR | 3,3 V, LDR, GPIO 34, resistor de 10 kΩ, GND |
| Buzzer ativo | GPIO 23 e GND |
| LED | o da própria placa (GPIO 2) |
| Alimentação | bateria no 12V do L298N, saída 5V do L298N no VIN do ESP32, GND de tudo junto |

Se você ligou em outros pinos, mude só a lista de pinos na seção 1 do `robo.ino`.

## Controles (Dabble, módulo Gamepad)
| Botão | O que faz |
|---|---|
| Seta cima / baixo | frente / ré (a frente é bloqueada a menos de 12 cm de um obstáculo) |
| Seta esquerda / direita | gira no lugar |
| **Triângulo** | liga/desliga o modo **autônomo** (anda sozinho e desvia das paredes) |
| X | volta ao manual |
| Quadrado | buzina |

## O que a IA faz no carrinho
A cada 0,1 s o carrinho lê o LDR e o sensor de distância. O modelo TinyML olha as últimas 8 leituras (0,8 s) e escolhe uma de 6 situações. A reação aparece no próprio carrinho, em qualquer modo:

| Situação da IA | Como testar | O que você vê |
|---|---|---|
| `ok` | luz normal, nada à frente | nada de especial |
| `pouca_luz` | cubra o LDR com o dedo | **LED acende** (farol) |
| `escuro_e_obstaculo` | cubra o LDR e ponha a mão a menos de 30 cm | **para, apita 3 vezes** e o LED fica aceso |
| `luz_piscando` | ligue e desligue a lanterna do celular sobre o LDR | **LED pisca** e apita 2 vezes (lâmpada com defeito) |
| `objeto_se_aproximando` | com o carrinho parado, leve a mão rápido na direção dele | apita 1 vez e ele **não anda para frente por 1,5 s** |
| `obstaculo` | mão parada a menos de 30 cm | a frente já está bloqueada pela regra da distância |

A parada diante de obstáculo usa a distância medida direto, não a IA: a segurança não depende do modelo. Para ver a diferença, mude `USAR_IA` para `0` no `robo.ino` (vira um carrinho comum) e grave de novo.

O Monitor Serial imprime a cada meio segundo, por exemplo: `luz  12% (ldr= 640) | dist  88 cm | IA: pouca_luz | manual | frente`.

## Ajustes (todos na seção 1 do `robo.ino`)
| Problema | O que mudar |
|---|---|
| Com a seta para cima uma roda vai para trás | `INVERTE_ESQUERDO` ou `INVERTE_DIREITO` para `1` (a roda que foi para trás) |
| Motor sem força | o código não limita a potência (ENA e ENB ficam sempre ligados, sem PWM). Confira o jumper/fio de ENA e ENB no L298N e o GND comum |
| Não anda para frente nunca | olhe `dist` no Monitor Serial: se estiver baixo sem nada à frente, o sensor está lendo errado (confira o ECHO). Teste com `PROTECAO_FRENTE 0` |
| A IA não percebe o escuro | olhe `ldr=` no Monitor Serial: com o dedo no LDR anote o valor e ponha em `LDR_ESCURO`; com muita luz, em `LDR_CLARO` |
| Bate na parede | suba `DIST_PARAR_CM` / `DIST_DESVIO_CM` |
| Quer o carrinho andando sem celular | `MODO_INICIAL 1` |
| Quer que NADA bloqueie a seta para cima | `PROTECAO_FRENTE 0` e `USAR_IA 0` (aí ele só obedece as setas) |

## TinyML (a pasta `tinyml/`)
- `simular_sensores.py` gera leituras de luz e distância com os defeitos de sensores de verdade (ruído, ecos falsos, sem eco) para as 6 situações.
- `treinar.py` treina a rede neural (5 entradas, 16 e 8 neurônios, 6 saídas, com busca de hiperparâmetros), mede o resultado (`metricas.json`, `matriz_confusao.png`, `robustez.png`) e escreve `robo/modelo_tinyml.h`. Resultado em dados simulados: **95,1% de acerto, F1 0,93**, contra 87,1% de regras fixas. **Em dados reais do carrinho ainda não foi medido.**
- `caracteristicas.py` e `robo/caracteristicas.h` fazem a mesma conta em Python e em C++. `testar_c.py` compila o C++ e confere que ele decide igual ao Python em 400 janelas.

```
pip install numpy scikit-learn matplotlib
python maker/tinyml/treinar.py     # treina e regrava robo/modelo_tinyml.h
python maker/tinyml/testar_c.py    # confere o C++ contra o Python
```

## Problema (CitizenTech)
Pontos de ônibus, calçadas e ruas mal iluminados, principalmente em dia de chuva e à noite, aumentam o risco de acidentes e de crimes, e a prefeitura só descobre quando alguém reclama. O robô percorre o local, mede a luz e a distância até os obstáculos e identifica onde precisa de atenção, inclusive lâmpadas com defeito. Contribui para os ODS 11 (cidades sustentáveis) e 9 (infraestrutura).

## Resultados com o robô
_A preencher depois dos testes: distâncias medidas, comportamento nas 6 situações, vídeo._
