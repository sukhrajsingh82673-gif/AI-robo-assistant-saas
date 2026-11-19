# ==============================================================================
# ZONATA UNIVERSAL AI COMPANY OPERATING SYSTEM
# Terraform Infrastructure Module: Secrets Manager & GitHub Actions OIDC IAM
# Enforces Zero Long-Lived Static Credentials and Secrets Separation
# ==============================================================================

# 1. Random Secrets Generation for Application Security
resource "random_password" "jwt_secret" {
  length  = 64
  special = false
}

resource "random_password" "session_secret" {
  length  = 64
  special = false
}

resource "random_password" "db_app_password" {
  length  = 32
  special = false
}

resource "random_password" "db_worker_password" {
  length  = 32
  special = false
}

# 2. AWS Secrets Manager Secret: Application Core Secrets
resource "aws_secretsmanager_secret" "app_secrets" {
  name                    = "zonata/${var.environment}/app_secrets"
  description             = "Runtime application secrets for ZONATA ${var.environment}"
  recovery_window_in_days = 0

  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_secretsmanager_secret_version" "app_secrets" {
  secret_id = aws_secretsmanager_secret.app_secrets.id
  secret_string = jsonencode({
    JWT_SECRET         = random_password.jwt_secret.result
    SESSION_SECRET     = random_password.session_secret.result
    DB_APP_PASSWORD    = random_password.db_app_password.result
    DB_WORKER_PASSWORD = random_password.db_worker_password.result
  })
}

# 3. AWS Secrets Manager Secret: Operational Alerting & Observability
resource "aws_secretsmanager_secret" "alerting_secrets" {
  name                    = "zonata/${var.environment}/alerting_secrets"
  description             = "Alertmanager receivers (Slack webhook, PagerDuty key) for ZONATA ${var.environment}"
  recovery_window_in_days = 0

  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_secretsmanager_secret_version" "alerting_secrets" {
  secret_id = aws_secretsmanager_secret.alerting_secrets.id
  secret_string = jsonencode({
    SLACK_WEBHOOK_URL  = "https://hooks.slack.com/services/PLACEHOLDER/CHANGE_IN_CONSOLE"
    PAGERDUTY_KEY      = "PLACEHOLDER_PAGERDUTY_INTEGRATION_KEY"
  })
}

# 4. GitHub Actions OIDC OpenID Connect Provider
# Checks if provider already exists in the AWS account or creates it
data "tls_certificate" "github" {
  url = "https://token.actions.githubusercontent.com/.well-known/openid-configuration"
}

resource "aws_iam_openid_connect_provider" "github_oidc" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.github.certificates[0].sha1_fingerprint]

  tags = {
    Name        = "github-actions-oidc"
    Environment = var.environment
  }
}

# 5. IAM Role for GitHub Actions CI/CD Deployer
resource "aws_iam_role" "github_deployer" {
  name = "zonata-${var.environment}-github-deployer"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRoleWithWebIdentity"
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_openid_connect_provider.github_oidc.arn
        }
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          }
          StringLike = {
            "token.actions.githubusercontent.com:sub" = "repo:${var.github_repo}:*"
          }
        }
      }
    ]
  })

  tags = {
    Environment = var.environment
    Role        = "ci-cd-deployer"
  }
}

# 6. Least-Privilege IAM Policy for Deployer Role
resource "aws_iam_policy" "deployer_policy" {
  name = "zonata-${var.environment}-deployer-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "SSMCommandExecution"
        Effect = "Allow"
        Action = [
          "ssm:SendCommand",
          "ssm:GetCommandInvocation",
          "ssm:ListCommandInvocations",
          "ssm:DescribeInstanceInformation"
        ]
        Resource = "*"
      },
      {
        Sid    = "ECRImageManagement"
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload"
        ]
        Resource = "*"
      },
      {
        Sid    = "SecretsManagerRead"
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = [
          aws_secretsmanager_secret.app_secrets.arn,
          aws_secretsmanager_secret.alerting_secrets.arn
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "deployer_attach" {
  role       = aws_iam_role.github_deployer.name
  policy_arn = aws_iam_policy.deployer_policy.arn
}
