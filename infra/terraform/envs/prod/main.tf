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
}

module "iam" {
  source       = "../../modules/iam"
  environment  = local.environment
  project_name = var.project_name
}

module "secrets" {
  source       = "../../modules/secrets"
  environment  = local.environment
  project_name = var.project_name
  tags         = module.iam.default_tags
}

module "s3" {
  source         = "../../modules/s3"
  environment    = local.environment
  project_name   = var.project_name
  aws_region     = var.aws_region
  aws_account_id = var.aws_account_id
  kms_key_arn    = module.secrets.kms_key_arn
  tags           = module.iam.default_tags
}

module "lambda" {
  source          = "../../modules/lambda"
  environment     = local.environment
  project_name    = var.project_name
  lambda_role_arn = module.iam.lambda_execution_role_arn
  kms_key_arn     = module.secrets.kms_key_arn
  secret_arns     = module.secrets.secret_arns
  tags            = module.iam.default_tags
}

module "monitoring" {
  source                = "../../modules/monitoring"
  environment           = local.environment
  project_name          = var.project_name
  lambda_function_names = module.lambda.lambda_function_names
  tags                  = module.iam.default_tags
}
