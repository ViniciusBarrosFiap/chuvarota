import json
from pathlib import Path

from busca import carregar_trechos

CASOS = Path(__file__).resolve().parents[1] / "avaliacao" / "casos.json"
IDS = {t["id"] for t in carregar_trechos()}


def carregar_casos():
    return json.loads(CASOS.read_text(encoding="utf-8"))


def julgar(caso, saida, risco_atual=None):
    texto = str(saida.get("resposta", "")).lower()
    recusou = bool(saida.get("recusa"))
    fonte = saida.get("fonte_id")
    r = {"json_valido": not saida.get("invalido"), "recusou": recusou, "citou_certo": None}
    if caso["tipo"] == "nao_consta":
        r["ok"] = recusou
        r["alucinou"] = not recusou
    elif caso["tipo"] == "ferramenta":
        r["ok"] = (not recusou) and risco_atual in texto
        r["citou_certo"] = fonte == "alertas.json"
        r["alucinou"] = (not recusou) and not r["ok"]
    else:
        termos = all(any(alt in texto for alt in grupo) for grupo in caso["termos"])
        proibido = any(p in texto for p in caso.get("proibido", []))
        r["ok"] = (not recusou) and termos and not proibido
        r["citou_certo"] = fonte in caso["fontes_ok"]
        r["alucinou"] = (not recusou) and (proibido or (fonte is not None and fonte not in IDS))
    return r


def rodar(config, casos, risco):
    saida = []
    for c in casos:
        s = config(c["pergunta"])
        saida.append({"caso": c["id"], "tipo": c["tipo"], "pergunta": c["pergunta"], "saida": s,
                      **julgar(c, s, risco.get(c.get("regiao")))})
    return saida


def resumo(resultados):
    n = len(resultados)
    com_fonte = [r for r in resultados if r["citou_certo"] is not None]
    return {
        "acertos (%)": round(100 * sum(r["ok"] for r in resultados) / n),
        "acerto com fonte certa (%)": round(100 * sum(r["ok"] and r["citou_certo"] is not False and (r["citou_certo"] or r["tipo"] == "nao_consta") for r in resultados) / n),
        "alucinações (%)": round(100 * sum(r["alucinou"] for r in resultados) / n),
        "JSON válido (%)": round(100 * sum(r["json_valido"] for r in resultados) / n),
        "citação certa (%)": round(100 * sum(r["citou_certo"] for r in com_fonte) / len(com_fonte)),
        "recusa correta (%)": round(100 * sum(r["recusou"] for r in resultados if r["tipo"] == "nao_consta") / 6),
    }
