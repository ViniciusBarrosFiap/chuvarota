import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
import rpa

R = [{"id": "a", "nome": "A", "lat": 0, "lon": 0}, {"id": "b", "nome": "B", "lat": 0, "lon": 0}]

def test_sucesso(tmp_path, monkeypatch):
    monkeypatch.setattr(rpa, "buscar", lambda g: [0, 8, 9, 0])
    out = tmp_path / "a.json"
    assert rpa.executar(R, out) == {"ok": 2, "falhas": 0}
    assert json.loads(out.read_text())["alertas"][0]["risco"] == "alto"

def test_decisao():
    assert [rpa.classificar(x) for x in (0, 5, 15)] == ["baixo", "medio", "alto"]
    assert rpa.max_3h([None, -1, 2]) == 2

def test_falha_e_duplicado(tmp_path, monkeypatch):
    def b(g):
        if g["id"] == "b": raise RuntimeError("api fora")
        return [1, 1, 1]
    monkeypatch.setattr(rpa, "buscar", b)
    assert rpa.executar(R + R[:1], tmp_path / "a.json") == {"ok": 1, "falhas": 1}
