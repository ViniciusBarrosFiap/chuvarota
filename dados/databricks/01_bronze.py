# Databricks notebook source
from pyspark.sql import functions as F

BASE = "/Volumes/workspace/gs/chegada"
spark.sql("CREATE SCHEMA IF NOT EXISTS workspace.gs")


def carregar(pasta, tabela, multiline="false"):
    leitura = (spark.readStream.format("cloudFiles")
               .option("cloudFiles.format", "json")
               .option("multiLine", multiline)
               .option("cloudFiles.schemaLocation", f"{BASE}/_controle/schema_{pasta}")
               .load(f"{BASE}/{pasta}")
               .withColumn("arquivo_origem", F.col("_metadata.file_path"))
               .withColumn("carregado_em", F.current_timestamp()))
    (leitura.writeStream
        .option("checkpointLocation", f"{BASE}/_controle/ckpt_{pasta}")
        .trigger(availableNow=True)
        .toTable(f"workspace.gs.{tabela}")
        .awaitTermination())


carregar("clima", "bronze_clima")
carregar("distritos", "bronze_distritos", "true")
carregar("robo", "bronze_robo", "true")

# COMMAND ----------

for t in ["bronze_clima", "bronze_distritos", "bronze_robo"]:
    print(t, spark.table(f"workspace.gs.{t}").count())
