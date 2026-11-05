"""RPA ChuvaRota: coleta previsao de chuva por regiao, classifica risco e grava alertas para o MVP."""
import json, logging, sys, time
from datetime import datetime, timezone
from pathlib import Path
import requests

REGIOES = [  # sem dados pessoais: so coordenadas publicas
    {"id": "se", "nome": "Sé", "lat": -23.55, "lon": -46.63},
    {"id": "pinheiros", "nome": "Pinheiros", "lat": -23.56, "lon": -46.69},
    {"id": "mooca", "nome": "Mooca", "lat": -23.55, "lon": -46.60},
    {"id": "santo-amaro", "nome": "Santo Amaro", "lat": -23.65, "lon": -46.71},
    {"id": "tatuape", "nome": "Tatuapé", "lat": -23.54, "lon": -46.57},
]
URL = "https://api.open-meteo.com/v1/forecast"
SAIDA = Path(__file__).parents[2] / "mvp" / "data" / "alertas.json"
LOG = Path(__file__).parents[1] / "logs" / "rpa.log"
logging.basicConfig(filename=LOG, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("rpa")


def classificar(mm_3h: float) -> str:
    """Regra de decisao: maior acumulado de chuva em 3h seguidas (mm)."""
    if mm_3h >= 15: return "alto"
    if mm_3h >= 5: return "medio"
    return "baixo"


def max_3h(horas: list) -> float:
    """Maior soma de 3 horas consecutivas; ignora nulos e negativos (dado invalido)."""
    v = [x if isinstance(x, (int, float)) and x >= 0 else 0.0 for x in horas]
    return max((sum(v[i:i + 3]) for i in range(max(len(v) - 2, 1))), default=0.0)


def buscar(regiao: dict, tentativas: int = 3) -> list:
    for t in range(1, tentativas + 1):
        try:
            r = requests.get(URL, params={"latitude": regiao["lat"], "longitude": regiao["lon"],
                                          "hourly": "precipitation", "forecast_days": 1,
                                          "timezone": "America/Sao_Paulo"}, timeout=15)
            r.raise_for_status()
            return r.json()["hourly"]["precipitation"]
        except (requests.RequestException, KeyError, ValueError) as e:
            log.warning("regiao=%s tentativa=%d erro=%s", regiao["id"], t, type(e).__name__)
            time.sleep(2 ** t if t < tentativas else 0)
    raise RuntimeError(f"falha apos {tentativas} tentativas")


def executar(regioes=REGIOES, saida=SAIDA) -> dict:
    alertas, vistos, ok, falhas = [], set(), 0, 0
    for g in regioes:                      # repeticao sobre a colecao
        if g["id"] in vistos:              # duplicado
            log.warning("regiao=%s duplicada, ignorada", g["id"]); continue
        vistos.add(g["id"])
        try:
            mm = max_3h(buscar(g))
            alertas.append({"id": g["id"], "regiao": g["nome"], "mm_3h": round(mm, 1), "risco": classificar(mm)})
            log.info("regiao=%s mm_3h=%.1f risco=%s", g["id"], mm, classificar(mm)); ok += 1
        except Exception as e:             # falha registrada, nunca silenciosa
            log.error("regiao=%s falhou: %s", g["id"], e); falhas += 1
    if ok:                                 # so sobrescreve se houve dado novo
        saida.write_text(json.dumps({"atualizado_em": datetime.now(timezone.utc).isoformat(),
                                     "alertas": alertas}, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("fim ok=%d falhas=%d", ok, falhas)
    return {"ok": ok, "falhas": falhas}


if __name__ == "__main__":
    res = executar()
    print(res)
    sys.exit(1 if res["ok"] == 0 else 0)
