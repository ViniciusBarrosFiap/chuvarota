import argparse
import time
from pathlib import Path

import cv2
from ultralytics import YOLO

from niveis import CORES, NOMES, alerta

PESOS = Path(__file__).resolve().parent / "modelo" / "best.pt"


def desenhar(quadro, resultado):
    for caixa in resultado.boxes:
        nivel = int(caixa.cls)
        x1, y1, x2, y2 = map(int, caixa.xyxy[0])
        cv2.rectangle(quadro, (x1, y1), (x2, y2), CORES[nivel], 3)
        cv2.putText(quadro, f"{NOMES[nivel]} {float(caixa.conf):.0%}", (x1, max(y1 - 8, 18)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, CORES[nivel], 2)
    return quadro


def main():
    ap = argparse.ArgumentParser(description="Detecta o nível de água em ônibus alagados (imagem, vídeo ou webcam)")
    ap.add_argument("fonte", help="caminho de uma imagem ou vídeo, ou 0 para a webcam")
    ap.add_argument("--saida", default="resultado", help="nome do arquivo de saída, sem extensão")
    ap.add_argument("--conf", type=float, default=0.4)
    args = ap.parse_args()

    modelo = YOLO(str(PESOS))
    fonte = int(args.fonte) if args.fonte.isdigit() else args.fonte
    if isinstance(fonte, str) and fonte.lower().endswith((".jpg", ".jpeg", ".png")):
        r = modelo.predict(fonte, conf=args.conf, verbose=False)[0]
        cv2.imwrite(args.saida + ".jpg", desenhar(r.orig_img.copy(), r))
        for c in r.boxes:
            print(NOMES[int(c.cls)], f"{float(c.conf):.0%}", "->", alerta(int(c.cls)))
        return

    video = cv2.VideoCapture(fonte)
    taxa = video.get(cv2.CAP_PROP_FPS) or 20
    escritor = None
    quadros, inicio = 0, time.time()
    while True:
        ok, quadro = video.read()
        if not ok:
            break
        r = modelo.predict(quadro, conf=args.conf, verbose=False)[0]
        quadro = desenhar(quadro, r)
        quadros += 1
        cv2.putText(quadro, f"{quadros / (time.time() - inicio):.0f} quadros/s", (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        if fonte == 0:
            cv2.imshow("ChuvaRota Visão (q para sair)", quadro)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
        else:
            if escritor is None:
                escritor = cv2.VideoWriter(args.saida + ".mp4", cv2.VideoWriter_fourcc(*"mp4v"), taxa, (quadro.shape[1], quadro.shape[0]))
            escritor.write(quadro)
    video.release()
    if escritor:
        escritor.release()


if __name__ == "__main__":
    main()
