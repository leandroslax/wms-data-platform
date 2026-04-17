terraform {
  backend "s3" {
    bucket         = "wms-tf-state"
    key            = "wms-data-platform/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "wms-tf-locks"
    encrypt        = true
  }
}
