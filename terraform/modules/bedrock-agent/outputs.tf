output "lambda_function_name" {
  description = "Name of the Bedrock hello-agent Lambda function."
  value       = aws_lambda_function.bedrock_hello.function_name
}

output "lambda_role_arn" {
  description = "IAM role ARN used by the Bedrock hello-agent Lambda."
  value       = aws_iam_role.bedrock_lambda.arn
}

output "log_group_name" {
  description = "CloudWatch log group for the Lambda function."
  value       = aws_cloudwatch_log_group.bedrock_lambda.name
}
