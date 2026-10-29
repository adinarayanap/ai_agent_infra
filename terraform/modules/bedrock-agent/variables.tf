variable "project" {
  description = "Project name used for resource naming and tags."
  type        = string
}

variable "environment" {
  description = "Deployment environment, such as dev or sandbox."
  type        = string
}

variable "bedrock_model_id" {
  description = "Bedrock inference profile or model ID used by the hello-agent."
  type        = string
  default     = "anthropic.claude-sonnet-5"
}

variable "bedrock_region" {
  description = "AWS region where Bedrock is available."
  type        = string
  default     = "us-east-1"
}

variable "tags" {
  description = "Standard resource tags."
  type        = map(string)
  default     = {}
}
variable "lambda_zip_path" {
  description = "Absolute or relative path to the packaged Lambda deployment archive."
  type        = string
}
