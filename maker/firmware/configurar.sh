#!/bin/bash
# cria firmware/robo/config.h com o token do MVP e o Wi-Fi que você digitar (o config.h não vai para o Git)
set -euo pipefail
cd "$(dirname "$0")"
TFVARS=../../infra/terraform.tfvars
[ -f "$TFVARS" ] || { echo "não achei $TFVARS (o token do robô fica lá, na chave robo_token)"; exit 1; }
TOKEN=$(grep -E '^robo_token' "$TFVARS" | cut -d'"' -f2)
read -r -p "Nome do Wi-Fi (2,4 GHz): " SSID
read -r -s -p "Senha do Wi-Fi: " SENHA
echo
SSID="$SSID" SENHA="$SENHA" TOKEN="$TOKEN" python3 - <<'PY'
import os
t = open("robo/config.example.h", encoding="utf-8").read()
t = t.replace("nome-da-rede", os.environ["SSID"]).replace("senha-da-rede", os.environ["SENHA"]).replace("troque-pelo-token", os.environ["TOKEN"])
open("robo/config.h", "w", encoding="utf-8").write(t)
PY
echo "config.h criado. Agora: ./gravar.sh"
