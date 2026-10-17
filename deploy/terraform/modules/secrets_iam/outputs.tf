output "app_secrets_arn" {
  description = "The ARN of the application secrets in Secrets Manager"
  value       = aws_secretsmanager_secret.app_secrets.arn
}

output "alerting_secrets_arn" {
  description = "The ARN of alerting secrets in Secrets Manager"
  value       = aws_secretsmanager_secret.alerting_secrets.arn
}

output "github_deployer_role_arn" {
  description = "The IAM Role ARN for GitHub Actions CI/CD OIDC assume-role"
  value       = aws_iam_role.github_deployer.arn
}
