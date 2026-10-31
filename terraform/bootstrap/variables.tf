variable "aws_region" {
  description = "AWS region for the bootstrap resources."
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name, such as dev, staging, or prod."
  type        = string
  default     = "dev"
}

variable "owner" {
  description = "Owner tag value, usually a GitHub username or team name."
  type        = string
  default     = "naghi20"
}

variable "state_bucket_name" {
  description = "Globally unique name for the Terraform state S3 bucket."
  type        = string
}

variable "budget_amount_usd" {
  description = "Monthly AWS budget threshold in USD."
  type        = number
  default     = "10"
}

variable "budget_alert_email" {
  description = "Email address that receives AWS Budget alerts."
  type        = string
}
variable "lambda_zip_path" {
  description = "Path to the packaged Bedrock Lambda deployment package"
  type        = string
}