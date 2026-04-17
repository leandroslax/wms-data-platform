output "lambda_function_names" {
  description = "Lambda functions created by the module"
  value       = { for key, fn in aws_lambda_function.this : key => fn.function_name }
}
