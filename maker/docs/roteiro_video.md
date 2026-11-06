# Roteiro do vídeo (até 6 minutos)

A atividade pede: o problema no contexto CitizenTech, a solução, o robô funcionando, **o sensor novo**, **a integração com a IA** e as principais funcionalidades.

| Tempo | O que mostrar |
|---|---|
| 0:00 | O problema: pontos escuros em ruas e paradas, e a chuva piora a visibilidade. Quem fiscaliza não vê. |
| 0:30 | O robô e as peças (ESP32, LDR, HC-SR04, motores). Dizer qual é o sensor novo: o LDR. |
| 1:00 | **Sensor novo:** cobrir o LDR com a mão e mostrar o valor mudando no Monitor Serial. |
| 1:45 | **IA (TinyML):** o modelo de 286 parâmetros no ESP32, que olha as últimas 8 leituras. Mostrar `modelo_tinyml.h`, a comparação com as regras clássicas (95% contra 87% de acerto na simulação) e a classe que ele escolhe para cada situação. |
| 2:30 | **Autonomia:** o robô anda sozinho, desvia de um obstáculo, e fica mais devagar no escuro. |
| 3:30 | **Escuro e obstáculo:** o robô para, apita 3 vezes e manda o alerta. |
| 4:00 | **Luz piscando e objeto se aproximando:** piscar a lanterna do celular sobre o LDR e vir com a mão rápido; mostrar as duas classes. |
| 4:30 | **Integração:** a tela do MVP (`chuvarota-85ixn.azurewebsites.net`) mostrando as leituras chegando em tempo real. |
| 5:00 | Teste de falha: tirar o Wi-Fi; o robô continua andando e volta a enviar quando a rede volta. |
| 5:30 | Fechamento: o que o robô já resolve e o próximo passo (mapear os pontos escuros). |
