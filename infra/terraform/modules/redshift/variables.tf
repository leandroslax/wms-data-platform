variable "project_name" {
  description = "Project name used as prefix for all resources."
  type        = string
}

variable "environment" {
  description = "Deployment environment (dev | prod)."
  type        = string
}

variable "aws_region" {
  description = "AWS region."
  type        = string
  default     = "us-east-1"
}

variable "aws_account_id" {
  description = "AWS account ID."
  type        = string
}

variable "admin_username" {
  description = "Admin username for the Redshift Serverless namespace."
  type        = string
  default     = "wmsadmin"
}

variable "admin_password" {
  description = "Admin password for the Redshift Serverless namespace."
  type        = string
  sensitive   = true
}

variable "db_name" {
  description = "Default database name."
  type        = string
  default     = "wms"
}

variable "base_capacity" {
  description = "Base RPU capacity for the workgroup. Minimum is 8."
  type        = number
  default     = 8
}

variable "kms_key_arn" {
  description = "KMS key ARN for Redshift encryption."
  type        = string
}

variable "glue_role_arn" {
  description = "ARN of the Glue execution role (for Spectrum access)."
  type        = string
}

variable "subnet_ids" {
  description = "List of subnet IDs for the workgroup VPC config. Empty = public endpoint."
  type        = list(string)
  default     = []
}

variable "security_group_ids" {
  description = "Security group IDs for the workgroup. Empty = default."
  type        = list(string)
  default     = []
}

variable "gold_bucket_arn" {
  description = "ARN of the gold S3 bucket for Spectrum external tables."
  type        = string
}

variable "tags" {
  description = "Tags applied to all resources."
  type        = map(string)
  default     = {}
}
