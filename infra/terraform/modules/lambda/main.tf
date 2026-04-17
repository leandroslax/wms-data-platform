locals {
  functions = {
    extractor = {
      memory_size = 1024
      timeout     = 900
    }
    api = {
      memory_size = 512
      timeout     = 30
    }
    embedder = {
      memory_size = 512
      timeout     = 300
    }
  }
}

resource "aws_lambda_function" "this" {
  for_each      = local.functions
  function_name = "${var.project_name}-${var.environment}-${each.key}"
  role          = var.lambda_role_arn
  package_type  = "Image"
  image_uri     = var.image_uri
  timeout       = each.value.timeout
  memory_size   = each.value.memory_size
  kms_key_arn   = var.kms_key_arn

  environment {
    variables = {
      APP_ENV             = var.environment
      ORACLE_SECRET_ARN   = lookup(var.secret_arns, "oracle_credentials", "")
      QDRANT_SECRET_ARN   = lookup(var.secret_arns, "qdrant", "")
      LANGFUSE_SECRET_ARN = lookup(var.secret_arns, "langfuse", "")
    }
  }

  tags = var.tags
}
