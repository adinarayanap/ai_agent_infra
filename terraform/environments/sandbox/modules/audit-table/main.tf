resource "aws_kms_key" "audit_table" {
  description             = "KMS key for DynamoDB audit table"
  deletion_window_in_days = 7
  enable_key_rotation     = true
  tags                    = var.tags
}

resource "aws_kms_alias" "audit_table" {
  name          = "alias/${var.project}-${var.environment}-audit-table"
  target_key_id = aws_kms_key.audit_table.key_id
}

resource "aws_dynamodb_table" "audit" {
  name           = "${var.project}-${var.environment}-audit-table"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "RequestId"

  attribute {
    name = "RequestId"
    type = "S"
  }

  ttl {
    attribute_name = "TTL"
    enabled        = true
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.audit_table.arn
  }

  tags = var.tags
}
