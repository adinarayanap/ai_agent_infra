"""Validation for UC3 infrastructure plans."""

import re


class PlanRejectedError(Exception):
    """Raised when an infrastructure plan violates UC3 requirements."""


REQUIRED_RESOURCE_TYPES = (
    "aws_dynamodb_table",
    "aws_lambda_function",
    "aws_apigatewayv2_api",
    "aws_iam_role",
    "aws_iam_policy",
)

FORBIDDEN_RESOURCE_TYPES = (
    "aws_iam_user",
)

ACCOUNT_ID_PATTERN = re.compile(r"\b\d{12}\b")


def validate_plan(plan: dict) -> dict:
    """Validate a UC3 infrastructure plan before Terraform generation."""
    if not isinstance(plan, dict):
        raise PlanRejectedError("Plan must be a JSON object.")

    if plan.get("status") != "approved":
        raise PlanRejectedError("Plan status must be approved.")


    resources = plan.get("resources")
    if not isinstance(resources, list) or not resources:
        raise PlanRejectedError("Plan must contain resources.")

    resource_types = [resource.get("type") for resource in resources]

    missing_types = [
        resource_type
        for resource_type in REQUIRED_RESOURCE_TYPES
        if resource_type not in resource_types
    ]
    if missing_types:
        raise PlanRejectedError(
            "Missing required resource types: " + ", ".join(missing_types)
        )

    forbidden_types = [
        resource_type
        for resource_type in resource_types
        if resource_type in FORBIDDEN_RESOURCE_TYPES
    ]
    if forbidden_types:
        raise PlanRejectedError(
            "Forbidden resource types: " + ", ".join(forbidden_types)
        )

    for resource in resources:
        tags = resource.get("tags")
        if not isinstance(tags, dict) or not tags:
            raise PlanRejectedError(
                f"Resource {resource.get('name')} is missing mandatory tags."
            )

    dynamodb_table = next(
        resource
        for resource in resources
        if resource.get("type") == "aws_dynamodb_table"
    )
    if dynamodb_table.get("server_side_encryption") is not True:
        raise PlanRejectedError(
            "DynamoDB table must enable server-side encryption."
        )
    if dynamodb_table.get("point_in_time_recovery") is not True:
        raise PlanRejectedError(
            "DynamoDB table must enable point-in-time recovery."
        )

    api = next(
        resource
        for resource in resources
        if resource.get("type") == "aws_apigatewayv2_api"
    )
    if api.get("https_only") is not True:
        raise PlanRejectedError("API Gateway must enforce HTTPS only.")

    iam_policy = next(
        resource
        for resource in resources
        if resource.get("type") == "aws_iam_policy"
    )
    statements = iam_policy.get("policy_document", {}).get("statements", [])

    for statement in statements:
        actions = statement.get("actions", [])
        if any("*" in action for action in actions):
            raise PlanRejectedError("IAM policy must not use wildcard actions.")

        for resource_arn in statement.get("resources", []):
            if (
                isinstance(resource_arn, str)
                and ACCOUNT_ID_PATTERN.search(resource_arn)
            ):
                raise PlanRejectedError(
                    "IAM policy must not contain a hardcoded AWS account ID."
                )

    return plan
