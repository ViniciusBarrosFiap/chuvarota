# Visão computacional: nível de água em ônibus alagados

Modelo YOLOv8 treinado por mim que detecta ônibus em rua alagada e diz até onde a água chega, em 4 níveis. No ChuvaRota ele serve para transformar uma foto da rua em um alerta ("não atravesse"), complementando a previsão de chuva.

Integrante: Vinicius Barros, RM 97824

## Dados
QIU, Yanbin (2025). [Automated urban flood level detection based on flooded bus dataset wading image using YOLOv8](https://doi.org/10.5281/zenodo.17151262). Zenodo, licença CC BY 4.0 (imagens de redes sociais anotadas no LabelImg). Usei só o `Original.zip`, sem alterá-lo; as imagens de `amostras/` vêm dele. 1.008 imagens, 4 classes:

| classe | água no ônibus |
|---|---|
| `nivel1_0a20cm` | 0 a 20 cm |
| `nivel2_20a45cm` | 20 a 45 cm |
| `nivel3_45a100cm` | 45 a 100 cm |
| `nivel4_acima_100cm` | mais de 100 cm |

O treino original (900) virou 810 de treino e 90 de validação (sorteio com semente 42); as 108 imagens de validação originais viraram o **teste**, que o modelo nunca viu.

## Resultado (teste: 108 imagens que o modelo nunca viu)
| | modelo treinado | YOLOv8n do COCO |
|---|---|---|
| acha o ônibus alagado (recall) | 71% | 50% |
| precisão | 75% | 72% |
| nível da água exato | 76% | não estima |
| nível com erro de no máximo 1 | 98% | não estima |

mAP50 0,59 · mAP50-95 0,41 · inferência de cerca de 13 ms por imagem na GPU do Mac (cerca de 70 ms em CPU, em `avaliacao/metricas.json`). Detalhes e limites (fotos de outro país, só ônibus, nível 4 fraco) em [relatorio_visao.pdf](relatorio_visao.pdf).

## Pastas
- `preparar_dados.py` divide o dataset e gera o `data.yaml`
- `treinar.py` treino (YOLOv8n a partir dos pesos do COCO)
- `avaliar.py` métricas no teste e comparação com o modelo base
- `gerar_amostras.py`, `gerar_video.py`, `gerar_relatorio.py` geram os exemplos, o vídeo e o PDF
- `detectar.py` detecção em imagem, vídeo ou webcam
- `api.py` API de análise de foto
- `modelo/best.pt` pesos treinados
- `avaliacao/` métricas e gráficos
- `amostras/` exemplos de entrada e saída

## Como reproduzir
```
pip install -r visao/requirements.txt
# baixar Original.zip do Zenodo (link acima) e extrair em visao/dados_brutos/bus/
python visao/preparar_dados.py
python visao/treinar.py
python visao/avaliar.py
python visao/detectar.py foto.jpg --saida resultado     # imagem
python visao/detectar.py video.mp4 --saida resultado    # vídeo
python visao/detectar.py 0                              # webcam (q para sair)
cd visao && uvicorn api:app --port 8002                 # API: POST /analisar com o campo "foto"
```

## Links
- Repositório: https://github.com/ViniciusBarrosFiap/chuvarota (pasta `visao/`)
- Vídeo: https://github.com/ViniciusBarrosFiap/chuvarota/blob/main/visao/amostras/video_visao.mp4
- Relatório: https://github.com/ViniciusBarrosFiap/chuvarota/blob/main/visao/relatorio_visao.pdf
