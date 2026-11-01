output "api_endpoint" {
  value = aws_apigatewayv2_api.prompt.api_endpoint
}

output "cognito_user_pool_id" {
  value = aws_cognito_user_pool.prompt.id
}

output "cognito_client_id" {
  value = aws_cognito_user_pool_client.prompt.id
}

output "cognito_domain" {
  value = aws_cognito_user_pool_domain.prompt.domain
}