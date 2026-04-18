variable "project_name" {
  description = "Nome do projeto"
  type        = string
}

variable "environment" {
  description = "Ambiente (dev, prod)"
  type        = string
}

variable "aws_region" {
  description = "Região AWS"
  type        = string
}

variable "aws_account_id" {
  description = "ID da conta AWS"
  type        = string
}

variable "subnet_id" {
  description = "ID da subnet pública onde a EC2 será criada"
  type        = string
}

variable "security_group_id" {
  description = "ID do security group da EC2 extratora"
  type        = string
}

variable "instance_type" {
  description = "Tipo da instância EC2"
  type        = string
  default     = "t3.small"
}

variable "ssh_public_key" {
  description = "Chave pública SSH para acesso à EC2"
  type        = string
}

variable "tags" {
  description = "Tags padrão"
  type        = map(string)
  default     = {}
}
