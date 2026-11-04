# tests/test_tool_registry.py
import pytest
from src.agent.tools.registry import (
    TOOL_REGISTRY,
    get_tool_specs,
    execute_tool,
    get_approved_modules,
    generate_terraform,
    validate_terraform,
    summarise_plan,
)

def test_tool_registry_and_specs_consistency():
    """
    Verify TOOL_REGISTRY dict and get_tool_specs() list contain EXACTLY the same tool names.
    """
    registry_names = set(TOOL_REGISTRY.keys())
    spec_names = set(spec["toolSpec"]["name"] for spec in get_tool_specs())

    assert registry_names == spec_names
    assert len(registry_names) == 4
    expected_tools = {"get_approved_modules", "generate_terraform", "validate_terraform", "summarise_plan"}
    assert registry_names == expected_tools

def test_forbidden_tools_excluded():
    """
    Verify forbidden tools are NOT in TOOL_REGISTRY or get_tool_specs().
    """
    forbidden_tools = {
        "apply_terraform",
        "destroy_terraform",
        "assume_deployment_role",
        "approve_deployment",
    }
    registry_names = set(TOOL_REGISTRY.keys())
    spec_names = set(spec["toolSpec"]["name"] for spec in get_tool_specs())

    for tool in forbidden_tools:
        assert tool not in registry_names
        assert tool not in spec_names

def test_execute_tool_invalid_name():
    """
    Verify tool execution handles invalid or forbidden tool name correctly.
    """
    result = execute_tool("apply_terraform", {}, "tool_use_1")
    assert result["status"] == "error"
    assert "error" in result["content"][0]["json"]
    assert result["toolUseId"] == "tool_use_1"

    result_unknown = execute_tool("nonexistent_tool", {}, "tool_use_2")
    assert result_unknown["status"] == "error"
    assert "error" in result_unknown["content"][0]["json"]

def test_execute_tool_invalid_args():
    """
    Verify tool execution handles invalid arguments correctly.
    """
    # Missing required argument 'use_case'
    result = execute_tool("get_approved_modules", {}, "tool_use_3")
    assert result["status"] == "error"
    assert "error" in result["content"][0]["json"]

    # Invalid input type (not a dict)
    result_non_dict = execute_tool("get_approved_modules", "not-a-dict", "tool_use_4")
    assert result_non_dict["status"] == "error"

def test_execute_tool_valid_call_get_approved_modules():
    """
    Verify valid tool execution for get_approved_modules.
    """
    result = execute_tool("get_approved_modules", {"use_case": "UC1"}, "tool_use_5")
    assert result["status"] == "success"
    assert "UC1" in result["content"][0]["json"]["use_case"]
    assert "aws_s3_bucket" in result["content"][0]["json"]["approved_resources"]

def test_valid_uc1_terraform_generation_and_validation():
    """
    Verify generate_terraform and validate_terraform handle valid UC1 plan correctly.
    """
    plan = {
        "status": "approved",
        "reason": "Deploy secure S3 bucket for UC1",
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

    # 1. Test generate_terraform via execute_tool
    gen_result = execute_tool("generate_terraform", {"plan": plan}, "tool_use_6")
    assert gen_result["status"] == "success"
    files = gen_result["content"][0]["json"]["files"]
    assert "main.tf" in files
    assert "variables.tf" in files
    assert "outputs.tf" in files

    # 2. Test validate_terraform via execute_tool
    val_result = execute_tool("validate_terraform", {"files": files}, "tool_use_7")
    assert val_result["status"] == "success"
    assert val_result["content"][0]["json"]["fmt_passed"] is True
    assert val_result["content"][0]["json"]["validate_passed"] is True

def test_execute_tool_summarise_plan():
    """
    Verify summarise_plan execution.
    """
    plan = {
        "status": "approved",
        "reason": "Summary test",
        "region": "ap-south-1",
        "resources": [
            {
                "name": "summary-bucket",
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
    result = execute_tool("summarise_plan", {"plan": plan}, "tool_use_8")
    assert result["status"] == "success"
    assert "Infrastructure Plan Approval Summary" in result["content"][0]["json"]["summary"]
    assert result["content"][0]["json"]["resource_count"] == 1
