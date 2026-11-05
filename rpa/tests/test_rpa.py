import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
import rpa

REGIOES = [{"id": "a", "nome": "A", "lat": 0, "lon": 0}, {"id": "b", "nome": "B", "lat": 0, "lon": 0}]


def test_sucesso(tmp_path, monkeypatch):
    monkeypatch.setattr(rpa, "buscar", lambda g: [0, 8, 9, 0])
    saida = tmp_path / "a.json"
    assert rpa.executar(REGIOES, saida) == {"ok": 2, "falhas": 0}
    assert json.loads(saida.read_text())["alertas"][0]["risco"] == "alto"


def test_decisao():
    assert [rpa.classificar(x) for x in (0, 5, 15)] == ["baixo", "medio", "alto"]
    assert rpa.max_3h([None, -1, 2]) == 2


def test_falha_e_duplicado(tmp_path, monkeypatch):
    def buscar(g):
        if g["id"] == "b":
            raise RuntimeError("api fora")
        return [1, 1, 1]
    monkeypatch.setattr(rpa, "buscar", buscar)
    assert rpa.executar(REGIOES + REGIOES[:1], tmp_path / "a.json") == {"ok": 1, "falhas": 1}


def test_falha_total_nao_apaga_arquivo(tmp_path, monkeypatch):
    saida = tmp_path / "a.json"
    saida.write_text("antigo")
    monkeypatch.setattr(rpa, "buscar", lambda g: (_ for _ in ()).throw(RuntimeError("api fora")))
    assert rpa.executar(REGIOES, saida) == {"ok": 0, "falhas": 2}
    assert saida.read_text() == "antigo"
