output "staging_public_ip" {
  description = "Public IP address of the staging application host"
  value       = module.ec2_host.public_ip
}

output "staging_ec2_instance_id" {
  description = "Instance ID of the staging application host"
  value       = module.ec2_host.instance_id
}

output "rds_endpoint" {
  description = "Private endpoint of the RDS PostgreSQL 16 database"
  value       = module.rds.endpoint
}

output "rds_secret_arn" {
  description = "Secrets Manager ARN for RDS master password"
  value       = module.rds.secret_arn
}

output "s3_backup_bucket_id" {
  description = "Primary S3 WORM backup bucket ID"
  value       = module.s3_backup.primary_bucket_id
}

output "github_deployer_role_arn" {
  description = "IAM Role ARN for GitHub Actions OIDC deployer"
  value       = module.secrets_iam.github_deployer_role_arn
}
