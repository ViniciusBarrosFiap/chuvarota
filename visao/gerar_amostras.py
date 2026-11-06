import shutil
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

from avaliar import TESTE, iou, verdade
from detectar import PESOS, desenhar

AQUI = Path(__file__).resolve().parent
SAIDA = AQUI / "amostras"
modelo = YOLO(str(PESOS))

acertos, erros = [], []
for img in sorted(TESTE.glob("*.jpg")):
    r = modelo.predict(str(img), conf=0.4, verbose=False)[0]
    preds = [(int(c.cls), c.xyxy[0].tolist()) for c in r.boxes]
    ok = bool(preds)
    for gc, gcaixa in verdade(img):
        casou = [p for p in preds if iou(gcaixa, p[1]) >= 0.5]
        ok = ok and bool(casou) and casou[0][0] == gc
    (acertos if ok else erros).append((img, r, {gc for gc, _ in verdade(img)}))

escolhidos = []
for nivel in range(4):  # um acerto de cada nível
    for item in acertos:
        if item[2] == {nivel} and item not in escolhidos:
            escolhidos.append(item)
            break
escolhidos += erros[:2]
quadros = []
for i, (img, r, _) in enumerate(escolhidos):
    shutil.copy(img, SAIDA / f"entrada_{i}.jpg")
    saida = desenhar(r.orig_img.copy(), r)
    cv2.imwrite(str(SAIDA / f"saida_{i}.jpg"), saida)
    quadros.append(cv2.resize(saida, (420, 300)))
cv2.imwrite(str(AQUI / "avaliacao" / "exemplos.jpg"), np.vstack([np.hstack(quadros[:3]), np.hstack(quadros[3:6])]))
print(len(acertos), "imagens totalmente certas;", len(erros), "com algum erro;", len(escolhidos), "amostras")
