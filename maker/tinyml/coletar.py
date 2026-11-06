"""Grava no dados_reais.csv o que o robô imprime no modo coleta (MODO_COLETA 1 no config.h).
Uso: python coletar.py /dev/cu.usbserial-XXXX
Com o robô parado, mude a luz e a distância e digite 0 a 5 para dizer qual é a situação (ver docs/teste_pecas.md)."""
import sys
from pathlib import Path

import serial  # pip install pyserial

SAIDA = Path(__file__).parent / "dados_reais.csv"
nova = not SAIDA.exists()
with serial.Serial(sys.argv[1], 115200, timeout=2) as porta, open(SAIDA, "a") as f:
    if nova:
        f.write("luz,distancia_cm,classe\n")
    print("gravando em", SAIDA, "(Ctrl+C para parar). Digite 0 a 5 + Enter para escolher a classe.")
    while True:
        try:
            if sys.stdin in __import__("select").select([sys.stdin], [], [], 0)[0]:
                porta.write(sys.stdin.readline().strip()[:1].encode())
            linha = porta.readline().decode(errors="ignore").strip()
            if linha and linha[0].isdigit() and linha.count(",") == 2:
                f.write(linha + "\n")
        except KeyboardInterrupt:
            break
