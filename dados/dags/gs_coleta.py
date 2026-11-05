from pathlib import Path

import pendulum
from airflow.sdk import DAG, Variable
from airflow.providers.standard.operators.empty import EmptyOperator
from airflow.providers.standard.operators.python import PythonOperator

import coleta

CHEGADA = Path(Variable.get("CHEGADA_DIR", default="/tmp/chegada"))

with DAG(
    "gs_coleta",
    schedule="@daily",
    start_date=pendulum.datetime(2026, 10, 20, tz="America/Sao_Paulo"),
    end_date=pendulum.datetime(2026, 10, 28, tz="America/Sao_Paulo"),
    catchup=True,
    max_active_runs=2,
    default_args={"retries": 2},
) as dag:
    inicio = EmptyOperator(task_id="inicio")
    clima = PythonOperator(task_id="coletar_clima", python_callable=lambda ds, **_: coleta.coletar_clima(ds, CHEGADA))
    distritos = PythonOperator(task_id="coletar_distritos", python_callable=lambda ds, **_: coleta.coletar_distritos(ds, CHEGADA))
    robo = PythonOperator(task_id="leituras_robo", python_callable=lambda ds, **_: coleta.leituras_robo(ds, CHEGADA))
    conferir = PythonOperator(task_id="conferir_chegada", python_callable=lambda ds, **_: coleta.conferir_chegada(ds, CHEGADA))

    inicio >> [clima, distritos, robo] >> conferir
