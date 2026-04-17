terraform {
  backend "s3" {
    bucket         = "wms-data-platform-tf-state-896159010925"
    key            = "wms-data-platform/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "wms-tf-locks"
    encrypt        = true
  }
}
