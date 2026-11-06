import json
import subprocess
from pathlib import Path

import cv2
import numpy as np

AQUI = Path(__file__).resolve().parent
TMP = Path("/tmp/video_visao")
TMP.mkdir(exist_ok=True)
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
M = json.loads((AQUI / "avaliacao" / "metricas.json").read_text(encoding="utf-8"))
C, B = M["modelo_customizado"], M["deteccao_de_onibus_customizado"]
BASE = M["deteccao_de_onibus_coco_base"]


def pagina(titulo, corpo):
    return f"""<html><body style="margin:0;width:1280px;height:720px;background:#14161a;color:#eee;font-family:Helvetica,Arial,sans-serif">
<div style="padding:36px 56px"><h1 style="font-size:36px;margin:0 0 22px">{titulo}</h1>{corpo}</div></body></html>"""


def tabela(linhas, tam=24):
    th = "".join(f'<th style="text-align:left;padding:8px 14px;border-bottom:2px solid #666">{c}</th>' for c in linhas[0])
    tr = "".join("<tr>" + "".join(f'<td style="padding:8px 14px;border-bottom:1px solid #444">{c}</td>' for c in l) + "</tr>" for l in linhas[1:])
    return f'<table style="border-collapse:collapse;font-size:{tam}px"><tr>{th}</tr>{tr}</table>'


p = lambda t: f'<p style="font-size:26px;line-height:1.5;margin:10px 0">{t}</p>'
img = lambda arq, w: f'<img src="{(AQUI / arq).as_uri()}" style="width:{w}px;border-radius:6px;background:#fff">'
pct = lambda x: f"{100 * x:.0f}%".replace(".", ",")

# vídeo de demonstração: 30 fotos do teste, 1 s cada, com a inferência real do modelo quadro a quadro
fotos = sorted((AQUI / "dataset" / "images" / "test").glob("*.jpg"))[::3][:30]
entrada, saida_demo = TMP / "entrada.mp4", TMP / "demo"
escritor = cv2.VideoWriter(str(entrada), cv2.VideoWriter_fourcc(*"mp4v"), 10, (960, 540))
for f in fotos:
    im = cv2.imread(str(f))
    fator = min(960 / im.shape[1], 540 / im.shape[0])
    im = cv2.resize(im, (int(im.shape[1] * fator), int(im.shape[0] * fator)))
    fundo = np.zeros((540, 960, 3), np.uint8)
    y, x = (540 - im.shape[0]) // 2, (960 - im.shape[1]) // 2
    fundo[y:y + im.shape[0], x:x + im.shape[1]] = im
    for _ in range(10):  # 1 segundo por foto
        escritor.write(fundo)
escritor.release()
subprocess.run([str(AQUI.parent / ".venv-ia" / "bin" / "python"), str(AQUI / "detectar.py"), str(entrada), "--saida", str(saida_demo)], check=True, cwd=AQUI)
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(saida_demo) + ".mp4", "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,fps=10",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", str(TMP / "demo_720.mp4")], check=True)

