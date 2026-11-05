import json
import logging
import os
import time

import boto3

from agent.modules.approved_modules import get_module_by_prompt

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

        converse_kwargs = {
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

        if GUARDRAIL_ID and GUARDRAIL_VERSION:
            converse_kwargs["guardrailConfig"] = {
                "guardrailIdentifier": GUARDRAIL_ID,
                "guardrailVersion": GUARDRAIL_VERSION,
            }

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
            write_audit_status(correlation_id, "BLOCKED", audit_table, prompt=prompt)
            return {
                "statusCode": 403,
                "body": json.dumps({"error": "Request blocked by policy"}),
            }

        reply = response["output"]["message"]["content"][0]["text"]

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
