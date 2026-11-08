# Carro robô ChuvaRota (Project-Based Maker Lab)

Integrante: **Vinicius Barros, RM 97824**

Carro robô com ESP32 **controlado pelo app Dabble** (Bluetooth), que também **anda sozinho**, desvia de obstáculos, mede a luz do ambiente com um **LDR (sensor novo)** e usa **IA** para entender o que está acontecendo e para **aprender a andar por tentativa e erro**. Quando acha uma situação de risco (ponto escuro com obstáculo, lâmpada piscando, algo vindo rápido), o robô reage e manda um alerta ao MVP do ChuvaRota, que mostra as leituras em tempo real.

> **Estado atual:** firmware, IA e integração com o MVP estão prontos e testados no computador (o firmware compila, o C++ decide igual ao Python, o aprendizado foi testado em simulação e o endpoint está no ar no Azure). **Nada foi medido ainda no carrinho de verdade**: a seção "Resultados com o robô" será preenchida depois dos testes.

## Começar (5 passos)
1. **Montar:** ligue as peças com o [docs/montagem.md](docs/montagem.md) (esquema em [docs/ligacao.png](docs/ligacao.png)).
2. **Gravar** (Arduino IDE, passo a passo em [docs/teste_pecas.md](docs/teste_pecas.md)): instale a biblioteca **DabbleESP32**, escolha a partição **Huge APP**, abra `maker/firmware/robo/robo.ino`, copie `wifi_local.example.h` para `wifi_local.h` (na mesma pasta) com o seu Wi-Fi e clique em Upload. Pelo terminal: `./maker/firmware/configurar.sh` e `./maker/firmware/gravar.sh`.
3. **Conferir cada peça** (opcional): `./maker/firmware/gravar.sh teste_pecas`.
4. **Calibrar** (uma vez, com o USB e o Monitor Serial em 115200, modo manual): `p` mede a precisão do sensor, `k` o calibra com régua, `v` mede a velocidade e `g` o giro. Cada um diz o que fazer e imprime o que colar no `config.h` ([docs/teste_pecas.md](docs/teste_pecas.md), seção 4b).
5. **Usar:** abra o **Dabble** no celular, conecte em **ChuvaRota** e dirija. O carrinho não precisa ficar ligado ao computador: só para gravar e para ver mensagens. **Atenção:** com o Dabble ligado o envio ao MVP fica desligado (não sobra memória para o HTTPS); para o MVP receber as leituras, use `USAR_DABBLE 0` no `config.h` (o robô então só anda sozinho).

## Painel (gráficos em tempo real)
Abra `maker/painel/index.html` no **Chrome ou Edge** e conecte o carrinho pelo USB: o painel mostra o treino acontecendo (distância ao vivo, ação, curva de aprendizado, o que ele aprendeu), deixa você **configurar o treino** e **estima o tempo** que falta. Dá para ver uma demonstração sem o carrinho. Passo a passo em [docs/painel.md](docs/painel.md).

## Modos (botões do Dabble)
| Botão | Modo | O que faz |
|---|---|---|
| (padrão) | **manual** | você dirige com as setas ou o joystick; ele não deixa bater de frente |
| **Triângulo** | **autônomo** | anda sozinho com movimento suave: diminui a velocidade e **curva antes da parede**, e só gira no lugar a menos de 25 cm |
| **Círculo** | **treino** | anda sozinho **e aprende** por tentativa e erro (LED aceso = testando ação aleatória; bip curto = freio de segurança, um erro) |
| **Start** | **IA** | usa o que aprendeu, sem explorar |
| **X** | volta ao **manual** | |
| **Quadrado** | buzina | |

O aprendizado do treino fica salvo na memória do ESP32. Botões e ajustes em [docs/dabble.md](docs/dabble.md).

## Comandos no Monitor Serial (115200)
`?` lista tudo. Resumo: `a` liga/desliga o treino, `u` a IA, `x` volta ao manual, `q` mostra o que aprendeu, `e` a curva de aprendizado (CSV), `z` apaga o aprendizado (use ao mudar de ambiente), `p` `k` `v` `g` calibração, `i` `r` calibração do LDR.

## Problema (CitizenTech)
Pontos de ônibus, calçadas e ruas mal iluminados, principalmente em dia de chuva e à noite, aumentam o risco de acidentes e de crimes, e a prefeitura só descobre quando alguém reclama. O robô percorre o local, mede a luz e a distância até os obstáculos e avisa onde precisa de atenção, inclusive lâmpadas com defeito. Contribui para os ODS 11 (cidades sustentáveis) e 9 (infraestrutura).

## Componentes
| Peça | Função |
|---|---|
| ESP32 DevKit | cérebro: lê os sensores, roda o TinyML, comanda os motores e fala com o MVP por Wi-Fi |
| Chassi 2WD com 2 motores TT | locomoção |
| Ponte H L298N | aciona os motores e fornece 5 V para o ESP32 |
| HC-SR04 | distância até obstáculos (o ECHO passa por divisor de tensão 1k/2k) |
| **LDR + resistor de 10 kΩ** | **sensor novo: luminosidade do ambiente** |
| Buzzer ativo | alerta sonoro |
| Bateria de 6 a 9 V | alimentação |
| Celular com o app **Dabble** | controle por Bluetooth (joystick, setas e botões) |

![ligação](docs/ligacao.png)

![ligação](docs/ligacao.png)