slides = [
    ("ChuvaRota Visão: nível de água em ônibus alagados",
     p("A previsão diz que vai chover. A câmera diz o quanto de água já está na rua.") +
     p("Um modelo YOLOv8 treinado por mim detecta ônibus em alagamento e estima a água em 4 níveis.") + p("Vinicius Barros · RM 97824"),
     "Oi, eu sou o Vinicius. No ChuvaRota, a previsão diz que vai chover, mas a câmera diz o quanto de água já está na rua. Eu treinei um modelo YOLO que detecta ônibus em alagamento e estima a água em quatro níveis, para virar um alerta de não atravessar."),
    ("Dados e treino",
     tabela([["classe", "água no ônibus"], ["nível 1", "0 a 20 cm"], ["nível 2", "20 a 45 cm"], ["nível 3", "45 a 100 cm"], ["nível 4", "mais de 100 cm"]], 24) +
     p("1.008 imagens (Zenodo, CC BY 4.0): 810 treino · 90 validação · 108 teste que o modelo nunca viu.") +
     p("YOLOv8n a partir do COCO, 60 épocas, 640 px, GPU do Mac, 33 minutos."),
     "Usei um conjunto aberto do Zenodo com mil e oito imagens de ônibus em ruas alagadas, anotadas em quatro níveis de água. Separei oitocentas e dez para treino, noventa para validação e cento e oito para teste, que o modelo nunca viu. Treinei um YOLOv8 pequeno, a partir dos pesos do COCO, por sessenta épocas, em trinta e três minutos."),
    ("Curvas do treino", img("avaliacao/curvas_treino.png", 1150),
     "Estas são as curvas do treino. As perdas caem ao longo das épocas e as métricas de validação sobem, sem sinal forte de superajuste."),
]
slides_fim = [
    ("Resultado no teste (108 imagens)",
     tabela([["", "modelo treinado", "YOLOv8n do COCO"], ["detecta o ônibus (recall)", pct(B["recall"]), pct(BASE["recall"])], ["precisão", pct(B["precisao"]), pct(BASE["precisao"])],
             ["acerta o nível da água", pct(B["nivel_exato"]), "não tem"], ["erro de no máximo 1 nível", pct(B["nivel_com_erro_de_um"]), "não tem"], ["mAP50", f'{C["mAP50"]:.2f}'.replace(".", ","), "não tem"]], 26) +
     p("Inferência em cerca de 13 ms por imagem, rápido o bastante para tempo real."),
     f"No teste, o modelo treinado detecta {pct(B['recall'])} dos ônibus alagados, contra {pct(BASE['recall'])} do YOLO original, que nem sabe dizer o nível da água. Ele acerta o nível exato em {pct(B['nivel_exato'])} dos casos, e em {pct(B['nivel_com_erro_de_um'])} erra no máximo um nível. A inferência leva uns treze milissegundos por imagem."),
    ("Onde o modelo erra", img("avaliacao/matriz_confusao_teste.png", 640) + p("Os erros ficam nos níveis vizinhos. O nível 4 (mais de 100 cm) é o mais difícil: pouco exemplo e o ônibus quase some na água."),
     "A matriz de confusão mostra que os erros ficam nos níveis vizinhos. O pior é o nível quatro, com mais de cem centímetros: há poucos exemplos e o ônibus quase desaparece na água."),
    ("Exemplos: quatro acertos e dois erros", img("avaliacao/exemplos.jpg", 1150),
     "Aqui, quatro acertos, um de cada nível, e dois erros. No primeiro erro, um ônibus com mais de cem centímetros foi dado como nível dois. No segundo, o nível está certo, mas a caixa não cobre bem o ônibus."),
    ("Limites e integração",
     p("• Fotos do dataset vêm de redes sociais, sobretudo de cidades chinesas: pode funcionar pior em São Paulo.") + p("• Só detecta ônibus; falta carro, moto e pessoa.") +
     p("• API: POST /analisar recebe uma foto e devolve o nível e o alerta. A foto não é gravada.") + p("Código, modelo e relatório: github.com/ViniciusBarrosFiap/chuvarota (pasta visao/)"),
     "Os limites: as fotos do conjunto vêm de redes sociais, principalmente de cidades chinesas, então o modelo pode funcionar pior em São Paulo, e ele só detecta ônibus. Para o ChuvaRota, deixei uma API que recebe uma foto e devolve o nível da água com o alerta, sem gravar a imagem. O código, o modelo e o relatório estão no repositório. Obrigado."),
]


def render(i, titulo, corpo, fala):
    h, png, aud = TMP / f"s{i}.html", TMP / f"s{i}.png", TMP / f"s{i}.aiff"
    h.write_text(pagina(titulo, corpo), encoding="utf-8")
    png.unlink(missing_ok=True)
    try:
        subprocess.run([CHROME, "--headless", "--disable-gpu", "--user-data-dir=/tmp/chrome-shot", "--window-size=1280,720", "--hide-scrollbars", f"--screenshot={png}", h.as_uri()], capture_output=True, timeout=25)
    except subprocess.TimeoutExpired:
        subprocess.run(["pkill", "-f", "chrome-shot"])
    assert png.exists(), f"sem imagem do slide {i}"
    subprocess.run(["say", "-v", "Luciana", "-o", str(aud), fala], check=True)
    mp4 = TMP / f"s{i}.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(png), "-i", str(aud), "-af", "apad=pad_dur=0.7", "-ar", "44100", "-ac", "1",
                    "-c:v", "libx264", "-tune", "stillimage", "-r", "10", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(mp4)], check=True)
    return mp4


partes = [render(i, *s) for i, s in enumerate(slides)]
# demonstração: o vídeo com a inferência real, narrado
fala_demo = "Agora o modelo em ação. São trinta fotos do conjunto de teste, uma por segundo, e o modelo detecta o ônibus em cada quadro e mostra o nível da água, com a velocidade de processamento no canto."
subprocess.run(["say", "-v", "Luciana", "-o", str(TMP / "demo.aiff"), fala_demo], check=True)
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(TMP / "demo_720.mp4"), "-i", str(TMP / "demo.aiff"), "-af", "apad", "-ar", "44100", "-ac", "1", "-c:v", "copy", "-c:a", "aac", "-shortest", str(TMP / "demo_final.mp4")], check=True)
partes.append(TMP / "demo_final.mp4")
partes += [render(10 + i, *s) for i, s in enumerate(slides_fim)]

(TMP / "lista.txt").write_text("".join(f"file '{m}'\n" for m in partes))
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(TMP / "lista.txt"), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "10", "-c:a", "aac", "-ar", "44100", "-ac", "1", str(AQUI / "amostras" / "video_visao.mp4")], check=True)
print("ok")
