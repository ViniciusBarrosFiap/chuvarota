variable "subscription_id" {
  type        = string
  description = "ID da assinatura Azure (vem do terraform.tfvars, que não vai para o Git)"
}

variable "regiao" {
  type    = string
  default = "brazilsouth"
}

variable "sku" {
  type        = string
  default     = "F1"
  description = "Plano do App Service: F1 é gratuito; B1 custa cerca de US$ 13 por mês"
}

variable "imagem" {
  type        = string
  default     = "viniciusbarrosfiap/chuvarota-mvp:latest"
  description = "Imagem do MVP no GitHub Container Registry (ghcr.io)"
}

variable "robo_token" {
  type        = string
  sensitive   = true
  description = "Token que o robô manda no cabeçalho X-Token (vem do terraform.tfvars, fora do Git)"
}
