output "bedrock_lambda_function_name" {
  description = "Bedrock hello-agent Lambda function name."
  value       = module.bedrock_agent.lambda_function_name
}

output "bedrock_lambda_role_arn" {
  description = "IAM role used by the Bedrock hello-agent Lambda."
  value       = module.bedrock_agent.lambda_role_arn
}
