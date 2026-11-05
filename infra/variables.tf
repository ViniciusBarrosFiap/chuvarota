variable "subscription_id" {
  type        = string
  description = "ID da assinatura Azure (vem do terraform.tfvars, que não vai para o Git)"
}

variable "regiao" {
  type    = string
  default = "brazilsouth"
}

variable "imagem" {
  type        = string
  default     = ""
  description = "Imagem do MVP no ACR. Vazio na primeira etapa, quando o registro ainda não tem imagem."
}
