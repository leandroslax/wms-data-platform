locals {
  buckets = {
    bronze = {
      name = "wms-bronze-${var.environment}"
    }
    silver = {
      name = "wms-silver-${var.environment}"
    }
    gold = {
      name = "wms-gold-${var.environment}"
    }
    artifacts = {
      name = "wms-artifacts-${var.environment}"
    }
    query_results = {
      name = "wms-query-results-${var.environment}"
    }
    frontend = {
      name = "wms-frontend-${var.environment}"
    }
  }
}

resource "aws_s3_bucket" "this" {
  for_each = local.buckets
  bucket   = each.value.name
  tags     = var.tags
}

resource "aws_s3_bucket_versioning" "this" {
  for_each = aws_s3_bucket.this

  bucket = each.value.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  for_each = aws_s3_bucket.this

  bucket = each.value.id
  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = var.kms_key_arn
      sse_algorithm     = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "this" {
  for_each = aws_s3_bucket.this

  bucket                  = each.value.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "query_results" {
  bucket = aws_s3_bucket.this["query_results"].id

  rule {
    id     = "expire-query-results"
    status = "Enabled"

    expiration {
      days = 7
    }

    filter {
      prefix = ""
    }
  }
}
