output "state_bucket_name" {
  description = "Name of the Terraform state bucket."
  value       = aws_s3_bucket.terraform_state.id
}

output "state_bucket_arn" {
  description = "ARN of the Terraform state bucket."
  value       = aws_s3_bucket.terraform_state.arn
}

output "terraform_lock_table_name" {
  description = "Name of the DynamoDB state-lock table."
  value       = aws_dynamodb_table.terraform_lock.name
}

output "kms_key_arn" {
  description = "ARN of the KMS key used for state encryption."
  value       = aws_kms_key.terraform_state.arn
}
