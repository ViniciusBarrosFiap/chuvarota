import json
import random
from pathlib import Path

import requests

REGIOES = [
    ("se", "Sé", -23.55, -46.63),
    ("pinheiros", "Pinheiros", -23.56, -46.69),
    ("mooca", "Mooca", -23.55, -46.60),
    ("santo-amaro", "Santo Amaro", -23.65, -46.71),
    ("tatuape", "Tatuapé", -23.54, -46.57),
]


def salvar(pasta, nome, dados):
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / nome).write_text(json.dumps(dados), encoding="utf-8")


def coletar_clima(ds, chegada):
    for rid, nome, lat, lon in REGIOES:
        r = requests.get(
            "https://archive-api.open-meteo.com/v1/archive",
            params={"latitude": lat, "longitude": lon, "start_date": ds, "end_date": ds,
                    "hourly": "precipitation", "timezone": "America/Sao_Paulo"},
            timeout=30,
        )
        r.raise_for_status()
        dados = r.json()
        dados["regiao_id"] = rid
        dados["regiao_nome"] = nome
        salvar(chegada / "clima", f"clima_{rid}_{ds}.json", dados)


def coletar_distritos(ds, chegada):
    url = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios/3550308/distritos"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    salvar(chegada / "distritos", f"distritos_{ds}.json", r.json())


def leituras_robo(ds, chegada):
    sorteio = random.Random(ds)
    linhas = []
    for hora in range(24):
        linhas.append({
            "device_id": f"robo-{sorteio.randint(1, 3)}",
            "regiao_id": sorteio.choice(REGIOES)[0],
            "data_hora": f"{ds}T{hora:02d}:00:00",
            "umidade_pct": round(sorteio.uniform(0, 100), 1),
        })
    salvar(chegada / "robo", f"robo_{ds}.json", linhas)


def conferir_chegada(ds, chegada):
    esperados = [chegada / "clima" / f"clima_{r[0]}_{ds}.json" for r in REGIOES]
    esperados.append(chegada / "distritos" / f"distritos_{ds}.json")
    esperados.append(chegada / "robo" / f"robo_{ds}.json")
    faltando = [p.name for p in esperados if not p.exists() or p.stat().st_size == 0]
    if faltando:
        raise FileNotFoundError(f"arquivos faltando: {faltando}")
