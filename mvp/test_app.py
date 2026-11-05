from fastapi.testclient import TestClient
from app import app
c = TestClient(app)

def test_health(): assert c.get("/health").json() == {"status": "ok"}
def test_leitura_ok(): assert c.post("/leituras", json={"sensor": "chuva", "valor": 70}).json()["risco_local"] == "alto"
def test_leitura_invalida(): assert c.post("/leituras", json={"sensor": "chuva", "valor": 500}).status_code == 422

def test_historico():
    r = c.get("/historico")
    assert r.status_code == 200 and "regiao" in r.json()[0]

def test_pagina(): assert "ChuvaRota" in c.get("/").text
