locals {
  default_tags = merge(var.tags, {
    Module = "ec2_extractor"
  })
}

# ── AMI: Amazon Linux 2023 (mais recente) ─────────────────────────────────────
data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# ── IAM: instance profile ──────────────────────────────────────────────────────
data "aws_iam_policy_document" "ec2_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "extractor" {
  name               = "${var.project_name}-${var.environment}-extractor-role"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume_role.json
  tags               = local.default_tags
}

data "aws_iam_policy_document" "extractor_policy" {
  # S3: escrita no bronze + leitura de checkpoints
  statement {
    effect = "Allow"
    actions = [
      "s3:PutObject",
      "s3:GetObject",
      "s3:DeleteObject",
      "s3:ListBucket"
    ]
    resources = [
      "arn:aws:s3:::wms-dp-${var.environment}-bronze-*",
      "arn:aws:s3:::wms-dp-${var.environment}-bronze-*/*",
      "arn:aws:s3:::wms-dp-${var.environment}-artifacts-*",
      "arn:aws:s3:::wms-dp-${var.environment}-artifacts-*/*"
    ]
  }

  # KMS: decrypt/encrypt nos buckets bronze e artifacts
  statement {
    effect = "Allow"
    actions = [
      "kms:Decrypt",
      "kms:GenerateDataKey",
      "kms:DescribeKey"
    ]
    resources = ["*"]
    condition {
      test     = "StringLike"
      variable = "kms:ViaService"
      values   = ["s3.*.amazonaws.com"]
    }
  }

  # Secrets Manager: ler credenciais Oracle e VPN
  statement {
    effect = "Allow"
    actions = [
      "secretsmanager:GetSecretValue",
      "secretsmanager:DescribeSecret"
    ]
    resources = [
      "arn:aws:secretsmanager:*:${var.aws_account_id}:secret:${var.project_name}/*"
    ]
  }

  # SSM Session Manager (acesso sem abrir porta SSH se preferir)
  statement {
    effect = "Allow"
    actions = [
      "ssm:UpdateInstanceInformation",
      "ssmmessages:CreateControlChannel",
      "ssmmessages:CreateDataChannel",
      "ssmmessages:OpenControlChannel",
      "ssmmessages:OpenDataChannel"
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "extractor" {
  name   = "${var.project_name}-${var.environment}-extractor-policy"
  role   = aws_iam_role.extractor.id
  policy = data.aws_iam_policy_document.extractor_policy.json
}

resource "aws_iam_instance_profile" "extractor" {
  name = "${var.project_name}-${var.environment}-extractor-profile"
  role = aws_iam_role.extractor.name
  tags = local.default_tags
}

# ── Key pair ──────────────────────────────────────────────────────────────────
resource "aws_key_pair" "extractor" {
  key_name   = "${var.project_name}-${var.environment}-extractor-key"
  public_key = var.ssh_public_key
  tags       = local.default_tags
}

# ── EC2 ───────────────────────────────────────────────────────────────────────
resource "aws_instance" "extractor" {
  ami                    = data.aws_ami.amazon_linux_2023.id
  instance_type          = var.instance_type
  subnet_id              = var.subnet_id
  vpc_security_group_ids = [var.security_group_id]
  key_name               = aws_key_pair.extractor.key_name
  iam_instance_profile   = aws_iam_instance_profile.extractor.name

  root_block_device {
    volume_type = "gp3"
    volume_size = 30
    encrypted   = true
  }

  user_data = base64encode(templatefile("${path.module}/user_data.sh", {
    aws_region   = var.aws_region
    environment  = var.environment
    project_name = var.project_name
  }))

  tags = merge(local.default_tags, {
    Name = "${var.project_name}-${var.environment}-extractor"
  })
}

# ── Elastic IP (IP fixo para o cliente liberar na VPN) ────────────────────────
resource "aws_eip" "extractor" {
  instance = aws_instance.extractor.id
  domain   = "vpc"
  tags     = merge(local.default_tags, { Name = "${var.project_name}-${var.environment}-extractor-eip" })
}
