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
                },
                "encryption_enabled": True,
                "versioning_enabled": True,
                "public_access_blocked": True
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

def test_s3_bucket_missing_encryption():
    plan = {
        "status": "approved",
        "reason": "S3 bucket missing encryption",
        "region": "ap-south-1",
        "resources": [
            {
                "name": "my-bucket",
                "type": "aws_s3_bucket",
                "tags": {
                    "project": "ai-infra",
                    "environment": "dev",
                    "owner": "platform-team",
                    "cost-center": "123",
                    "managed-by": "claude"
                },
                "versioning_enabled": True,
                "public_access_blocked": True
            }
        ]
    }
    with pytest.raises(PlanRejectedError) as exc:
        validate_plan(plan)
    assert "S3 bucket must have server-side encryption enabled." in str(exc.value.details[0])

def test_s3_bucket_missing_versioning():
    plan = {
        "status": "approved",
        "reason": "S3 bucket missing versioning",
        "region": "ap-south-1",
        "resources": [
            {
                "name": "my-bucket",
                "type": "aws_s3_bucket",
                "tags": {
                    "project": "ai-infra",
                    "environment": "dev",
                    "owner": "platform-team",
                    "cost-center": "123",
                    "managed-by": "claude"
                },
                "encryption_enabled": True,
                "public_access_blocked": True
            }
        ]
    }
    with pytest.raises(PlanRejectedError) as exc:
        validate_plan(plan)
    assert "S3 bucket must have versioning enabled." in str(exc.value.details[0])

def test_s3_bucket_public_access_not_blocked():
    plan = {
        "status": "approved",
        "reason": "S3 bucket public access not blocked",
        "region": "ap-south-1",
        "resources": [
            {
                "name": "my-bucket",
                "type": "aws_s3_bucket",
                "tags": {
                    "project": "ai-infra",
                    "environment": "dev",
                    "owner": "platform-team",
                    "cost-center": "123",
                    "managed-by": "claude"
                },
                "encryption_enabled": True,
                "versioning_enabled": True,
                "public_access_blocked": False
            }
        ]
    }
    with pytest.raises(PlanRejectedError) as exc:
        validate_plan(plan)
    assert "Public S3 access is strictly prohibited (N1 control)." in str(exc.value.details[0])

def test_s3_bucket_explicit_public_access_rejected():
    plan = {
        "status": "approved",
        "reason": "S3 bucket explicit public access requested",
        "region": "ap-south-1",
        "resources": [
            {
                "name": "my-bucket",
                "type": "aws_s3_bucket",
                "tags": {
                    "project": "ai-infra",
                    "environment": "dev",
                    "owner": "platform-team",
                    "cost-center": "123",
                    "managed-by": "claude"
                },
                "encryption_enabled": True,
                "versioning_enabled": True,
                "public_access": True,
                "public_access_blocked": False
            }
        ]
    }
    with pytest.raises(PlanRejectedError) as exc:
        validate_plan(plan)
    assert "Public S3 access is strictly prohibited (N1 control)." in str(exc.value.details[0])
