resource "aws_kms_key" "platform" {
  description         = "KMS key for ${var.project_name} ${var.environment} secrets and data"
  enable_key_rotation = true
  tags                = var.tags
}

resource "aws_kms_alias" "platform" {
  name          = "alias/${var.project_name}-${var.environment}"
  target_key_id = aws_kms_key.platform.key_id
}

locals {
  secrets = {
    oracle_credentials = jsonencode({ username = "wms_reader", password = "change-me", dsn = "change-me" })
    qdrant             = jsonencode({ url = "change-me", api_key = "change-me" })
    langfuse           = jsonencode({ public_key = "change-me", secret_key = "change-me", host = "change-me" })
    redshift           = jsonencode({ host = "change-me", port = 5439, dbname = "wms", username = "wmsadmin", password = "change-me" })
  }
}

resource "aws_secretsmanager_secret" "this" {
  for_each   = local.secrets
  name       = "${var.project_name}/${var.environment}/${each.key}"
  kms_key_id = aws_kms_key.platform.arn
  tags       = var.tags
}

resource "aws_secretsmanager_secret_version" "this" {
  for_each      = local.secrets
  secret_id     = aws_secretsmanager_secret.this[each.key].id
  secret_string = each.value
}
