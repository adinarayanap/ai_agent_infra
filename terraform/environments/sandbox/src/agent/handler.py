import json
import logging
import os
import time

import boto3

from agent.modules.approved_modules import get_module_by_prompt
from agent.tools.generate_terraform import generate_terraform
from agent.tools.validate_terraform import validate_terraform
from agent.validators.plan_validator import PlanRejectedError, validate_plan

logger = logging.getLogger()
logger.setLevel(logging.INFO)

BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "ap-south-1")
MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID",
    "mistral.mistral-large-3-675b-instruct",
)
GUARDRAIL_ID = os.environ.get("GUARDRAIL_ID")
GUARDRAIL_VERSION = os.environ.get("GUARDRAIL_VERSION")
AUDIT_TABLE_NAME = os.environ.get("AUDIT_TABLE_NAME")

MAX_GENERATION_ATTEMPTS = 3

bedrock = None
table = None


def get_clients():
    global bedrock, table

    if bedrock is None:
        bedrock = boto3.client(
            "bedrock-runtime",
            region_name=BEDROCK_REGION,
        )

    if table is None:
        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(AUDIT_TABLE_NAME)

    return bedrock, table


def load_system_prompt():
    prompt_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "agents",
        "prompts",
        "system_prompt.txt",
    )

    with open(prompt_path, "r") as prompt_file:
        return prompt_file.read()


def build_retrieval_context(module):
    if not module:
        return ""

    constraints = "\n".join(
        f"- {constraint}"
        for constraint in module.get("security_constraints", [])
    )
    tags = ", ".join(module.get("required_tags", []))
    resources = ", ".join(module.get("allowed_resource_types", []))

    return (
        "\n\nApproved module context:\n"
        f"Module: {module.get('module_name')}\n"
        f"Description: {module.get('description')}\n"
        f"Approved use cases: "
        f"{', '.join(module.get('approved_use_cases', []))}\n"
        f"Security constraints:\n{constraints}\n"
        f"Required tags: {tags}\n"
        f"Allowed resource types: {resources}\n"
        f"Usage guidance: {module.get('usage_guidance')}\n"
        "Use only this approved module and obey all constraints."
    )


def build_converse_kwargs(user_content):
    return {
        "modelId": MODEL_ID,
        "system": [{"text": load_system_prompt()}],
        "messages": [
            {
                "role": "user",
                "content": [{"text": user_content}],
            }
        ],
        "inferenceConfig": {
            "maxTokens": 1000,
            "temperature": 0.1,
            "topP": 0.9,
        },
    }


def add_guardrail_config(converse_kwargs):
    if GUARDRAIL_ID and GUARDRAIL_VERSION:
        converse_kwargs["guardrailConfig"] = {
            "guardrailIdentifier": GUARDRAIL_ID,
            "guardrailVersion": GUARDRAIL_VERSION,
        }
    return converse_kwargs


def write_audit_status(
    request_id,
    status,
    audit_table,
    prompt=None,
    reply=None,
    error=None,
):
    item = {
        "RequestId": request_id,
        "Status": status,
        "Timestamp": int(time.time()),
        "TTL": int(time.time()) + (86400 * 7),
    }

    if prompt is not None:
        item["Prompt"] = prompt

    if reply is not None:
        item["Reply"] = reply

    if error is not None:
        item["Error"] = error

    audit_table.put_item(Item=item)


def parse_model_reply(reply):
    if not isinstance(reply, str):
        return reply

    try:
        plan = json.loads(reply)
    except (json.JSONDecodeError, TypeError):
        return None

    return plan if isinstance(plan, dict) else None


def validation_failed_response(correlation_id, errors):
    return {
        "statusCode": 422,
        "body": json.dumps(
            {
                "correlation_id": correlation_id,
                "status": "validation_failed",
                "errors": errors,
            }
        ),
    }


