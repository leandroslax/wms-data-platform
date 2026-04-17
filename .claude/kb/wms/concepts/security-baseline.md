# Security Baseline

## Required controls

- Secrets Manager for credentials and API keys
- KMS for S3 data, Lambda env vars, and Redshift encryption
- IAM least privilege with one role per service boundary
- WAF on API Gateway and CloudFront
- CloudTrail for account-wide auditability
- GuardDuty and AWS Config for continuous detection and compliance
- S3 Block Public Access on all non-frontend buckets

## Delivery rule

No scaffold is complete unless it names the security boundary and the observability hook for that component.
