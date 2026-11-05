# Day 12 Closure Report — Bedrock Guardrails

## Status

Day 12 is complete.

## Objective

Implement Bedrock Guardrails for N4: protect the agent against prompt
injection, unsafe requests, and out-of-scope infrastructure requests.

## Implemented

- Bedrock Guardrail Terraform resource with MISCONDUCT content filtering
- High-strength input and output filtering
- Guardrail version resource
- GUARDRAIL_ID and GUARDRAIL_VERSION Lambda environment variables
- Conditional guardrailConfig in Bedrock Converse requests
- Guardrail intervention handling in the sandbox Lambda handler
- BLOCKED audit records for blocked requests
- Mocked unit tests for guardrail configuration and intervention behavior

## Guardrail behavior

When Bedrock intervenes:

- The handler logs a structured guardrail_intervention event.
- It writes a BLOCKED audit record.
- It returns HTTP 403.
- It returns only: Request blocked by policy.
- It does not expose internal guardrail details.

## Security controls

- The guardrail is defined through Terraform.
- Guardrail ID and version are supplied through environment variables.
- guardrailConfig is added only when both values are configured.
- The model and agent Lambda cannot deploy infrastructure.
- No deployment tools are registered.
- No credentials, account IDs, secrets, tokens, or private IPs are stored.
- No broad IAM permissions were added.

## Validation

- pytest -q: <INSERT ACTUAL TEST COUNT> passed
- terraform fmt -check -recursive: passed
- terraform validate: passed

## Scope boundary

- Day 12 Bedrock Guardrails complete.
- Guardrail defined but not deployed.
- UC2 has not been started.
- Step Functions deployment workflow remains scheduled for Day 15.

## Next

Day 13: self-correction and UC3.
