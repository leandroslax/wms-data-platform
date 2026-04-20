locals {
  default_tags = merge(var.tags, {
    Module = "vpc"
  })
}

# ── VPC ────────────────────────────────────────────────────────────────────────
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = merge(local.default_tags, { Name = "${var.project_name}-${var.environment}-vpc" })
}

# ── Internet Gateway ───────────────────────────────────────────────────────────
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags   = merge(local.default_tags, { Name = "${var.project_name}-${var.environment}-igw" })
}

# ── Subnet pública ─────────────────────────────────────────────────────────────
resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnet_cidr
  availability_zone       = "${var.aws_region}a"
  map_public_ip_on_launch = false
  tags                    = merge(local.default_tags, { Name = "${var.project_name}-${var.environment}-public-subnet" })
}

# ── Route table ────────────────────────────────────────────────────────────────
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = merge(local.default_tags, { Name = "${var.project_name}-${var.environment}-public-rt" })
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

# ── Security group da EC2 extratora ───────────────────────────────────────────
resource "aws_security_group" "extractor" {
  name        = "${var.project_name}-${var.environment}-extractor-sg"
  description = "EC2 extratora: SSH de IPs autorizados + saida livre para VPN e S3"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "SSH de IPs autorizados"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.ssh_allowed_cidrs
  }

  egress {
    description = "Saida livre (VPN FortiGate + S3 + Oracle)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.default_tags, { Name = "${var.project_name}-${var.environment}-extractor-sg" })
}
