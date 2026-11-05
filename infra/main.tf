resource "random_string" "sufixo" {
  length  = 6
  upper   = false
  special = false
}

resource "azurerm_resource_group" "rg" {
  name     = "rg-chuvarota"
  location = var.regiao
}

# registro de imagens: sem usuário admin, o acesso é por identidade
resource "azurerm_container_registry" "acr" {
  name                = "chuvarota${random_string.sufixo.result}"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "Basic"
  admin_enabled       = false
}

resource "azurerm_log_analytics_workspace" "logs" {
  name                = "log-chuvarota"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

resource "azurerm_container_app_environment" "env" {
  name                       = "cae-chuvarota"
  resource_group_name        = azurerm_resource_group.rg.name
  location                   = azurerm_resource_group.rg.location
  log_analytics_workspace_id = azurerm_log_analytics_workspace.logs.id
}

resource "azurerm_user_assigned_identity" "app" {
  name                = "id-chuvarota-mvp"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
}

resource "azurerm_role_assignment" "puxar_imagem" {
  scope                = azurerm_container_registry.acr.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.app.principal_id
}

# só existe depois que há uma imagem no registro
resource "azurerm_container_app" "mvp" {
  count                        = var.imagem == "" ? 0 : 1
  name                         = "chuvarota-mvp"
  resource_group_name          = azurerm_resource_group.rg.name
  container_app_environment_id = azurerm_container_app_environment.env.id
  revision_mode                = "Single"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.app.id]
  }

  registry {
    server   = azurerm_container_registry.acr.login_server
    identity = azurerm_user_assigned_identity.app.id
  }

  template {
    min_replicas = 1
    max_replicas = 2

    container {
      name   = "mvp"
      image  = var.imagem
      cpu    = 0.25
      memory = "0.5Gi"

      liveness_probe {
        transport = "HTTP"
        port      = 8000
        path      = "/health"
      }
    }
  }

  # a única porta exposta é a 443 (HTTPS) do MVP; não existe porta de administração
  ingress {
    external_enabled           = true
    target_port                = 8000
    allow_insecure_connections = false

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  # a imagem passa a ser atualizada pelo pipeline
  lifecycle {
    ignore_changes = [template[0].container[0].image]
  }

  depends_on = [azurerm_role_assignment.puxar_imagem]
}
