import csv
import html
import subprocess
from pathlib import Path

IA = Path(__file__).resolve().parents[1]
TMP = Path("/tmp/video_ia")
TMP.mkdir(exist_ok=True)
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def pagina(titulo, corpo):
    return f"""<html><body style="margin:0;width:1280px;height:720px;background:#14161a;color:#eee;font-family:Helvetica,Arial,sans-serif">
<div style="padding:36px 56px"><h1 style="font-size:36px;margin:0 0 22px">{titulo}</h1>{corpo}</div></body></html>"""


def pre(texto, tam=18):
    return f'<pre style="background:#0b0c0e;color:#d6f5d6;padding:16px;font-size:{tam}px;white-space:pre-wrap;border-radius:6px;margin:0">{html.escape(texto)}</pre>'


def tabela(linhas, tam=22):
    th = "".join(f'<th style="text-align:left;padding:8px 14px;border-bottom:2px solid #666">{c}</th>' for c in linhas[0])
    tr = "".join("<tr>" + "".join(f'<td style="padding:8px 14px;border-bottom:1px solid #444">{c}</td>' for c in l) + "</tr>" for l in linhas[1:])
    return f'<table style="border-collapse:collapse;font-size:{tam}px">{th and "<tr>" + th + "</tr>"}{tr}</table>'


p = lambda t: f'<p style="font-size:26px;line-height:1.5;margin:10px 0">{t}</p>'
img = lambda arq, w: f'<img src="{(IA / arq).as_uri()}" style="width:{w}px;border-radius:6px;background:#fff">'

placar = list(csv.reader(open(IA / "avaliacao" / "placar.csv", encoding="utf-8")))
placar[0][0] = "configuração"
placar = [[l[0], l[1] + ("%" if l[1].isdigit() else ""), l[3] + ("%" if l[3].isdigit() else ""), l[5] + ("%" if l[5].isdigit() else ""), l[6] + ("%" if l[6].isdigit() else "")] if i else ["configuração", "acertos", "alucinações", "citação certa", "recusa correta"] for i, l in enumerate(placar)]
demo = "\n".join(l[:118] for l in (IA / "avaliacao" / "demo_api.txt").read_text(encoding="utf-8").splitlines() if "trecho_citado" not in l or "null" in l)

