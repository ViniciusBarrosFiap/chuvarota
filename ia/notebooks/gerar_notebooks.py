import nbformat as nbf
from nbclient import NotebookClient

TOPO = "import sys\nsys.path.insert(0, '../src')\nimport json\nimport pandas as pd\nfrom avaliar import carregar_casos\n"


def montar(nome, celulas):
    nb = nbf.v4.new_notebook()
    nb.cells = [nbf.v4.new_markdown_cell(c) if t == "md" else nbf.v4.new_code_cell(c) for t, c in celulas]
    NotebookClient(nb, timeout=900, kernel_name="chuvarota-ia", resources={"metadata": {"path": "."}}).execute()
    nbf.write(nb, nome)


montar("01_base_e_busca.ipynb", [
    ("md", "# 01. Base de conhecimento e busca\nBase com trechos de orientações oficiais (gov.br) sobre alagamentos e enchentes. Aqui conferimos a base e medimos a busca (recall@1 e recall@3)."),
    ("code", TOPO + "from busca import carregar_trechos\nt = pd.DataFrame(carregar_trechos())\nt.groupby(['fonte', 'url']).size().rename('trechos').reset_index()"),
    ("code", "t.sample(6, random_state=1)[['id', 'texto']]"),
    ("md", "## Recall da busca\nA pergunta de teste está certa se o trecho esperado aparece na posição 1 (recall@1) ou entre os 3 primeiros (recall@3). Comparo a busca por palavras (TF-IDF) com a busca semântica (embeddings bge-m3)."),
    ("code", """from busca import Busca, BuscaSemantica
casos = carregar_casos()
resp = [c for c in casos if c['tipo'] == 'resposta']
buscas = {'lexical (TF-IDF)': Busca(), 'semântica (bge-m3)': BuscaSemantica()}
linhas = []
for nome, b in buscas.items():
    r1 = r3 = 0
    for c in resp:
        ids = [x['id'] for x, _ in b.buscar(c['pergunta'], 3)]
        r1 += ids[0] in c['fontes_ok']
        r3 += any(i in c['fontes_ok'] for i in ids)
    linhas.append({'busca': nome, 'recall@1': f'{r1}/{len(resp)} ({100*r1//len(resp)}%)', 'recall@3': f'{r3}/{len(resp)} ({100*r3//len(resp)}%)'})
pd.DataFrame(linhas)"""),
    ("md", "## Limiar de recusa\nSe a melhor nota da busca for menor que o limiar, o assistente nem chama o modelo e responde que não consta. Teste vários valores: quantas perguntas com resposta continuam passando e quantas sem resposta são barradas."),
    ("code", """b = buscas['semântica (bge-m3)']
com = [b.buscar(c['pergunta'], 1)[0][1] for c in resp]
sem = [b.buscar(c['pergunta'], 1)[0][1] for c in casos if c['tipo'] == 'nao_consta']
print('notas das perguntas COM resposta:', sorted(round(x, 2) for x in com))
print('notas das perguntas SEM resposta:', sorted(round(x, 2) for x in sem))
pd.DataFrame([{'limiar': l, 'com resposta que passam': f'{sum(x >= l for x in com)}/{len(com)}', 'sem resposta barradas': f'{sum(x < l for x in sem)}/{len(sem)}'} for l in (0.50, 0.55, 0.58, 0.60, 0.65)])"""),
    ("md", "**Escolha: 0,58.** Com esse limiar todas as perguntas sem resposta são barradas e só 1 pergunta com resposta é perdida. Para um assistente de segurança é melhor recusar do que inventar. Limite: o valor foi escolhido com as mesmas 24 perguntas do teste, então precisa ser revalidado com perguntas novas."),
])

montar("02_geracao_e_placar.ipynb", [
    ("md", "# 02. Geração fundamentada e placar\nTrês configurações, com o mesmo modelo local (qwen2.5:3b no Ollama, temperatura 0) e os mesmos 27 casos:\n- **A sem contexto**: o modelo responde sozinho.\n- **B RAG simples**: busca os 3 trechos mais parecidos e responde só com eles, citando a fonte, ou recusa.\n- **C RAG + agente**: o modelo escolhe uma ferramenta (consultar o risco de chuva do ChuvaRota ou buscar na base) e a resposta passa por uma verificação da fonte."),
    ("code", TOPO + """import configs
from avaliar import rodar, resumo
casos = carregar_casos()
risco = {a['id']: a['risco'] for a in json.load(open('../../mvp/data/alertas.json'))['alertas']}
todos = {nome: rodar(f, casos, risco) for nome, f in configs.CONFIGURACOES.items()}
json.dump(todos, open('../avaliacao/resultados.json', 'w'), ensure_ascii=False, indent=1)
print('ok')"""),
    ("md", "## Placar geral"),
    ("code", "placar = pd.DataFrame({n: resumo(r) for n, r in todos.items()}).T\nplacar.to_csv('../avaliacao/placar.csv')\nplacar"),
    ("md", "## Por tipo de pergunta\nOrientações (18 perguntas com resposta na base), não consta (6 perguntas fora da base) e risco atual (3 perguntas que só a ferramenta do ChuvaRota responde)."),
    ("code", """linhas = []
for n, r in todos.items():
    for tipo in ('resposta', 'nao_consta', 'ferramenta'):
        rs = [x for x in r if x['tipo'] == tipo]
        linhas.append({'config': n, 'tipo': tipo, 'acertos': f"{sum(x['ok'] for x in rs)}/{len(rs)}", 'alucinações': sum(x['alucinou'] for x in rs)})
pd.DataFrame(linhas).pivot(index='config', columns='tipo', values=['acertos', 'alucinações'])"""),
    ("md", "## Onde cada configuração errou"),
    ("code", """for n, r in todos.items():
    print('=====', n)
    for x in r:
        if not x['ok'] or x['alucinou']:
            s = x['saida']
            print(f"caso {x['caso']} ({x['tipo']}) | {x['pergunta']}\\n   -> recusa={s.get('recusa')} fonte={s.get('fonte_id')} motivo={s.get('motivo')} | {str(s.get('resposta'))[:150]}")"""),
])
print("ok")
