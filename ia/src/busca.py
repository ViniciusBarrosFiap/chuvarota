import json
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer

BASE = Path(__file__).resolve().parents[1] / "base" / "trechos.jsonl"


def carregar_trechos():
    return [json.loads(linha) for linha in BASE.read_text(encoding="utf-8").splitlines()]


class Busca:
    def __init__(self, trechos=None):
        self.trechos = trechos or carregar_trechos()
        self.vetor = TfidfVectorizer(analyzer="char_wb", ngram_range=(4, 5), strip_accents="unicode", lowercase=True)
        self.matriz = self.vetor.fit_transform([t["texto"] for t in self.trechos])

    def buscar(self, pergunta, k=3):
        notas = (self.matriz @ self.vetor.transform([pergunta]).T).toarray().ravel()
        ordem = notas.argsort()[::-1][:k]
        return [(self.trechos[i], float(notas[i])) for i in ordem]


class BuscaSemantica:
    def __init__(self, trechos=None, modelo="bge-m3"):
        import numpy as np

        self.np, self.modelo = np, modelo
        self.trechos = trechos or carregar_trechos()
        self.matriz = self._embed([t["texto"] for t in self.trechos])

    def _embed(self, textos):
        import requests

        r = requests.post("http://localhost:11434/api/embed", json={"model": self.modelo, "input": textos}, timeout=300)
        r.raise_for_status()
        m = self.np.array(r.json()["embeddings"])
        return m / self.np.linalg.norm(m, axis=1, keepdims=True)

    def buscar(self, pergunta, k=3):
        notas = self.matriz @ self._embed([pergunta])[0]
        ordem = notas.argsort()[::-1][:k]
        return [(self.trechos[i], float(notas[i])) for i in ordem]
