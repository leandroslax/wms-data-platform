variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "lambda_function_names" {
  type = map(string)
}

variable "tags" {
  type = map(string)
}
