variable "project_name" {
  description = "Project name"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "lambda_role_arn" {
  description = "IAM role ARN used by Lambda"
  type        = string
}

variable "kms_key_arn" {
  description = "KMS key ARN used by Lambda"
  type        = string
}

variable "image_uri" {
  description = "Container image URI published in ECR"
  type        = string
}

variable "secret_arns" {
  description = "Secrets Manager ARNs by logical name"
  type        = map(string)
}

variable "tags" {
  description = "Common tags"
  type        = map(string)
  default     = {}
}
