
resource "aws_cognito_user_pool" "prompt" {
  name = "${var.project}-${var.environment}-users"

  password_policy {
    minimum_length    = 12
    require_lowercase = true
    require_numbers   = true
    require_symbols   = true
    require_uppercase = true
  }

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  tags = var.tags
}

resource "aws_cognito_user_pool_domain" "prompt" {
  domain       = "${var.project}-${var.environment}-${var.domain_suffix}"
  user_pool_id = aws_cognito_user_pool.prompt.id
}

resource "aws_cognito_user_pool_client" "prompt" {
  name         = "${var.project}-${var.environment}-client"
  user_pool_id = aws_cognito_user_pool.prompt.id

  explicit_auth_flows = [
    "ALLOW_USER_SRP_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH"
  ]

  generate_secret                      = false
  prevent_user_existence_errors        = "ENABLED"
  allowed_oauth_flows_user_pool_client = false
}

resource "aws_apigatewayv2_api" "prompt" {
  name          = "${var.project}-${var.environment}-api"
  protocol_type = "HTTP"
  description   = "Authenticated Prompt-to-Infra API"

  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["POST", "OPTIONS"]
    allow_headers = ["authorization", "content-type"]
  }

  tags = var.tags
}

resource "aws_apigatewayv2_authorizer" "cognito" {
  api_id           = aws_apigatewayv2_api.prompt.id
  authorizer_type  = "JWT"
  identity_sources = ["$request.header.Authorization"]

  jwt_configuration {
    audience = [aws_cognito_user_pool_client.prompt.id]
    issuer   = "https://${aws_cognito_user_pool.prompt.endpoint}"
  }

  name = "${var.project}-${var.environment}-cognito-authorizer"
}

resource "aws_apigatewayv2_integration" "bedrock" {
  api_id                 = aws_apigatewayv2_api.prompt.id
  integration_type       = "AWS_PROXY"
  integration_method     = "POST"
  integration_uri        = var.bedrock_lambda_invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "prompt" {
  api_id             = aws_apigatewayv2_api.prompt.id
  route_key          = "POST /prompt"
  target             = "integrations/${aws_apigatewayv2_integration.bedrock.id}"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
  authorization_type = "JWT"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.prompt.id
  name        = "$default"
  auto_deploy = true

  tags = var.tags
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.bedrock_lambda_function_name
  principal     = "apigateway.amazonaws.com"

  source_arn = "${aws_apigatewayv2_api.prompt.execution_arn}/*/*/prompt"
}