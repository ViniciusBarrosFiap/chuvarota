# Carro robô ChuvaRota (Project-Based Maker Lab)

Integrante: **Vinicius Barros, RM 97824**

Carro robô com ESP32 que anda sozinho, desvia de obstáculos, mede a luz do ambiente com um **LDR (sensor novo)** e usa um **modelo TinyML** para entender o que está acontecendo. Quando acha uma situação de risco (ponto escuro com obstáculo, lâmpada piscando, algo vindo rápido), o robô reage e manda um alerta ao MVP do ChuvaRota, que mostra as leituras em tempo real.

> **Estado atual:** firmware, modelo TinyML e integração com o MVP estão prontos e testados no computador (o firmware compila, o C++ decide igual ao Python e o endpoint está no ar no Azure). **O carrinho ainda não foi montado**, então nada foi testado no hardware: a seção "Resultados com o robô" abaixo será preenchida depois dos testes de bancada.

## Montar e gravar (resumo)
1. Ligar as peças como em [docs/ligacao.png](docs/ligacao.png) (pinos e divisor do ECHO em [docs/teste_pecas.md](docs/teste_pecas.md)).
2. Conectar o ESP32 por USB (cabo de dados) e rodar:
```
./maker/firmware/configurar.sh     # pergunta o Wi-Fi (2,4 GHz) e cria o config.h com o token do MVP
./maker/firmware/gravar.sh         # compila, grava e abre o Monitor Serial
```
3. Antes disso, se quiser testar cada peça sozinha: `./maker/firmware/gravar.sh teste_pecas`.

Não precisa calibrar o LDR (o robô aprende o mais escuro e o mais claro que vê) nem mexer no código: motor ao contrário, velocidade e tempo de giro se ajustam no `config.h`.

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

![ligação](docs/ligacao.png)

## Como funciona
1. A cada 100 ms o robô lê a distância (mediana de 3 medidas) e a luz (média de 8 leituras, normalizada de 0 a 1 pela autocalibração).
2. Guarda as últimas 8 leituras (0,8 s) e calcula 5 características: luz média, oscilação e amplitude da luz, distância mediana e a velocidade com que a distância muda.
3. O modelo TinyML escolhe uma de 6 situações:

| classe | significado | o que o robô faz |
|---|---|---|
| `ok` | claro e caminho livre | anda em velocidade normal |
| `pouca_luz` | ambiente escuro, caminho livre | anda devagar e acende o LED |
| `obstaculo` | algo a menos de 30 cm | recua e vira |
| `escuro_e_obstaculo` | escuro com algo à frente | para, apita 3 vezes, manda alerta na hora e desvia |
| `luz_piscando` | a luz oscila (lâmpada com defeito) | segue devagar e avisa ao MVP (no máximo a cada 30 s) |
| `objeto_se_aproximando` | algo vem rápido na direção do robô | freia e recua antes de chegar perto |

4. Uma regra de segurança fica **acima** do modelo: a menos de 8 cm o robô para, mesmo que o modelo erre. Situações de risco valem na hora; as demais só trocam depois de 2 decisões iguais seguidas.
5. Outra tarefa do ESP32 envia a situação ao MVP a cada 5 s (e na hora no caso de alerta), por HTTPS com a hora acertada por NTP, sem travar o robô.

Autonomia: depois de ligado, o robô não recebe nenhum comando manual.

## TinyML
- Rede neural pequena: 5 entradas, camadas de 16 e 8 neurônios (ReLU) e 6 saídas, **286 parâmetros (cerca de 1 KB)**. O treino é em Python (`tinyml/treinar.py`, scikit-learn) e o resultado vira um arquivo C++ (`firmware/robo/modelo_tinyml.h`) que roda no ESP32 sem biblioteca nenhuma.
- **Dados: simulados**, porque o robô ainda não existe. `tinyml/simular_sensores.py` simula a rua (luz e distância verdadeiras) e as leituras com os defeitos dos sensores: ruído do LDR, calibração errada em ±8%, HC-SR04 que às vezes não ouve eco ou lê um valor falso, lâmpada que pisca e objetos que se aproximam. São 5.000 episódios de 40 s (346,500 janelas de treino, 74,250 de validação e 74,250 de teste, separados por episódio). Os rótulos vêm dos limites que eu defini (escuro: luz menor que 0,30; obstáculo: menos de 30 cm; aproximando: mais de 40 cm/s a menos de 100 cm).
- **Treino com ruído variado** (0,5 a 3 vezes o previsto) e busca de hiperparâmetros: 27 arquiteturas na primeira rodada (todas empataram em F1 entre 0,91 e 0,93; a maior, com 2.662 parâmetros, ficou menos robusta ao ruído) e uma segunda rodada focada. Escolhi o **menor modelo dentro de 0,003 do melhor**.
- O modelo escolhido foi comparado com duas soluções clássicas, no mesmo teste:

