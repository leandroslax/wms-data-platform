output "kms_key_arn" {
  value = aws_kms_key.platform.arn
}

output "secret_arns" {
  value = { for key, secret in aws_secretsmanager_secret.this : key => secret.arn }
}
