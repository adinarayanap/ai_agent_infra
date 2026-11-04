# Day 05: Request Data Model

## Goal
To implement a persistent request auditing system using DynamoDB, enabling the AI agent to track the lifecycle of infrastructure requests from `RECEIVED` to `DEPLOYED`.

## Why DynamoDB?
- **Persistence:** Track request state across invocations.
- **Auditing:** Maintain a log of who requested what and the resulting infra plan.
- **TTL (Time to Live):** Automatically clean up old request records to save costs.
- **Security:** Encrypt at rest using KMS.

## Resources to Create

### 1. New Module: `audit-table`
**Location:** `terraform/environments/sandbox/modules/audit-table/`

*   **`main.tf`**:
    *   `aws_dynamodb_table`: Name: `prompt-to-infra-audit-${var.environment}`, HashKey: `RequestId`, Attributes: `RequestId` (S), TTL enabled on `TTL` attribute.
    *   `aws_kms_key` & `aws_kms_alias`: For table encryption.
*   **`variables.tf`**: `project`, `environment`, `tags`.
*   **`outputs.tf`**: `audit_table_name`, `audit_table_arn`.

### 2. Infrastructure Updates
**Location:** `terraform/environments/sandbox/`

*   **`main.tf`**: Instantiate `module "audit_table"`.
*   **Update `bedrock-agent`**: Pass `audit_table_arn` and `audit_table_name` as variables. Update IAM role to allow `dynamodb:PutItem` and `dynamodb:UpdateItem` on the table ARN.

### 3. Lambda Updates
**Location:** `src/bedrock_hello/handler.py`

*   Add DynamoDB client logic to `put_item` (RECEIVED) at start and `update_item` (DEPLOYED/FAILED) at end/exception.
