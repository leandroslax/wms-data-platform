# ─────────────────────────────────────────────────────────────
# Redshift Serverless — namespace + workgroup
# Serves as the analytical query layer for the WMS Data Platform.
# Mounts gold Iceberg tables from S3 via Redshift Spectrum.
# ─────────────────────────────────────────────────────────────

# IAM role that Redshift Serverless uses to read S3 / Glue Catalog
data "aws_iam_policy_document" "redshift_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["redshift.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "redshift" {
  name               = "${var.project_name}-${var.environment}-redshift-role"
  assume_role_policy = data.aws_iam_policy_document.redshift_assume_role.json
  tags               = var.tags
}

data "aws_iam_policy_document" "redshift_s3_glue" {
  # S3 read access to gold bucket (Spectrum external tables)
  statement {
    effect  = "Allow"
    actions = ["s3:GetObject", "s3:ListBucket"]
    resources = [
      var.gold_bucket_arn,
      "${var.gold_bucket_arn}/*",
    ]
  }

  # Glue Data Catalog — Spectrum needs schema metadata
  statement {
    effect = "Allow"
    actions = [
      "glue:GetDatabase",
      "glue:GetDatabases",
      "glue:GetTable",
      "glue:GetTables",
      "glue:GetPartitions",
    ]
    resources = ["*"]
  }

  # KMS decrypt for encrypted S3 objects
  statement {
    effect    = "Allow"
    actions   = ["kms:Decrypt", "kms:DescribeKey"]
    resources = [var.kms_key_arn]
  }
}

resource "aws_iam_role_policy" "redshift_s3_glue" {
  name   = "${var.project_name}-${var.environment}-redshift-s3-glue-policy"
  role   = aws_iam_role.redshift.id
  policy = data.aws_iam_policy_document.redshift_s3_glue.json
}

# ─────────────────────────────────────────────────────────────
# Namespace — logical container for databases and users
# ─────────────────────────────────────────────────────────────
resource "aws_redshiftserverless_namespace" "this" {
  namespace_name      = "${var.project_name}-${var.environment}"
  admin_username      = var.admin_username
  admin_user_password = var.admin_password
  db_name             = var.db_name
  kms_key_id          = var.kms_key_arn

  iam_roles = [aws_iam_role.redshift.arn]

  log_exports = ["userlog", "connectionlog", "useractivitylog"]

  tags = var.tags
}

# ─────────────────────────────────────────────────────────────
# Workgroup — compute layer
# Dev: public endpoint (no VPC). Prod: set subnet_ids + sg_ids.
# ─────────────────────────────────────────────────────────────
resource "aws_redshiftserverless_workgroup" "this" {
  namespace_name = aws_redshiftserverless_namespace.this.namespace_name
  workgroup_name = "${var.project_name}-${var.environment}"
  base_capacity  = var.base_capacity

  # Public endpoint in dev (no VPC required)
  publicly_accessible = length(var.subnet_ids) == 0 ? true : false

  subnet_ids         = length(var.subnet_ids) > 0 ? var.subnet_ids : null
  security_group_ids = length(var.security_group_ids) > 0 ? var.security_group_ids : null

  config_parameter {
    parameter_key   = "enable_user_activity_logging"
    parameter_value = "true"
  }

  config_parameter {
    parameter_key   = "max_query_execution_time"
    parameter_value = "3600"
  }

  tags = var.tags

  depends_on = [aws_redshiftserverless_namespace.this]
}
