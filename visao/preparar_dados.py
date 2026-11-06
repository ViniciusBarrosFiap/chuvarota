import random
import shutil
from pathlib import Path

BRUTO = Path(__file__).parent / "dados_brutos" / "bus" / "Original"
SAIDA = Path(__file__).parent / "dataset"
CLASSES = ["nivel1_0a20cm", "nivel2_20a45cm", "nivel3_45a100cm", "nivel4_acima_100cm"]


def copiar(pares, parte):
    for i, (img, lab) in enumerate(pares):
        nome = f"{parte}_{i:04d}"
        for sub, origem, ext in (("images", img, ".jpg"), ("labels", lab, ".txt")):
            destino = SAIDA / sub / parte
            destino.mkdir(parents=True, exist_ok=True)
            shutil.copy(origem, destino / (nome + ext))


def pares(pasta):
    saida = []
    for img in sorted((BRUTO / "images" / pasta).glob("*.jpg")):
        lab = BRUTO / "labels" / pasta / (img.stem + ".txt")
        if lab.exists():
            saida.append((img, lab))
    return saida


treino_todo = pares("train")
random.Random(42).shuffle(treino_todo)
corte = int(len(treino_todo) * 0.9)
copiar(treino_todo[:corte], "train")
copiar(treino_todo[corte:], "val")
copiar(pares("val"), "test")  # o val original vira o teste: o modelo nunca o vê durante o treino

yaml = f"path: {SAIDA}\ntrain: images/train\nval: images/val\ntest: images/test\nnames:\n" + "".join(f"  {i}: {n}\n" for i, n in enumerate(CLASSES))
(Path(__file__).parent / "data.yaml").write_text(yaml)
for parte in ("train", "val", "test"):
    print(parte, len(list((SAIDA / "images" / parte).glob("*.jpg"))))
