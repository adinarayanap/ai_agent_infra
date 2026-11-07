import pytest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../src/agent")
    )
)

from tools.generate_terraform import generate_terraform
from tools.validate_terraform import validate_terraform

def get_valid_uc3_plan():
    return {
        "status": "approved",
        "use_case": "UC3",
        "region": "ap-south-1",
        "resources": [
            {
                "type": "aws_dynamodb_table",
                "name": "app-table",
                "hash_key": "id",
                "billing_mode": "PAY_PER_REQUEST",
                "attribute_definitions": [{"name": "id", "type": "S"}],
                "server_side_encryption": True,
                "point_in_time_recovery": True,
                "tags": {"project": "ai", "environment": "dev", "owner": "me", "cost-center": "1", "managed-by": "claude"}
            },
            {
                "type": "aws_lambda_function",
                "name": "app-func",
                "runtime": "python3.12",
                "handler": "handler.handler",
                "memory_size": 256,
                "timeout": 30,
                "iam_role": "lambda-role",
                "iam_policy": "lambda-policy",
                "tags": {"project": "ai", "environment": "dev", "owner": "me", "cost-center": "1", "managed-by": "claude"}
            },
            {
                "type": "aws_apigatewayv2_api",
                "name": "app-api",
                "protocol_type": "HTTP",
                "https_only": True,
                "integration": {"type": "AWS_PROXY", "target": "app-func"},
                "route": {"route_key": "ANY /", "target": "app-func"},
                "tags": {"project": "ai", "environment": "dev", "owner": "me", "cost-center": "1", "managed-by": "claude"}
            },
            {
                "type": "aws_iam_role",
                "name": "lambda-role",
                "tags": {"project": "ai", "environment": "dev", "owner": "me", "cost-center": "1", "managed-by": "claude"}
            },
            {
                "type": "aws_iam_policy",
                "name": "lambda-policy",
                "policy_document": {
                    "statements": [
                        {"effect": "Allow", "actions": ["dynamodb:GetItem", "dynamodb:PutItem", "logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"], "resources": ["app-table", "/aws/lambda/app-func"]}
                    ]
                },
                "tags": {"project": "ai", "environment": "dev", "owner": "me", "cost-center": "1", "managed-by": "claude"}
            }
        ]
    }

def test_hcl_generation_success():
    plan = get_valid_uc3_plan()
    result = generate_terraform(plan)
    hcl = result["files"]["main.tf"]

    # Resources
    assert 'resource "aws_dynamodb_table" "this"' in hcl
    assert 'resource "aws_lambda_function" "this"' in hcl
    assert 'resource "aws_apigatewayv2_api" "this"' in hcl
    assert 'resource "aws_lambda_permission"' in hcl
    assert 'principal     = "apigateway.amazonaws.com"' in hcl

    # Mandatory Tags
    assert 'tags = var.tags' in hcl

    # Scoped IAM Policy Document
    policy_doc = hcl.split('data "aws_iam_policy_document" "lambda_policy"')[1]
    assert '"dynamodb:GetItem"' in policy_doc
    assert '"logs:PutLogEvents"' in policy_doc
    assert '"*"' not in policy_doc

    # No Secrets/Hardcoded
    assert "arn:aws:iam::" not in hcl
    assert "AKIA" not in hcl
    assert "SECRET" not in hcl.upper()

def test_terraform_fmt_failure_surfaced():
    files = {"main.tf": "invalid hcl content"}
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stderr="Error: Expected identifier")
        result = validate_terraform(files)
        assert result["valid"] is False
        assert "Error: Expected identifier" in result["errors"]
