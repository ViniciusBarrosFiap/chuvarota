resource "random_string" "sufixo" {
  length  = 5
  upper   = false
  special = false
}

resource "azurerm_resource_group" "rg" {
  name     = "rg-chuvarota"
  location = var.regiao
}

resource "azurerm_service_plan" "plano" {
  name                = "plan-chuvarota"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  os_type             = "Linux"
  sku_name            = var.sku
}

resource "azurerm_linux_web_app" "mvp" {
  name                = "chuvarota-${random_string.sufixo.result}"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  service_plan_id     = azurerm_service_plan.plano.id

  # só HTTPS, e sem as portas de publicação por usuário e senha (FTP e Web Deploy)
  https_only                                     = true
  ftp_publish_basic_authentication_enabled       = false
  webdeploy_publish_basic_authentication_enabled = false

  site_config {
    always_on           = var.sku != "F1" # o plano gratuito não aceita
    ftps_state          = "Disabled"
    minimum_tls_version = "1.2"

    application_stack {
      docker_image_name   = var.imagem
      docker_registry_url = "https://ghcr.io"
    }
  }

  app_settings = {
    WEBSITES_PORT                       = "8000"
    WEBSITES_ENABLE_APP_SERVICE_STORAGE = "false"
    ROBO_TOKEN                          = var.robo_token
  }

  # a imagem passa a ser atualizada pelo pipeline
  lifecycle {
    ignore_changes = [site_config[0].application_stack]
  }
}
