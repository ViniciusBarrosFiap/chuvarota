# ChuvaRota — Ficha Técnica do MVP
| Item | Conteúdo |
|---|---|
| Nome | ChuvaRota |
| Cidadão e território | Quem se desloca a pé ou de ônibus em São Paulo |
| Problema | Chuva forte e alagamento pegam o cidadão sem aviso por região nem orientação |
| Proposta de valor | Risco de chuva por região, orientação com fonte da Defesa Civil e alerta local por sensor |
| Arquitetura | RPA (alertas) → MVP FastAPI; Airflow/Databricks (dados); LLM local (RAG); YOLOv8 (fotos); robô ESP32 autônomo, dirigido pelo Dabble, sem envio à internet |
| Fontes de dados | Open-Meteo, IBGE, cartilhas da Defesa Civil |
| Modelos de IA | LLM local + RAG/agente, YOLOv8n, TinyML no robô |
| URL / repositório | MVP: https://chuvarota-85ixn.azurewebsites.net · código: https://github.com/ViniciusBarrosFiap/chuvarota |
| Indicadores de impacto | Alertas emitidos, antecedência média, leituras locais confirmadas |
| ODS | 11 (cidades sustentáveis), 13 (ação climática) |

Autor: Vinicius Barros, RM 97824

Pastas: `dados/` (Big Data), `rpa/` (automação), `ia/` (IA generativa), `visao/` (visão computacional, nível de água em ônibus alagados), `mvp/` (API e tela), `infra/` (Terraform, Azure), `monitoring/` (Prometheus e Grafana), `maker/` (robô: um único `robo.ino` e o TinyML).

Para rodar o MVP: `docker compose up --build` (MVP em :8000, Prometheus em :9090, Grafana em :3000) ou `pip install -r mvp/requirements.txt` e `cd mvp && uvicorn app:app`.

DevOps: pipeline em `.github/workflows/devsecops.yml` (Gitleaks, Semgrep, testes, Trivy, publicação), nuvem em `infra/` (Terraform) e relatório em `infra/relatorio_devops.pdf`.
