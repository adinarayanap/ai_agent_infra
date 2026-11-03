import pytest
from src.agent.validators.plan_validator import validate_plan, PlanRejectedError

def test_valid_plan():
    plan = {
        "status": "approved",
        "reason": "Test approval",
        "region": "ap-south-1",
        "resources": [
            {
                "name": "test-bucket",
                "type": "aws_s3_bucket",
                "tags": {
                    "project": "ai-infra",
                    "environment": "dev",
                    "owner": "platform-team",
                    "cost-center": "123",
                    "managed-by": "claude"
                }
            }
        ]
    }
    assert validate_plan(plan) == plan

def test_invalid_region():
    plan = {
        "status": "approved",
        "reason": "Invalid region",
        "region": "us-east-1",
        "resources": []
    }
    with pytest.raises(PlanRejectedError) as exc:
        validate_plan(plan)
    assert "'ap-south-1' was expected" in str(exc.value.details[0])

def test_invalid_resource():
    plan = {
        "status": "approved",
        "reason": "Invalid resource",
        "region": "ap-south-1",
        "resources": [
            {
                "name": "bad-resource",
                "type": "aws_ec2_instance",
                "tags": {
                    "project": "ai-infra",
                    "environment": "dev",
                    "owner": "platform-team",
                    "cost-center": "123",
                    "managed-by": "claude"
                }
            }
        ]
    }
    with pytest.raises(PlanRejectedError) as exc:
        validate_plan(plan)
    assert "Resource type not allowed" in str(exc.value.details[0])
