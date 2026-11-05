#!/bin/bash
# sobe só a interface e o leitor de DAGs (o scheduler dá erro no meu mac)
cd "$(dirname "$0")/.."
export no_proxy='*' PATH=$PWD/.venv-af/bin:$PATH AIRFLOW_HOME=$PWD/airflow_home
export AIRFLOW__CORE__DAGS_FOLDER=$PWD/dados/dags AIRFLOW__CORE__LOAD_EXAMPLES=False
export AIRFLOW_VAR_CHEGADA_DIR=$PWD/dados/chegada PYTHONPATH=$PWD/dados/dags
airflow dag-processor &
airflow api-server --port 8080
