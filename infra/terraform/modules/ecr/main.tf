resource "aws_ecr_repository" "lambda" {
  name                 = "${var.project_name}-${var.environment}-lambda"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = var.tags
}
