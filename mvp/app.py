"""MVP ChuvaRota: le alertas gerados pela RPA e recebe leituras do sensor do robo."""
import csv, json, time
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from pydantic import BaseModel, Field

app = FastAPI(title="ChuvaRota")

PEDIDOS = Counter("http_requests_total", "Pedidos HTTP", ["method", "path", "status"])
DURACAO = Histogram("http_request_duration_seconds", "Duração dos pedidos", ["path"])
EM_ANDAMENTO = Gauge("http_requests_in_flight", "Pedidos em andamento")


@app.middleware("http")
async def metricas(request: Request, call_next):
    inicio = time.perf_counter()
    EM_ANDAMENTO.inc()
    status = 500
    try:
        resposta = await call_next(request)
        status = resposta.status_code
        return resposta
    finally:
        EM_ANDAMENTO.dec()
        rota = request.scope.get("route")
        path = rota.path if rota else "outro"  # nome da rota, não a URL, para não criar uma série por URL
        PEDIDOS.labels(request.method, path, status).inc()
        DURACAO.labels(path).observe(time.perf_counter() - inicio)

DADOS = Path(__file__).parent / "data" / "alertas.json"
leituras: list = []  # shortcut: memoria efemera; trocar por banco/KV se for alem da demo


class Leitura(BaseModel):
    sensor: str = Field(max_length=32)
    valor: float = Field(ge=0, le=100)  # 0-100 (% de umidade/nivel)


@app.get("/")
def pagina():
    return FileResponse(Path(__file__).parent / "index.html")


@app.get("/metrics", include_in_schema=False)
def metricas_prometheus():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


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
