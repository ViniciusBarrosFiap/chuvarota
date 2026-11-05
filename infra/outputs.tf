output "acr" {
  value = azurerm_container_registry.acr.name
}

output "grupo_de_recursos" {
  value = azurerm_resource_group.rg.name
}

output "url_do_mvp" {
  value = try("https://${azurerm_container_app.mvp[0].ingress[0].fqdn}", "ainda sem imagem")
}
