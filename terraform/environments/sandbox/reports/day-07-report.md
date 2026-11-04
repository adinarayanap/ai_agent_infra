# Day 07 Report: Sprint 1 Review

## Goal
Validate the "Foundations & Secure Access" sprint, ensuring end-to-end functionality and adherence to the sprint requirements.

## Smoke Test Results
- **Identity & Auth**: Verified API returns 401 Unauthorized without token; 200 OK with valid JWT.
- **Bedrock Integration**: Lambda successfully invokes Claude; requests are being processed.
- **Audit Lifecycle**: Confirmed `RECEIVED` and `COMPLETED` records exist in the DynamoDB audit table.
- **Observability**: CloudWatch dashboard is active; SNS alert subscription verified via email.
- **Foundations**: Terraform state encrypted; budget alerts confirmed in AWS Console.

## Sprint 1 Deliverables Checklist
- [x] Repo, remote state, budget alerts, CI.
- [x] Identity Center + sandbox target account.
- [x] Authenticated POST /prompt calling Bedrock (Claude).
- [x] DynamoDB request and audit lifecycle.
- [x] Structured logs and CloudWatch alarms.

## Status
- **Sprint 1 complete.**
- Ready to begin **Sprint 2: Agent Brain**.



## 💨 Sprint 1 Smoke Test Script

Run these tests from your terminal to verify that all components are connected correctly.

1. Identity & Auth Test

Verify that your API is secured and that the Cognito configuration is correct.
# Verify 401 Unauthorized without token
curl -i -X POST https://<your-api-endpoint>/prompt \
  -d '{"prompt": "Hello"}'

# Verify 200 OK with a valid JWT
# (You will need to get a token from your Cognito User Pool,
# then paste it here)
curl -i -X POST https://<your-api-endpoint>/prompt \
  -H "Authorization: Bearer <YOUR_JWT_TOKEN>" \
  -d '{"prompt": "Tell me a story about cloud infrastructure."}'

2. Bedrock & Audit Test

Verify the Lambda calls Bedrock and the audit table logs the result.
# Check the audit table for the request
# Replace with your table name
aws dynamodb scan --table-name prompt-infra-sandbox-audit-table
Expected: You should see an item with Status: COMPLETED, Prompt, and Reply fields.

3. Observability Test (Alarms/Dashboard)

- Manual Alarm Trigger:
  - Temporarily modify your Lambda code to raise an exception or provide an invalid MODEL_ID (so it fails).
  - Invoke the API.
  - Check your email for the SNS alert.
  - Verify: The CloudWatch Alarm (lambda-errors) should trigger within 1-2 minutes.
  - Revert: Fix the Lambda and run terraform apply to resolve the alarm.

4. Foundation Checks

- Budget: Log into the AWS Console, navigate to Billing -> Budgets, and confirm the "Monthly Budget" is active and your email is set as a subscriber.
- State: Check the S3 bucket in terraform/bootstrap/ to ensure terraform.tfstate is updated and encrypted.