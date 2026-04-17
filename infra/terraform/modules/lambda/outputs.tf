output "lambda_function_names" {
  value = { for key, fn in aws_lambda_function.this : key => fn.function_name }
}

output "ecr_repository_url" {
  value = aws_ecr_repository.lambda.repository_url
}
