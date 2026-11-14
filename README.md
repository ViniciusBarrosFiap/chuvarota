# ChuvaRota

Vinicius Oliveira de Barros, RM 97824 (FIAP, Global Solution 2026, CitizenTech)

ChuvaRota avisa quem anda a pé ou de ônibus em São Paulo se vai chover forte na região dele, para ninguém ser pego de surpresa por um alagamento. Este repositório tem o site (MVP), a automação que atualiza os alertas e toda a parte de nuvem e segurança (DevOps).

Site no ar: https://chuvarota-85ixn.azurewebsites.net

## Teste rápido (para quem vai avaliar)
1. Abra o site no ar: https://chuvarota-85ixn.azurewebsites.net (se demorar uns segundos no primeiro acesso, é o plano gratuito acordando).
2. Veja o pipeline na aba **Actions** deste repositório. Esta execução foi **barrada** pela verificação de segurança: https://github.com/ViniciusBarrosFiap/chuvarota/actions/runs/43599824816 e esta é a **corrigida**: https://github.com/ViniciusBarrosFiap/chuvarota/actions/runs/43599902680
3. Para rodar na sua máquina (precisa do Docker): `docker compose up --build`. O site abre em http://localhost:8000, o Prometheus em 9090 e o Grafana em 3000.
4. Os prints do painel, do alerta e da nuvem estão no relatório [infra/relatorio_devops.pdf](infra/relatorio_devops.pdf).

## Ficha técnica
| Item | Conteúdo |
|---|---|
| Quem usa | Quem se desloca a pé ou de ônibus em São Paulo |
| Problema | A chuva forte e o alagamento pegam o cidadão sem aviso por região e sem orientação do que fazer |
| O que o produto entrega | Risco de chuva por região, orientação da Defesa Civil e alerta no local por sensor |
| Como funciona | A automação (RPA) busca a previsão e gera os alertas, e o site mostra. Dados, IA, visão e o carrinho ficam em repositórios à parte |
| Dados usados | Open-Meteo (previsão), IBGE (distritos) e cartilhas da Defesa Civil |
| IA | Assistente de orientação (LLM local), detector de nível de água em ônibus (YOLO) e IA pequena no carrinho |
| Impacto | Alertas emitidos, antecedência do alerta e leituras locais confirmadas pelo carrinho |
| ODS | 11 (cidades sustentáveis) e 13 (ação contra a mudança do clima) |

## Cada disciplina tem o seu repositório
| Disciplina | Onde está |
|---|---|
| Dados | https://github.com/ViniciusBarrosFiap/chuvarota-dados |
| Automação (RPA) | aqui, na pasta `rpa/` (usa o GitHub Actions deste repositório) |
| IA generativa | https://github.com/ViniciusBarrosFiap/chuvarota-ia |
| Visão computacional | https://github.com/ViniciusBarrosFiap/chuvarota-visao |
| DevOps | aqui (`Dockerfile`, `.github/`, `infra/` e `monitoring/`) |
| Maker | https://github.com/ViniciusBarrosFiap/chuvarota-maker |

## Pastas
- `mvp/`: o site (FastAPI) e os dados que ele mostra
- `rpa/`: a automação dos alertas
- `infra/`: a nuvem no Azure, criada com Terraform
- `monitoring/`: Prometheus e Grafana
- `.github/workflows/`: o pipeline de segurança e de publicação, e o agendamento da automação

## Como rodar
Com Docker, sobe o site, o Prometheus (porta 9090) e o Grafana (porta 3000):

```
docker compose up --build
```

O site fica em http://localhost:8000. Sem Docker:

```
pip install -r mvp/requirements.txt
cd mvp && uvicorn app:app
```

## DevOps
- A cada push o GitHub Actions procura senhas vazadas (Gitleaks), erros de segurança no código (Semgrep), roda os testes, olha a imagem e o Terraform atrás de falhas (Trivy) e só então publica no Azure.
- A nuvem é criada pelo Terraform (pasta `infra/`).
- O relatório completo, com prints, está em [infra/relatorio_devops.pdf](infra/relatorio_devops.pdf).
