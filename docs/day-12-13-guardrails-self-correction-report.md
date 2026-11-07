# Day 12–13 Closure Report: Bedrock Guardrails and UC3 Self-Correction

## Status

Day 12 enhancement and Day 13 UC3 self-correction are implemented and covered
by unit tests. The full unit suite passes:

```text
37 passed
```

The implementation is under:

```text
terraform/environments/sandbox/
```

The following commits are already pushed to
`origin/day-13-self-correction-uc3`:

```text
e90e19e test(day-12): add deterministic local guardrail pre-check tests
109c40b feat(day-13): implement UC3 self-correction and Terraform generation
```

## Scope

This report covers two related but distinct changes:

| Milestone | Scope | Status |
|---|---|---|
| Day 12 enhancement | Deterministic local pre-checks before Bedrock Guardrails | Complete |
| Day 13 | UC3 plan validation, Terraform generation, handler self-correction | Complete |

Day 12 does **not** replace Bedrock Guardrails. It is an additional local
defense layer that rejects clearly invalid or unsafe requests before AWS is
invoked.

## Day 12: Local Pre-Check

### Files

| File | Purpose |
|---|---|
| `terraform/environments/sandbox/src/agent/validators/pre_check.py` | Implements `LocalRejectionError` and `pre_check_request()` |
| `terraform/environments/sandbox/tests/fixtures/valid_prompts.json` | Valid UC1–UC3 request fixtures |
| `terraform/environments/sandbox/tests/fixtures/blocked_prompts.json` | Blocked-request fixtures |
| `terraform/environments/sandbox/tests/unit/test_guardrails.py` | Day 12 unit tests |

### Behavior

`pre_check_request(body)` performs local validation before Bedrock Guardrails.

It rejects:

- Non-dict request bodies.
- Non-JSON-serializable request bodies.
- Requests larger than `MAX_REQUEST_SIZE_BYTES`.
- Missing, empty, or whitespace-only prompts.
- EC2, RDS, Kubernetes, IAM-user, credential, destructive, public-exposure,
  cost-abuse, malware, and prompt-injection requests.
- Requests outside the supported UC1–UC3 scope.

On failure, it raises `LocalRejectionError`.

### Integration status

The local pre-check is **not yet integrated into `handler.py`**. Therefore, it
does not currently return an HTTP status directly. The Day 12 unit tests prove
that local rejection occurs without creating a Boto3 client or invoking AWS.

A future handler integration must translate `LocalRejectionError` into an
appropriate API error response, likely HTTP 400 for malformed requests and
HTTP 403 for policy-rejected requests.

### Security controls

- Deterministic, fail-closed validation.
- No Boto3 client creation during local rejection.
- Rejection of explicit public S3 exposure requests.
- Rejection of destructive bulk operations.
- Rejection of credential or secret requests.
- Rejection of prompt injection and instruction override.
- Configurable maximum request size through `MAX_REQUEST_SIZE_BYTES`.

## Day 13: UC3 Self-Correction

### Files

| File | Purpose |
|---|---|
| `terraform/environments/sandbox/src/agent/handler.py` | Request orchestration and self-correction |
| `terraform/environments/sandbox/src/agent/validators/plan_validator.py` | UC3 plan validation |
| `terraform/environments/sandbox/src/agent/tools/generate_terraform.py` | Deterministic UC3 Terraform generation |
| `terraform/environments/sandbox/src/agent/tools/validate_terraform.py` | Terraform formatting validation |
| `terraform/environments/sandbox/src/agents/prompts/system_prompt.txt` | System prompt used by Bedrock |
| `terraform/environments/sandbox/tests/unit/conftest.py` | Test import-path configuration |
| `terraform/environments/sandbox/tests/unit/test_uc3_validation.py` | UC3 plan-validation tests |
| `terraform/environments/sandbox/tests/unit/test_uc3_hcl.py` | UC3 Terraform-generation tests |
| `terraform/environments/sandbox/tests/unit/test_uc3_orchestration.py` | Handler orchestration tests |

### UC3 plan validation

`validate_plan(plan)` validates an approved UC3 infrastructure plan before
Terraform generation.

A valid plan must:

- Be a JSON object.
- Have `status` equal to `approved`.
- Include `aws_dynamodb_table`, `aws_lambda_function`,
  `aws_apigatewayv2_api`, `aws_iam_role`, and `aws_iam_policy` resources.
- Include non-empty tags on every resource.
- Enable DynamoDB server-side encryption.
- Enable DynamoDB point-in-time recovery.
- Enable HTTPS-only API Gateway.
- Exclude IAM users.
- Exclude wildcard IAM actions.
- Exclude hardcoded AWS account IDs in IAM policy resources.

Invalid plans raise `PlanRejectedError`.

### Terraform generation

`generate_terraform(plan)` returns a dictionary containing generated
`variables.tf`, `outputs.tf`, and `main.tf` files.

For UC3, it generates:

- DynamoDB table with server-side encryption, point-in-time recovery, and
  mandatory tags.
