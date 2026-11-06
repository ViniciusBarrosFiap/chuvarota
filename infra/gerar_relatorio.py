import html
import subprocess
from pathlib import Path

NOME, RM = "Vinicius Barros", "97824"
REPO = "https://github.com/ViniciusBarrosFiap/chuvarota"
URL = "https://chuvarota-85ixn.azurewebsites.net"
BARRADA = REPO + "/actions/runs/41960832140"
CORRIGIDA = REPO + "/actions/runs/41961124580"
AQUI = Path(__file__).resolve().parent
EV = AQUI / "evidencias"


def txt(p):
    return html.escape((EV / p).read_text(encoding="utf-8").strip())


def img(p, legenda, w="100%"):
    return f'<figure><img src="{(EV / p).as_uri()}" style="width:{w}"><figcaption>{legenda}</figcaption></figure>'


secret = subprocess.run(["gh", "secret", "list", "-R", "ViniciusBarrosFiap/chuvarota"], capture_output=True, text=True).stdout
deploy_ok = "AZURE_CREDENTIALS" in secret
segredos = ("A credencial do Azure fica em <b>GitHub Secrets</b> (<code>AZURE_CREDENTIALS</code>, papel Website Contributor só no grupo de recursos) e o nome do app em Variables."
            if deploy_ok else "<b>Pendente:</b> a credencial do Azure (<code>AZURE_CREDENTIALS</code>) ainda não foi gravada em GitHub Secrets; sem ela a etapa de deploy automático fica desativada.")

