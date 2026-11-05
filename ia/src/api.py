import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).parent))
import configs  # noqa: E402

app = FastAPI(title="ChuvaRota IA")


class Pergunta(BaseModel):
    pergunta: str = Field(min_length=3, max_length=300)


@app.post("/perguntar")
def perguntar(p: Pergunta):
    try:
        saida = configs.agente(p.pergunta)
    except Exception:
        raise HTTPException(503, "assistente indisponível")
    trecho = next((t["texto"] for t in configs.busca.trechos if t["id"] == saida.get("fonte_id")), None)
    # a pergunta não é gravada em lugar nenhum (LGPD)
    return {**saida, "trecho_citado": trecho}
