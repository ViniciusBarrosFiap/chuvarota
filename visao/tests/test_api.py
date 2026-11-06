import sys
from pathlib import Path

from fastapi.testclient import TestClient

AQUI = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AQUI))
import api  # noqa: E402

c = TestClient(api.app)


def test_arquivo_que_nao_e_imagem():
    r = c.post("/analisar", files={"foto": ("a.txt", b"nao sou imagem", "text/plain")})
    assert r.status_code == 400


def test_foto_grande_demais():
    r = c.post("/analisar", files={"foto": ("a.jpg", b"0" * (5 * 1024 * 1024 + 10), "image/jpeg")})
    assert r.status_code == 413


def test_foto_de_onibus_alagado():
    r = c.post("/analisar", files={"foto": ("a.jpg", (AQUI / "amostras" / "entrada_1.jpg").read_bytes(), "image/jpeg")})
    corpo = r.json()
    assert r.status_code == 200 and corpo["deteccoes"][0]["nivel"].startswith("nível 2")
    assert "não atravesse" in corpo["mensagem"].lower()
