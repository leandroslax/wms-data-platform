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

variable "vpc_cidr" {
  description = "CIDR block da VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidr" {
  description = "CIDR block da subnet pública"
  type        = string
  default     = "10.0.1.0/24"
}

variable "ssh_allowed_cidrs" {
  description = "Lista de CIDRs autorizados para SSH na EC2 extratora"
  type        = list(string)
  default     = ["0.0.0.0/0"] # restringir para seu IP em produção
}

variable "tags" {
  description = "Tags padrão"
  type        = map(string)
  default     = {}
}
