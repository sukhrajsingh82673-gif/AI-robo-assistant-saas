output "production_ec2_private_ip" {
  description = "Private IP of the production application host"
  value       = module.ec2_host.private_ip
}

output "production_ec2_instance_id" {
  description = "Instance ID of the production application host"
  value       = module.ec2_host.instance_id
}

output "rds_endpoint" {
  description = "Private endpoint of the Multi-AZ RDS PostgreSQL 16 database"
  value       = module.rds.endpoint
}

output "rds_secret_arn" {
  description = "Secrets Manager ARN for RDS master password"
  value       = module.rds.secret_arn
}

output "primary_s3_backup_bucket_id" {
  description = "Primary production S3 WORM backup bucket ID"
  value       = module.s3_backup.primary_bucket_id
}

output "replica_s3_backup_bucket_id" {
  description = "Cross-region replica S3 WORM backup bucket ID"
  value       = module.s3_backup.replica_bucket_id
}

output "github_deployer_role_arn" {
  description = "IAM Role ARN for GitHub Actions OIDC deployer"
  value       = module.secrets_iam.github_deployer_role_arn
}
