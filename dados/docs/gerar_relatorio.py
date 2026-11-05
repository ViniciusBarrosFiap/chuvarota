import subprocess
from pathlib import Path

NOME = "Vinicius Barros"
RM = "97824"
REPO = "https://github.com/ViniciusBarrosFiap/chuvarota"
AQUI = Path(__file__).parent
ASSETS = AQUI.parent / "assets"
fluxo = (AQUI / "fluxo.svg").read_text(encoding="utf-8")


def img(arq, legenda):
    return f'<figure><img src="{(ASSETS / arq).as_uri()}"><figcaption>{legenda}</figcaption></figure>'


req = [
    ("01 Fontes de dados",
     "Duas fontes reais e públicas: a API de arquivo do Open-Meteo (chuva por hora, uma região por arquivo) e a API de localidades do IBGE (distritos de São Paulo). Uma terceira, as leituras do robô, é gerada por uma função em <code>dags/coleta.py</code>, porque o robô ainda não envia dados em campo.", []),
    ("02 DAG de coleta agendada",
     "A DAG <code>gs_coleta</code> roda todo dia e grava um arquivo por coleta na pasta <code>chegada/</code>, com a data no nome (ex.: <code>clima_mooca_2026-10-25.json</code>).",
     [("01_airflow_grid.jpg", "Airflow, visão Grid: execuções concluídas.")]),
    ("03 Paralelismo e verificação",
     "As tarefas <code>coletar_clima</code>, <code>coletar_distritos</code> e <code>leituras_robo</code> rodam em paralelo e a tarefa <code>conferir_chegada</code> falha se algum arquivo estiver ausente ou vazio. As APIs usadas não pedem chave; o caminho da pasta vem de uma Variable do Airflow, não do código.",
     [("02_airflow_graph.jpg", "Airflow, visão Graph.")]),
    ("04 Dois lotes no Volume",
     "O lote 1 tem os dias 21 a 24/10 e o lote 2 os dias 25 a 27/10. Os dois foram enviados pela interface ao Volume <code>workspace.gs.chegada</code>.",
     [("03_volume_distritos.jpg", "Volume com os arquivos de distritos do lote 1.")]),
    ("05 Bronze incremental",
     "A Bronze usa Auto Loader com checkpoint. Depois do lote 1 a tabela tinha 20 / 384 / 96 linhas (clima / distritos / robô). Depois do lote 2, 35 / 672 / 168: só entraram os arquivos novos. Rodando de novo sem arquivo novo, nada mudou.",
     [("04_bronze_lote1.jpg", "Contagens após o lote 1."), ("05_bronze_lote2.jpg", "Contagens após o lote 2."), ("06_bronze_rerun.jpg", "Contagens após rodar de novo, sem arquivo novo.")]),
    ("06 Prata",
     "O campo <code>hourly</code> chega como texto e é convertido com <code>from_json</code>; depois as listas paralelas viram uma linha por hora. Há três regras de qualidade, com o total barrado por cada uma: nulos (0), negativos (0) e acima de 100 mm (0). O dado real veio limpo, então nenhuma linha foi barrada. O <code>MERGE</code> pela chave região + hora gerou 840 linhas (35 arquivos × 24 horas).",
     [("07_prata_regras.jpg", "Regras de qualidade e MERGE."), ("08_prata_contagem.jpg", "Total de linhas da prata_clima.")]),
    ("07 Ouro",
     "A tabela fato é <code>fato_chuva</code> (chuva por hora, soma de 3 horas e risco). As dimensões são <code>dim_regiao</code> e <code>dim_tempo</code>. Também há <code>fato_leitura_robo</code> e a tabela de resumo <code>ouro_mvp</code>. As 5 consultas estão no fim deste relatório.",
     [("09_ouro_mvp.jpg", "Tabela ouro_mvp.")]),
    ("08 LGPD e uso pelo MVP",
     "Não há dado pessoal nas fontes. O único identificador é o <code>device_id</code> do robô, que na Ouro só aparece como hash SHA-256 (<code>device_hash</code>). O MVP usa a tabela <code>ouro_mvp</code>: o CSV exportado fica em <code>mvp/data/ouro_resumo.csv</code> e a rota <code>/historico</code> o entrega à tela inicial.",
     [("15_mvp_tela.jpg", "Tela do MVP com a tabela do histórico.")]),
    ("09 Repositório e README",
     f"Código, notebooks, amostras e instruções em <a href='{REPO}'>{REPO}</a> (pasta <code>dados/</code>).", []),
]
consultas = [
    ("1. Quais regiões mais choveram?", "10_consulta1.png", "Tatuapé teve 67,6 mm, Pinheiros 66,2, Mooca e Sé 65,4 e Santo Amaro 62,6. A diferença entre a maior e a menor é de cerca de 5 mm: a chuva ficou bem distribuída pela cidade nesse período."),
    ("2. Quantas horas de risco alto por região?", "11_consulta2.png", "Só Pinheiros e Tatuapé passaram do limite de 15 mm em 3 horas, com 2 horas cada. As outras três regiões não tiveram nenhuma."),
    ("3. Em que horário chove mais?", "12_consulta3.png", "As maiores médias são à 1h (1,14 mm) e à meia-noite (1,13 mm), depois 7h (0,94). A chuva do período se concentrou na madrugada e de manhã cedo."),
    ("4. Qual dia teve mais chuva?", "13_consulta4.png", "O dia 25/10 teve 183 mm somando as cinco regiões, bem acima dos outros. Os dias 21 e 27/10 ficaram quase secos (0,5 e 1,3 mm)."),
    ("5. Impacto: leituras do robô em horas de risco", "14_consulta5.png", "Foram 5 leituras com umidade acima de 60% em horas de risco médio ou alto. Como as leituras ainda são geradas, o número só prova que o cruzamento funciona. Com o ESP32 mandando dados reais, a mesma consulta passa a medir quantos alertas o robô confirmou no local."),
]

html = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>Relatório Dados - ChuvaRota</title>
<style>
body{{font-family:Helvetica,Arial,sans-serif;font-size:12px;line-height:1.5;margin:0;color:#111}}
h1{{font-size:22px}} h2{{font-size:15px;border-bottom:1px solid #999;padding-bottom:3px;margin-top:22px}}
table{{border-collapse:collapse;width:100%}} td,th{{border:1px solid #999;padding:4px 6px;text-align:left}}
figure{{margin:8px 0;page-break-inside:avoid}} img{{max-width:100%;border:1px solid #ccc}} figcaption{{font-size:10px;color:#555}}
svg{{width:100%;height:auto}} code{{background:#eee;padding:0 3px}}
</style></head><body>
<h1>Big Data Architecture &amp; Data Integration: ChuvaRota</h1>
<p>Global Solution 2026.2 · Engenharia de Software · 4º ano</p>

<h2>1. Integrantes</h2>
<p>{NOME}, RM {RM}</p>

<h2>2. O produto e as perguntas que o MVP responde</h2>
<p>ChuvaRota mostra o risco de chuva por região de São Paulo para quem se desloca a pé ou de ônibus. As perguntas que a parte de dados responde: onde mais choveu, onde houve horas de risco alto, em que horário chove mais e se o sensor do robô confirma o risco previsto.</p>

<h2>3. Diagrama do fluxo de dados</h2>
{fluxo}

<h2>4. Fontes</h2>
<table><tr><th>Fonte</th><th>Origem</th><th>Formato</th><th>Frequência</th></tr>
<tr><td>Clima por hora</td><td>Open-Meteo (API de arquivo)</td><td>JSON, 1 arquivo por região e dia</td><td>diária</td></tr>
<tr><td>Distritos de SP</td><td>IBGE (API de localidades)</td><td>JSON, 1 arquivo por dia</td><td>diária</td></tr>
<tr><td>Leituras do robô</td><td>gerada em código (o robô ainda não envia)</td><td>JSON, 1 arquivo por dia</td><td>diária</td></tr></table>

<h2>5. Requisitos 01 a 09</h2>
{''.join(f'<h3>{t}</h3><p>{d}</p>' + ''.join(img(a, l) for a, l in imgs) for t, d, imgs in req)}

<h2>6. Contagens da Bronze</h2>
<table><tr><th>Momento</th><th>clima</th><th>distritos</th><th>robô</th></tr>
<tr><td>Depois do lote 1</td><td>20</td><td>384</td><td>96</td></tr>
<tr><td>Depois do lote 2</td><td>35</td><td>672</td><td>168</td></tr>
<tr><td>Segunda execução, sem arquivo novo</td><td>35</td><td>672</td><td>168</td></tr></table>

<h2>7. As 5 consultas SQL</h2>
{''.join(f'<h3>{t}</h3>' + img(a, '') + f'<p>{i}</p>' for t, a, i in consultas)}

<h2>8. Conclusão técnica</h2>
<p>A pipeline coleta, trata em três camadas e entrega ao MVP uma tabela de resumo, sem duplicar dados ao rodar de novo. Dois limites: o envio dos arquivos ao Databricks é manual, porque a edição gratuita não se conecta ao Airflow, e as regras de qualidade não barraram nada porque o dado real veio limpo. Código, notebooks e passo a passo: <a href="{REPO}">{REPO}</a>.</p>
</body></html>"""

saida = AQUI / "relatorio.html"
saida.write_text(html, encoding="utf-8")
chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
subprocess.run([chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer", "--user-data-dir=/tmp/chrome-pdf",
                f"--print-to-pdf={AQUI / 'relatorio_dados.pdf'}", saida.as_uri()], capture_output=True)
saida.unlink()
print("ok")
