# Infrastructure Boundaries

## Private network components

- Oracle connectivity path
- extraction Lambda
- CDC components
- Redshift Serverless
- secrets access

## Public edge components

- API Gateway
- CloudFront
- WAF

## Storage boundaries

- data buckets are private and encrypted
- frontend bucket is private behind CloudFront OAC
- Terraform state bucket is isolated from data buckets

## Design rule

Keep data plane private, expose only the product edge, and route service-to-service access through IAM and VPC endpoints where possible.