## Como funciona (resumo)
1. A cada 100 ms o robô lê a **distância** (3 a 5 leituras, descartando as falsas) e a **luz** (média de 8 leituras, normalizada pela autocalibração).
2. O **modelo TinyML** olha as últimas 8 leituras (0,8 s) e escolhe uma de 6 situações:

| classe | significado | o que o robô faz (modo autônomo) |
|---|---|---|
| `ok` | claro e caminho livre | anda em velocidade normal |
| `pouca_luz` | ambiente escuro, caminho livre | anda devagar e acende o LED |
| `obstaculo` | algo a menos de 30 cm | curva e, se precisar, gira no lugar |
| `escuro_e_obstaculo` | escuro com algo à frente | para, apita 3 vezes, manda alerta na hora e desvia |
| `luz_piscando` | a luz oscila (lâmpada com defeito) | segue devagar e avisa ao MVP (no máximo a cada 30 s) |
| `objeto_se_aproximando` | algo vem rápido na direção do robô | freia e recua antes de chegar perto |

3. **Segurança acima da IA:** a menos de 25 cm (`DIST_MINIMA_CM`) o robô tira a velocidade na hora e gira no lugar até ter 45 cm livres. Antes disso, a partir de 75 cm, ele vai diminuindo a velocidade e curvando (o lado da curva é conferido pela distância: se piora, ele troca). Se mandar andar e a distância não mudar por 3 ciclos, ele entende que está preso numa parede e faz uma fuga.
4. Outra tarefa do ESP32 envia a situação ao MVP a cada 5 s (na hora, no caso de alerta), por HTTPS com a hora acertada por NTP, sem travar o robô.
5. No **treino**, um segundo tipo de IA (Q-learning) aprende o que fazer a cada distância, e o robô ajusta sozinho a distância do freio (de 20 cm até no mínimo 14 cm). Ele aprende reflexos para o ambiente, e **não faz um mapa** do lugar (um sensor só, olhando para frente, e nada que meça o quanto andou).

**Resultados em simulação** (salas simuladas, o mesmo código do robô; no carrinho real ainda não foram medidos): TinyML com 95,1% de acerto e F1 0,93 contra 87,1% das regras fixas. O modo autônomo **antigo** passava 63% do tempo empurrando a parede sem sair do lugar; o **novo** (movimento suave) passa 7%, anda 5 vezes mais e visita quase 5 vezes mais cantos da sala. O agente do treino anda 5 vezes mais que o autônomo antigo, com cerca de 11 vezes menos freios de segurança. Detalhes, limites e gráficos em [docs/ia.md](docs/ia.md).

## Integração com o MVP
`POST /robo` recebe `{luz_pct, distancia_cm, situacao}` com o cabeçalho `X-Token`; `GET /robo` devolve as últimas leituras, que aparecem na tela inicial do MVP: https://chuvarota-85ixn.azurewebsites.net

- O token do robô está em `config.h`, versionado de propósito para quem avaliar poder reproduzir. É um **token de demonstração**: só permite enviar leituras de teste ao MVP de demonstração (`POST /robo`) e não dá acesso a mais nada. No Azure ele é configurado pelo Terraform (`robo_token`); para usar outro MVP, defina outro `ROBO_TOKEN` lá e troque o valor no `config.h`. O **Wi-Fi não vai para o Git**: fica em `wifi_local.h`.
- A conexão com o MVP é criptografada (HTTPS), mas o robô não confere o certificado do servidor: o ESP32 recusava a cadeia do Azure. Limite aceito para a demo; o token só grava leituras de teste.
- Não há dado pessoal: só luz, distância e a classe. O MVP guarda as últimas 50 leituras em memória.

## Pastas
- `firmware/robo/`: o programa do robô. `robo.ino` (principal), `config.h` (ajustes), `logica.h` (setas, filtro da distância e sensor), `aprendizado.h` (Q-learning), `caracteristicas.h` e `modelo_tinyml.h` (TinyML, gerado), `wifi_local.example.h`
- `firmware/teste_pecas/`: sketch para testar cada peça sozinha. `firmware/configurar.sh` e `firmware/gravar.sh`
- `tinyml/`: treino do modelo, simulações e testes
- `simulador/`: finge ser o robô para testar o endpoint do MVP
- `painel/`: o painel gráfico do treino em tempo real (`index.html`) e a demonstração
- `docs/`: montagem, Dabble, testes de bancada e calibração, como a IA funciona ([ia.md](docs/ia.md)) e o painel ([painel.md](docs/painel.md))

## Testes (no computador)
- **`python maker/tinyml/testar_tudo.py`**: roda tudo de uma vez (TinyML em C++, setas do Dabble, filtro e detector, sensor e calibração, regras do Q-learning e a simulação do treino).
- `arduino-cli compile --fqbn esp32:esp32:esp32 maker/firmware/robo`: compila o firmware.
- `pytest mvp`: o endpoint `/robo`. `ROBO_TOKEN=... python maker/simulador/simular_robo.py <url> 8`: manda leituras de teste ao MVP.
- Testes de bancada com as peças: [docs/teste_pecas.md](docs/teste_pecas.md).

## Resultados com o robô
_A preencher depois dos testes de bancada: distâncias medidas, comportamento nas 6 situações, taxa de acerto com dados reais, vídeo._

## Vídeo
Link do vídeo: _a preencher_.