slides = [
    ("Assistente de orientação do ChuvaRota",
     p("O cidadão que enfrenta uma rua alagada acha orientação solta, às vezes errada e sem fonte.") +
     p("A IA responde só com orientações oficiais, mostra a fonte e recusa o que não sabe.") + p("Vinicius Barros · RM 97824"),
     "Oi, eu sou o Vinicius. No ChuvaRota, o cidadão que enfrenta uma rua alagada acha orientação solta, às vezes errada e sem fonte. A IA que eu construí responde só com orientações oficiais, mostra a fonte e recusa o que não sabe."),
    ("Pipeline de IA", img("assets/pipeline.png", 1150),
     "Este é o pipeline. A pergunta entra pela API. O agente, que é um modelo pequeno rodando local no Ollama, escolhe uma ferramenta: consultar o risco de chuva atual, que vem do robô de automação, ou buscar nas orientações. Na busca, se a nota de similaridade fica abaixo do limiar, o assistente recusa. Se não, o modelo responde em JSON citando a fonte, e uma verificação confere essa fonte."),
    ("Base de conhecimento: 79 trechos oficiais",
     tabela([["Fonte", "Trechos", "Licença"], ["MDR: Alagamentos", "37", "portal gov.br"], ["MDR: Inundações", "6", "portal gov.br"],
             ["gov.br: autoproteção", "14", "CC Atribuição-SemDerivações 3.0"], ["Min. da Saúde: leptospirose", "18", "CC Atribuição-SemDerivações 3.0"],
             ["Min. da Saúde: como me proteger", "4", "CC Atribuição-SemDerivações 3.0"]], 24) +
     p("Trechos literais, com id e link da fonte."),
     "A base tem setenta e nove trechos literais de cinco documentos oficiais do gov.br, da Defesa Civil e do Ministério da Saúde. Como a licença não permite derivações, eu copio o trecho como está e sempre cito a fonte."),
    ("Busca e limiar de recusa",
     tabela([["Busca", "recall@1", "recall@3"], ["palavras (TF-IDF)", "10/18 (55%)", "16/18 (88%)"], ["semântica (bge-m3)", "17/18 (94%)", "17/18 (94%)"]], 26) +
     p("Limiar 0,58: barra as 6 perguntas fora da base e perde 1 com resposta.<br>Prefiro recusar a inventar."),
     "Medi a busca em dezoito perguntas com resposta. A busca por palavras acerta o primeiro trecho em cinquenta e cinco por cento. A semântica acerta em noventa e quatro. O limiar de zero vírgula cinquenta e oito barra as seis perguntas que não constam na base e perde só uma com resposta. Para um assistente de segurança, é melhor recusar do que inventar."),
    ("Demonstração da API", pre(demo, 17),
     "Aqui a API respondendo de verdade. Na primeira pergunta, ela diz que não se deve atravessar rua alagada, cita a fonte e devolve o trecho. Na segunda, o seguro do carro não está na base, então ela recusa. Na terceira, ela usa a ferramenta e responde o risco de chuva atual do Tatuapé."),
    ("Placar: três configurações, 27 casos", tabela(placar, 24) +
     p("A: modelo sozinho · B: RAG simples · C: RAG + agente"),
     "Comparei três configurações com o mesmo modelo. Sem contexto, ele acerta trinta por cento e alucina em quarenta e quatro. Com RAG, as alucinações caem a zero e as respostas passam a ter fonte. Com o agente, chega a oitenta e nove por cento de acertos, porque a ferramenta responde o risco atual, que a base não tem."),
    ("Alucinações do modelo sem contexto",
     pre('"Um carro pode ser arrastado por até 30 centímetros de água"\n   (sem fonte, número que não está na base)\n\n"O risco na região da Mooca é considerado moderado"\n   (o dado real era baixo)\n\n"O seguro do carro geralmente cobre danos causados por enchente"\n   (fora da base, sem fonte)', 22),
     "Estes são erros reais do modelo sem contexto. Ele inventou que trinta centímetros de água arrastam um carro, disse que o risco na Mooca era moderado quando o dado real era baixo, e afirmou que o seguro geralmente cobre enchente. Nada disso tem fonte. Com RAG e agente, as três perguntas foram recusadas ou respondidas com o dado real."),
    ("Limites e conclusão",
     p("• O modelo de 3 bilhões ainda recusa perguntas que a base responde (ex.: roedores).") + p("• Só 27 casos, e ajustei o sistema olhando os erros deles: números otimistas.") +
     p("• Roda local, não grava perguntas, toda resposta traz fonte e trecho.") + p("Código, notebooks e relatório: github.com/ViniciusBarrosFiap/chuvarota (pasta ia/)"),
     "Os limites: o modelo pequeno ainda recusa perguntas que a base responde, e são só vinte e sete casos, ajustados olhando os próprios erros, então os números são otimistas. Em compensação, tudo roda local, as perguntas não são gravadas e toda resposta traz fonte e trecho. O código, os notebooks e o relatório estão no repositório. Obrigado."),
]

partes = []
for i, (titulo, corpo, fala) in enumerate(slides):
    h, png, aud, mp4 = TMP / f"s{i}.html", TMP / f"s{i}.png", TMP / f"s{i}.aiff", TMP / f"s{i}.mp4"
    h.write_text(pagina(titulo, corpo), encoding="utf-8")
    png.unlink(missing_ok=True)
    try:
        subprocess.run([CHROME, "--headless", "--disable-gpu", "--user-data-dir=/tmp/chrome-shot", "--window-size=1280,720",
                        "--hide-scrollbars", f"--screenshot={png}", h.as_uri()], capture_output=True, timeout=25)
    except subprocess.TimeoutExpired:
        subprocess.run(["pkill", "-f", "chrome-shot"])
    assert png.exists(), f"sem imagem do slide {i}"
    subprocess.run(["say", "-v", "Luciana", "-o", str(aud), fala], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(png), "-i", str(aud), "-af", "apad=pad_dur=0.7",
                    "-c:v", "libx264", "-tune", "stillimage", "-r", "10", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(mp4)], check=True)
    partes.append(mp4)

lista = TMP / "lista.txt"
lista.write_text("".join(f"file '{m}'\n" for m in partes))
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy", str(IA / "assets" / "video_ia.mp4")], check=True)
print("ok")
