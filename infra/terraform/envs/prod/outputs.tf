output "environment" {
  description = "Environment name"
  value       = local.environment
}

output "bucket_names" {
  description = "S3 buckets created for the platform"
  value       = module.s3.bucket_names
}

output "alerts_topic_arn" {
  description = "SNS topic ARN for platform alerts"
  value       = module.monitoring.alerts_topic_arn
}

output "ecr_repository_name" {
  description = "ECR repository name for Lambda images"
  value       = module.ecr.repository_name
}

output "ecr_repository_url" {
  description = "ECR repository URL for Lambda images"
  value       = module.ecr.repository_url
}
