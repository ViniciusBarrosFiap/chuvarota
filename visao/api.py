import sys
from pathlib import Path

import cv2
import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from ultralytics import YOLO

sys.path.insert(0, str(Path(__file__).resolve().parent))
from niveis import NOMES, alerta  # noqa: E402

PESOS = Path(__file__).resolve().parent / "modelo" / "best.pt"
MAX_BYTES = 5 * 1024 * 1024
app = FastAPI(title="ChuvaRota Visão")
modelo = YOLO(str(PESOS))


@app.post("/analisar")
async def analisar(foto: UploadFile = File(...)):
    dados = await foto.read(MAX_BYTES + 1)
    if len(dados) > MAX_BYTES:
        raise HTTPException(413, "foto maior que 5 MB")
    imagem = cv2.imdecode(np.frombuffer(dados, np.uint8), cv2.IMREAD_COLOR)
    if imagem is None:
        raise HTTPException(400, "o arquivo não é uma imagem")
    # a foto não é gravada em lugar nenhum (LGPD)
    r = modelo.predict(imagem, conf=0.4, verbose=False)[0]
    deteccoes = [{"nivel": NOMES[int(c.cls)], "confianca": round(float(c.conf), 2), "caixa": [round(float(v)) for v in c.xyxy[0]], "alerta": alerta(int(c.cls))} for c in r.boxes]
    return {"deteccoes": deteccoes, "mensagem": deteccoes[0]["alerta"] if deteccoes else "Nenhum ônibus em alagamento encontrado na foto."}
