# Day 12–13 Report: Guardrails Enhancement and UC3 Self-Correction

## Objective

This report documents the Day 12 local guardrail enhancement and the Day 13
UC3 self-correction implementation.

Day 12 added a deterministic local pre-check layer before Bedrock Guardrails.
Day 13 implemented UC3 infrastructure-plan validation, deterministic Terraform
generation, handler self-correction, and bounded retry behavior.

## Day 12 Enhancement

### Local pre-check

The agent now performs local, deterministic validation before invoking Bedrock
Guardrails. This reduces unnecessary model and guardrail invocations for
requests that are malformed, oversized, or outside the supported scope.

The pre-check rejects:

- Missing, empty, or malformed request bodies.
- Requests exceeding the configured size limit.
- Requests outside the supported UC1–UC3 scope.
- Requests for unsupported infrastructure, including EC2, RDS, and Kubernetes.
- Destructive bulk operations, such as deleting or terminating all resources.
- Requests for credentials, passwords, access keys, or SSH keys.
- Prompt-injection and instruction-override requests.
- Public-exposure requests for S3 resources.
- Cost-abuse or resource-explosion requests, including cryptocurrency mining.
- Requests containing cryptocurrency, malware, or similar prohibited terms.

### Test coverage

The Day 12 enhancement is covered by fixture-driven unit tests:

- Valid infrastructure requests pass local validation.
- Malformed and empty requests are rejected.
- Oversized requests are rejected.
- All blocked-request fixtures are rejected before AWS invocation.
- Explicit public-exposure requests are rejected.
- The implementation does not invoke Boto3 or AWS during local rejection.

Test result:

```text
8 passed
```

## Day 13 Implementation

### UC3 objective

UC3 generates a secure, serverless API architecture containing:

- Amazon DynamoDB
- AWS Lambda
- Amazon API Gateway HTTP API
- IAM role and scoped IAM policy
- CloudWatch log group

The generated infrastructure uses mandatory project tags, DynamoDB encryption
and point-in-time recovery, HTTPS-only API Gateway access, and least-privilege
IAM permissions.

### Plan validation

`agent.validators.plan_validator` validates an approved UC3 plan before
Terraform generation.

It rejects plans that:

- Are not approved.
- Do not contain the required resource types.
- Include IAM users.
- Lack mandatory tags.
- Disable DynamoDB server-side encryption or point-in-time recovery.
- Disable HTTPS-only API Gateway access.
- Use wildcard IAM actions.
- Contain hardcoded AWS account IDs.

### Terraform generation

`agent.tools.generate_terraform` converts a validated UC3 plan into
deterministic Terraform configuration.

The generated configuration includes:

- DynamoDB table with encryption, PITR, and mandatory tags.
- Lambda function with configured runtime, handler, memory, and timeout.
- API Gateway HTTP API with an AWS_PROXY Lambda integration and route.
- IAM role for Lambda.
- Scoped IAM policy for DynamoDB and CloudWatch Logs.
- Lambda permission for API Gateway invocation.

The generated IAM policy does not use wildcard actions or hardcoded AWS
account IDs.

### Self-correction flow

The Lambda handler now supports bounded self-correction for UC3 requests.

1. The handler receives and validates the request.
2. It retrieves approved-module context when available.
3. It invokes Bedrock with the configured system prompt and guardrail.
4. If Bedrock Guardrails intervene, it returns HTTP 403 and records `BLOCKED`.
5. It parses the model reply as a JSON infrastructure plan.
6. It validates the plan before Terraform generation.
7. It generates Terraform files and validates them with `terraform fmt`.
8. If validation fails, it returns the exact validation errors to the model.
9. It retries for up to three total model calls.
10. If validation still fails, it returns HTTP 422 with the validation errors.
11. Successful requests return the generated Terraform files.

### Retry policy

The retry counter is scoped to each Lambda invocation. A new request receives
a fresh retry budget.

The handler permits a maximum of three total model calls for one UC3 request:

- Initial generation
- First correction attempt
- Second correction attempt

A fourth model call is never made after three failed Terraform-validation
attempts.

## Security Controls

| Control | Implementation |
|---|---|
| Local request validation | Deterministic pre-check before AWS |
| Bedrock Guardrails | Guardrail configuration and blocked-request handling |
| Plan validation | Required resources, tags, encryption, PITR, HTTPS, IAM constraints |
| Least privilege | No wildcard IAM actions; scoped DynamoDB and Logs permissions |
| No IAM users | IAM user resources are rejected |
| No hardcoded account IDs | Account IDs in policy resources are rejected |
| Audit trail | Request status and errors recorded in DynamoDB |
| Bounded retries | Maximum of three total model calls per request |

## Test Evidence

The full unit suite passes:

```text
37 passed
```

Test coverage includes:

- Day 12 local guardrail pre-checks.
- UC3 plan validation.
- UC3 Terraform generation.
- UC3 handler orchestration.
- Retry success and failure paths.
- Guardrail-intervention handling.
- Per-request retry-counter isolation.
- JSON validation before Terraform generation.

## Commits

```text
e90e19e test(day-12): add deterministic local guardrail pre-check tests
109c40b feat(day-13): implement UC3 self-correction and Terraform generation
```

## Known Limitations

- `terraform validate` is deferred to a prepared pipeline directory.
- The handler does not yet deploy generated Terraform.
- The implementation does not yet include end-to-end AWS integration tests.
- The local pre-check is keyword-based and should be expanded with structured
  intent classification in a future iteration.
- The report files and `.claude/` working artifacts remain untracked and should
  be reviewed before inclusion in the repository.

## Day 14 Follow-ups

- Add structured plan-schema validation.
- Add integration tests for Bedrock, DynamoDB, and API Gateway.
- Add policy-as-code checks for generated Terraform.
- Add deployment workflow for validated infrastructure plans.
- Add end-to-end test for a complete UC3 request.
