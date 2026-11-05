# Databricks notebook source
from pyspark.sql import functions as F

S = "workspace.gs."

clima = (spark.table(S + "bronze_clima")
         .withColumn("hourly", F.from_json("hourly", "struct<time:array<string>,precipitation:array<double>>"))
         .select("regiao_id", "regiao_nome",
                 F.explode(F.arrays_zip(F.col("hourly.time"), F.col("hourly.precipitation"))).alias("h"))
         .select("regiao_id", "regiao_nome",
                 F.to_timestamp("h.time").alias("data_hora"),
                 F.col("h.precipitation").cast("double").alias("chuva_mm")))

nulos = clima.filter("chuva_mm IS NULL OR data_hora IS NULL")
negativos = clima.filter("chuva_mm < 0")
absurdos = clima.filter("chuva_mm > 100")
print("nulos barrados:", nulos.count())
print("negativos barrados:", negativos.count())
print("acima de 100mm barrados:", absurdos.count())

limpo = (clima.filter("chuva_mm IS NOT NULL AND data_hora IS NOT NULL AND chuva_mm >= 0 AND chuva_mm <= 100")
         .dropDuplicates(["regiao_id", "data_hora"]))
limpo.createOrReplaceTempView("lote_clima")

spark.sql(f"""CREATE TABLE IF NOT EXISTS {S}prata_clima
              (regiao_id STRING, regiao_nome STRING, data_hora TIMESTAMP, chuva_mm DOUBLE)""")
spark.sql(f"""MERGE INTO {S}prata_clima a USING lote_clima n
              ON a.regiao_id = n.regiao_id AND a.data_hora = n.data_hora
              WHEN MATCHED THEN UPDATE SET *
              WHEN NOT MATCHED THEN INSERT *""")

# COMMAND ----------

(spark.table(S + "bronze_distritos")
    .select(F.col("id").cast("long").alias("distrito_id"), F.col("nome"))
    .dropna().dropDuplicates(["distrito_id"])
    .write.mode("overwrite").saveAsTable(S + "prata_distritos"))

(spark.table(S + "bronze_robo")
    .select("device_id", "regiao_id",
            F.to_timestamp("data_hora").alias("data_hora"),
            F.col("umidade_pct").cast("double").alias("umidade_pct"))
    .filter("umidade_pct BETWEEN 0 AND 100")
    .dropDuplicates(["device_id", "data_hora"])
    .write.mode("overwrite").saveAsTable(S + "prata_robo"))

print("prata_clima:", spark.table(S + "prata_clima").count())
