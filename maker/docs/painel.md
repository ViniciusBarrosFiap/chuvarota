# Painel do carrinho (treino em tempo real)

Uma página que mostra o treino acontecendo, deixa você configurá-lo e estima quanto tempo falta, tudo com gráficos. Não precisa instalar nada: é um arquivo, `maker/painel/index.html`.

> **Estado:** testado em um navegador de verdade (sem janela) com uma porta serial simulada e com a demonstração. **Ainda não foi testado com o carrinho real.**

## O que você precisa
- **Chrome ou Edge**, no computador (o Firefox e o Safari não têm a função que fala com a porta USB).
- Cabo USB **de dados** ligado ao ESP32.
- O `robo.ino` novo gravado (ele passou a mandar a telemetria e a aceitar os ajustes do painel).
- O **Monitor Serial do Arduino IDE fechado**: a porta só aceita um programa por vez.

## Passo a passo
1. Dê duplo clique em `maker/painel/index.html` (ou arraste para o Chrome/Edge).
2. Para conhecer sem o carrinho, clique em **Ver demonstração**. É o replay de um treino simulado (não são dados do carrinho). Use os botões 1×, 10×, 50× e 200× para acelerar.
3. Com o carrinho ligado no USB, clique em **Conectar ao carrinho (USB)** e escolha a porta (aparece como CP210x, CH340 ou COM3, COM5...).
4. **O carrinho reinicia ao conectar** e fica parado, em modo manual. Em uns 3 segundos o painel preenche os ajustes, a curva de aprendizado e o que ele já aprendeu.
5. Escolha uma **receita** (ou ajuste à mão) em "Configurar o treino" e veja o **tempo estimado** mudar na hora.
6. Coloque o carrinho **no chão, em um espaço livre e sem degraus**, e clique em **Iniciar treino**. O painel pede uma confirmação antes, porque o carrinho vai andar sozinho.
7. Acompanhe. Quando chegar na meta, o carrinho para sozinho, salva e apita 5 vezes. Para parar antes, clique em **Parar**.

## O que cada parte mostra
| Parte | O que mostra |
|---|---|
| **Treino agora** | A ação que ele está fazendo, passos de treino contra a meta, **tempo restante estimado**, quanto ele ainda explora, distância do freio, freios de segurança e fugas de canto, e a que horas deve terminar |
| **Distância à frente, ao vivo** | A distância lida pelo sensor nos últimos 60 s, com as faixas coloridas (freio, perigo, perto, médio, longe) e, embaixo, uma faixa colorida com a ação de cada instante |
| **O que o carrinho vê** | Visão de cima: o carrinho, o alcance do sensor em zonas coloridas e para onde ele pretende ir |
| **Curva de aprendizado** | A nota média por bloco de 100 passos (subir = aprendendo) e as quase-batidas e freios (cair = aprendendo) |
| **O que ele aprendeu** | A melhor ação que ele conhece para cada distância e tendência (aproximando, estável, afastando) |
| **Freio e exploração** | Como a distância do freio e a exploração mudam ao longo do treino |

## Como o tempo estimado é calculado
**Tempo restante = passos que faltam até a meta × segundos por passo.**
- Os segundos por passo são **medidos** no carrinho (variação dos passos nos últimos 2 minutos). Enquanto não há dados suficientes (uns 15 s de treino), o painel usa o valor da última sessão e, se não houver, estima pela duração da ação (`ciclos por ação × 0,15 s`). Isso aparece marcado como "estimado" ou "da última sessão".
- Se você definir um **tempo máximo**, vale o que vier primeiro.
- Também mostra em que passo a exploração chega a 10%.
É uma estimativa: o ritmo muda conforme o ambiente (freios e fugas gastam tempo).

## O que você pode configurar
| Ajuste | O que faz |
|---|---|
| Meta de passos | Para de treinar quando o total chega aqui (0 = sem meta) |
| Tempo máximo da sessão | Para depois de tantos minutos |
| Exploração no começo e no fim | Quanto ele testa ações aleatórias no início e no fim do treino |
| Rapidez da queda da exploração | Quantos passos para a exploração cair a 37% do valor inicial |
| Duração de cada ação | Ciclos (~0,15 s) que ele mantém uma ação. Mais = mais suave, mas aprende mais devagar |
| Freio mínimo | Ele nunca freia mais perto que isso (limite de segurança) |
| Ajustar o freio sozinho | Mede o espaço que sobra depois de frear e chega mais perto aos poucos |
| Começar com um palpite inicial | Vale ao apagar o aprendizado |

Os ajustes ficam na memória do carrinho **até ele ser desligado**: o painel guarda os seus valores no navegador e os reenvia a cada "Iniciar treino". Para um ajuste ficar para sempre, mude o `config.h`.

## Limites que você precisa saber
- **O cabo USB prende o carrinho.** Use um cabo comprido ou um espaço de treino pequeno. Para treinar sem cabo, use o Dabble (círculo) e depois conecte o USB só para ver os resultados.
- **Conectar reinicia o carrinho.** Ele não continua um treino que estava em andamento: começa em modo manual. O que ele aprendeu continua salvo.
- Com o **Dabble ligado** o envio ao MVP fica desligado (não sobra memória). O painel funciona junto com o Dabble.
- Sem o carrinho, a demonstração mostra um treino **simulado**: serve para conhecer o painel, não para avaliar o carrinho.

## Se não funcionar
| Sintoma | O que fazer |
|---|---|
| O botão de conectar está desabilitado | Abra a página no Chrome ou no Edge |
| Não aparece nenhuma porta | Troque o cabo (tem que ser de dados) e instale o driver CP210x ou CH340 |
| "Não consegui abrir a porta" | Feche o Monitor Serial do Arduino IDE e outros programas que usam a porta |
| "O carrinho não respondeu" | Confira se o `robo.ino` novo foi gravado e aperte EN na placa |
| Os números não mexem | O carrinho está em modo manual: clique em **Iniciar treino** |

## Para quem quer mexer
- Comandos que o painel manda (linhas terminadas em Enter, também dá para usar no Monitor Serial): `painel 1` liga a telemetria, `cfg?` lista os ajustes, `cfg nome valor` muda um ajuste, `modo manual|autonomo|treino|ia` troca o modo e as letras de sempre (`e`, `q`, `z`...). `?` lista tudo.
- Telemetria (uma linha por ciclo): `~ms,distância,luz,classe,modo,ação,explorando,freio,passos,exploração`. Os formatos estão em `robo.ino` e são conferidos contra a demonstração por `python maker/tinyml/testar_protocolo.py`.
- Testes do painel: `node maker/painel/testar_painel.js` (precisa do Playwright: `npm i playwright && npx playwright install chromium`).
- A demonstração é gerada por `python maker/tinyml/gerar_demo_painel.py` (a semente 2 é a mediana entre 6 testadas, não a melhor).
