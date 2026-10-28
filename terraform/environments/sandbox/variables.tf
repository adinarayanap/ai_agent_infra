variable "aws_region" {
  description = "AWS region for sandbox resources."
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Project name."
  type        = string
  default     = "prompt-infra"
}

variable "environment" {
  description = "Deployment environment."
  type        = string
  default     = "sandbox"
}

variable "owner" {
  description = "Resource owner."
  type        = string
  default     = "ahmed-al-naghi"
}

variable "cost_center" {
  description = "Cost center tag."
  type        = string
  default     = "learning"
}

variable "bedrock_model_id" {
  description = "Bedrock model used by the hello-agent."
  type        = string
  default     = "anthropic.claude-sonnet-5"
}

variable "lambda_zip_path" {
  description = "Path to the Bedrock hello-agent Lambda deployment package."
  type        = string
  default     = "/home/naghi/ai_agent_infra/build/bedrock_hello.zip"
}
