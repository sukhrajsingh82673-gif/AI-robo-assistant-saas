variable "environment" {
  description = "Target deployment environment (staging, production)"
  type        = string
}

variable "subnet_id" {
  description = "Subnet ID for the EC2 host (public if standalone with EIP, private if behind ALB)"
  type        = string
}

variable "security_group_ids" {
  description = "List of security group IDs"
  type        = list(string)
}

variable "instance_type" {
  description = "EC2 instance type (e.g. t3.xlarge for staging 4vCPU/16GB, t3.2xlarge for prod)"
  type        = string
  default     = "t3.xlarge"
}

variable "root_volume_size" {
  description = "Root EBS volume size in GB"
  type        = number
  default     = 100
}

variable "assign_public_ip" {
  description = "Assign public IP to the instance (true if standalone without ALB)"
  type        = bool
  default     = true
}

variable "backup_bucket_arn" {
  description = "ARN of the S3 backup bucket for IAM access"
  type        = string
}
