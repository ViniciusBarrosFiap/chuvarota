#!/bin/bash
# cria a nuvem e publica o MVP. Precisa de `az login` feito e de infra/terraform.tfvars
set -euo pipefail
cd "$(dirname "$0")"

terraform init
terraform apply -auto-approve          # registro, logs e ambiente; o app só entra com a imagem
ACR=$(terraform output -raw acr)
IMG="$ACR.azurecr.io/chuvarota-mvp:inicial"
az acr login --name "$ACR"
docker build -t "$IMG" ..
docker push "$IMG"
terraform apply -auto-approve -var "imagem=$IMG"
terraform output
