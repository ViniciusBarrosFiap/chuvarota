import json
import subprocess
from pathlib import Path

AQUI = Path(__file__).resolve().parent
M = json.loads((AQUI / "avaliacao" / "metricas.json").read_text(encoding="utf-8"))
C, B, BASE = M["modelo_customizado"], M["deteccao_de_onibus_customizado"], M["deteccao_de_onibus_coco_base"]
REPO = "https://github.com/ViniciusBarrosFiap/chuvarota"
pct = lambda x: f"{100 * x:.0f}%"
f2 = lambda x: f"{x:.2f}".replace(".", ",")

RESUMO = f"""Este trabalho apresenta o treinamento customizado de uma arquitetura de visão computacional, o YOLOv8, para detectar ônibus em ruas alagadas e estimar até onde a água chega, em quatro níveis: 0 a 20 cm, 20 a 45 cm, 45 a 100 cm e mais de 100 cm. O modelo faz parte do ChuvaRota, produto que avisa o cidadão de São Paulo sobre o risco de chuva: a previsão diz que vai chover, e a imagem mostra o quanto de água já está na rua. Foram usadas 1.008 imagens públicas do Zenodo, com licença CC BY 4.0, divididas em 810 para treino, 90 para validação e 108 para teste, que o modelo nunca viu. O treino partiu dos pesos do COCO, durou 60 épocas, com imagens de 640 pixels, e levou 33 minutos em uma GPU de notebook. No conjunto de teste, o modelo treinado detectou {pct(B['recall'])} dos ônibus alagados, contra {pct(BASE['recall'])} do YOLOv8n original, e acertou o nível exato da água em {pct(B['nivel_exato'])} dos casos, com erro de no máximo um nível em {pct(B['nivel_com_erro_de_um'])}. O mAP50 foi {f2(C['mAP50'])} e a inferência leva cerca de 13 milissegundos por imagem, o bastante para tempo real. Como as fotos vêm de redes sociais, sobretudo de cidades chinesas, o desempenho em São Paulo pode ser pior. Foram entregues o código, os pesos, uma API que recebe uma foto e devolve o alerta sem gravá-la, e um vídeo de demonstração. O trabalho mostra que um modelo pequeno já traz informação útil para a segurança no trânsito em alagamentos."""
OBJETIVO = "Treinar um modelo YOLOv8 que detecte ônibus em ruas alagadas e estime o nível da água em quatro faixas, medir seu desempenho em imagens de teste inéditas e disponibilizar o resultado como alerta de segurança para o cidadão no ChuvaRota, por meio de uma API simples, sem guardar as fotos."
n_resumo, n_obj = len(RESUMO.split()), len(OBJETIVO.split())
print("palavras: resumo", n_resumo, "| objetivo", n_obj)
assert 245 <= n_resumo <= 255 and 48 <= n_obj <= 52


def img(p, legenda, w="100%"):
    return f'<figure><img src="{(AQUI / p).as_uri()}" style="width:{w}"><figcaption>{legenda}</figcaption></figure>'


