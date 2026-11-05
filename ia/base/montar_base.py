import difflib
import json
import re
import subprocess
from pathlib import Path

BRUTOS = Path(__file__).parent / "brutos"
FONTES = {
    "alagamentos_mdr": ("Como agir: Alagamentos (MDR, 2021)", "https://www.gov.br/mdr/pt-br/assuntos/protecao-e-defesa-civil/copy2_of_ComoagirAlagamentosMDR.pdf", "pdf"),
    "inundacoes_mdr": ("Como agir: Inundações (MDR)", "https://www.gov.br/mdr/pt-br/assuntos/protecao-e-defesa-civil/ComoagirInundaesMDR.pdf", "pdf"),
    "autoprotecao": ("Medidas de autoproteção em alagamentos (gov.br, 2022)", "https://www.gov.br/pt-br/noticias/transito-e-transportes/2022/07/conheca-medidas-de-autoprotecao-que-a-populacao-deve-tomar-em-casos-de-alagamento", "html"),
    "lepto_medidas": ("Prevenção da leptospirose em enchentes (Min. da Saúde, 2022)", "https://www.gov.br/pt-br/noticias/saude-e-vigilancia-sanitaria/2022/11/medidas-essenciais-para-prevencao-da-leptospirose-em-caso-de-inundacoes-e-enchentes", "html"),
    "lepto_como_proteger": ("Como me proteger da leptospirose (Min. da Saúde, 2024)", "https://www.gov.br/saude/pt-br/acesso-a-informacao/faq/enchentes-e-inundacoes-leptospirose/como-posso-me-proteger", "html"),
}


def texto(chave, tipo):
    if tipo == "pdf":
        pdf = BRUTOS / f"{chave}.pdf"
        return subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, text=True).stdout
    return (BRUTOS / f"{chave}.txt").read_text(encoding="utf-8")


def trechos(txt):
    txt = re.sub(r"[ \t]+", " ", txt)
    txt = re.sub(r"(?<![.;:?!])\n(?=[a-zà-ú(])", " ", txt)  # junta linhas quebradas no meio da frase
    saida = []
    for linha in txt.splitlines():
        linha = linha.strip(" -•\f")
        # só frases com cara de orientação: 7 palavras ou mais
        for frase in re.split(r"(?<=[;.])\s+", linha):
            frase = frase.strip()
            if len(frase.split()) >= 7 and not frase.endswith("?") and not frase.startswith(("Com informações", "#", "Publicado", "Atualizado")):
                saida.append(frase)
    return saida


chunks = []
for chave, (titulo, url, tipo) in FONTES.items():
    n = 0
    for t in trechos(texto(chave, tipo)):
        # as duas cartilhas do MDR repetem muita coisa: pula trecho quase igual a um que já entrou
        if any(difflib.SequenceMatcher(None, t.lower(), c["texto"].lower()).ratio() > 0.8 for c in chunks):
            continue
        n += 1
        chunks.append({"id": f"{chave}-{n:02d}", "fonte": titulo, "url": url, "texto": t})

# telefones: no pdf estão em linhas curtas que o corte descarta
tel = FONTES["alagamentos_mdr"]
chunks.append({"id": "alagamentos_mdr-tel", "fonte": tel[0], "url": tel[1],
               "texto": "Defesa Civil: 199. Bombeiros: 193. Polícia Militar: 190. SAMU: 192."})

(Path(__file__).parent / "trechos.jsonl").write_text("\n".join(json.dumps(c, ensure_ascii=False) for c in chunks), encoding="utf-8")
print(len(chunks), "trechos")
