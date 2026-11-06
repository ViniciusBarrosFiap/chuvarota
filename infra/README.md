# Infraestrutura (Terraform, Azure)

Cria o MVP no Azure App Service (Linux, plano gratuito F1): grupo de recursos, plano e o app, que roda a imagem do GitHub Container Registry. O app só aceita HTTPS (TLS 1.2 ou mais), com FTP e Web Deploy por usuário e senha desligados. A única porta exposta é a 443 do site; não existe porta de administração, então nada fica aberto para `0.0.0.0/0` além do próprio site.

A assinatura Azure for Students Starter só permite alguns provedores (Web, SQL, Insights e poucos mais), por isso não uso Container Apps nem ACR.

## Como rodar
1. `az login` (assinatura Azure for Students).
2. `cp terraform.tfvars.example terraform.tfvars` e colocar o id da assinatura (`az account show --query id -o tsv`). O `.tfvars` e o state ficam fora do Git (`.gitignore`).
3. `terraform init && terraform apply`.
4. `./configurar_github.sh` cria o acesso do pipeline: `AZURE_CREDENTIALS` em GitHub Secrets (papel Website Contributor só neste grupo de recursos) e as variáveis `APP_NAME` e `RESOURCE_GROUP`. A partir daí cada push na `main` que passa nos testes de segurança publica sozinho.

Para apagar tudo: `terraform destroy`.
