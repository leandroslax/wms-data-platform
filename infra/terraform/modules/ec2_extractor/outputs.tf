output "instance_id" {
  description = "ID da EC2 extratora"
  value       = aws_instance.extractor.id
}

output "elastic_ip" {
  description = "IP elástico da EC2 (informar ao cliente para liberação na VPN)"
  value       = aws_eip.extractor.public_ip
}

output "instance_profile_arn" {
  description = "ARN do instance profile"
  value       = aws_iam_instance_profile.extractor.arn
}
