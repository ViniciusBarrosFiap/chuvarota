import json
import re
import unicodedata
from pathlib import Path

from busca import BuscaSemantica
from llm import como_json, perguntar

ALERTAS = Path(__file__).resolve().parents[2] / "mvp" / "data" / "alertas.json"
LIMIAR = 0.58  # ver notebook 01: separa as perguntas com resposta das sem resposta
NAO_CONSTA = "Não consta na base de orientações."
busca = BuscaSemantica()

FORMATO = 'Responda só com JSON: {"resposta": "texto curto", "fonte_id": "id do trecho usado ou null", "recusa": false}.'
EXEMPLOS = """Exemplo 1
Trechos:
[ex-1] Evite andar em áreas com fiação elétrica caída.
Pergunta: Posso andar perto de fios caídos?
Resposta: {"resposta": "Não. Evite andar em áreas com fiação elétrica caída.", "fonte_id": "ex-1", "recusa": false}

Exemplo 2
Trechos:
[ex-1] Evite andar em áreas com fiação elétrica caída.
Pergunta: Qual o preço da bateria do celular?
Resposta: {"resposta": "%s", "fonte_id": null, "recusa": true}
""" % NAO_CONSTA


def vazio(resposta=NAO_CONSTA, extra=None):
    d = {"resposta": resposta, "fonte_id": None, "recusa": True}
    d.update(extra or {})
    return d


def invalido(extra=None):
    d = {"resposta": "", "fonte_id": None, "recusa": False, "invalido": True}
    d.update(extra or {})
    return d


def sem_acento(t):
    return unicodedata.normalize("NFD", t.lower()).encode("ascii", "ignore").decode()


def contexto(achados):
    return "\n".join(f'[{t["id"]}] {t["texto"]}' for t, _ in achados)


def sem_contexto(pergunta):
    sistema = "Você é o assistente do ChuvaRota e orienta cidadãos sobre chuva forte e alagamentos em São Paulo. " + FORMATO
    return como_json(perguntar(sistema, pergunta)) or invalido()


def responder(pergunta, achados):
    sistema = ("Você responde usando SOMENTE os trechos abaixo. Se nenhum trecho trata do assunto da pergunta, "
               'responda {"resposta": "' + NAO_CONSTA + '", "fonte_id": null, "recusa": true}. '
               "Em fonte_id coloque o id do trecho usado, sem os colchetes. A resposta deve ser uma frase, nunca o id. "
               + FORMATO + "\n\n" + EXEMPLOS + "\nAgora a tarefa real.\nTrechos:\n" + contexto(achados))
    return como_json(perguntar(sistema, f"Pergunta: {pergunta}")) or invalido()


def rag_simples(pergunta):
    achados = busca.buscar(pergunta, 3)
    if achados[0][1] < LIMIAR:
        return vazio(extra={"motivo": "abaixo do limiar"})
    return responder(pergunta, achados)


def consultar_risco(regiao):
    for a in json.loads(ALERTAS.read_text(encoding="utf-8"))["alertas"]:
        if sem_acento(regiao) in (a["id"], sem_acento(a["regiao"])):
            return a
    return None


def agente(pergunta):
    # 1) o modelo escolhe a ferramenta
    sistema = ('Escolha UMA ferramenta para a pergunta e responda só com JSON.\n'
               '- {"acao": "consultar_risco", "regiao": "nome da região"} só quando a pergunta cita uma das regiões '
               "(Sé, Pinheiros, Mooca, Santo Amaro, Tatuapé) e quer saber o risco de chuva agora.\n"
               '- {"acao": "buscar"} para qualquer outra pergunta.')
    escolha = como_json(perguntar(sistema, pergunta)) or {}
    if escolha.get("acao") == "consultar_risco":
        regiao = str(escolha.get("regiao", ""))
        # o argumento precisa estar na pergunta do cidadão, senão o modelo pode ter inventado
        if regiao and sem_acento(regiao) in sem_acento(pergunta):
            alerta = consultar_risco(regiao)
            if alerta:
                return {"resposta": f'O risco de chuva agora em {alerta["regiao"]} é {alerta["risco"]} ({alerta["mm_3h"]} mm em 3 h).',
                        "fonte_id": "alertas.json", "recusa": False, "ferramenta": "consultar_risco"}
    # 2) busca e resposta fundamentada
    achados = busca.buscar(pergunta, 3)
    if achados[0][1] < LIMIAR:
        return vazio(extra={"ferramenta": "buscar", "motivo": "abaixo do limiar"})
    saida = responder(pergunta, achados)
    saida["ferramenta"] = "buscar"
    # 3) verificação sem LLM: a fonte citada tem que ser um dos trechos buscados e ter palavras da resposta
    if not saida.get("recusa") and not saida.get("invalido"):
        citado = next((t for t, _ in achados if t["id"] == saida.get("fonte_id")), None)
        palavras = {p for p in re.findall(r"\w{5,}", sem_acento(str(saida.get("resposta", ""))))}
        if citado is None or not palavras & set(re.findall(r"\w{5,}", sem_acento(citado["texto"]))):
            return vazio("Não consegui confirmar a resposta em nenhuma fonte.", {"ferramenta": "buscar", "motivo": "verificação reprovou"})
    return saida


CONFIGURACOES = {"A sem contexto": sem_contexto, "B RAG simples": rag_simples, "C RAG + agente": agente}
