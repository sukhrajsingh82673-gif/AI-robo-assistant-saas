# ==============================================================================
# ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
# Terraform Infrastructure Module: Private Amazon RDS PostgreSQL 16
# Enforces Private Endpoints, Storage Encryption, Automated Backups & SSL
# ==============================================================================

# 1. Generate Secure Random Password for Master Admin
resource "random_password" "db_master_password" {
  length           = 32
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

# 2. Store Master Password in AWS Secrets Manager
resource "aws_secretsmanager_secret" "db_credentials" {
  name                    = "zonata/${var.environment}/rds_master_credentials"
  description             = "Master credentials for ZONATA RDS PostgreSQL 16"
  recovery_window_in_days = 0

  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_secretsmanager_secret_version" "db_credentials" {
  secret_id = aws_secretsmanager_secret.db_credentials.id
  secret_string = jsonencode({
    engine   = "postgres"
    host     = aws_db_instance.postgres16.address
    port     = aws_db_instance.postgres16.port
    username = var.admin_username
    password = random_password.db_master_password.result
    database = var.database_name
  })
}

# 3. DB Subnet Group (Private Database Subnets Only)
resource "aws_db_subnet_group" "db_subnets" {
  name        = "zonata-${var.environment}-db-subnet-group"
  description = "Private database subnets for RDS PostgreSQL 16"
  subnet_ids  = var.subnet_ids

  tags = {
    Name        = "zonata-${var.environment}-db-subnets"
    Environment = var.environment
  }
}

# 4. DB Parameter Group (Enforce SSL & Performance Settings)
resource "aws_db_parameter_group" "pg16_params" {
  name   = "zonata-${var.environment}-pg16-params"
  family = "postgres16"

  parameter {
    name  = "rds.force_ssl"
    value = "1" # Force SSL for all client connections (BLK-02)
  }

  parameter {
    name  = "log_connections"
    value = "1"
  }

  parameter {
    name  = "log_disconnections"
    value = "1"
  }

  tags = {
    Environment = var.environment
  }
}

# 5. RDS PostgreSQL 16 Instance
resource "aws_db_instance" "postgres16" {
  identifier                  = "zonata-${var.environment}-pg16"
  engine                      = "postgres"
  engine_version              = "16.2"
  instance_class              = var.instance_class
  allocated_storage           = var.allocated_storage
  max_allocated_storage       = var.max_allocated_storage
  storage_type                = "gp3"
  storage_encrypted           = true
  multi_az                    = var.multi_az
  publicly_accessible         = false # Strictly Private

  db_name                     = var.database_name
  username                    = var.admin_username
  password                    = random_password.db_master_password.result
  port                        = 5432

  db_subnet_group_name        = aws_db_subnet_group.db_subnets.name
  vpc_security_group_ids      = var.security_group_ids
  parameter_group_name        = aws_db_parameter_group.pg16_params.name

  backup_retention_period     = var.backup_retention_period
  backup_window               = "03:00-04:00"
  maintenance_window          = "Sun:04:30-Sun:05:30"
  auto_minor_version_upgrade  = true
  deletion_protection         = var.deletion_protection
  skip_final_snapshot         = var.environment == "staging" ? true : false
  final_snapshot_identifier   = var.environment == "production" ? "zonata-${var.environment}-pg16-final" : null

  copy_tags_to_snapshot       = true

  tags = {
    Name        = "zonata-${var.environment}-rds-postgres16"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}
