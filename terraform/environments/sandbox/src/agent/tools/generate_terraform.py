import json

def generate_terraform(plan_data: dict) -> dict:
    """
    Generates deterministic Terraform configuration using typed resource arrays.
    """
    uc = plan_data.get("use_case")
    resources = plan_data.get("resources", [])

    # Build lookup maps
    res_map = {r["type"]: r for r in resources}

    files = {
        "variables.tf": _generate_variables(),
        "outputs.tf": _generate_outputs(uc, res_map),
        "main.tf": _generate_main(uc, res_map)
    }
    return {"files": files}

def _generate_variables() -> str:
    return """
variable "project" { type = string }
variable "environment" { type = string }
variable "tags" { type = map(string) }
variable "lambda_package_path" { type = string }
variable "dynamodb_kms_key_arn" { type = string }
"""

def _generate_outputs(uc: str, res_map: dict) -> str:
    if uc == "UC1":
        return """
output "bucket_name" { value = aws_s3_bucket.this.id }
output "bucket_arn" { value = aws_s3_bucket.this.arn }
"""
    return """
output "api_endpoint" { value = aws_apigatewayv2_api.this.api_endpoint }
output "lambda_arn" { value = aws_lambda_function.this.arn }
"""

def _generate_main(uc: str, res_map: dict) -> str:
    if uc == "UC1":
        return _hcl_uc1()
    elif uc == "UC3":
        return _hcl_uc3(res_map)
    raise ValueError(f"Unsupported use case: {uc}")

def _hcl_uc1() -> str:
    return """
resource "aws_s3_bucket" "this" {
  bucket = "${var.project}-${var.environment}-data"
  tags   = var.tags
}
resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  bucket = aws_s3_bucket.this.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}
resource "aws_s3_bucket_versioning" "this" {
  bucket = aws_s3_bucket.this.id
  versioning_configuration {
    status = "Enabled"
  }
}
resource "aws_s3_bucket_public_access_block" "this" {
  bucket = aws_s3_bucket.this.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
"""

def _hcl_uc3(res_map: dict) -> str:
    db = res_map["aws_dynamodb_table"]
    fn = res_map["aws_lambda_function"]
    api = res_map["aws_apigatewayv2_api"]

    attr_blocks = ""
    for attr in db.get("attribute_definitions", []):
        attr_blocks += f"""
  attribute {{
    name = "{attr['name']}"
    type = "{attr['type']}"
  }}
"""

    return f"""
resource "aws_dynamodb_table" "this" {{
  name             = "{db['name']}"
  billing_mode     = "PAY_PER_REQUEST"
  hash_key         = "{db['hash_key']}"
{attr_blocks}
  server_side_encryption {{
    enabled     = true
    kms_key_arn = var.dynamodb_kms_key_arn
  }}
  tags = var.tags
}}

resource "aws_dynamodb_table_point_in_time_recovery" "this" {{
  table_name = aws_dynamodb_table.this.name
  enabled    = true
}}

resource "aws_cloudwatch_log_group" "this" {{
  name = "/aws/lambda/{fn['name']}"
  tags = var.tags
}}

data "aws_iam_policy_document" "lambda_policy" {{
  statement {{
    actions   = ["dynamodb:GetItem", "dynamodb:PutItem"]
    resources = [aws_dynamodb_table.this.arn]
  }}
  statement {{
    actions   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${{aws_cloudwatch_log_group.this.arn}}:*"]
  }}
}}

resource "aws_iam_role" "this" {{
  name = "{fn['name']}-role"
  assume_role_policy = jsonencode({{
    Version = "2012-10-17"
    Statement = [{{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {{ Service = "lambda.amazonaws.com" }}
    }}]
  }})
  tags = var.tags
}}

resource "aws_iam_role_policy" "this" {{
  role   = aws_iam_role.this.id
  policy = data.aws_iam_policy_document.lambda_policy.json
}}

resource "aws_lambda_function" "this" {{
  function_name = "{fn['name']}"
  runtime       = "{fn['runtime']}"
  handler       = "{fn['handler']}"
  memory_size   = {fn['memory_size']}
  timeout       = {fn['timeout']}
  role          = aws_iam_role.this.arn
  filename      = var.lambda_package_path
  tags          = var.tags
}}

resource "aws_apigatewayv2_api" "this" {{
  name          = "{api['name']}"
  protocol_type = "HTTP"
  tags          = var.tags
}}

resource "aws_lambda_permission" "this" {{
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.this.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${{aws_apigatewayv2_api.this.execution_arn}}/*/*"
}}

resource "aws_apigatewayv2_integration" "this" {{
  api_id           = aws_apigatewayv2_api.this.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.this.invoke_arn
}}

resource "aws_apigatewayv2_route" "this" {{
  api_id    = aws_apigatewayv2_api.this.id
  route_key = "{api.get('route', {}).get('route_key', 'ANY /')}"
  target    = "integrations/${{aws_apigatewayv2_integration.this.id}}"
}}
"""
