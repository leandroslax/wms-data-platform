terraform {
  required_version = ">= 1.7.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.70"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

locals {
  environment = "prod"

  # default_tags definido aqui para evitar dependência circular entre iam e secrets
  default_tags = {
    project     = var.project_name
    environment = local.environment
    managed_by  = "terraform"
  }
}

module "secrets" {
  source       = "../../modules/secrets"
  environment  = local.environment
  project_name = var.project_name
  tags         = local.default_tags
}

module "iam" {
  source       = "../../modules/iam"
  environment  = local.environment
  project_name = var.project_name
  kms_key_arns = [module.secrets.kms_key_arn]
}

module "s3" {
  source         = "../../modules/s3"
  environment    = local.environment
  project_name   = var.project_name
  aws_region     = var.aws_region
  aws_account_id = var.aws_account_id
  kms_key_arn    = module.secrets.kms_key_arn
  tags           = local.default_tags
}

module "ecr" {
  source       = "../../modules/ecr"
  environment  = local.environment
  project_name = var.project_name
  tags         = local.default_tags
}

module "lambda" {
  source          = "../../modules/lambda"
  environment     = local.environment
  project_name    = var.project_name
  lambda_role_arn = module.iam.lambda_execution_role_arn
  kms_key_arn     = module.secrets.kms_key_arn
  image_uri       = "896159010925.dkr.ecr.us-east-1.amazonaws.com/wms-data-platform-prod-lambda:latest"
  secret_arns     = module.secrets.secret_arns
  tags            = local.default_tags
}

module "monitoring" {
  source                = "../../modules/monitoring"
  environment           = local.environment
  project_name          = var.project_name
  lambda_function_names = module.lambda.lambda_function_names
  tags                  = local.default_tags
}
