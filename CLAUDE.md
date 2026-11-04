# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Architecture
This repository implements a Governed AI Infrastructure Deployment Platform. It follows a multi-account AWS strategy with a clear separation between control-plane and workload accounts.

- **Infrastructure**: Managed via Terraform. Structure separates bootstrap (remote state, CI) from environment-specific resources (`terraform/environments/`).
- **Application Logic**: Python Lambda functions in `src/`.
- **Core Workflow**:
    1. Infrastructure requests are orchestrated by a Lambda function.
    2. Amazon Bedrock generates infrastructure proposals based on an approved module catalog.
    3. AWS Step Functions manage the workflow (validation, plan generation, security checks, human approval, and application).
- **Observability**: CloudWatch metrics, alarms, and dashboards are used to monitor infrastructure and agent performance.

## Key Development Workflows

### Bootstrap Infrastructure (Day 01 Setup)
To recreate the foundation (Remote State, CI/CD, Budget Alerts):
1.  **Checkout Bootstrap**: Ensure you are on a fresh branch for bootstrapping.
2.  **Initialize**: Navigate to `terraform/bootstrap/`.
3.  **Configure**: Update `terraform.tfvars` if necessary for account specifics.
4.  **Deploy**: 
    - `terraform init`
    - `terraform plan -out=tfplan`
    - `terraform apply "tfplan"`
5.  **Verify**: Confirm S3 bucket creation (remote state), DynamoDB table (locking), and AWS Budget alerts.

### Infrastructure (Terraform)
- **Environments**: Located in `terraform/environments/`. Navigate to a specific environment folder before running `terraform` commands.
- **Bootstrapping**: Resources for CI/CD and remote state are in `terraform/bootstrap/`.
- **Validation**: Ensure `terraform plan` is executed and reviewed before any apply. CI pipeline handles automated checks.

### Application (Python)
- **Structure**: `src/` contains service-specific logic (e.g., `src/bedrock_hello/`).
- **Packaging**: Lambda functions are packaged into zip files in `build/`.
- **Testing**: Tests are located in `tests/`.

### Common Commands
- **Run tests**: `pytest tests/`
- **Linting**: (Run project-specific linting tools, e.g., `flake8` or `pylint` if configured)
- **Terraform Plan**: `terraform plan -out=tfplan` (Run inside environment directory)

## Security
- **Principles**: Least privilege, encryption at rest and in transit, and audited execution.
- **Constraint**: Do not hardcode credentials. Use IAM roles and Secrets Manager.
- **Workflow**: All destructive changes (create, update, replace, destroy) require explicit human approval via the authenticated review interface.
