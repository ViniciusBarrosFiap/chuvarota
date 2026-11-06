from fastapi.testclient import TestClient
import app as app_mod
from app import app
c = TestClient(app)

def test_health(): assert c.get("/health").json() == {"status": "ok"}
LEITURA = {"luz_pct": 12, "distancia_cm": 20, "situacao": "escuro_e_obstaculo"}


def test_robo_desativado_sem_token_configurado(monkeypatch):
    monkeypatch.setattr(app_mod, "TOKEN_ROBO", "")
    assert c.post("/robo", json=LEITURA, headers={"X-Token": "x"}).status_code == 503


def test_robo_token_errado_ou_ausente(monkeypatch):
    monkeypatch.setattr(app_mod, "TOKEN_ROBO", "segredo")
    assert c.post("/robo", json=LEITURA).status_code == 401
    assert c.post("/robo", json=LEITURA, headers={"X-Token": "outro"}).status_code == 401


def test_robo_leitura_valida_aparece_na_lista(monkeypatch):
    monkeypatch.setattr(app_mod, "TOKEN_ROBO", "segredo")
    assert c.post("/robo", json=LEITURA, headers={"X-Token": "segredo"}).status_code == 201
    assert c.get("/robo").json()[0]["situacao"] == "escuro_e_obstaculo"


def test_robo_leitura_invalida(monkeypatch):
    monkeypatch.setattr(app_mod, "TOKEN_ROBO", "segredo")
    assert c.post("/robo", json={**LEITURA, "situacao": "qualquer"}, headers={"X-Token": "segredo"}).status_code == 422
    assert c.post("/robo", json={**LEITURA, "luz_pct": 500}, headers={"X-Token": "segredo"}).status_code == 422

def test_historico():
    r = c.get("/historico")
    assert r.status_code == 200 and "regiao" in r.json()[0]

def test_pagina(): assert "ChuvaRota" in c.get("/").text


def test_metricas():
    c.get("/health")
    texto = c.get("/metrics").text
    assert 'http_requests_total{method="GET",path="/health",status="200"}' in texto
    assert "http_request_duration_seconds_bucket" in texto
