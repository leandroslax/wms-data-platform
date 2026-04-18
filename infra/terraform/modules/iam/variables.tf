variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "kms_key_arns" {
  description = "List of KMS key ARNs that the Glue role needs to use (decrypt, generate data key)"
  type        = list(string)
  default     = []
}
