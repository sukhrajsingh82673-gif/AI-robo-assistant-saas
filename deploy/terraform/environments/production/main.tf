# ==============================================================================
# ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
# Terraform Production Environment Composition
# Provisions: Multi-AZ RDS PostgreSQL 16, S3 WORM with Cross-Region Replication,
# Private VPC with NAT Gateways, Hardened EC2 Compose Host, Secrets & OIDC
# ==============================================================================

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.40"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }

  # Production S3 Remote Backend with DynamoDB State Locking
  # backend "s3" {
  #   bucket         = "zonata-terraform-state-production"
  #   key            = "production/terraform.tfstate"
  #   region         = "us-east-1"
  #   dynamodb_table = "zonata-terraform-locks-production"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "ZONATA"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# Provider for cross-region replication secondary region
provider "aws" {
  alias  = "replica"
  region = var.replica_region

  default_tags {
    tags = {
      Project     = "ZONATA"
      Environment = var.environment
      ManagedBy   = "terraform"
      Role        = "disaster-recovery-region"
    }
  }
}

# 1. VPC Module (Full Multi-AZ with NAT Gateways for private subnet egress)
module "vpc" {
  source             = "../../modules/vpc"
  environment        = var.environment
  enable_nat_gateway = true
}

# 2. S3 WORM Immutable Backup Module (30-day compliance retention + cross-region replication)
module "s3_backup" {
  source                          = "../../modules/s3_backup_worm"
  environment                     = var.environment
  primary_bucket_name             = var.primary_backup_bucket_name
  replica_bucket_name             = var.replica_backup_bucket_name
  object_lock_retention_days      = 30
  object_lock_mode                = "COMPLIANCE"
  enable_cross_region_replication = true
}

# 3. RDS PostgreSQL 16 Module (Multi-AZ, 30-day backups, deletion protection)
module "rds" {
  source                  = "../../modules/rds_postgres"
  environment             = var.environment
  subnet_ids              = module.vpc.private_db_subnet_ids
  security_group_ids      = [module.vpc.db_security_group_id]
  instance_class          = "db.r6g.xlarge" # 4 vCPU, 32 GB RAM production database
  allocated_storage       = 100
  max_allocated_storage   = 500
  multi_az                = true # Multi-AZ standby replica for zero-downtime failover
  backup_retention_period = 30
  deletion_protection     = true
}

# 4. EC2 Docker Compose Application Host
module "ec2_host" {
  source             = "../../modules/ec2_compose_host"
  environment        = var.environment
  subnet_id          = module.vpc.private_app_subnet_ids[0] # Private subnet behind ALB in prod
  security_group_ids = [module.vpc.app_host_security_group_id]
  instance_type      = "t3.2xlarge" # 8 vCPU, 32 GB RAM for high concurrency
  root_volume_size   = 200
  assign_public_ip   = false
  backup_bucket_arn  = module.s3_backup.primary_bucket_arn
}

# 5. Secrets Manager & GitHub Actions OIDC
module "secrets_iam" {
  source        = "../../modules/secrets_iam"
  environment   = var.environment
  github_repo   = "sukhrajsingh82673-gif/AI-robo-assistant-saas"
  github_branch = "engineering/production-readiness-gap-closure"
}
