data "aws_caller_identity" "current" {}

data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "bedrock_lambda" {
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]

    resources = [
      "arn:aws:logs:*:*:*"
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream"
    ]

    resources = [
      "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-haiku-20240307-v1:0",
      "arn:aws:bedrock:${var.bedrock_region}:${data.aws_caller_identity.current.account_id}:inference-profile/us.${var.bedrock_model_id}",
      "arn:aws:bedrock:*::foundation-model/${var.bedrock_model_id}",
    ]
  }
}

resource "aws_iam_role" "bedrock_lambda" {
  name               = "${var.project}-${var.environment}-bedrock-hello-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json

  tags = var.tags
}

resource "aws_iam_role_policy" "bedrock_lambda" {
  name   = "${var.project}-${var.environment}-bedrock-hello-policy"
  role   = aws_iam_role.bedrock_lambda.id
  policy = data.aws_iam_policy_document.bedrock_lambda.json
}

resource "aws_cloudwatch_log_group" "bedrock_lambda" {
  name              = "/aws/lambda/${var.project}-${var.environment}-bedrock-hello"
  retention_in_days = 14

  tags = var.tags
}

resource "aws_lambda_function" "bedrock_hello" {
  function_name = "${var.project}-${var.environment}-bedrock-hello"
  role          = aws_iam_role.bedrock_lambda.arn
  runtime       = "python3.12"
  handler       = "handler.handler"
  timeout       = 30
  memory_size   = 256

  filename         = var.lambda_zip_path
  source_code_hash = filebase64sha256(var.lambda_zip_path)

  environment {
    variables = {
      BEDROCK_REGION   = var.bedrock_region
      BEDROCK_MODEL_ID = "arn:aws:bedrock:${var.bedrock_region}:${data.aws_caller_identity.current.account_id}:inference-profile/us.${var.bedrock_model_id}"
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.bedrock_lambda,
    aws_iam_role_policy.bedrock_lambda
  ]

  tags = var.tags
}