provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "prompt-to-infra-ai-agent"
      Environment = var.environment
      Owner       = var.owner
      ManagedBy   = "terraform"
    }
  }
}
