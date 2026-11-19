# ==============================================================================
# ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
# Terraform Infrastructure Module: S3 WORM Immutable Backup Storage
# Enforces BLK-01: Off-Host Storage, Object Lock Compliance Mode, and Cross-Region Replication
# ==============================================================================

# 1. Primary Backup Bucket
resource "aws_s3_bucket" "primary_backup" {
  bucket              = var.primary_bucket_name
  object_lock_enabled = true

  tags = {
    Name        = "zonata-${var.environment}-primary-backup"
    Environment = var.environment
    ManagedBy   = "terraform"
    Retention   = "${var.object_lock_retention_days}d-${var.object_lock_mode}"
  }
}

# 2. Enforce S3 Bucket Versioning (Mandatory for Object Lock)
resource "aws_s3_bucket_versioning" "primary_versioning" {
  bucket = aws_s3_bucket.primary_backup.id
  versioning_configuration {
    status = "Enabled"
  }
}

# 3. Object Lock Configuration (WORM / Compliance Mode)
# In COMPLIANCE mode, retention period cannot be decreased and objects cannot be deleted
# by ANY user (including AWS root account) until the retention duration expires.
resource "aws_s3_bucket_object_lock_configuration" "primary_lock" {
  bucket = aws_s3_bucket.primary_backup.id

  rule {
    default_retention {
      mode = var.object_lock_mode
      days = var.object_lock_retention_days
    }
  }

  depends_on = [aws_s3_bucket_versioning.primary_versioning]
}

# 4. Server-Side Encryption (AES-256 / SSE-S3 or KMS)
resource "aws_s3_bucket_server_side_encryption_configuration" "primary_encryption" {
  bucket = aws_s3_bucket.primary_backup.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# 5. Public Access Block (Strict 100% Private)
resource "aws_s3_bucket_public_access_block" "primary_public_block" {
  bucket = aws_s3_bucket.primary_backup.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# 6. Lifecycle Policy for Archived Tiering (Transition to Glacier Instant Retrieval after 90 days)
resource "aws_s3_bucket_lifecycle_configuration" "primary_lifecycle" {
  bucket = aws_s3_bucket.primary_backup.id

  rule {
    id     = "archive-old-backups"
    status = "Enabled"

    transition {
      days          = 90
      storage_class = "GLACIER_IR"
    }

    noncurrent_version_transition {
      noncurrent_days = 60
      storage_class   = "GLACIER_IR"
    }
  }

  depends_on = [aws_s3_bucket_versioning.primary_versioning]
}

# 7. Cross-Region Replica Bucket (Conditional on enable_cross_region_replication)
resource "aws_s3_bucket" "replica_backup" {
  count               = var.enable_cross_region_replication ? 1 : 0
  bucket              = var.replica_bucket_name
  object_lock_enabled = true

  tags = {
    Name        = "zonata-${var.environment}-replica-backup"
    Environment = var.environment
    ManagedBy   = "terraform"
    Role        = "disaster-recovery-crr"
  }
}

resource "aws_s3_bucket_versioning" "replica_versioning" {
  count  = var.enable_cross_region_replication ? 1 : 0
  bucket = aws_s3_bucket.replica_backup[0].id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_object_lock_configuration" "replica_lock" {
  count  = var.enable_cross_region_replication ? 1 : 0
  bucket = aws_s3_bucket.replica_backup[0].id

  rule {
    default_retention {
      mode = var.object_lock_mode
      days = var.object_lock_retention_days
    }
  }

  depends_on = [aws_s3_bucket_versioning.replica_versioning]
}

resource "aws_s3_bucket_public_access_block" "replica_public_block" {
  count  = var.enable_cross_region_replication ? 1 : 0
  bucket = aws_s3_bucket.replica_backup[0].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# 8. IAM Role for Cross-Region S3 Replication
resource "aws_iam_role" "replication" {
  count = var.enable_cross_region_replication ? 1 : 0
  name  = "zonata-${var.environment}-s3-crr-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "s3.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_policy" "replication" {
  count = var.enable_cross_region_replication ? 1 : 0
  name  = "zonata-${var.environment}-s3-crr-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:GetReplicationConfiguration",
          "s3:ListBucket"
        ]
        Effect   = "Allow"
        Resource = [aws_s3_bucket.primary_backup.arn]
      },
      {
        Action = [
          "s3:GetObjectVersionForReplication",
          "s3:GetObjectVersionAcl",
          "s3:GetObjectVersionTagging"
        ]
        Effect   = "Allow"
        Resource = ["${aws_s3_bucket.primary_backup.arn}/*"]
      },
      {
        Action = [
          "s3:ReplicateObject",
          "s3:ReplicateDelete",
          "s3:ReplicateTags"
        ]
        Effect   = "Allow"
        Resource = ["${aws_s3_bucket.replica_backup[0].arn}/*"]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "replication" {
  count      = var.enable_cross_region_replication ? 1 : 0
  role       = aws_iam_role.replication[0].name
  policy_arn = aws_iam_policy.replication[0].arn
}

resource "aws_s3_bucket_replication_configuration" "replication" {
  count      = var.enable_cross_region_replication ? 1 : 0
  role       = aws_iam_role.replication[0].arn
  bucket     = aws_s3_bucket.primary_backup.id

  rule {
    id     = "replicate-all"
    status = "Enabled"

    destination {
      bucket        = aws_s3_bucket.replica_backup[0].arn
      storage_class = "STANDARD"
    }
  }

  depends_on = [aws_s3_bucket_versioning.primary_versioning]
}
