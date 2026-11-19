variable "aws_region" {
  description = "Primary AWS region for production"
  type        = string
  default     = "us-east-1"
}

variable "replica_region" {
  description = "Secondary AWS region for disaster recovery cross-region backup replication"
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "domain_name" {
  description = "Production apex or subdomain (e.g., app.zonata.ai)"
  type        = string
}

variable "primary_backup_bucket_name" {
  description = "Globally unique bucket name for production S3 WORM backups"
  type        = string
}

variable "replica_backup_bucket_name" {
  description = "Globally unique bucket name for cross-region disaster recovery S3 backups"
  type        = string
}
