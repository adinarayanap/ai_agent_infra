import pytest
import json
import sys
import os
from unittest.mock import MagicMock, patch

sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../src")
    )
)

from agent.handler import handler
from agent.validators.plan_validator import PlanRejectedError

def get_valid_uc3_plan():
    return {
        "status": "approved", "use_case": "UC3", "region": "ap-south-1",
        "resources": [
            {"type": "aws_dynamodb_table", "name": "app-table", "hash_key": "id", "billing_mode": "PAY_PER_REQUEST", "attribute_definitions": [{"name": "id", "type": "S"}], "server_side_encryption": True, "point_in_time_recovery": True, "tags": {"project": "ai", "environment": "dev", "owner": "me", "cost-center": "1", "managed-by": "claude"}},
            {"type": "aws_lambda_function", "name": "app-func", "runtime": "python3.12", "handler": "handler.handler", "memory_size": 256, "timeout": 30, "iam_role": "lambda-role", "iam_policy": "lambda-policy", "tags": {"project": "ai", "environment": "dev", "owner": "me", "cost-center": "1", "managed-by": "claude"}},
            {"type": "aws_apigatewayv2_api", "name": "app-api", "protocol_type": "HTTP", "https_only": True, "integration": {"type": "AWS_PROXY", "target": "app-func"}, "route": {"route_key": "ANY /", "target": "app-func"}, "tags": {"project": "ai", "environment": "dev", "owner": "me", "cost-center": "1", "managed-by": "claude"}},
            {"type": "aws_iam_role", "name": "lambda-role", "tags": {"project": "ai", "environment": "dev", "owner": "me", "cost-center": "1", "managed-by": "claude"}},
            {"type": "aws_iam_policy", "name": "lambda-policy", "policy_document": {"statements": [{"effect": "Allow", "actions": ["dynamodb:GetItem", "dynamodb:PutItem", "logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"], "resources": ["app-table", "/aws/lambda/app-func"]}]}, "tags": {"project": "ai", "environment": "dev", "owner": "me", "cost-center": "1", "managed-by": "claude"}}
        ]
    }

@pytest.fixture
def mock_env():
    bedrock = MagicMock()
    table = MagicMock()
    with patch("agent.handler.get_clients", return_value=(bedrock, table)):
        yield bedrock, table

def test_orchestration_1st_attempt_success(mock_env):
    bedrock, _ = mock_env
    bedrock.converse.return_value = {"output": {"message": {"content": [{"text": json.dumps(get_valid_uc3_plan())}]}}}
    with patch("agent.handler.validate_terraform", return_value={"valid": True, "errors": []}):
        assert handler({"body": json.dumps({"prompt": "create UC3"})}, MagicMock(aws_request_id="r1"))["statusCode"] == 200

def test_orchestration_retry_success(mock_env):
    bedrock, _ = mock_env
    bedrock.converse.return_value = {"output": {"message": {"content": [{"text": json.dumps(get_valid_uc3_plan())}]}}}
    with patch("agent.handler.validate_terraform", side_effect=[{"valid": False, "errors": ["e"]}, {"valid": True, "errors": []}]):
        assert handler({"body": json.dumps({"prompt": "create UC3"})}, MagicMock(aws_request_id="r2"))["statusCode"] == 200

def test_orchestration_3rd_success(mock_env):
    bedrock, _ = mock_env
    bedrock.converse.return_value = {"output": {"message": {"content": [{"text": json.dumps(get_valid_uc3_plan())}]}}}
    with patch("agent.handler.validate_terraform", side_effect=[{"valid": False, "errors": ["e1"]}, {"valid": False, "errors": ["e2"]}, {"valid": True, "errors": []}]):
        assert handler({"body": json.dumps({"prompt": "create UC3"})}, MagicMock(aws_request_id="r3"))["statusCode"] == 200

def test_orchestration_3rd_fail_validation_failed(mock_env):
    bedrock, _ = mock_env
    bedrock.converse.return_value = {"output": {"message": {"content": [{"text": json.dumps(get_valid_uc3_plan())}]}}}
    with patch("agent.handler.validate_terraform", return_value={"valid": False, "errors": ["e1"]}):
        response = handler({"body": json.dumps({"prompt": "create UC3"})}, MagicMock(aws_request_id="r4"))
        assert response["statusCode"] == 422
        assert json.loads(response["body"])["status"] == "validation_failed"

def test_orchestration_no_4th_model_call(mock_env):
    bedrock, _ = mock_env
    bedrock.converse.return_value = {"output": {"message": {"content": [{"text": json.dumps(get_valid_uc3_plan())}]}}}
    with patch("agent.handler.validate_terraform", return_value={"valid": False, "errors": ["e"]}):
        handler({"body": json.dumps({"prompt": "create UC3"})}, MagicMock(aws_request_id="r5"))
        assert bedrock.converse.call_count == 3

def test_orchestration_exact_tf_error_feedback(mock_env):
    bedrock, _ = mock_env
    bedrock.converse.return_value = {"output": {"message": {"content": [{"text": json.dumps(get_valid_uc3_plan())}]}}}
    with patch("agent.handler.validate_terraform", return_value={"valid": False, "errors": ["syntax error"]}):
        response = handler({"body": json.dumps({"prompt": "create UC3"})}, MagicMock(aws_request_id="r6"))
        assert "syntax error" in response["body"]

def test_orchestration_scoped_retry_counter(mock_env):
    bedrock, _ = mock_env
    bedrock.converse.return_value = {"output": {"message": {"content": [{"text": json.dumps(get_valid_uc3_plan())}]}}}
    with patch("agent.handler.validate_terraform", side_effect=[
        {"valid": False, "errors": ["e"]}, {"valid": True, "errors": []},
        {"valid": False, "errors": ["e"]}, {"valid": True, "errors": []}
    ]):
        first = handler({"body": json.dumps({"prompt": "c1"})}, MagicMock(aws_request_id="req-a"))
        second = handler({"body": json.dumps({"prompt": "c2"})}, MagicMock(aws_request_id="req-b"))
    assert first["statusCode"] == 200
    assert second["statusCode"] == 200
    assert bedrock.converse.call_count == 4

def test_orchestration_json_validation_before_gen(mock_env):
    with patch("agent.handler.validate_plan", side_effect=PlanRejectedError("Invalid JSON")), \
         patch("agent.handler.generate_terraform") as mock_gen:
        response = handler({"body": json.dumps({"prompt": "create UC3"})}, MagicMock(aws_request_id="req-json"))
        assert response["statusCode"] == 422
        mock_gen.assert_not_called()

def test_orchestration_guardrail_403_blocked(mock_env):
    bedrock, table = mock_env
    bedrock.converse.return_value = {"stopReason": "guardrail_intervened"}
    response = handler({"body": json.dumps({"prompt": "bad"})}, MagicMock(aws_request_id="req-guard"))
    assert response["statusCode"] == 403
    table.put_item.assert_called()
    assert table.put_item.call_args[1]["Item"]["Status"] == "BLOCKED"
