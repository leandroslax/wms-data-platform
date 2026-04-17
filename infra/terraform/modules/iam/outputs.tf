output "default_tags" {
  value = local.default_tags
}

output "lambda_execution_role_arn" {
  value = aws_iam_role.lambda_execution.arn
}
