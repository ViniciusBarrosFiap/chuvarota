"""Roda todos os testes do carrinho no computador, um depois do outro, e mostra um resumo.
Uso: python maker/tinyml/testar_tudo.py   (precisa de numpy e matplotlib: pip install numpy matplotlib)"""
import subprocess
import sys
import time
from pathlib import Path

AQUI = Path(__file__).parent
TESTES = [
    ("TinyML: o C++ do robô decide igual ao Python", "testar_c.py"),
    ("Setas e joystick do Dabble viram o movimento certo", "testar_direcao.py"),
    ("Filtro da distância e detector de travamento", "testar_seguranca.py"),
    ("Sensor: leituras, calibração e giro", "testar_sensor.py"),
    ("Movimento suave: velocidade pela distância, rampa e navegador", "testar_movimento.py"),
    ("Q-learning: regras do aprendizado", "testar_aprendizado.py"),
    ("Simulação do treino em salas (leva uns segundos)", "simular_treino.py"),
]

resultados = []
for nome, arquivo in TESTES:
    inicio = time.time()
    r = subprocess.run([sys.executable, "-I", str(AQUI / arquivo)], capture_output=True, text=True)
    ok = r.returncode == 0
    resultados.append((nome, ok, time.time() - inicio))
    print(f"{'ok  ' if ok else 'ERRO'} {nome} ({resultados[-1][2]:.1f} s)")
    if not ok:
        print((r.stdout + r.stderr).strip()[-1500:])

falhas = [n for n, ok, _ in resultados if not ok]
print()
print("todos os testes passaram" if not falhas else f"{len(falhas)} teste(s) falharam: " + ", ".join(falhas))
sys.exit(1 if falhas else 0)
