variable "environment" {
  description = "Target deployment environment (staging, production)"
  type        = string
}

variable "primary_bucket_name" {
  description = "Name for the primary S3 backup bucket"
  type        = string
}

variable "replica_bucket_name" {
  description = "Name for the cross-region replica S3 backup bucket"
  type        = string
}

variable "object_lock_retention_days" {
  description = "Number of days for Object Lock Compliance mode retention"
  type        = number
  default     = 30
}

variable "object_lock_mode" {
  description = "Object lock mode (COMPLIANCE or GOVERNANCE)"
  type        = string
  default     = "COMPLIANCE"
}

variable "enable_cross_region_replication" {
  description = "Enable cross-region replication (true for production, false for staging cost-optimization)"
  type        = bool
  default     = false
}
