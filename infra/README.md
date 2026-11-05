# Infraestrutura (Terraform, Azure)

Cria o ambiente do MVP no Azure: grupo de recursos, registro de imagens (ACR, sem usuário admin), logs, ambiente do Container Apps e o app, que puxa a imagem do registro por identidade gerenciada. A única porta exposta é a 443 (HTTPS) do MVP; não existe porta de administração, então nada fica aberto para `0.0.0.0/0` além do site.

## Como rodar
1. `az login` (assinatura Azure for Students).
2. `cp terraform.tfvars.example terraform.tfvars` e colocar o id da assinatura (`az account show --query id -o tsv`). O `.tfvars` e o state ficam fora do Git (`.gitignore`).
3. `./publicar.sh` cria a nuvem, envia a primeira imagem e sobe o app.
4. `./configurar_github.sh` cria o acesso do pipeline (`AZURE_CREDENTIALS` em GitHub Secrets; `ACR_NAME` e `RESOURCE_GROUP` em Variables). A partir daí cada push na `main` que passa nos testes de segurança publica sozinho.

Para apagar tudo: `terraform destroy`.
