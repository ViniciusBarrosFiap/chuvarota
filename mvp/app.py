"""MVP ChuvaRota: le alertas gerados pela RPA e recebe leituras do sensor do robo."""
import csv, json, time
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

app = FastAPI(title="ChuvaRota")
DADOS = Path(__file__).parent / "data" / "alertas.json"
leituras: list = []  # shortcut: memoria efemera; trocar por banco/KV se for alem da demo


class Leitura(BaseModel):
    sensor: str = Field(max_length=32)
    valor: float = Field(ge=0, le=100)  # 0-100 (% de umidade/nivel)


@app.get("/")
def pagina():
    return FileResponse(Path(__file__).parent / "index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/alertas")
def alertas():
    if not DADOS.exists():
        raise HTTPException(503, "alertas ainda nao gerados")
    return json.loads(DADOS.read_text(encoding="utf-8"))


@app.get("/historico")
def historico():
    arq = Path(__file__).parent / "data" / "ouro_resumo.csv"
    if not arq.exists():
        raise HTTPException(503, "resumo da Ouro ainda nao exportado")
    with open(arq, encoding="utf-8") as f:
        return list(csv.DictReader(f))


@app.post("/leituras", status_code=201)
def nova_leitura(l: Leitura):
    leituras.append({"t": time.time(), **l.model_dump()})
    del leituras[:-100]
    return {"risco_local": "alto" if l.valor >= 60 else "baixo"}
