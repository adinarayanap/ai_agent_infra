# PROJECT_CONTEXT — ai_agent_infra

This is the authoritative project map. Claude must read this before proposing
or writing any code.

## Repository layout

- CLAUDE.md
  Permanent Claude Code project rules.

- PROJECT_CONTEXT.md
  Authoritative repository map and current sprint state.

- src/agent/
  Day 10 UC1 agent components at repository root.
  Contains:
  - tools/registry.py
  - tools/generate_terraform.py
  - tools/validate_terraform.py
  - validators/plan_validator.py
  - modules/approved_modules.py

- tests/
  Repository-root tests for Day 10 UC1 tools and validators.
  Run from repository root with: pytest -q

- terraform/environments/sandbox/src/agent/
  Deployed Lambda agent source.
  Contains:
  - handler.py
  - config.py
  - prompts.py
  - modules/approved_modules.py
  - validators/plan_validator.py
  - schemas/infrastructure_plan.schema.json

- terraform/environments/sandbox/
  Sandbox Terraform environment and Lambda deployment source.

- src/bedrock_hello/handler.py
  Working Day 09 Bedrock Converse hello-agent handler.
  Use as a reference for Converse, DynamoDB audit, and logging patterns.

- day09_smoke_test.py
  Day 09 smoke test.

- evals/
  Evaluation prompts and reports.

## Important path rule

There are TWO agent source locations:

1. src/agent/
   Used by repository-root unit tests and Day 10 UC1 tooling.

2. terraform/environments/sandbox/src/agent/
   Used by the deployed sandbox Lambda.

Do not mix them.
Do not create a new src/agent/handler.py.
Do not create src/llm_integration.py.
Do not create duplicate Bedrock clients or simulated model responses.

## Current sprint state

- Completed: Days 01-10
- Current day: Day 11
- Day 11 task: approved-module retrieval for UC1
- Day 11 is not complete until retrieval tests pass.
- Do not start UC2.
- Do not implement Step Functions before Day 15.

## Current architecture

User prompt
  -> API Gateway + Cognito
  -> Lambda handler:
       terraform/environments/sandbox/src/agent/handler.py
  -> get_module_by_prompt()
       terraform/environments/sandbox/src/agent/modules/approved_modules.py
  -> Bedrock Converse / Mistral Large 3
  -> reply
  -> DynamoDB audit record

Day 10 components:
  src/agent/tools/registry.py
  src/agent/tools/generate_terraform.py
  src/agent/tools/validate_terraform.py
  src/agent/validators/plan_validator.py

## Model rules

- Model: Mistral Large 3
- Model ID: mistral.mistral-large-3-675b-instruct
- Region: ap-south-1
- API: Amazon Bedrock Converse
- Temperature: 0.1 for infrastructure generation
- Top P: 0.9
- Maximum tool iterations: 3

## Security boundary

- Mistral proposes.
- plan_validator accepts or rejects.
- The delivery pipeline validates security and cost.
- A human approves.
- Only the deployment pipeline applies Terraform.
- The model and agent Lambda never deploy infrastructure.
- Never register apply_terraform, destroy_terraform,
  assume_deployment_role, or approve_deployment as model tools.

## Required commands

Activate environment:

source .venv/bin/activate

Run all tests:

pytest -q

Do not use:
pytest -q tests

Validate Terraform:

terraform fmt -check -recursive
terraform validate

Compile Lambda source:

python -m compileall terraform/environments/sandbox/src

## Mandatory workflow

For every code task:

1. Read PROJECT_CONTEXT.md.
2. Read every file that will be changed.
3. State the objective.
4. List exact files to create or modify.
5. Show the complete proposed diff or complete new file.
6. Explain every change.
7. List validation commands.
8. Wait for explicit approval.
9. Only after approval, apply the exact approved change.
10. Run tests.
11. If tests fail, stop and report the failure.

Never write files immediately after receiving a task.
Never overwrite working code without approval.