| | acerto | F1 macro |
|---|---|---|
| decidir só pela última leitura (sem janela) | 81,7% | 0.57 |
| limites fixos sobre as mesmas características | 87,1% | 0.81 |
| **modelo TinyML** | **95,1%** | **0.93** |

- **Robustez** (F1 macro com sensores mais ruidosos que o previsto): ruído 1x: modelo 0.93 contra 0.81 das regras; 2x: 0.91 contra 0.81; 3x: 0.89 contra 0.79.
- Pior classe: `objeto_se_aproximando` (precisão 0.80, recall 0.90), porque o limite entre "aproximando" e "obstáculo" é difuso.

![matriz de confusão](tinyml/matriz_confusao.png)

- `tinyml/testar_c.py` compila o C++ do robô no computador e confere que ele decide **igual** ao Python a partir das leituras brutas (100% de 400 janelas).
- **Limite importante:** esses números medem o quanto o modelo lida com ruído e falhas que **eu simulei**, não o desempenho no robô. Quando o carrinho estiver montado, o `tinyml/coletar.py` grava dados reais (passos em [docs/teste_pecas.md](docs/teste_pecas.md)) e o `treinar.py` passa a usá-los automaticamente.

## Integração com o MVP
`POST /robo` recebe `{luz_pct, distancia_cm, situacao}` com o cabeçalho `X-Token`; `GET /robo` devolve as últimas leituras, que aparecem na tela inicial do MVP: https://chuvarota-85ixn.azurewebsites.net

- O token fica em `config.h` (fora do Git, criado pelo `configurar.sh`) e no Azure (configurado pelo Terraform, não está no código).
- O robô valida o certificado do MVP (raiz DigiCert Global Root G2 em `cert_raiz.h`); não desliga a verificação de TLS.
- Não há dado pessoal: só luz, distância e a classe. O MVP guarda as últimas 50 leituras em memória.

## Pastas
- `firmware/robo/` firmware do robô (`robo.cpp`; o `robo.ino` é só o arquivo principal que o Arduino exige), `caracteristicas.h`, `modelo_tinyml.h` (gerado), `cert_raiz.h`, `config.example.h`
- `firmware/teste_pecas/` sketch para testar cada peça sozinha
- `firmware/configurar.sh` e `firmware/gravar.sh`
- `tinyml/` simulador dos sensores, características, treino, testes e coleta de dados reais
- `simulador/` finge ser o robô para testar o endpoint do MVP
- `docs/` ligação, testes de bancada e roteiro do vídeo

## Testes
- `python maker/tinyml/testar_c.py`: o C++ decide igual ao Python.
- `arduino-cli compile --fqbn esp32:esp32:esp32 maker/firmware/robo` (com um `config.h`): compila.
- `pytest mvp`: o endpoint `/robo` (sem token, token errado, leitura inválida e válida).
- `ROBO_TOKEN=... python maker/simulador/simular_robo.py <url> 8`: manda leituras de teste ao MVP.
- Testes de bancada com as peças: [docs/teste_pecas.md](docs/teste_pecas.md).

## Resultados com o robô
_A preencher depois dos testes de bancada: distâncias medidas, comportamento nas 6 situações, taxa de acerto com dados reais, vídeo._

## Vídeo
Roteiro em [docs/roteiro_video.md](docs/roteiro_video.md). Link do vídeo: _a preencher_.
