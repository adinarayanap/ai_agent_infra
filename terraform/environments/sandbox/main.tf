module "bedrock_agent" {
  source = "../../modules/bedrock-agent"

  project          = var.project
  environment      = var.environment
  bedrock_model_id = var.bedrock_model_id
  bedrock_region   = var.aws_region
  lambda_zip_path  = var.lambda_zip_path


  tags = {
    project     = var.project
    environment = var.environment
    owner       = var.owner
    cost-center = var.cost_center
    managed-by  = "terraform"
  }
}
