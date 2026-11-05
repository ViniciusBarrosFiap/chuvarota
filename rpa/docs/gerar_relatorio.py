import html
import subprocess
from pathlib import Path

NOME, RM = "Vinicius Barros", "97824"
REPO = "https://github.com/ViniciusBarrosFiap/chuvarota"
VIDEO = REPO + "/blob/main/rpa/assets/video_rpa.mp4"
AQUI = Path(__file__).parent
RPA = AQUI.parent


def ler(p):
    return html.escape((RPA / p).read_text(encoding="utf-8"))


def img(p, legenda):
    return f'<figure><img src="{(RPA / p).as_uri()}"><figcaption>{legenda}</figcaption></figure>'


codigo = ler("src/rpa.py")
doc = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>Relatório RPA - ChuvaRota</title>
<style>
body{{font-family:Helvetica,Arial,sans-serif;font-size:12px;line-height:1.5;color:#111;margin:0}}
h1{{font-size:22px}} h2{{font-size:15px;border-bottom:1px solid #999;padding-bottom:3px;margin-top:22px}}
table{{border-collapse:collapse;width:100%}} td,th{{border:1px solid #999;padding:4px 6px;text-align:left}}
pre{{background:#f2f2f2;padding:8px;font-size:9.5px;white-space:pre-wrap;word-break:break-all}}
figure{{margin:8px 0;page-break-inside:avoid}} img{{max-width:100%;border:1px solid #ccc}} figcaption{{font-size:10px;color:#555}}
code{{background:#eee;padding:0 3px}}
</style></head><body>
<h1>Robotic Process Automation: alertas de chuva do ChuvaRota</h1>
<p>Global Solution 2026.2 · Engenharia de Software · 4º ano</p>

<h2>1. Integrantes</h2><p>{NOME}, RM {RM}</p>

<h2>2. CitizenTech e problema resolvido</h2>
<p>O ChuvaRota mostra o risco de chuva por região de São Paulo para quem se desloca a pé ou de ônibus. O problema operacional dos bastidores: alguém precisaria consultar a previsão de cada região e atualizar à mão o arquivo que o MVP exibe. Sem isso, o aviso fica velho e deixa de servir ao cidadão.</p>

<h2>3. Objetivo e benefício para o cidadão</h2>
<p>Atualizar os alertas sozinha, a cada 3 horas, sem ninguém mexer. O cidadão abre o MVP e vê o risco por região com a previsão do dia, em vez de dados desatualizados.</p>

<h2>4. Processo e fluxo</h2>
<p>O fluxo em BPMN mostra o processo principal e o detalhe do tratamento de cada região. O PDD completo está em <code>rpa/docs/PDD.md</code>.</p>
{img("assets/fluxo_bpmn.png", "Fluxo BPMN do processo.")}

<h2>5. Tecnologias e justificativa</h2>
<table><tr><th>Tecnologia</th><th>Por que</th></tr>
<tr><td>Python</td><td>Simples, fica versionado no GitHub e é fácil de testar.</td></tr>
<tr><td>API Open-Meteo</td><td>Pública e gratuita, não exige chave (nada de segredo no código).</td></tr>
<tr><td>GitHub Actions</td><td>Agenda a execução a cada 3 horas sem servidor próprio e grava o resultado no repositório.</td></tr>
<tr><td>pytest</td><td>Testa sucesso, decisão e falha sem depender da internet.</td></tr></table>

<h2>6. Regras de negócio, decisões e processamento</h2>
<ul><li><b>Repetição:</b> o programa passa por cada uma das 5 regiões da lista.</li>
<li><b>Decisão:</b> pega o maior acumulado de chuva em 3 horas seguidas. 15 mm ou mais é <b>alto</b>, 5 mm ou mais é <b>médio</b>, abaixo disso é <b>baixo</b>.</li>
<li><b>Dados inválidos:</b> valores nulos ou negativos contam como 0.</li>
<li><b>Região repetida:</b> é ignorada e registrada no log.</li></ul>

<h2>7. Exceções e recuperação</h2>
<p>Se a API falha, o programa tenta 3 vezes (esperando 2 e 4 segundos), registra o erro e segue para a próxima região. Se nenhuma região der certo, o arquivo <code>alertas.json</code> anterior é mantido e o programa termina com erro, que o GitHub Actions marca como falha. Nada falha em silêncio.</p>

<h2>8. Logs e auditoria</h2>
<p>O log tem data e hora, região, chuva, risco e erros, sem nenhum dado pessoal. Execução normal:</p><pre>{ler("logs/amostra_sucesso.log")}</pre>
<p>Execução com a API inacessível (simulada):</p><pre>{ler("logs/amostra_falha.log")}</pre>

<h2>9. Integração com o MVP</h2>
<p>O resultado é gravado em <code>mvp/data/alertas.json</code> e o MVP o entrega pela rota <code>/alertas</code> e na tela inicial. O workflow do GitHub Actions também foi executado de verdade na nuvem, com sucesso: <code>{ler("logs/execucao_github_actions.txt").strip()}</code></p>
{img("assets/mvp_alertas.png", "Tela do MVP exibindo os alertas gerados pelo RPA.")}

<h2>10. Testes realizados</h2>
<table><tr><th>Cenário</th><th>Teste</th><th>Resultado</th></tr>
<tr><td>Sucesso</td><td><code>test_sucesso</code>: duas regiões, risco alto gravado</td><td>passou</td></tr>
<tr><td>Decisão</td><td><code>test_decisao</code>: limites 0, 5 e 15 mm; nulo e negativo viram 0</td><td>passou</td></tr>
<tr><td>Falha</td><td><code>test_falha_e_duplicado</code>: uma região com API fora e uma repetida</td><td>passou</td></tr>
<tr><td>Falha total</td><td><code>test_falha_total_nao_apaga_arquivo</code>: arquivo anterior preservado</td><td>passou</td></tr></table>
<pre>{ler("tests/resultado_testes.txt")}</pre>

<h2>11. Segurança e LGPD</h2>
<p>O programa não usa chave nem senha (a API é pública), então não há segredo no código; o repositório também roda o Gitleaks a cada push. Os dados são só previsão de chuva por região, sem nenhum dado pessoal, e o log guarda apenas região, chuva e risco.</p>

<h2>12. Código principal</h2><pre>{codigo}</pre>

<h2>13. Links</h2>
<p>Repositório: <a href="{REPO}">{REPO}</a> (pasta <code>rpa/</code>)<br>Vídeo: <a href="{VIDEO}">{VIDEO}</a></p>
</body></html>"""

saida = AQUI / "relatorio.html"
saida.write_text(doc, encoding="utf-8")
chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
try:
    subprocess.run([chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer", "--user-data-dir=/tmp/chrome-pdf",
                    f"--print-to-pdf={AQUI / 'relatorio_rpa.pdf'}", saida.as_uri()], capture_output=True, timeout=60)
except subprocess.TimeoutExpired:
    pass  # o chrome às vezes não encerra depois de gerar o pdf
saida.unlink()
print("ok")
