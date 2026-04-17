locals {
  bucket_prefix = "wms-dp-${var.environment}"

  buckets = {
    bronze = {
      name = "${local.bucket_prefix}-bronze-${var.aws_region}-${var.aws_account_id}"
    }
    silver = {
      name = "${local.bucket_prefix}-silver-${var.aws_region}-${var.aws_account_id}"
    }
    gold = {
      name = "${local.bucket_prefix}-gold-${var.aws_region}-${var.aws_account_id}"
    }
    artifacts = {
      name = "${local.bucket_prefix}-artifacts-${var.aws_region}-${var.aws_account_id}"
    }
    query_results = {
      name = "${local.bucket_prefix}-query-results-${var.aws_region}-${var.aws_account_id}"
    }
    frontend = {
      name = "${local.bucket_prefix}-frontend-${var.aws_region}-${var.aws_account_id}"
    }
  }
}

resource "aws_s3_bucket" "this" {
  for_each = local.buckets

  bucket        = each.value.name
  force_destroy = false
  tags          = var.tags
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
