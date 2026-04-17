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
