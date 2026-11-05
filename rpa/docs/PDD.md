# PDD: alertas de chuva

**Processo:** atualizar os alertas de chuva do MVP.
**Início:** agenda do GitHub Actions, a cada 3 horas (ou execução manual).
**Entradas:** lista de regiões com latitude e longitude; API Open-Meteo.
**Saída:** `mvp/data/alertas.json` e linhas no `logs/rpa.log`.

| Etapa | O que acontece |
|---|---|
| 1 | Ler a lista de regiões. |
| 2 | Para cada região: se o id já foi visto, avisar no log e pular. |
| 3 | Consultar a previsão por hora do dia. Em caso de erro, esperar e tentar de novo até 3 vezes; se falhar, registrar o erro e seguir para a próxima. |
| 4 | Calcular o maior acumulado de 3 horas seguidas (nulo e negativo contam como 0). |
| 5 | Classificar: alto (15 mm ou mais), médio (5 mm ou mais), baixo. |
| 6 | Guardar o alerta e registrar no log. |
| 7 | No fim, se pelo menos uma região deu certo, gravar `alertas.json`; senão, manter o arquivo anterior. |
| 8 | Registrar o resumo (quantas deram certo e quantas falharam). |

**Exceções:** API fora do ar, resposta sem o campo esperado, valor nulo ou negativo, região repetida.
**Intervenção humana:** nenhuma no fluxo normal. Se todas as regiões falharem, o programa termina com erro e o GitHub Actions marca a execução como falha.
**Dados pessoais:** nenhum.