doc = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>Relatório DevOps - ChuvaRota</title>
<style>
body{{font-family:Helvetica,Arial,sans-serif;font-size:12px;line-height:1.5;color:#111;margin:0}}
h1{{font-size:22px}} h2{{font-size:15px;border-bottom:1px solid #999;padding-bottom:3px;margin-top:22px}} h3{{font-size:13px}}
table{{border-collapse:collapse;width:100%}} td,th{{border:1px solid #999;padding:4px 6px;text-align:left;vertical-align:top}}
pre{{background:#f2f2f2;padding:8px;font-size:9.5px;white-space:pre-wrap;word-break:break-all}}
figure{{margin:8px 0;page-break-inside:avoid}} img{{border:1px solid #ccc}} figcaption{{font-size:10px;color:#555}}
code{{background:#eee;padding:0 3px}}
</style></head><body>
<h1>Secure DevOps &amp; Cloud: deploy do ChuvaRota</h1>
<p>Global Solution 2026.2 · Engenharia de Software · 4º ano</p>

<h2>1. Integrantes e links</h2>
<p>{NOME}, RM {RM}<br>
MVP publicado: <a href="{URL}">{URL}</a><br>
Repositório: <a href="{REPO}">{REPO}</a> (<code>Dockerfile</code>, <code>compose.yml</code>, <code>infra/</code>, <code>.github/workflows/devsecops.yml</code>, <code>monitoring/</code>)</p>

<h2>2. Arquitetura</h2>
<figure><img src="{(AQUI / 'arquitetura.png').as_uri()}" style="width:100%"><figcaption>Fluxo do código à nuvem e do monitoramento.</figcaption></figure>
<p><b>Escolha da nuvem.</b> Usei o Azure for Students. A assinatura "Starter" só permite alguns provedores de recursos (Web, SQL, Insights e poucos mais), então Container Apps, registro de imagens (ACR) e Log Analytics foram bloqueados. O MVP roda no <b>Azure App Service (Linux, plano F1 gratuito)</b>, com a imagem vinda do GitHub Container Registry (ghcr.io), que é público e gratuito.</p>

<h2>3. Container e infraestrutura como código</h2>
<h3>3.1 Dockerfile e docker compose</h3>
<ul><li>Imagem <code>python:3.12-slim</code>, 169 MB, com os pacotes do sistema atualizados.</li>
<li>Roda como usuário <code>app</code> (uid 10001), sem root. Nenhum segredo entra na imagem (não há variável de ambiente sensível; o <code>.dockerignore</code> deixa de fora o que não é do MVP).</li>
<li><code>HEALTHCHECK</code> em <code>/health</code>. No <code>compose.yml</code> o MVP roda com sistema de arquivos somente leitura, <code>cap_drop: ALL</code> e <code>no-new-privileges</code>, junto com Prometheus e Grafana: <code>docker compose up --build</code>.</li></ul>
<pre>{txt("container.txt")}</pre>

<h3>3.2 Terraform</h3>
<p>O Terraform (pasta <code>infra/</code>) criou o grupo de recursos, o plano e o app (<code>terraform apply</code>: 4 recursos). O state e o <code>terraform.tfvars</code> ficam fora do Git (<code>infra/.gitignore</code>); o repositório só tem o <code>terraform.tfvars.example</code>.</p>
<pre>{txt("terraform_saida.txt")}</pre>
<p><b>Porta de administração.</b> Nenhuma porta de administração é exposta, para ninguém: o app só aceita HTTPS (o HTTP redireciona com 301), com TLS mínimo 1.2, FTPS desativado e publicação por FTP e Web Deploy com usuário e senha desligada no Terraform. Não existe regra de firewall com <code>0.0.0.0/0</code>.</p>
<pre>{txt("azure_config.txt")}</pre>
{img("mvp_publicado.png", "MVP publicado no Azure.", "70%")}

<h2>4. Pipeline DevSecOps (GitHub Actions)</h2>
<table><tr><th>Etapa</th><th>Ferramenta</th><th>O que barra</th></tr>
<tr><td>gitleaks</td><td>Gitleaks</td><td>segredos no código e no histórico</td></tr>
<tr><td>semgrep</td><td>Semgrep (158 regras: Python e Dockerfile)</td><td>falhas no código</td></tr>
<tr><td>testes</td><td>pytest</td><td>regressões do RPA e do MVP</td></tr>
<tr><td>imagem</td><td>Trivy na imagem Docker</td><td>vulnerabilidades HIGH e CRITICAL com correção</td></tr>
<tr><td>terraform</td><td>Trivy (config) em <code>infra/</code></td><td>configuração insegura na nuvem</td></tr>
<tr><td>publicar e deploy</td><td>docker, ghcr.io, Azure CLI</td><td>só roda se tudo acima passou; termina com teste de fumaça em <code>/health</code></td></tr></table>
<p>{segredos} O RPA, ao atualizar os alertas, dispara o pipeline para o MVP publicar os dados novos.</p>

<h3>4.1 Execução barrada</h3>
<p>O Trivy reprovou a imagem por 2 vulnerabilidades HIGH no pacote <code>apt</code> da imagem base (versão 3.0.3, corrigida na 3.0.4), e o pipeline parou antes de publicar. <a href="{BARRADA}">{BARRADA}</a></p>
<pre>{txt("trivy_barrada.txt")}</pre>
{img("pipeline_barrada.png", "Execução reprovada: o job imagem falhou e o deploy foi pulado.", "80%")}
<h3>4.2 Execução corrigida</h3>
<p>Corrigi o Dockerfile (<code>apt-get upgrade</code>) e o mesmo pipeline passou em todas as etapas. <a href="{CORRIGIDA}">{CORRIGIDA}</a></p>
{img("pipeline_corrigida.png", "Execução corrigida: todas as etapas de segurança aprovadas.", "80%")}

<h2>5. Observabilidade</h2>
<p>O MVP expõe <code>/metrics</code>. O Prometheus e o Grafana rodam localmente (<code>docker compose -f monitoring/compose.publicado.yml up</code>) e apontam para o <b>MVP publicado</b> no Azure, coletando a cada 15 segundos.</p>
{img("prometheus_alvo.png", "Prometheus coletando do MVP publicado (estado UP).", "90%")}
<table><tr><th>Sinal de ouro</th><th>Métrica</th></tr>
<tr><td>Latência</td><td>p95 de <code>http_request_duration_seconds</code></td></tr>
<tr><td>Tráfego</td><td>pedidos por segundo por rota (<code>http_requests_total</code>)</td></tr>
<tr><td>Erros</td><td>proporção de respostas 4xx e 5xx</td></tr>
<tr><td>Saturação</td><td>memória do processo e pedidos em andamento</td></tr></table>
{img("grafana_dashboard.png", "Painel do Grafana com os 4 sinais de ouro, durante um teste com tráfego e erros.", "90%")}
<p><b>Alerta disparado.</b> A regra <code>TaxaDeErrosAlta</code> (mais de 10% de erros por 30 segundos) disparou quando mandei pedidos válidos e inválidos ao MVP publicado. Há também <code>MVPForaDoAr</code> e <code>LatenciaAlta</code>.</p>
{img("prometheus_alerta.png", "Alerta TaxaDeErrosAlta em FIRING.", "90%")}

<h2>6. Responsabilidade compartilhada e LGPD</h2>
<table><tr><th>Camada</th><th>Quem cuida</th></tr>
<tr><td>Datacenter, rede física, hipervisor, sistema operacional e atualização do App Service, terminação do HTTPS</td><td>Microsoft (Azure)</td></tr>
<tr><td>Imagem e dependências, código do MVP, configuração do app (HTTPS, TLS, FTP), pipeline, segredos e acessos ao GitHub e ao Azure</td><td>Equipe</td></tr>
<tr><td>Dados tratados no MVP e o cumprimento da LGPD</td><td>Equipe (controladora)</td></tr></table>
<p><b>Onde ficam dados pessoais.</b> O MVP não pede cadastro e não guarda dados pessoais: mostra previsão de chuva por região e histórico agregado, e as leituras do sensor ficam só em memória, sem identificação de pessoa. O único dado possivelmente pessoal é o endereço IP de quem acessa, que passa pela plataforma do Azure (Brazil South) e não é gravado pelo MVP. Não configurei o Log Analytics (bloqueado na assinatura); se os logs HTTP do App Service forem ligados, o IP passa a ser registrado e a retenção deve ser definida.</p>

<h2>7. Estimativa de custo</h2>
<table><tr><th>Item</th><th>Custo</th></tr>
<tr><td>App Service plano F1 (Brazil South)</td><td>US$ 0 (gratuito)</td></tr>
<tr><td>GitHub Container Registry e GitHub Actions (repositório público)</td><td>US$ 0</td></tr>
<tr><td>Prometheus e Grafana (rodando na máquina da equipe)</td><td>US$ 0</td></tr>
<tr><td>Total do que está em uso</td><td><b>US$ 0 por mês</b></td></tr></table>
<p>Limites do plano gratuito: cota de CPU por dia (cerca de 60 minutos) e sem "always on" (o app dorme depois de um tempo sem uso, e o Prometheus coletando a cada 15 s ajuda a mantê-lo acordado). Se for preciso mais estabilidade, trocar para o plano B1 custa cerca de US$ 13 por mês (valor de tabela aproximado; confirmar na calculadora do Azure) e cabe no crédito de US$ 100 do Azure for Students: <code>terraform apply -var sku=B1</code>.</p>

<h2>8. Reprodução</h2>
<p><code>az login</code>, copiar <code>infra/terraform.tfvars.example</code> para <code>terraform.tfvars</code> com o id da assinatura, <code>terraform apply</code> em <code>infra/</code> e <code>infra/configurar_github.sh</code>. Detalhes em <code>infra/README.md</code>.</p>
</body></html>"""

saida = AQUI / "relatorio.html"
saida.write_text(doc, encoding="utf-8")
chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
try:
    subprocess.run([chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer", "--user-data-dir=/tmp/chrome-pdf",
                    f"--print-to-pdf={AQUI / 'relatorio_devops.pdf'}", saida.as_uri()], capture_output=True, timeout=60)
except subprocess.TimeoutExpired:
    pass
saida.unlink()
print("ok", "deploy configurado" if deploy_ok else "deploy pendente")
