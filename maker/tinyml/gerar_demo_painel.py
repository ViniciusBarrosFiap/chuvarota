"""Gera maker/painel/demo.js: um treino SIMULADO (o mesmo código do robô, em salas simuladas) no formato exato que o carrinho manda pela porta
serial, para o painel mostrar a demonstração sem o carrinho. Uso: python maker/tinyml/gerar_demo_painel.py [ciclos] [semente]
A semente 2 é a mediana entre 6 sementes testadas (não é a melhor nem a pior)."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

AQUI = Path(__file__).parent
FW = AQUI.parent / "firmware" / "robo"
CICLOS = int(sys.argv[1]) if len(sys.argv) > 1 else 9000
SEMENTE = int(sys.argv[2]) if len(sys.argv) > 2 else 2

with tempfile.TemporaryDirectory() as tmp:
    exe = Path(tmp) / "mundo"
    subprocess.run(["c++", "-std=c++14", "-O2", "-I", str(FW), str(AQUI / "mundo_treino.cpp"), "-o", str(exe)], check=True)
    saida = subprocess.run([str(exe), "--demo", str(CICLOS), str(SEMENTE)], capture_output=True, text=True, check=True).stdout

linhas = [l for l in saida.splitlines() if l.strip()]
descricao = f"Treino simulado ({CICLOS} ciclos, semente {SEMENTE}): o mesmo código do robô aprendendo em salas simuladas. Não são dados do carrinho real."
destino = AQUI.parent / "painel" / "demo.js"
destino.write_text(
    "// Gerado por maker/tinyml/gerar_demo_painel.py. Não edite à mão.\n"
    "window.DEMO = " + json.dumps({"descricao": descricao, "linhas": linhas}, ensure_ascii=False, separators=(",", ":")) + ";\n",
    encoding="utf-8",
)
print(f"{len(linhas)} linhas, {destino.stat().st_size / 1024:.0f} KB em {destino}")
