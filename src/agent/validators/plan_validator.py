# src/agent/validators/plan_validator.py
import json
from pathlib import Path
from jsonschema import Draft202012Validator

SCHEMA_PATH = (
    Path(__file__).parents[1]
    / "schemas"
    / "infrastructure_plan.schema.json"
)

with SCHEMA_PATH.open() as schema_file:
    SCHEMA = json.load(schema_file)

validator = Draft202012Validator(SCHEMA)

ALLOWED_RESOURCE_TYPES = {
    "aws_s3_bucket",
    "aws_s3_bucket_versioning",
    "aws_s3_bucket_server_side_encryption_configuration",
    "aws_s3_bucket_public_access_block",
    "aws_vpc",
    "aws_subnet",
    "aws_route_table",
    "aws_internet_gateway",
    "aws_nat_gateway",
    "aws_lambda_function",
    "aws_apigatewayv2_api",
    "aws_dynamodb_table"
}

def validate_plan(plan: dict) -> dict:
    # Validate against JSON schema first
    errors = list(validator.iter_errors(plan))

    # If schema validation fails, return early with those errors
    if errors:
        raise PlanRejectedError(
            "Infrastructure plan failed schema validation",
            details=[e.message for e in errors]
        )

    if plan.get("status") != "approved":
        raise PlanRejectedError("Plan was not approved")

    # Additional business logic validation
    # (Schema already handles region: ap-south-1, but we can add more here)

    for resource in plan.get("resources", []):
        if resource.get("type") not in ALLOWED_RESOURCE_TYPES:
            errors.append(
                _error(
                    resource.get("name", "unknown"),
                    f"Resource type not allowed: {resource.get('type')}"
                )
            )

    if errors:
        raise PlanRejectedError(
            "Infrastructure plan failed business validation",
            details=[e.message for e in errors]
        )

    return plan

def _error(resource: str, message: str):
    class Error:
        def __init__(self, msg):
            self.message = msg
            self.path = []
    return Error(f"{resource}: {message}")

class PlanRejectedError(Exception):
    def __init__(self, message, details=None):
        super().__init__(message)
        self.details = details
