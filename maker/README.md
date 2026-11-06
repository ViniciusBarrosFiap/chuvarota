# Carro robô ChuvaRota (Project-Based Maker Lab)

Integrante: **Vinicius Barros, RM 97824**

Carro robô com ESP32 que anda sozinho, desvia de obstáculos, mede a luz do ambiente com um **LDR (sensor novo)** e usa um **modelo TinyML** para classificar o que está vendo. Quando acha um ponto escuro com algo à frente, o robô para, apita e manda um alerta ao MVP do ChuvaRota, que mostra as leituras em tempo real.

> **Estado atual:** o firmware compila (`arduino-cli`, pacote esp32 3.3.12: 79% da flash e 14% da memória), o modelo TinyML está treinado e testado no computador e o endpoint do MVP está no ar e testado. O carrinho ainda não foi montado (as peças estão a caminho): o item "Resultados com o robô" abaixo será preenchido depois dos testes de bancada.

## Problema (CitizenTech)
Pontos de ônibus, calçadas e ruas mal iluminados, principalmente em dia de chuva e à noite, aumentam o risco de acidentes e de crimes, e a prefeitura só descobre quando alguém reclama. O robô percorre o local, mede a luz e a distância até os obstáculos e avisa onde precisa de atenção. Contribui para os ODS 11 (cidades sustentáveis) e 9 (infraestrutura).

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

![ligação](docs/ligacao.png)

## Como funciona
1. A cada 100 ms o robô lê a distância (mediana de 3 medidas) e a luz (média de 8 leituras, normalizada de 0 a 1 com a calibração do `config.h`).
2. O modelo TinyML recebe `luz` e `distância` e escolhe uma de 4 situações:

| classe | significado | o que o robô faz |
|---|---|---|
| `ok` | claro e caminho livre | anda em velocidade normal |
| `pouca_luz` | ambiente escuro, caminho livre | anda devagar e acende o LED |
| `obstaculo` | algo a menos de 30 cm | recua e vira |
| `escuro_e_obstaculo` | escuro com algo à frente | para, apita 3 vezes, manda alerta na hora e desvia |

3. Uma regra de segurança fica **acima** do modelo: a menos de 8 cm o robô para, mesmo que o modelo erre.
4. Outra tarefa do ESP32 envia a situação ao MVP a cada 5 s (e na hora no caso de alerta), por HTTPS, sem travar o robô.

Autonomia: depois de ligado, o robô não recebe nenhum comando manual.

## TinyML
- Rede neural com 1 camada escondida de 8 neurônios (ReLU): **60 parâmetros**, 1,5 KB. O treino é em Python (`tinyml/treinar.py`, scikit-learn) e o resultado vira um arquivo C (`firmware/robo/modelo_tinyml.h`) que roda no ESP32 sem biblioteca nenhuma.
- `tinyml/testar_c.py` compila esse código C no computador e confere que ele decide **igual** ao modelo Python (100% de 800 amostras).
- **Dados:** por enquanto são **sintéticos** (`tinyml/gerar_dados.py`, 4.000 amostras com ruído de sensor, rótulos por limites de 0,30 de luz e 30 cm), porque o robô ainda não existe. Acerto no teste: **94,3%**. Esse número mede o quanto o modelo aprendeu as regras, não o desempenho no robô.
- Quando o robô estiver montado, o `tinyml/coletar.py` grava dados reais (passos em [docs/teste_pecas.md](docs/teste_pecas.md)) e o `treinar.py` passa a usá-los automaticamente.

## Integração com o MVP
`POST /robo` recebe `{luz_pct, distancia_cm, situacao}` com o cabeçalho `X-Token`; `GET /robo` devolve as últimas leituras, que aparecem na tela inicial do MVP: https://chuvarota-85ixn.azurewebsites.net

- O token fica em `config.h` (fora do Git) e no Azure (configurado pelo Terraform, não está no código).
- O robô valida o certificado do MVP (raiz DigiCert Global Root G2 em `cert_raiz.h`); não desliga a verificação de TLS.
- Não há dado pessoal: só luz, distância e a classe. O MVP guarda as últimas 50 leituras em memória.

## Pastas
- `firmware/robo/` firmware do robô (`robo.cpp`; o `robo.ino` é só o arquivo principal que o Arduino exige, `modelo_tinyml.h`, `cert_raiz.h`, `config.example.h`)
- `firmware/teste_pecas/` sketch para testar cada peça sozinha
- `tinyml/` dados, treino, exportação para C, teste do código C e coleta de dados reais
- `simulador/` finge ser o robô para testar o endpoint do MVP
- `docs/` ligação, testes de bancada e roteiro do vídeo

## Como compilar e gravar
Pacote `esp32` 3.x do Arduino e a placa "ESP32 Dev Module".
```
cp maker/firmware/robo/config.example.h maker/firmware/robo/config.h   # preencher Wi-Fi e token
arduino-cli compile --fqbn esp32:esp32:esp32 maker/firmware/robo
arduino-cli upload  --fqbn esp32:esp32:esp32 -p /dev/cu.usbserial-XXXX maker/firmware/robo
```

## Testes
- `python maker/tinyml/testar_c.py`: o código C decide igual ao Python.
- `pytest mvp`: o endpoint `/robo` (sem token, token errado, leitura inválida e leitura válida).
- `ROBO_TOKEN=... python maker/simulador/simular_robo.py <url> 8`: manda leituras de teste ao MVP.
- Testes de bancada com as peças: [docs/teste_pecas.md](docs/teste_pecas.md).

## Resultados com o robô
_A preencher depois dos testes de bancada: calibração do LDR, distâncias medidas, taxa de acerto do modelo com dados reais, vídeo._

## Vídeo
Roteiro em [docs/roteiro_video.md](docs/roteiro_video.md). Link do vídeo: _a preencher_.
