output "primary_bucket_id" {
  description = "The ID of the primary S3 backup bucket"
  value       = aws_s3_bucket.primary_backup.id
}

output "primary_bucket_arn" {
  description = "The ARN of the primary S3 backup bucket"
  value       = aws_s3_bucket.primary_backup.arn
}

output "object_lock_mode" {
  description = "The configured Object Lock mode (COMPLIANCE)"
  value       = var.object_lock_mode
}

output "object_lock_retention_days" {
  description = "The configured retention days"
  value       = var.object_lock_retention_days
}

output "replica_bucket_id" {
  description = "The ID of the cross-region replica S3 bucket (if enabled)"
  value       = var.enable_cross_region_replication ? aws_s3_bucket.replica_backup[0].id : null
}

output "replica_bucket_arn" {
  description = "The ARN of the cross-region replica S3 bucket (if enabled)"
  value       = var.enable_cross_region_replication ? aws_s3_bucket.replica_backup[0].arn : null
}
