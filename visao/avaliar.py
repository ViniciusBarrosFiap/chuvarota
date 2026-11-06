import json
import time
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

AQUI = Path(__file__).resolve().parent
TESTE = AQUI / "dataset" / "images" / "test"
ROTULOS = AQUI / "dataset" / "labels" / "test"
NOMES = ["nivel1_0a20cm", "nivel2_20a45cm", "nivel3_45a100cm", "nivel4_acima_100cm"]


def iou(a, b):
    x1, y1, x2, y2 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    uniao = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / uniao if uniao else 0


def verdade(img):
    h, w = cv2.imread(str(img)).shape[:2]
    caixas = []
    for linha in (ROTULOS / (img.stem + ".txt")).read_text().splitlines():
        c, x, y, bw, bh = linha.split()
        x, y, bw, bh = float(x) * w, float(y) * h, float(bw) * w, float(bh) * h
        caixas.append((int(c), [x - bw / 2, y - bh / 2, x + bw / 2, y + bh / 2]))
    return caixas


def comparar(modelo, so_onibus_coco=False):
    """Casa cada ônibus real com a melhor detecção (IoU 0,5) e mede acerto de detecção e de nível."""
    tp = fp = fn = igual = perto = 0
    matriz = np.zeros((4, 4), int)
    tempos = []
    for img in sorted(TESTE.glob("*.jpg")):
        t = time.time()
        r = modelo.predict(str(img), conf=0.25, verbose=False, **({"classes": [5]} if so_onibus_coco else {}))[0]
        tempos.append(time.time() - t)
        preds = [(int(c.cls), c.xyxy[0].tolist()) for c in r.boxes]
        usadas = set()
        for gc, gcaixa in verdade(img):
            melhor = max(((iou(gcaixa, p[1]), i) for i, p in enumerate(preds) if i not in usadas), default=(0, None))
            if melhor[0] >= 0.5:
                usadas.add(melhor[1])
                tp += 1
                if not so_onibus_coco:
                    pc = preds[melhor[1]][0]
                    matriz[gc, pc] += 1
                    igual += pc == gc
                    perto += abs(pc - gc) <= 1
            else:
                fn += 1
        fp += len(preds) - len(usadas)
    p, rc = tp / max(tp + fp, 1), tp / max(tp + fn, 1)
    saida = {"verdadeiros_positivos": tp, "falsos_positivos": fp, "falsos_negativos": fn,
             "precisao": round(p, 3), "recall": round(rc, 3), "f1": round(2 * p * rc / max(p + rc, 1e-9), 3),
             "ms_por_imagem": round(1000 * float(np.mean(tempos)), 1)}
    if not so_onibus_coco:
        saida.update(nivel_exato=round(igual / max(tp, 1), 3), nivel_com_erro_de_um=round(perto / max(tp, 1), 3), matriz_confusao=matriz.tolist())
    return saida


if __name__ == "__main__":
    pesos = AQUI / "modelo" / "best.pt"
    custom = YOLO(str(pesos))
    val = custom.val(data=str(AQUI / "data.yaml"), split="test", device="mps", plots=True, project=str(AQUI / "runs"), name="teste", exist_ok=True, verbose=False)
    por_classe = {NOMES[int(i)]: {"AP50": round(float(val.box.ap50[k]), 3), "AP50-95": round(float(val.box.ap[k]), 3)} for k, i in enumerate(val.box.ap_class_index)}
    resultado = {
        "teste": {"imagens": len(list(TESTE.glob("*.jpg")))},
        "modelo_customizado": {"mAP50": round(float(val.box.map50), 3), "mAP50-95": round(float(val.box.map), 3),
                               "precisao": round(float(val.box.mp), 3), "recall": round(float(val.box.mr), 3), "por_classe": por_classe},
        "deteccao_de_onibus_customizado": comparar(custom),
        "deteccao_de_onibus_coco_base": comparar(YOLO("yolov8n.pt"), so_onibus_coco=True),
    }
    (AQUI / "avaliacao" / "metricas.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(resultado, ensure_ascii=False, indent=1))
