# Databricks notebook source
from pyspark.sql import functions as F, Window

S = "workspace.gs."
clima = spark.table(S + "prata_clima")

# dimensões
(clima.select("regiao_id", F.col("regiao_nome").alias("nome")).distinct()
    .join(spark.table(S + "prata_distritos").withColumnRenamed("nome", "nome_distrito"),
          F.col("nome") == F.col("nome_distrito"), "left")
    .select("regiao_id", "nome", "distrito_id")
    .write.mode("overwrite").saveAsTable(S + "dim_regiao"))

(clima.select("data_hora").distinct()
    .select("data_hora", F.to_date("data_hora").alias("data"), F.hour("data_hora").alias("hora"))
    .write.mode("overwrite").saveAsTable(S + "dim_tempo"))

# fato: risco pelo acumulado de 3 horas (mesma regra do RPA)
janela = Window.partitionBy("regiao_id").orderBy("data_hora").rowsBetween(-2, 0)
(clima.withColumn("chuva_3h", F.sum("chuva_mm").over(janela))
    .withColumn("risco", F.when(F.col("chuva_3h") >= 15, "alto")
                          .when(F.col("chuva_3h") >= 5, "medio")
                          .otherwise("baixo"))
    .select("regiao_id", "data_hora", "chuva_mm", "chuva_3h", "risco")
    .write.mode("overwrite").saveAsTable(S + "fato_chuva"))

# o id do robô vira hash
(spark.table(S + "prata_robo")
    .withColumn("device_hash", F.sha2("device_id", 256))
    .drop("device_id")
    .write.mode("overwrite").saveAsTable(S + "fato_leitura_robo"))

spark.sql(f"""CREATE OR REPLACE TABLE {S}ouro_mvp AS
              SELECT r.nome AS regiao,
                     ROUND(SUM(f.chuva_mm), 1) AS chuva_total_mm,
                     SUM(CASE WHEN f.risco = 'alto' THEN 1 ELSE 0 END) AS horas_risco_alto
              FROM {S}fato_chuva f JOIN {S}dim_regiao r USING (regiao_id)
              GROUP BY r.nome""")
