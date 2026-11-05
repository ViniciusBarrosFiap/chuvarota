import html
import subprocess
from pathlib import Path

RPA = Path(__file__).parents[1]
TMP = Path("/tmp/video_rpa")
TMP.mkdir(exist_ok=True)
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def ler(p):
    return html.escape((RPA / p).read_text(encoding="utf-8")).strip()


def pagina(titulo, corpo):
    return f"""<html><body style="margin:0;width:1280px;height:720px;background:#14161a;color:#eee;font-family:Helvetica,Arial,sans-serif">
<div style="padding:40px 60px"><h1 style="font-size:38px;margin:0 0 24px">{titulo}</h1>{corpo}</div></body></html>"""


def pre(texto, tam=20):
    return f'<pre style="background:#0b0c0e;color:#d6f5d6;padding:18px;font-size:{tam}px;white-space:pre-wrap;border-radius:6px">{texto}</pre>'


img = lambda p, w: f'<img src="{(RPA / p).as_uri()}" style="width:{w}px;border-radius:6px">'
p = lambda t: f'<p style="font-size:26px;line-height:1.5">{t}</p>'

execucao = ler("logs/execucao_github_actions.txt")
slides = [
    ("ChuvaRota: automação dos alertas de chuva",
     p("Problema: alguém teria que consultar a previsão de cada região e atualizar o arquivo do MVP à mão.") +
     p("Solução: um robô que faz isso sozinho, a cada 3 horas.") + p("Vinicius Barros · RM 97824"),
     "Oi, eu sou o Vinicius. O ChuvaRota mostra o risco de chuva por região de São Paulo. O problema dos bastidores é que alguém teria que consultar a previsão de cada região e atualizar um arquivo à mão. A automação faz isso sozinha, a cada três horas."),
    ("O fluxo do processo (BPMN)", img("assets/fluxo_bpmn.png", 1160),
     "Este é o fluxo em BPMN. O programa lê a lista de regiões, processa cada uma, e no fim grava o arquivo de alertas se pelo menos uma região deu certo. Se todas falharem, ele mantém o arquivo anterior."),
    ("Execução de ponta a ponta", pre("$ python rpa/src/rpa.py\n{'ok': 5, 'falhas': 0}\n\n" + ler("logs/amostra_sucesso.log"), 22),
     "Aqui está a execução de ponta a ponta. Rodei o programa e ele consultou as cinco regiões, calculou a chuva de cada uma e registrou o resultado no log, sem nenhuma intervenção minha."),
    ("Regra de decisão",
     p("Maior acumulado de chuva em 3 horas seguidas:") + p("15 mm ou mais → <b>alto</b><br>5 mm ou mais → <b>médio</b><br>abaixo disso → <b>baixo</b>") +
     p("Valor nulo ou negativo conta como 0.") + pre("tests/test_rpa.py::test_decisao PASSED", 22),
     "A regra de decisão usa o maior acumulado de chuva em três horas seguidas. Quinze milímetros ou mais é risco alto, cinco ou mais é médio, e abaixo disso é baixo. Valores nulos ou negativos contam como zero. Os testes cobrem esses limites."),
    ("Tratamento de falhas (API fora do ar)", pre(ler("logs/amostra_falha.log") + "\n\ntests/test_rpa.py::test_falha_total_nao_apaga_arquivo PASSED", 18),
     "Agora o tratamento de falhas. Aqui simulei a API fora do ar. O programa tentou três vezes em cada região, registrou cada erro no log e terminou com o resumo de zero sucessos e duas falhas. Como nada deu certo, o arquivo de alertas anterior foi preservado, e um teste confirma isso."),
    ("Integração com o MVP",
     f'<div style="display:flex;gap:30px;align-items:flex-start">{img("assets/mvp_alertas.png", 640)}<div style="width:520px">' +
     pre("GET /alertas\n\n" + html.escape(Path("/tmp/alertas_video.json").read_text()), 16) + "</div></div>",
     "A integração com o MVP é pelo arquivo estruturado de alertas, que a API do MVP entrega na rota alertas. Na tela inicial do MVP aparecem as cinco regiões com o risco calculado pela automação."),
    ("Agendamento na nuvem (GitHub Actions)",
     p("Roda a cada 3 horas. Execução manual disparada na nuvem:") + pre(execucao + "\n\ncheckout ✓  python ✓  rpa.py ✓  commit dos alertas ✓", 22),
     "O agendamento roda no GitHub Actions a cada três horas. Disparei uma execução manual na nuvem e ela terminou com sucesso, gravando o resultado no repositório."),
    ("Testes e entrega", pre(ler("tests/resultado_testes.txt"), 22) +
     p("Sem chave, sem dado pessoal.<br>Código, relatório e vídeo: github.com/ViniciusBarrosFiap/chuvarota (pasta rpa/)"),
     "Foram quatro testes, de sucesso, decisão e falha, todos passando. A automação não usa chave nem dado pessoal. O código, o relatório e este vídeo estão no repositório. Obrigado."),
]

partes = []
for i, (titulo, corpo, fala) in enumerate(slides):
    h = TMP / f"s{i}.html"
    h.write_text(pagina(titulo, corpo), encoding="utf-8")
    png, aud, mp4 = TMP / f"s{i}.png", TMP / f"s{i}.aiff", TMP / f"s{i}.mp4"
    png.unlink(missing_ok=True)
    try:
        subprocess.run([CHROME, "--headless", "--disable-gpu", "--user-data-dir=/tmp/chrome-shot", "--window-size=1280,720",
                        "--hide-scrollbars", f"--screenshot={png}", h.as_uri()], capture_output=True, timeout=25)
    except subprocess.TimeoutExpired:
        subprocess.run(["pkill", "-f", "chrome-shot"])  # o chrome às vezes não encerra
    assert png.exists(), f"sem imagem do slide {i}"
    subprocess.run(["say", "-v", "Luciana", "-o", str(aud), fala], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(png), "-i", str(aud), "-af", "apad=pad_dur=0.7",
                    "-c:v", "libx264", "-tune", "stillimage", "-r", "10", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(mp4)], check=True)
    partes.append(mp4)

lista = TMP / "lista.txt"
lista.write_text("".join(f"file '{m}'\n" for m in partes))
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy",
                str(RPA / "assets" / "video_rpa.mp4")], check=True)
print("ok")
