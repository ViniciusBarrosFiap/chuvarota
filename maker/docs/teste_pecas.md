# Testes quando as peças chegarem

Nesta ordem. Cada passo tem o que esperar; se não bater, não passe para o próximo.

**Preparação (uma vez)**
1. Arduino IDE ou `arduino-cli` com o pacote `esp32` (versão 3.x) e a placa "ESP32 Dev Module".
2. Copie `firmware/robo/config.example.h` para `config.h` e preencha o Wi-Fi e o token (o mesmo valor que está no `terraform.tfvars`, chave `robo_token`).

| # | Teste | Como | Esperado |
|---|---|---|---|
| 1 | Placa viva | gravar `firmware/teste_pecas/teste_pecas.ino` e abrir o Monitor Serial (115200) | aparece `pronto: m, d, l, b ou t` |
| 2 | Motores (sem as rodas no chão) | digitar `m` | gira um motor de cada vez, para frente e para trás. Se algum girar ao contrário, troque os dois fios dele no L298N |
| 3 | Distância | digitar `d` com a mão a 10, 20 e 50 cm | valores perto de 10, 20 e 50 (erro de 1 a 2 cm). `-1` = sem eco (confira o divisor 1k/2k do ECHO) |
| 4 | LDR | digitar `l` com o sensor coberto e com uma lanterna | valor baixo no escuro e alto com luz. **Anote os dois**: são o `LDR_ESCURO` e o `LDR_CLARO` do `config.h` |
| 5 | Buzzer | digitar `b` | apita 0,3 s |
| 6 | Rede | gravar `firmware/robo/robo.ino` (com `MODO_COLETA 0`) com o robô no colo | no Monitor Serial aparece `envio: {...} -> 201` e a leitura aparece na tela do MVP |
| 7 | Autonomia | colocar o robô no chão, com um obstáculo à frente | desvia sozinho; no escuro com obstáculo, apita 3 vezes e manda alerta |

**Dados reais para o TinyML (opcional, melhora o modelo)**
1. `MODO_COLETA 1` no `config.h` e gravar o `robo.ino`.
2. `pip install pyserial` e `python maker/tinyml/coletar.py /dev/cu.usbserial-XXXX`.
3. Com o robô parado, varie luz e distância e digite `0` (ok), `1` (pouca luz), `2` (obstáculo) ou `3` (escuro e obstáculo). Colete uns 5 minutos de cada situação.
4. `python maker/tinyml/treinar.py` (usa o `dados_reais.csv` quando existe) e `python maker/tinyml/testar_c.py`.
5. Voltar `MODO_COLETA` para 0 e regravar o robô.

**Se der problema**
- Reinicia sozinho ao ligar os motores: a bateria não segura a corrente; use pilhas novas ou outra bateria, e confira o GND comum.
- `envio -> -1`: sem Wi-Fi ou senha errada. `envio -> 401`: token diferente do que está no Azure.
- A distância fica sempre em 200: o ECHO não chega ao ESP32.