def handler(event, context):
    correlation_id = context.aws_request_id

    logger.info(
        json.dumps(
            {
                "event": "agent_request_received",
                "correlation_id": correlation_id,
            }
        )
    )

    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "invalid JSON body"}),
        }

    prompt = body.get("prompt")

    if not isinstance(prompt, str) or not prompt.strip():
        return {
            "statusCode": 400,
            "body": json.dumps(
                {"error": "prompt must be a non-empty string"}
            ),
        }

    bedrock_client, audit_table = get_clients()

    write_audit_status(
        correlation_id,
        "RECEIVED",
        audit_table,
        prompt=prompt,
    )

    try:
        approved_module = get_module_by_prompt(prompt)

        if approved_module:
            logger.info(
                json.dumps(
                    {
                        "event": "approved_module_retrieved",
                        "correlation_id": correlation_id,
                        "module": approved_module.get("module_name"),
                    }
                )
            )

        user_content = prompt + build_retrieval_context(approved_module)
        converse_kwargs = add_guardrail_config(
            build_converse_kwargs(user_content)
        )

        response = bedrock_client.converse(**converse_kwargs)

        if response.get("stopReason") == "guardrail_intervened":
            logger.warning(
                json.dumps(
                    {
                        "event": "guardrail_intervention",
                        "correlation_id": correlation_id,
                    }
                )
            )
            write_audit_status(
                correlation_id,
                "BLOCKED",
                audit_table,
                prompt=prompt,
            )
            return {
                "statusCode": 403,
                "body": json.dumps(
                    {"error": "Request blocked by policy"}
                ),
            }

        reply = response["output"]["message"]["content"][0]["text"]
        plan = parse_model_reply(reply)

        is_uc3_request = isinstance(plan, dict) or not isinstance(reply, str)

        if not is_uc3_request:
            logger.info(
                json.dumps(
                    {
                        "event": "agent_request_completed",
                        "correlation_id": correlation_id,
                        "model_id": MODEL_ID,
                        "approved_module": (
                            approved_module.get("module_name")
                            if approved_module
                            else None
                        ),
                    }
                )
            )

            write_audit_status(
                correlation_id,
                "COMPLETED",
                audit_table,
                prompt=prompt,
                reply=reply,
            )

            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "correlation_id": correlation_id,
                        "model_id": MODEL_ID,
                        "approved_module": (
                            approved_module.get("module_name")
                            if approved_module
                            else None
                        ),
                        "reply": reply,
                    }
                ),
            }

        try:
            validate_plan(plan)
        except PlanRejectedError as error:
            logger.warning(
                json.dumps(
                    {
                        "event": "plan_validation_failed",
                        "correlation_id": correlation_id,
                        "error": str(error),
                    }
                )
            )
            write_audit_status(
                correlation_id,
                "VALIDATION_FAILED",
                audit_table,
                prompt=prompt,
                error=str(error),
            )
            return validation_failed_response(correlation_id, [str(error)])

        generated = generate_terraform(plan)
        validation = validate_terraform(generated["files"])
        attempts = 1

        while not validation["valid"] and attempts < MAX_GENERATION_ATTEMPTS:
            feedback = "\n".join(
                f"- {error}" for error in validation["errors"]
            )
            retry_content = (
                f"{user_content}\n\n"
                "The previous Terraform generation failed validation. "
                "Correct every error and return only the corrected JSON plan.\n"
                f"Validation errors:\n{feedback}"
            )
            retry_kwargs = add_guardrail_config(
                build_converse_kwargs(retry_content)
            )

            response = bedrock_client.converse(**retry_kwargs)
            attempts += 1

            if response.get("stopReason") == "guardrail_intervened":
                write_audit_status(
                    correlation_id,
                    "BLOCKED",
                    audit_table,
                    prompt=prompt,
                )
                return {
                    "statusCode": 403,
                    "body": json.dumps(
                        {"error": "Request blocked by policy"}
                    ),
                }

            reply = response["output"]["message"]["content"][0]["text"]
            plan = parse_model_reply(reply)

            if not isinstance(plan, dict):
                validation = {
                    "valid": False,
                    "errors": ["Model returned invalid JSON."],
                }
                continue

            try:
                validate_plan(plan)
            except PlanRejectedError as error:
                validation = {
                    "valid": False,
                    "errors": [str(error)],
                }
                continue

            generated = generate_terraform(plan)
            validation = validate_terraform(generated["files"])

        if not validation["valid"]:
            logger.warning(
                json.dumps(
                    {
                        "event": "terraform_validation_failed",
                        "correlation_id": correlation_id,
                        "attempts": attempts,
                    }
                )
            )
            write_audit_status(
                correlation_id,
                "VALIDATION_FAILED",
                audit_table,
                prompt=prompt,
                error="Terraform validation failed",
            )
            return validation_failed_response(
                correlation_id,
                validation["errors"],
            )

        generated_hcl = generated["files"]["main.tf"]

        logger.info(
            json.dumps(
                {
                    "event": "agent_request_completed",
                    "correlation_id": correlation_id,
                    "model_id": MODEL_ID,
                    "approved_module": (
                        approved_module.get("module_name")
                        if approved_module
                        else None
                    ),
                    "generation_attempts": attempts,
                }
            )
        )

        write_audit_status(
            correlation_id,
            "COMPLETED",
            audit_table,
            prompt=prompt,
            reply=generated_hcl,
        )

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "correlation_id": correlation_id,
                    "model_id": MODEL_ID,
                    "approved_module": (
                        approved_module.get("module_name")
                        if approved_module
                        else None
                    ),
                    "generation_attempts": attempts,
                    "files": generated["files"],
                }
            ),
        }

    except Exception:
        logger.exception(
            json.dumps(
                {
                    "event": "agent_request_failed",
                    "correlation_id": correlation_id,
                }
            )
        )

        write_audit_status(
            correlation_id,
            "FAILED",
            audit_table,
            prompt=prompt,
            error="Bedrock invocation failed",
        )

        return {
            "statusCode": 500,
            "body": json.dumps(
                {
                    "correlation_id": correlation_id,
                    "error": "Bedrock invocation failed",
                }
            ),
        }
