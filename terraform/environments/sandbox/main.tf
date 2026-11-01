locals {
  tags = {
    project     = var.project
    environment = var.environment
    owner       = var.owner
    managed-by  = "terraform"
    cost-center = var.cost_center
  }
}

module "audit_table" {
  source      = "./modules/audit-table"
  project     = var.project
  environment = var.environment
  tags        = local.tags
}

module "bedrock_agent" {
  source = "./modules/bedrock-agent"

  project         = var.project
  environment     = var.environment
  lambda_zip_path = var.lambda_zip_path
  audit_table_arn  = module.audit_table.audit_table_arn
  audit_table_name = module.audit_table.audit_table_name
  notification_email = var.notification_email
  tags            = local.tags
}

module "api_auth" {
  source = "./modules/api-auth"

  project       = var.project
  environment   = var.environment
  domain_suffix = var.domain_suffix

  bedrock_lambda_function_name = module.bedrock_agent.lambda_function_name
  bedrock_lambda_invoke_arn    = module.bedrock_agent.bedrock_lambda_invoke_arn

  tags = local.tags
}

output "api_endpoint" {
  value = module.api_auth.api_endpoint
}

output "cognito_user_pool_id" {
  value = module.api_auth.cognito_user_pool_id
}

output "cognito_client_id" {
  value = module.api_auth.cognito_client_id
}

output "cognito_domain" {
  value = module.api_auth.cognito_domain
}