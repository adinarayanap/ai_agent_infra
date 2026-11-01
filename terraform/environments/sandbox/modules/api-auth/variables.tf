variable "project" {
  type = string
}

variable "environment" {
  type = string
}

variable "domain_suffix" {
  description = "Unique suffix for the Cognito hosted UI domain."
  type        = string
}

variable "bedrock_lambda_function_name" {
  type = string
}

variable "bedrock_lambda_invoke_arn" {
  type = string
}

variable "tags" {
  type = map(string)
}
variable "owner" {
  description = "Owner tag value"
  type        = string
  default     = "ahmed"
}

variable "cost_center" {
  description = "Cost center tag value"
  type        = string
  default     = "learning"
}