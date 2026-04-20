output "default_tags" {
  value = local.default_tags
}

output "lambda_execution_role_arn" {
  value = aws_iam_role.lambda_execution.arn
}

output "glue_role_arn" {
  description = "ARN of the Glue execution role."
  value       = aws_iam_role.glue.arn
}

output "glue_role_name" {
  description = "Name of the Glue execution role."
  value       = aws_iam_role.glue.name
}
