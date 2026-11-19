# ==============================================================================
# ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
# Terraform Infrastructure Module: Hardened EC2 Docker Compose Application Host
# Enforces Zero Open SSH Ports (SSM Managed), Encrypted Storage, & Least-Privilege IAM
# ==============================================================================

# 1. Look up latest Ubuntu 24.04 LTS AMI
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# 2. IAM Role for EC2 Instance (SSM Session Manager & S3 Access)
resource "aws_iam_role" "ec2_role" {
  name = "zonata-${var.environment}-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}

# Attach AWS Systems Manager Core policy (enables SSM Session Manager; no port 22 needed!)
resource "aws_iam_role_policy_attachment" "ssm_core" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# Custom policy for S3 backup bucket access and Secrets Manager reading
resource "aws_iam_policy" "ec2_app_policy" {
  name = "zonata-${var.environment}-ec2-app-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Effect   = "Allow"
        Resource = [
          var.backup_bucket_arn,
          "${var.backup_bucket_arn}/*"
        ]
      },
      {
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Effect   = "Allow"
        Resource = [
          "arn:aws:secretsmanager:*:*:secret:zonata/${var.environment}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "app_policy_attach" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = aws_iam_policy.ec2_app_policy.arn
}

resource "aws_iam_instance_profile" "ec2_profile" {
  name = "zonata-${var.environment}-ec2-profile"
  role = aws_iam_role.ec2_role.name
}

# 3. User Data Script: Installs Docker, Docker Compose, AWS CLI & Directory Prep
locals {
  user_data = <<-EOF
              #!/bin/bash
              set -euo pipefail
              export DEBIAN_FRONTEND=noninteractive

              echo "Starting ZONATA host provisioning..."
              apt-get update -y
              apt-get install -y ca-certificates curl gnupg lsb-release unzip jq

              # Install Docker
              install -m 0755 -d /etc/apt/keyrings
              curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
              chmod a+r /etc/apt/keyrings/docker.gpg
              echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
              apt-get update -y
              apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

              # Install AWS CLI v2
              curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
              unzip -q awscliv2.zip
              ./aws/install
              rm -rf aws awscliv2.zip

              # Enable and start Docker
              systemctl enable docker
              systemctl start docker

              # Create application directories
              mkdir -p /opt/zonata /opt/zonata/storage /opt/zonata/config /opt/zonata/certs
              chown -R 10001:10001 /opt/zonata/storage

              echo "ZONATA host provisioning complete."
              EOF
}

# 4. EC2 Application Host Instance
resource "aws_instance" "app_host" {
  ami                  = data.aws_ami.ubuntu.id
  instance_type        = var.instance_type
  subnet_id            = var.subnet_id
  vpc_security_group_ids = var.security_group_ids
  iam_instance_profile = aws_iam_instance_profile.ec2_profile.name
  associate_public_ip_address = var.assign_public_ip
  user_data            = local.user_data

  root_block_device {
    volume_type           = "gp3"
    volume_size           = var.root_volume_size
    encrypted             = true
    delete_on_termination = true

    tags = {
      Name        = "zonata-${var.environment}-root-ebs"
      Environment = var.environment
    }
  }

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required" # IMDSv2 mandatory (defense against SSRF credential theft)
    http_put_response_hop_limit = 1
  }

  tags = {
    Name        = "zonata-${var.environment}-app-host"
    Environment = var.environment
    ManagedBy   = "terraform"
    Role        = "docker-compose-app-host"
  }
}

# 5. Elastic IP for Direct Standalone Ingress (if enabled)
resource "aws_eip" "app_eip" {
  count    = var.assign_public_ip ? 1 : 0
  instance = aws_instance.app_host.id
  domain   = "vpc"

  tags = {
    Name        = "zonata-${var.environment}-app-eip"
    Environment = var.environment
  }
}
