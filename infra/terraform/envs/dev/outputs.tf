output "environment" {
  value = "dev"
}

output "bucket_names" {
  value = module.s3.bucket_names
}

output "lambda_function_names" {
  value = module.lambda.lambda_function_names
}

output "alerts_topic_arn" {
  value = module.monitoring.alerts_topic_arn
}
