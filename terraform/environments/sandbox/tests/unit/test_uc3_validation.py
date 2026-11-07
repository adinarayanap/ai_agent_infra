import pytest
import sys
import os

sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../src")
    )
)

from agent.validators.plan_validator import validate_plan, PlanRejectedError

def get_valid_uc3_plan():
    return {
        "status": "approved",
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

def test_uc3_plan_valid():
    assert validate_plan(get_valid_uc3_plan()) == get_valid_uc3_plan()

def test_uc3_missing_lambda():
    plan = get_valid_uc3_plan()
    plan["resources"] = [r for r in plan["resources"] if r["type"] != "aws_lambda_function"]
    with pytest.raises(PlanRejectedError):
        validate_plan(plan)

def test_uc3_missing_apigw():
    plan = get_valid_uc3_plan()
    plan["resources"] = [r for r in plan["resources"] if r["type"] != "aws_apigatewayv2_api"]
    with pytest.raises(PlanRejectedError):
        validate_plan(plan)

def test_uc3_missing_dynamo():
    plan = get_valid_uc3_plan()
    plan["resources"] = [r for r in plan["resources"] if r["type"] != "aws_dynamodb_table"]
    with pytest.raises(PlanRejectedError):
        validate_plan(plan)

def test_uc3_missing_iam_role_or_policy():
    plan = get_valid_uc3_plan()
    plan["resources"] = [r for r in plan["resources"] if r["type"] not in ["aws_iam_role", "aws_iam_policy"]]
    with pytest.raises(PlanRejectedError):
        validate_plan(plan)

def test_uc3_missing_mandatory_tags():
    plan = get_valid_uc3_plan()
    plan["resources"][0]["tags"] = {}
    with pytest.raises(PlanRejectedError):
        validate_plan(plan)

def test_uc3_encryption_false_fails():
    plan = get_valid_uc3_plan()
    plan["resources"][0]["server_side_encryption"] = False
    with pytest.raises(PlanRejectedError):
        validate_plan(plan)

def test_uc3_pitr_false_fails():
    plan = get_valid_uc3_plan()
    plan["resources"][0]["point_in_time_recovery"] = False
    with pytest.raises(PlanRejectedError):
        validate_plan(plan)

def test_uc3_apigw_https_false_fails():
    plan = get_valid_uc3_plan()
    plan["resources"][2]["https_only"] = False
    with pytest.raises(PlanRejectedError):
        validate_plan(plan)

def test_uc3_iam_wildcard_fails():
    plan = get_valid_uc3_plan()
    plan["resources"][4]["policy_document"]["statements"][0]["actions"] = ["dynamodb:*"]
    with pytest.raises(PlanRejectedError):
        validate_plan(plan)

def test_uc3_iam_user_creation_fails():
    plan = get_valid_uc3_plan()
    plan["resources"].append({"type": "aws_iam_user", "name": "bad-user", "tags": plan["resources"][0]["tags"]})
    with pytest.raises(PlanRejectedError):
        validate_plan(plan)

def test_uc3_hardcoded_id_fails():
    plan = get_valid_uc3_plan()
    plan["resources"][4]["policy_document"]["statements"][0]["resources"] = ["arn:aws:dynamodb:ap-south-1:123456789012:table/hardcoded-table"]
    with pytest.raises(PlanRejectedError):
        validate_plan(plan)
