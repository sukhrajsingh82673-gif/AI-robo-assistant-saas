variable "aws_region" {
  description = "AWS region for staging deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "staging"
}

variable "domain_name" {
  description = "Domain name for staging (e.g., staging.zonata.ai or user domain)"
  type        = string
  default     = "staging.zonata.internal"
}

variable "primary_backup_bucket_name" {
  description = "Globally unique bucket name for staging S3 WORM backups"
  type        = string
  default     = "zonata-staging-worm-backups-2026"
}

variable "replica_backup_bucket_name" {
  description = "Globally unique bucket name for cross-region replica S3 backups"
  type        = string
  default     = "zonata-staging-worm-backups-crr-2026"
}
