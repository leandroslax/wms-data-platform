variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "lambda_role_arn" {
  type = string
}

variable "kms_key_arn" {
  type = string
}

variable "secret_arns" {
  type = map(string)
}

variable "tags" {
  type = map(string)
}