- DynamoDB point-in-time recovery resource.
- CloudWatch log group.
- IAM role for Lambda.
- IAM policy scoped to DynamoDB and CloudWatch Logs actions.
- Lambda function.
- API Gateway HTTP API.
- API Gateway integration and route.
- Lambda permission for API Gateway invocation.

The generated IAM policy uses explicit DynamoDB and CloudWatch Logs actions.
It does not use wildcard actions or hardcoded AWS account IDs.

### Terraform validation

`validate_terraform(files)` writes the generated files to a temporary
directory and runs:

```bash
terraform fmt -check -recursive
```

This checks formatting only. It does **not** run `terraform validate`, does
not initialize a Terraform backend, and does not deploy infrastructure.

The function returns:

```python
{
    "valid": bool,
    "fmt_passed": bool,
    "validate_passed": None,
    "errors": list[str],
}
```

`terraform validate` remains deferred to a future prepared-pipeline stage.

### Handler orchestration

`handler(event, context)` implements this flow:

```text
API request
  -> JSON and prompt validation
  -> Bedrock Converse with system prompt and Guardrails
  -> Guardrail intervention check
  -> Model-reply parsing
  -> UC3 routing
  -> Plan validation
  -> Terraform generation
  -> Terraform fmt validation
  -> Bounded self-correction
  -> Response and audit record
```

For a non-UC3 request, the handler returns the model reply directly.

For a UC3 request, the handler validates the plan before calling
`generate_terraform()`. A plan-validation failure immediately returns HTTP 422
and does not invoke Terraform generation.

### Self-correction policy

The handler permits a maximum of three total Bedrock model calls for one UC3
request:

1. Initial plan generation.
2. First correction attempt.
3. Second correction attempt.

A fourth model call is never made after three failed Terraform-validation
attempts.

The retry counter is local to each Lambda invocation. It is not shared across
requests.

Retry occurs only after a Terraform formatting-validation failure. The handler
includes the exact validation errors in the next model prompt.

Plan-validation failures do not trigger a model retry. They immediately return
HTTP 422.

### Audit behavior

The handler writes audit records to DynamoDB using the request correlation ID.

Supported statuses are:

- `RECEIVED`
- `BLOCKED`
- `VALIDATION_FAILED`
- `COMPLETED`
- `FAILED`

Guardrail-intervened requests return HTTP 403 and are recorded as `BLOCKED`.

## Security Controls

| Control | Implementation |
|---|---|
| Local deterministic validation | `pre_check_request()` rejects unsafe or out-of-scope requests before AWS |
| Bedrock Guardrails | Guardrail configuration is attached to Converse requests |
| Guardrail enforcement | Guardrail interventions return HTTP 403 and `BLOCKED` audit status |
| Plan validation | Required resources, tags, encryption, PITR, HTTPS, and IAM constraints |
| Least-privilege generation | Generated IAM policy is scoped to DynamoDB and CloudWatch Logs |
| No wildcard IAM actions | Wildcard actions are rejected during plan validation |
| No IAM users | IAM-user resources are rejected |
| No hardcoded account IDs | Account IDs in policy resources are rejected |
| Bounded model usage | Maximum of three total model calls per UC3 request |
| Audit trail | Request status and errors are recorded in DynamoDB |

## Test Evidence

| Suite | Test file | Tests | Result |
|---|---|---:|---|
| Day 12 guardrail pre-check | `test_guardrails.py` | 8 | Passed |
| UC3 plan validation | `test_uc3_validation.py` | 12 | Passed |
| UC3 Terraform generation | `test_uc3_hcl.py` | 2 | Passed |
| UC3 handler orchestration | `test_uc3_orchestration.py` | 9 | Passed |
| Pre-existing unit tests | Other unit-test files | 6 | Passed |
| **Full unit suite** |  | **37** | **Passed** |

The Day 13-specific suites contain 23 tests. The full suite contains 37 tests
because it also includes the eight Day 12 tests and six pre-existing tests.

AWS client interactions are mocked in the orchestration tests. The tests
verify HTTP status codes, model-call counts, guardrail handling, audit calls,
and validation-error feedback.

## Known Limitations

- The local pre-check is keyword-based and does not detect advanced or novel
  prompt-injection techniques.
- The local pre-check is not yet integrated into the API handler.
- `validate_terraform()` performs formatting validation only; it does not run
  `terraform validate`.
- The handler does not deploy generated Terraform.
- There are no end-to-end AWS integration tests.
- Bedrock throttling and exponential-backoff handling are not implemented.
- The generated infrastructure has not been deployed or validated in a live
  AWS environment.
- The repository-root `src/agent/tools` changes were an older parallel
  implementation and were discarded; the sandbox implementation is
  authoritative.

## Day 14 Follow-ups

- Integrate `pre_check_request()` into the API handler and map
  `LocalRejectionError` to appropriate HTTP responses.
- Add structured JSON-schema validation for model-generated plans.
- Add `terraform validate` and policy-as-code checks in a prepared pipeline.
- Add end-to-end tests for Bedrock, DynamoDB, API Gateway, and Lambda.
- Add Bedrock throttling detection and bounded exponential-backoff handling.
- Add a deployment workflow for validated Terraform plans.
- Add observability metrics for generation attempts and validation failures.
