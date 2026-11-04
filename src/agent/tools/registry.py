# src/agent/tools/registry.py
import json
import os
from typing import Any, Dict, List

from src.agent.validators.plan_validator import validate_plan, PlanRejectedError
from src.agent.tools.generate_terraform import generate_terraform
from src.agent.tools.validate_terraform import validate_terraform as _core_validate_terraform

APPROVED_MODULES = {
    "UC1": {
        "use_case": "UC1",
        "description": "Encrypted, versioned, private S3 bucket",
        "approved_resources": [
            "aws_s3_bucket",
            "aws_s3_bucket_versioning",
            "aws_s3_bucket_server_side_encryption_configuration",
            "aws_s3_bucket_public_access_block",
        ],
    },
    "UC2": {
        "use_case": "UC2",
        "description": "VPC with public and private subnets",
        "approved_resources": [
            "aws_vpc",
            "aws_subnet",
            "aws_route_table",
            "aws_internet_gateway",
            "aws_nat_gateway",
        ],
    },
    "UC3": {
        "use_case": "UC3",
        "description": "Lambda + API Gateway + DynamoDB",
        "approved_resources": [
            "aws_lambda_function",
            "aws_apigatewayv2_api",
            "aws_dynamodb_table",
        ],
    },
}

def get_approved_modules(use_case: str) -> dict:
    """
    Returns approved module metadata for the given use case (UC1, UC2, UC3).
    """
    if use_case not in APPROVED_MODULES:
        raise ValueError(
            f"Unknown or unapproved use case: {use_case}. Allowed: {list(APPROVED_MODULES.keys())}"
        )
    return APPROVED_MODULES[use_case]

def validate_terraform(files: dict) -> dict:
    """
    Runs terraform fmt -check and terraform validate in an isolated temporary directory.
    """
    if not isinstance(files, dict) or not files:
        raise ValueError("files argument must be a non-empty dictionary of filename -> content.")

    res = _core_validate_terraform(files=files)
    return {
        "status": "success" if res["valid"] else "failed",
        "fmt_passed": res["fmt_passed"],
        "validate_passed": res["validate_passed"],
        "errors": res.get("errors", []),
        "details": res.get("details", "")
    }

def summarise_plan(plan: dict) -> dict:
    """
    Creates a human-readable approval summary for an infrastructure plan.
    """
    validated_plan = validate_plan(plan)
    status = validated_plan.get("status", "unknown")
    reason = validated_plan.get("reason", "No reason provided")
    region = validated_plan.get("region", "ap-south-1")
    resources = validated_plan.get("resources", [])

    resource_summaries = []
    for r in resources:
        r_name = r.get("name")
        r_type = r.get("type")
        r_tags = r.get("tags", {})
        resource_summaries.append(
            f"- Resource: {r_name} (Type: {r_type}, Tags: {list(r_tags.keys())})"
        )

    summary_text = (
        f"Infrastructure Plan Approval Summary:\n"
        f"Status: {status.upper()}\n"
        f"Region: {region}\n"
        f"Reason: {reason}\n"
        f"Total Resources: {len(resources)}\n"
        f"Resources:\n" + "\n".join(resource_summaries) + "\n"
        f"Security Checks: Passed (Encryption, Versioning, Public Access Blocked, Mandatory Tags)."
    )

    return {
        "status": "summarised",
        "summary": summary_text,
        "region": region,
        "resource_count": len(resources),
    }

TOOL_REGISTRY: Dict[str, Any] = {
    "get_approved_modules": get_approved_modules,
    "generate_terraform": generate_terraform,
    "validate_terraform": validate_terraform,
    "summarise_plan": summarise_plan,
}

def get_tool_specs() -> List[dict]:
    """
    Returns Bedrock tool specifications for all registered allowed tools.
    """
    return [
        {
            "toolSpec": {
                "name": "get_approved_modules",
                "description": "Get approved infrastructure module metadata and resources for a specific use case (UC1, UC2, UC3).",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "use_case": {
                                "type": "string",
                                "enum": ["UC1", "UC2", "UC3"],
                                "description": "The use case identifier.",
                            }
                        },
                        "required": ["use_case"],
                    }
                },
            }
        },
        {
            "toolSpec": {
                "name": "generate_terraform",
                "description": "Convert a validated UC1 JSON infrastructure plan into deterministic approved Terraform configuration files.",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "plan": {
                                "type": "object",
                                "description": "The validated infrastructure plan JSON dictionary.",
                            }
                        },
                        "required": ["plan"],
                    }
                },
            }
        },
        {
            "toolSpec": {
                "name": "validate_terraform",
                "description": "Run terraform fmt -check and terraform validate on generated Terraform files in an isolated temporary directory.",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "files": {
                                "type": "object",
                                "description": "Dictionary mapping filename (e.g. main.tf) to file content string.",
                                "additionalProperties": {"type": "string"},
                            }
                        },
                        "required": ["files"],
                    }
                },
            }
        },
        {
            "toolSpec": {
                "name": "summarise_plan",
                "description": "Create a human-readable approval summary for an infrastructure plan.",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "plan": {
                                "type": "object",
                                "description": "The infrastructure plan JSON dictionary.",
                            }
                        },
                        "required": ["plan"],
                    }
                },
            }
        },
    ]

def execute_tool(tool_name: str, tool_input: dict, tool_use_id: str) -> dict:
    """
    Executes a tool call and returns a Bedrock toolResult format:
    {"toolUseId": tool_use_id, "content": [{"json": result_data}], "status": "success"/"error"}
    """
    forbidden_tools = {
        "apply_terraform",
        "destroy_terraform",
        "assume_deployment_role",
        "approve_deployment",
    }

    if tool_name in forbidden_tools or tool_name not in TOOL_REGISTRY:
        return {
            "toolUseId": tool_use_id,
            "content": [{"json": {"error": f"Tool not found or forbidden: {tool_name}"}}],
            "status": "error",
        }

    if not isinstance(tool_input, dict):
        return {
            "toolUseId": tool_use_id,
            "content": [{"json": {"error": "Tool input must be a dictionary."}}],
            "status": "error",
        }

    tool_func = TOOL_REGISTRY[tool_name]

    try:
        if tool_name == "get_approved_modules":
            if "use_case" not in tool_input:
                raise ValueError("Missing required argument 'use_case' for get_approved_modules.")
        elif tool_name in ("generate_terraform", "summarise_plan"):
            if "plan" not in tool_input:
                raise ValueError(f"Missing required argument 'plan' for {tool_name}.")
        elif tool_name == "validate_terraform":
            if "files" not in tool_input:
                raise ValueError("Missing required argument 'files' for validate_terraform.")

        result_data = tool_func(**tool_input)
        return {
            "toolUseId": tool_use_id,
            "content": [{"json": result_data}],
            "status": "success",
        }
    except Exception as e:
        return {
            "toolUseId": tool_use_id,
            "content": [{"json": {"error": str(e)}}],
            "status": "error",
        }
