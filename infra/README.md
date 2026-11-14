# Infraestrutura (Terraform, Azure)

Aqui a nuvem é montada por código. O Terraform cria no Azure um grupo de recursos, um plano gratuito (F1) e o app do site, que roda a imagem guardada no GitHub. O site só aceita HTTPS, e o envio de arquivos por FTP e por usuário e senha está desligado. A única porta aberta é a 443 do próprio site, então não existe porta de administração exposta.

A minha assinatura de estudante só deixa usar alguns serviços do Azure, por isso não usei Container Apps nem ACR.

## Como rodar
1. `az login` (assinatura Azure for Students).
2. `cp terraform.tfvars.example terraform.tfvars` e colocar o id da assinatura (`az account show --query id -o tsv`). O `.tfvars` e o state ficam fora do Git (`.gitignore`).
3. `terraform init && terraform apply`.
4. `./configurar_github.sh` cria o acesso do pipeline: `AZURE_CREDENTIALS` em GitHub Secrets (papel Website Contributor só neste grupo de recursos) e as variáveis `APP_NAME` e `RESOURCE_GROUP`. Daí em diante, cada push na `main` que passa nos testes de segurança publica o site sozinho.

Para apagar tudo: `terraform destroy`.
