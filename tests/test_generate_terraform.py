import pytest
import os
from src.agent.tools.generate_terraform import generate_terraform, TerraformGenerationError
from src.agent.validators.plan_validator import PlanRejectedError

def test_valid_uc1_generation():
    plan = {
        "status": "approved",
        "reason": "Approved UC1 S3 bucket plan",
        "region": "ap-south-1",
        "resources": [
            {
                "name": "secure-data-bucket",
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
    result = generate_terraform(plan)
    assert result["status"] == "success"
    assert "files" in result
    assert "main.tf" in result["files"]
    assert "variables.tf" in result["files"]
    assert "outputs.tf" in result["files"]

    main_tf = result["files"]["main.tf"]

    # Verify required S3 security resources are present
    assert 'resource "aws_s3_bucket"' in main_tf
    assert 'resource "aws_s3_bucket_versioning"' in main_tf
    assert 'resource "aws_s3_bucket_server_side_encryption_configuration"' in main_tf
    assert 'resource "aws_s3_bucket_public_access_block"' in main_tf

    # Verify mandatory tags are present in resource
    assert 'project     = var.project' in main_tf or 'project' in main_tf
    assert 'environment = var.environment' in main_tf or 'environment' in main_tf
    assert 'owner       = var.owner' in main_tf or 'owner' in main_tf
    assert 'cost-center = var.cost_center' in main_tf or 'cost-center' in main_tf
    assert 'managed-by  = var.managed_by' in main_tf or 'managed-by' in main_tf

    # Verify state backend uses use_lockfile = true
    assert 'use_lockfile = true' in main_tf

    # Verify public access block settings (No public access / ACLs)
    assert 'block_public_acls       = true' in main_tf
    assert 'block_public_policy     = true' in main_tf
    assert 'ignore_public_acls      = true' in main_tf
    assert 'restrict_public_buckets = true' in main_tf

def test_missing_mandatory_tags_raises_error():
    plan = {
        "status": "approved",
        "reason": "Missing owner tag",
        "region": "ap-south-1",
        "resources": [
            {
                "name": "secure-data-bucket",
                "type": "aws_s3_bucket",
                "tags": {
                    "project": "ai-infra",
                    "environment": "dev",
                    # "owner": missing!
                    "cost-center": "123",
                    "managed-by": "claude"
                },
                "encryption_enabled": True,
                "versioning_enabled": True,
                "public_access_blocked": True
            }
        ]
    }
    with pytest.raises(TerraformGenerationError) as exc:
        generate_terraform(plan)
    assert "Missing mandatory tags" in str(exc.value)

def test_missing_encryption_raises_error():
    plan = {
        "status": "approved",
        "reason": "Missing encryption",
        "region": "ap-south-1",
        "resources": [
            {
                "name": "secure-data-bucket",
                "type": "aws_s3_bucket",
                "tags": {
                    "project": "ai-infra",
                    "environment": "dev",
                    "owner": "platform-team",
                    "cost-center": "123",
                    "managed-by": "claude"
                },
                "encryption_enabled": False,
                "versioning_enabled": True,
                "public_access_blocked": True
            }
        ]
    }
    with pytest.raises(TerraformGenerationError) as exc:
        generate_terraform(plan)
    assert "S3 bucket must have server-side encryption enabled." in str(exc.value)

def test_missing_versioning_raises_error():
    plan = {
        "status": "approved",
        "reason": "Missing versioning",
        "region": "ap-south-1",
        "resources": [
            {
                "name": "secure-data-bucket",
                "type": "aws_s3_bucket",
                "tags": {
                    "project": "ai-infra",
                    "environment": "dev",
                    "owner": "platform-team",
                    "cost-center": "123",
                    "managed-by": "claude"
                },
                "encryption_enabled": True,
                "versioning_enabled": False,
                "public_access_blocked": True
            }
        ]
    }
    with pytest.raises(TerraformGenerationError) as exc:
        generate_terraform(plan)
    assert "S3 bucket must have versioning enabled." in str(exc.value)

def test_public_access_not_blocked_raises_error():
    plan = {
        "status": "approved",
        "reason": "Public access not blocked",
        "region": "ap-south-1",
        "resources": [
            {
                "name": "secure-data-bucket",
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
    with pytest.raises(TerraformGenerationError) as exc:
        generate_terraform(plan)
    assert "S3 bucket must have public access blocked." in str(exc.value)
