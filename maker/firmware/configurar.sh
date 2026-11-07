#!/bin/bash
# cria firmware/robo/wifi_local.h com o Wi-Fi que você digitar (o Git ignora esse arquivo; o token já está no config.h)
set -euo pipefail
cd "$(dirname "$0")"
read -r -p "Nome do Wi-Fi (2,4 GHz): " SSID
read -r -s -p "Senha do Wi-Fi: " SENHA
echo
SSID="$SSID" SENHA="$SENHA" python3 - <<'PY'
import os
t = open("robo/wifi_local.example.h", encoding="utf-8").read()
t = t.replace("nome-do-seu-wifi", os.environ["SSID"]).replace("senha-do-seu-wifi", os.environ["SENHA"])
open("robo/wifi_local.h", "w", encoding="utf-8").write(t)
PY
echo "wifi_local.h criado. Agora: ./gravar.sh"
