# ==============================================================================
# ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
# Terraform Staging Environment Composition
# Provisions: VPC, RDS PostgreSQL 16 (Cost-Optimized), S3 WORM, EC2 Host, Secrets & OIDC
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

  # Backend configuration: in staging/production, configure S3 backend with DynamoDB locking
  # backend "s3" {
  #   bucket         = "zonata-terraform-state-staging"
  #   key            = "staging/terraform.tfstate"
  #   region         = "us-east-1"
  #   dynamodb_table = "zonata-terraform-locks-staging"
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

# 1. VPC Module
module "vpc" {
  source             = "../../modules/vpc"
  environment        = var.environment
  enable_nat_gateway = false # Cost optimization: EC2 uses public IP / IGW for staging
}

# 2. S3 WORM Immutable Backup Module
module "s3_backup" {
  source                          = "../../modules/s3_backup_worm"
  environment                     = var.environment
  primary_bucket_name             = var.primary_backup_bucket_name
  replica_bucket_name             = var.replica_backup_bucket_name
  object_lock_retention_days      = 7 # 7 days retention for staging testing
  object_lock_mode                = "COMPLIANCE"
  enable_cross_region_replication = false # Cost optimization for staging
}

# 3. RDS PostgreSQL 16 Module (Cost-Optimized Single-AZ for Staging)
module "rds" {
  source                  = "../../modules/rds_postgres"
  environment             = var.environment
  subnet_ids              = module.vpc.private_db_subnet_ids
  security_group_ids      = [module.vpc.db_security_group_id]
  instance_class          = "db.t4g.micro" # $0.016/hr (~$12/month)
  allocated_storage       = 20
  multi_az                = false # Single-AZ for staging cost saving
  backup_retention_period = 7
  deletion_protection     = false # Allows easy teardown in disposable staging
}

# 4. EC2 Docker Compose Application Host
module "ec2_host" {
  source             = "../../modules/ec2_compose_host"
  environment        = var.environment
  subnet_id          = module.vpc.public_subnet_ids[0] # Direct public access for staging ingress
  security_group_ids = [module.vpc.ingress_security_group_id, module.vpc.app_host_security_group_id]
  instance_type      = "t3.xlarge" # 4 vCPU, 16 GB RAM for complete 10-service staging stack
  root_volume_size   = 80
  assign_public_ip   = true
  backup_bucket_arn  = module.s3_backup.primary_bucket_arn
}

# 5. Secrets Manager & GitHub Actions OIDC
module "secrets_iam" {
  source        = "../../modules/secrets_iam"
  environment   = var.environment
  github_repo   = "sukhrajsingh82673-gif/AI-robo-assistant-saas"
  github_branch = "engineering/production-readiness-gap-closure"
}
