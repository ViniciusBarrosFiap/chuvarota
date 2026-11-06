output "grupo_de_recursos" {
  value = azurerm_resource_group.rg.name
}

output "app" {
  value = azurerm_linux_web_app.mvp.name
}

output "url_do_mvp" {
  value = "https://${azurerm_linux_web_app.mvp.default_hostname}"
}
