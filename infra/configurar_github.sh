#!/bin/bash
# cria o acesso do pipeline ao Azure (só para este grupo de recursos) e guarda em GitHub Secrets e Variables
set -euo pipefail
cd "$(dirname "$0")"

RG=$(terraform output -raw grupo_de_recursos)
APP=$(terraform output -raw app)
SUB=$(az account show --query id -o tsv)

SP=$(mktemp)
trap 'rm -f "$SP"' EXIT
az ad sp create-for-rbac --name sp-chuvarota-deploy --role "Website Contributor" \
  --scopes "/subscriptions/$SUB/resourceGroups/$RG" --json-auth > "$SP"

gh secret set AZURE_CREDENTIALS < "$SP"
gh variable set APP_NAME --body "$APP"
gh variable set RESOURCE_GROUP --body "$RG"
echo "pronto: secret AZURE_CREDENTIALS e variáveis APP_NAME e RESOURCE_GROUP criadas"
