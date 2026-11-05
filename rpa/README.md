# RPA: alertas de chuva

Automação do ChuvaRota. A cada 3 horas ela consulta a previsão de chuva de 5 regiões de São Paulo, classifica o risco (alto, médio ou baixo) e grava o resultado em `mvp/data/alertas.json`, que o MVP lê na tela inicial e na rota `/alertas`. Antes era preciso consultar o clima na mão e atualizar o arquivo.

Integrante: Vinicius Barros, RM 97824

![fluxo](assets/fluxo_bpmn.png)

## Como funciona
- **Entrada:** lista de regiões (`src/rpa.py`) e a API pública Open-Meteo (sem chave).
- **Repetição:** passa por cada região da lista.
- **Decisão:** maior acumulado de 3 horas seguidas. 15 mm ou mais é alto, 5 mm ou mais é médio, abaixo disso é baixo.
- **Falhas:** região repetida é ignorada; API fora do ar tenta 3 vezes e registra o erro; valores nulos ou negativos viram 0; se nenhuma região der certo, o arquivo anterior é mantido.
- **Log:** `logs/rpa.log` com data e hora, região, chuva, risco e erros. Não há dado pessoal.
- **Saída:** `mvp/data/alertas.json`, consumido pelo MVP via API (`/alertas`).
- **Agendamento:** `.github/workflows/rpa.yml` (GitHub Actions) roda a cada 3 horas e salva o resultado no repositório.

## Como rodar
```
pip install requests pytest
python rpa/src/rpa.py
pytest rpa/tests
```

## Pastas
- `src/` código
- `tests/` testes e `resultado_testes.txt`
- `logs/` log real, amostra de sucesso e amostra de falha
- `docs/` fluxo BPMN (`fluxo_bpmn.svg`) e `PDD.md`
- `assets/` imagens e evidências
