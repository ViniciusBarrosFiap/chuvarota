# Montagem e testes quando as peças chegarem

O firmware, o modelo e a conexão com o MVP já estão prontos. O que falta é ligar as peças e conferir cada uma. Siga a ordem; se um passo não bater, não vá para o próximo.

## 1. Arduino IDE: abrir e gravar o código
1. Instale o Arduino IDE 2. Em **Arduino IDE > Settings > URLs adicionais para o Gerenciador de Placas**, cole `https://espressif.github.io/arduino-esp32/package_esp32_index.json`.
2. **Ferramentas > Placa > Gerenciador de Placas**, busque `esp32` e instale **"esp32 by Espressif Systems" versão 3.x** (a 2.x não serve: o código usa `ledcAttach`).
2b. **Ferramentas > Gerenciar Bibliotecas**, busque **DabbleESP32** (de STEMpedia) e instale: é ela que faz o carrinho obedecer ao app Dabble.
3. **Arquivo > Abrir** e escolha o arquivo `maker/firmware/robo/robo.ino` (o arquivo, não a pasta). O IDE abre abas com `robo.ino`, `caracteristicas.h`, `cert_raiz.h`, `config.example.h` e `modelo_tinyml.h`.
4. Crie o `config.h`: copie `config.example.h` para `config.h` **na mesma pasta** e preencha o Wi-Fi (2,4 GHz) e o token (ou rode `./maker/firmware/configurar.sh`, que faz isso). Sem o `config.h` o IDE mostra o erro "Falta o config.h".
5. **Ferramentas > Placa > esp32 > ESP32 Dev Module**, **Ferramentas > Partition Scheme > Huge APP (3MB No OTA/1MB SPIFFS)** (obrigatório: sem isso o IDE diz "Sketch too big"), e em **Porta** escolha `/dev/cu.usbserial-...` (se não aparecer, instale o driver CP210x ou CH340 e use um cabo USB de dados).
6. Clique em **Upload** (seta para a direita). Se aparecer `Connecting........`, segure o botão **BOOT** do ESP32 até começar a gravar.
7. **Ferramentas > Monitor Serial**, velocidade **115200**.

Para testar cada peça antes, abra `maker/firmware/teste_pecas/teste_pecas.ino` do mesmo jeito.

## 1b. Preparação pelo terminal (alternativa, no Mac)
- `arduino-cli` e o pacote `esp32` 3.x já estão instalados neste Mac. Em outro computador: `arduino-cli core install esp32:esp32 --additional-urls https://espressif.github.io/arduino-esp32/package_esp32_index.json`.
- Driver da placa: se o Mac não enxergar o ESP32 em `/dev/cu.*`, instale o driver CP210x ou CH340 (veja o chip que está escrito na placa). Use um cabo USB **de dados**.
- `./maker/firmware/configurar.sh` pergunta o Wi-Fi (2,4 GHz) e cria o `config.h` com o token do MVP.

## 2. Ligação
**Passo a passo completo, fio a fio, em [montagem.md](montagem.md).** Esquema geral em [ligacao.png](ligacao.png). Resumo dos pinos:

| Peça | Liga em |
|---|---|
| L298N ENA, IN1, IN2 (motor esquerdo) | GPIO 25, 26, 27 |
| L298N ENB, IN3, IN4 (motor direito) | GPIO 13, 32, 33 |
| HC-SR04 TRIG | GPIO 5 |
| HC-SR04 ECHO | divisor 1 kΩ / 2 kΩ, depois GPIO 18 |
| LDR | 3,3 V, LDR, GPIO 34, resistor de 10 kΩ, GND |
| Buzzer ativo | GPIO 23 e GND |
| Alimentação | bateria no 12V do L298N; saída 5V do L298N no VIN do ESP32; GND de tudo junto |

Divisor do ECHO: 5 V do sensor → resistor de 1 kΩ → ponto que vai ao GPIO 18 → resistor de 2 kΩ → GND. Sem ele o ECHO manda 5 V para um pino de 3,3 V.

Dica: um capacitor de 470 µF entre VIN e GND do ESP32 evita reinício quando os motores arrancam.

## 3. Testes de bancada (rodas fora do chão)
Grave o sketch de teste: `./maker/firmware/gravar.sh teste_pecas` e digite os comandos no Monitor Serial.

