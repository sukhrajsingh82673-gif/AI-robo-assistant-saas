variable "environment" {
  description = "Target deployment environment (staging, production)"
  type        = string
}

variable "subnet_ids" {
  description = "List of private database subnet IDs"
  type        = list(string)
}

variable "security_group_ids" {
  description = "List of security group IDs for RDS instance"
  type        = list(string)
}

variable "instance_class" {
  description = "RDS instance class (e.g., db.t4g.micro for staging, db.r6g.xlarge for prod)"
  type        = string
  default     = "db.t4g.micro"
}

variable "allocated_storage" {
  description = "Allocated storage in GB"
  type        = number
  default     = 20
}

variable "max_allocated_storage" {
  description = "Max storage threshold in GB for auto-scaling"
  type        = number
  default     = 100
}

variable "multi_az" {
  description = "Enable Multi-AZ deployment (false for staging to save cost, true for prod)"
  type        = bool
  default     = false
}

variable "database_name" {
  description = "Initial database name"
  type        = string
  default     = "zonata_production"
}

variable "admin_username" {
  description = "Master administrative username"
  type        = string
  default     = "zonata_admin"
}

variable "backup_retention_period" {
  description = "Backup retention period in days (7 for staging, 30 for prod)"
  type        = number
  default     = 7
}

variable "deletion_protection" {
  description = "Protect database against accidental deletion"
  type        = bool
  default     = true
}
