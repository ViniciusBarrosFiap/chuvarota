# ChuvaRota — Ficha Técnica do MVP
| Item | Conteúdo |
|---|---|
| Nome | ChuvaRota |
| Cidadão e território | Quem se desloca a pé ou de ônibus em São Paulo |
| Problema | Chuva forte e alagamento pegam o cidadão sem aviso por região nem orientação |
| Proposta de valor | Risco de chuva por região, orientação com fonte da Defesa Civil e alerta local por sensor |
| Arquitetura | RPA (alertas) → MVP FastAPI ← robô ESP32 (sensor); Airflow/Databricks (dados); LLM local (RAG); YOLO (fotos) |
| Fontes de dados | Open-Meteo, IBGE, cartilhas da Defesa Civil |
| Modelos de IA | LLM local + RAG/agente, YOLOv8n, TinyML no robô |
| URL / repositório | https://github.com/ViniciusBarrosFiap/chuvarota |
| Indicadores de impacto | Alertas emitidos, antecedência média, leituras locais confirmadas |
| ODS | 11 (cidades sustentáveis), 13 (ação climática) |

Autor: Vinicius Barros, RM 97824

Pastas: `dados/` (Big Data), `rpa/` (automação), `mvp/` (API e tela), `maker/` (robô).

Para rodar o MVP: `pip install -r mvp/requirements.txt` e `cd mvp && uvicorn app:app`.