por_classe = "".join(f"<tr><td>{n}</td><td>{f2(v['AP50'])}</td><td>{f2(v['AP50-95'])}</td></tr>" for n, v in C["por_classe"].items())
doc = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>Relatório Visão - ChuvaRota</title>
<style>
body{{font-family:Helvetica,Arial,sans-serif;font-size:12px;line-height:1.5;color:#111;margin:0}}
h1{{font-size:22px}} h2{{font-size:15px;border-bottom:1px solid #999;padding-bottom:3px;margin-top:22px}}
table{{border-collapse:collapse;width:100%}} td,th{{border:1px solid #999;padding:4px 6px;text-align:left}}
figure{{margin:8px 0;page-break-inside:avoid}} img{{border:1px solid #ccc}} figcaption{{font-size:10px;color:#555}}
code{{background:#eee;padding:0 3px}}
</style></head><body>
<h1>ChuvaRota Visão: detecção do nível de água em ônibus alagados com YOLOv8</h1>
<p>Global Solution 2026.2 · Applied Computer Vision · Engenharia de Software · 4º ano</p>

<h2>Integrantes</h2><p>Vinicius Barros, RM 97824</p>

<h2>Resumo</h2><p>{RESUMO}</p>

<h2>1. Introdução</h2>
<p>Em um alagamento, o risco para quem se desloca depende de quanta água já está na rua, e a previsão do tempo não mostra isso. A orientação oficial da Defesa Civil é clara: nunca atravessar pontes, ruas ou avenidas alagadas, mesmo de carro, moto ou bicicleta, porque a força da água pode arrastar o veículo. Mas o cidadão só consegue julgar o perigo olhando para a rua, e muitas vezes subestima a água.</p>
<p>A visão computacional pode fazer essa leitura a partir de uma foto. Usei um ônibus como régua: por ser grande e ter altura conhecida, o quanto dele está submerso indica a profundidade. O resultado complementa o resto do ChuvaRota (previsão de chuva por região, alertas automáticos e assistente de orientações) com a imagem do que está acontecendo agora.</p>

<h2>2. Objetivo</h2><p>{OBJETIVO}</p>

<h2>3. Ferramentas</h2>
<table><tr><th>Ferramenta</th><th>Uso e justificativa</th></tr>
<tr><td>YOLOv8n (Ultralytics 8.4)</td><td>Arquitetura de detecção de objetos em um só estágio. A versão "n" tem 3,1 milhões de parâmetros e 8,6 GFLOPs: é pequena e rápida, adequada a poucas imagens e a tempo real.</td></tr>
<tr><td>Transferência de aprendizado (pesos do COCO)</td><td>Com só 810 imagens de treino, partir de um modelo que já sabe achar ônibus é muito melhor do que treinar do zero.</td></tr>
<tr><td>PyTorch 2.x com GPU Apple (MPS)</td><td>Motor de treino; a GPU integrada do Mac permitiu treinar sem servidor.</td></tr>
<tr><td>OpenCV</td><td>Leitura de imagens e vídeos, desenho das caixas e criação dos vídeos de teste.</td></tr>
<tr><td>FastAPI e pytest</td><td>API <code>POST /analisar</code> e seus testes.</td></tr>
<tr><td>Python 3.12, ffmpeg</td><td>Scripts e montagem do vídeo de demonstração.</td></tr></table>

<h2>4. Metodologia</h2>
<p><b>Passo 1: dados.</b> Procurei bases abertas que eu pudesse baixar sem criar conta. Os conjuntos do Roboflow exigem chave de API e o "Flood Dataset-1" do Mendeley tinha só 300 imagens sem anotação. Usei o conjunto do <a href="https://doi.org/10.5281/zenodo.17151262">Zenodo</a> (CC BY 4.0): 1.008 imagens de ônibus em alagamento, coletadas de redes sociais e anotadas em formato YOLO, com 4 classes de nível de água: 0 a 20 cm, 20 a 45 cm, 45 a 100 cm e mais de 100 cm.</p>
<p><b>Passo 2: preparação.</b> O script <code>preparar_dados.py</code> sorteou (semente 42) 90 das 900 imagens de treino para validação e manteve 810 para treino. As 108 imagens de validação originais viraram o <b>teste</b>, sem nenhum uso no treino ou na escolha do modelo.</p>
<p><b>Passo 3: treino.</b> <code>treinar.py</code>: YOLOv8n com pesos do COCO, 60 épocas, imagens de 640 px, lote de 16, semente 42, parada antecipada com paciência 15 e aumento de dados padrão (mosaico, espelhamento, variação de cor). Levou 33 minutos e o melhor ponto foi a época 56 (mAP50 de validação 0,56).</p>
{img("avaliacao/curvas_treino.png", "Curvas do treino: perdas caem e as métricas de validação sobem até o fim.", "95%")}
<p><b>Passo 4: avaliação.</b> <code>avaliar.py</code> mede, só no teste: mAP50 e mAP50-95, precisão e recall por classe; a capacidade de achar o ônibus (caixa com IoU de pelo menos 0,5, ignorando o nível), comparada com o YOLOv8n original do COCO; o acerto do nível; e a matriz de confusão.</p>
<p><b>Passo 5: uso.</b> <code>detectar.py</code> detecta em imagem, vídeo ou webcam e escreve o alerta; <code>api.py</code> expõe o modelo por <code>POST /analisar</code>, com validação do arquivo (imagem de até 5 MB) e sem gravar a foto.</p>

<h2>5. Resultados</h2>
<h3>5.1 Métricas no conjunto de teste (108 imagens, 168 ônibus)</h3>
<table><tr><th>mAP50</th><th>mAP50-95</th><th>Precisão</th><th>Recall</th></tr>
<tr><td>{f2(C['mAP50'])}</td><td>{f2(C['mAP50-95'])}</td><td>{f2(C['precisao'])}</td><td>{f2(C['recall'])}</td></tr></table>
<table style="margin-top:8px"><tr><th>Classe</th><th>AP50</th><th>AP50-95</th></tr>{por_classe}</table>
<p>Essas métricas exigem que a caixa <b>e</b> o nível estejam certos, por isso são mais baixas que as da tabela seguinte, que só avalia se o ônibus foi encontrado.</p>
<h3>5.2 Modelo treinado contra o YOLOv8n do COCO</h3>
<table><tr><th></th><th>Modelo treinado</th><th>YOLOv8n do COCO</th></tr>
<tr><td>Recall (acha o ônibus alagado)</td><td>{pct(B['recall'])}</td><td>{pct(BASE['recall'])}</td></tr>
<tr><td>Precisão</td><td>{pct(B['precisao'])}</td><td>{pct(BASE['precisao'])}</td></tr>
<tr><td>F1</td><td>{f2(B['f1'])}</td><td>{f2(BASE['f1'])}</td></tr>
<tr><td>Nível da água exato</td><td>{pct(B['nivel_exato'])} ({sum(B['matriz_confusao'][i][i] for i in range(4))} de {B['verdadeiros_positivos']})</td><td>não estima</td></tr>
<tr><td>Nível com erro de no máximo 1</td><td>{pct(B['nivel_com_erro_de_um'])}</td><td>não estima</td></tr></table>
<p>O treino melhorou a detecção dos ônibus alagados e deu ao modelo algo que ele não tinha: o nível da água. Não investiguei por que o modelo original perde tantos ônibus; uma hipótese é a água cobrindo parte do veículo.</p>
{img("avaliacao/matriz_confusao_teste.png", "Matriz de confusão normalizada no teste: os erros se concentram nos níveis vizinhos.", "60%")}
<h3>5.3 Exemplos</h3>
{img("avaliacao/exemplos.jpg", "Quatro acertos (um de cada nível) e dois erros: no 5º (embaixo, no centro) um ônibus com mais de 100 cm foi dado como nível 2, com 62% de confiança; no 6º o nível está certo, mas a caixa não cobre bem o ônibus.", "100%")}
<h3>5.4 Velocidade</h3>
<p>A inferência leva cerca de 13 ms por imagem no teste (GPU do Mac). No script de vídeo, com leitura, desenho e gravação, o ritmo ficou em torno de 15 quadros por segundo, suficiente para tempo real em câmera de rua.</p>

<h2>6. Limitações</h2>
<ul><li>As fotos vêm de redes sociais, principalmente de cidades chinesas: ônibus, ruas e câmeras diferentes das de São Paulo, então o desempenho aqui pode ser pior e precisa ser medido com fotos locais.</li>
<li>O modelo só conhece ônibus; carros, motos e pessoas ficam de fora.</li>
<li>O nível 4 (mais de 100 cm) é o mais fraco (AP50 de {f2(C['por_classe']['nivel4_acima_100cm']['AP50'])}): há poucos exemplos e o ônibus quase desaparece na água.</li>
<li>Exigindo que todos os ônibus de uma foto estejam com caixa e nível certos (confiança 0,4), 50 das 108 fotos do teste (46%) ficam totalmente certas.</li>
<li>O teste tem só 108 imagens, então as porcentagens têm margem de erro grande.</li></ul>

<h2>7. Conclusão</h2>
<p>Um YOLOv8 pequeno, ajustado em 33 minutos com 810 imagens, passou a achar ônibus alagados melhor que o modelo original ({pct(B['recall'])} contra {pct(BASE['recall'])}) e a estimar a água com erro de no máximo um nível em {pct(B['nivel_com_erro_de_um'])} dos casos. Para o ChuvaRota, isso já permite transformar uma foto em um alerta de "não atravesse". Os próximos passos são treinar com fotos de São Paulo, incluir outros veículos e pessoas, e juntar o resultado ao risco de chuva por região.</p>

<h2>8. Links</h2>
<p>Repositório: <a href="{REPO}">{REPO}</a> (pasta <code>visao/</code>)<br>
Vídeo: <a href="{REPO}/blob/main/visao/amostras/video_visao.mp4">{REPO}/blob/main/visao/amostras/video_visao.mp4</a><br>
Dados: QIU, Yanbin (2025). <i>Automated urban flood level detection based on flooded bus dataset wading image using YOLOv8</i>. Zenodo, <a href="https://doi.org/10.5281/zenodo.17151262">doi.org/10.5281/zenodo.17151262</a>, licença CC BY 4.0. Usei só as imagens e anotações originais ("Original.zip"), sem alterá-las.</p>
</body></html>"""

saida = AQUI / "relatorio.html"
saida.write_text(doc, encoding="utf-8")
chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
try:
    subprocess.run([chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer", "--user-data-dir=/tmp/chrome-pdf", f"--print-to-pdf={AQUI / 'relatorio_visao.pdf'}", saida.as_uri()], capture_output=True, timeout=60)
except subprocess.TimeoutExpired:
    pass
saida.unlink()
print("ok")
