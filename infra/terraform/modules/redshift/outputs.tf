output "namespace_name" {
  description = "Redshift Serverless namespace name."
  value       = aws_redshiftserverless_namespace.this.namespace_name
}

output "workgroup_name" {
  description = "Redshift Serverless workgroup name."
  value       = aws_redshiftserverless_workgroup.this.workgroup_name
}

output "workgroup_endpoint" {
  description = "Redshift Serverless endpoint (host:port)."
  value = format(
    "%s:%s",
    aws_redshiftserverless_workgroup.this.endpoint[0].address,
    aws_redshiftserverless_workgroup.this.endpoint[0].port,
  )
}

output "workgroup_host" {
  description = "Redshift Serverless hostname."
  value       = aws_redshiftserverless_workgroup.this.endpoint[0].address
}

output "redshift_role_arn" {
  description = "IAM role ARN used by Redshift Serverless for S3/Glue access."
  value       = aws_iam_role.redshift.arn
}
