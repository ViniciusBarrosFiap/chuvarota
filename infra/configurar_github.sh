#!/bin/bash
# cria o acesso do pipeline ao Azure e guarda em GitHub Secrets e Variables. Rodar depois do publicar.sh
set -euo pipefail
cd "$(dirname "$0")"

RG=$(terraform output -raw grupo_de_recursos)
ACR=$(terraform output -raw acr)
SUB=$(az account show --query id -o tsv)

SP=$(mktemp)
trap 'rm -f "$SP"' EXIT
az ad sp create-for-rbac --name sp-chuvarota-deploy --role Contributor \
  --scopes "/subscriptions/$SUB/resourceGroups/$RG" --json-auth > "$SP"
az role assignment create --assignee "$(python3 -c "import json,sys;print(json.load(open('$SP'))['clientId'])")" \
  --role AcrPush --scope "$(az acr show --name "$ACR" --query id -o tsv)" > /dev/null

gh secret set AZURE_CREDENTIALS < "$SP"
gh variable set ACR_NAME --body "$ACR"
gh variable set RESOURCE_GROUP --body "$RG"
echo "pronto: secret AZURE_CREDENTIALS e variáveis ACR_NAME e RESOURCE_GROUP criadas"
