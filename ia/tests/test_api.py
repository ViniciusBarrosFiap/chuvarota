import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import api  # noqa: E402

c = TestClient(api.app)


def test_pergunta_curta_demais():
    assert c.post("/perguntar", json={"pergunta": "oi"}).status_code == 422


def test_modelo_fora_do_ar(monkeypatch):
    def quebra(p):
        raise RuntimeError("ollama fora")
    monkeypatch.setattr(api.configs, "agente", quebra)
    assert c.post("/perguntar", json={"pergunta": "posso atravessar a rua alagada?"}).status_code == 503
