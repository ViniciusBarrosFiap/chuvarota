#!/bin/bash
# compila, grava no ESP32 ligado por USB e abre o Monitor Serial. Uso: ./gravar.sh [robo|teste_pecas]
set -euo pipefail
cd "$(dirname "$0")"
PROJETO=${1:-robo}
FQBN=esp32:esp32:esp32:PartitionScheme=huge_app  # o programa com Bluetooth não cabe na partição padrão
arduino-cli lib install DabbleESP32 > /dev/null
[ "$PROJETO" = "robo" ] && [ ! -f robo/config.h ] && { echo "rode ./configurar.sh antes (cria o config.h)"; exit 1; }
PORTA=$(ls /dev/cu.usbserial* /dev/cu.SLAB* /dev/cu.wchusbserial* /dev/cu.usbmodem* 2>/dev/null | head -1 || true)
[ -n "$PORTA" ] || { echo "ESP32 não encontrado. Conecte o cabo USB (de dados, não só de carga) e confira o driver CP210x ou CH340."; exit 1; }
echo "porta: $PORTA"
arduino-cli compile --fqbn "$FQBN" "$PROJETO"
arduino-cli upload --fqbn "$FQBN" -p "$PORTA" "$PROJETO"
echo "gravado. Abrindo o Monitor Serial (Ctrl+C para sair)"
arduino-cli monitor -p "$PORTA" -c baudrate=115200
