variable "project_name" {
  description = "Project name used in resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "aws_region" {
  description = "AWS region for globally unique resource names"
  type        = string
}

variable "aws_account_id" {
  description = "AWS account id for globally unique resource names"
  type        = string
}

variable "kms_key_arn" {
  description = "KMS key ARN used for bucket encryption"
  type        = string
}

variable "tags" {
  description = "Common tags applied to all resources"
  type        = map(string)
  default     = {}
}
