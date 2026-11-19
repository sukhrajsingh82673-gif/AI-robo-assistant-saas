variable "environment" {
  description = "Target deployment environment (staging, production)"
  type        = string
}

variable "github_repo" {
  description = "GitHub repository (owner/repo) authorized for OIDC assume-role"
  type        = string
  default     = "sukhrajsingh82673-gif/AI-robo-assistant-saas"
}

variable "github_branch" {
  description = "GitHub branch authorized for OIDC assume-role"
  type        = string
  default     = "engineering/production-readiness-gap-closure"
}
