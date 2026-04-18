variable "project_name" {
  description = "Project name"
  type        = string
  default     = "wms-data-platform"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "aws_account_id" {
  description = "AWS account id"
  type        = string
  default     = "896159010925"
}

variable "ssh_public_key" {
  description = "Chave pública SSH para acesso à EC2 extratora (conteúdo do ~/.ssh/id_rsa.pub ou similar)"
  type        = string
  default     = ""
}

variable "ssh_allowed_cidrs" {
  description = "CIDRs autorizados para SSH na EC2 (use seu IP: curl ifconfig.me)"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "redshift_admin_password" {
  description = "Admin password for Redshift Serverless namespace."
  type        = string
  sensitive   = true
  default     = "WmsAdmin2026!"  # trocar antes do deploy em prod
}
