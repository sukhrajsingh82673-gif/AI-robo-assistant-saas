output "endpoint" {
  description = "The connection endpoint for the RDS instance"
  value       = aws_db_instance.postgres16.endpoint
}

output "address" {
  description = "The hostname of the RDS instance"
  value       = aws_db_instance.postgres16.address
}

output "port" {
  description = "The database port"
  value       = aws_db_instance.postgres16.port
}

output "database_name" {
  description = "The name of the default database"
  value       = aws_db_instance.postgres16.db_name
}

output "master_username" {
  description = "The master username"
  value       = aws_db_instance.postgres16.username
}

output "secret_arn" {
  description = "The ARN of the Secrets Manager secret containing DB credentials"
  value       = aws_secretsmanager_secret.db_credentials.arn
}

output "secret_name" {
  description = "The name of the Secrets Manager secret"
  value       = aws_secretsmanager_secret.db_credentials.name
}