| # | Comando | Como | Esperado |
|---|---|---|---|
| 1 | (nenhum) | gravar | aparece `pronto: m, d, l, b ou t` |
| 2 | `m` | motores | gira um motor de cada vez, para frente e para trás. Se uma roda girar ao contrário, troque `INVERTE_ESQUERDO` ou `INVERTE_DIREITO` no `config.h` (não precisa mexer nos fios) |
| 3 | `d` | mão a 10, 20 e 50 cm | valores perto de 10, 20 e 50 (erro de 1 a 2 cm). `-1` = sem eco (confira o divisor do ECHO) |
| 4 | `l` | LDR coberto e com luz forte | valor baixo no escuro e alto com luz. **Não precisa calibrar**: o robô aprende o mais escuro e o mais claro que vê e guarda na memória |
| 5 | `b` | buzzer | apita 0,3 s |

## 4. O robô de verdade
`./maker/firmware/gravar.sh` (compila, grava e abre o Monitor Serial).

| # | Teste | Esperado |
|---|---|---|
| 6 | Rede, com o robô no colo | aparece `envio: {...} -> 201` e a leitura aparece na tela do MVP (https://chuvarota-85ixn.azurewebsites.net) |
| 7 | Dabble: conectar em `ChuvaRota` ([dabble.md](dabble.md)) e dirigir com as setas | o carrinho anda e vira; a menos de 8 cm de um obstáculo ele não avança |
| 7b | Apertar o **triângulo** (apita 2 vezes) com um obstáculo à frente | modo autônomo: desvia sozinho. **X** volta ao manual |
| 8 | Cobrir o LDR | anda devagar (pouca luz) |
| 9 | Cobrir o LDR e pôr a mão na frente | para, apita 3 vezes e o alerta aparece no MVP |
| 10 | Piscar a lanterna do celular sobre o LDR | classe `luz_piscando` aparece no MVP (a cada 30 s no máximo) |
| 11 | Mão vindo rápido na direção do robô | freia e recua antes de chegar perto |

Comandos no Monitor Serial com o robô rodando: `i` mostra a calibração do LDR; `r` apaga a calibração (use se o robô aprendeu um valor errado, por exemplo depois de um flash de câmera).

## 5. Ajustes sem mexer no código (`config.h`)
- Gira pouco ou demais na manobra: `TEMPO_GIRO_MS`. Recua pouco: `TEMPO_RE_MS`.
- Muito rápido ou lento: `VELOCIDADE_NORMAL` e `VELOCIDADE_LENTA`.
- Os motores zumbem e não andam: aumente `PWM_MINIMO`.
Depois de mudar, rode `./gravar.sh` de novo.

## 6. Dados reais para o TinyML (opcional; melhora o modelo)
O modelo já vem treinado em dados simulados. Com dados do seu robô ele se ajusta aos seus sensores.
1. `MODO_COLETA 1` no `config.h` e `./gravar.sh` (o robô fica parado e imprime uma linha a cada 100 ms).
2. Feche o Monitor Serial, rode `pip install pyserial` e `python maker/tinyml/coletar.py /dev/cu.usbserial-XXXX`. Digite a classe e Enter para trocar de situação.
3. Colete uns 3 a 5 minutos de cada situação:

| classe | como fazer |
|---|---|
| `0` ok | luz normal, nada à frente (mais de 80 cm) |
| `1` pouca_luz | cobrir parte do LDR (escuro), nada à frente |
| `2` obstaculo | luz normal, mão parada a 10 a 25 cm |
| `3` escuro_e_obstaculo | LDR coberto e mão a 10 a 25 cm |
| `4` luz_piscando | lanterna do celular ligando e desligando sobre o LDR, a cada 0,2 a 0,6 s |
| `5` objeto_se_aproximando | mão vindo de 100 cm até 30 cm em cerca de 1 s, repetindo |

4. `python maker/tinyml/treinar.py` (usa o `dados_reais.csv` sozinho) e `python maker/tinyml/testar_c.py`.
5. `MODO_COLETA 0` e `./gravar.sh`.

## Se der problema
- Reinicia ao ligar os motores: a bateria não segura a corrente; use pilhas novas e confira o GND comum.
- `envio -> -1`: sem Wi-Fi ou senha errada (a rede precisa ser de 2,4 GHz). `envio -> 401`: token diferente do que está no Azure; rode `./configurar.sh` de novo.
- A distância fica sempre em 200: o ECHO não chega ao ESP32.
