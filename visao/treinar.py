from pathlib import Path

from ultralytics import YOLO

AQUI = Path(__file__).resolve().parent

modelo = YOLO("yolov8n.pt")  # parte dos pesos do COCO e ajusta para os 4 níveis de água
modelo.train(
    data=str(AQUI / "data.yaml"),
    epochs=60,
    imgsz=640,
    batch=16,
    device="mps",
    seed=42,
    patience=15,
    project=str(AQUI / "runs"),
    name="chuvarota",
    exist_ok=True,
)
