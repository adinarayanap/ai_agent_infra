import json
import logging
import os

import boto3

from .config import MODEL_ID
from .prompts import SYSTEM_PROMPT
from .tools.registry import TOOL_REGISTRY, get_tool_specs
from .validators.plan_validator import PlanRejectedError, validate_plan

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_bedrock = None
MAX_TOOL_ITERATIONS = 3


def get_bedrock():
    global _bedrock

    if _bedrock is None:
        _bedrock = boto3.client(
            "bedrock-runtime",
            region_name=os.environ.get("BEDROCK_REGION", "ap-south-1")
        )

    return _bedrock


def handler(event, context):
    correlation_id = context.aws_request_id

    try:
        body = json.loads(event.get("body") or "{}")
        prompt = body.get("prompt")

        if not isinstance(prompt, str) or not prompt.strip():
            return _response(400, {
                "correlation_id": correlation_id,
                "error": "prompt must be a non-empty string"
            })

        messages = [{
            "role": "user",
            "content": [{"text": prompt}]
        }]

        for _ in range(MAX_TOOL_ITERATIONS):
            response = get_bedrock().converse(
                modelId=MODEL_ID,
                system=[{"text": SYSTEM_PROMPT}],
                messages=messages,
                toolConfig={"tools": get_tool_specs()},
                inferenceConfig={
                    "maxTokens": 1000,
                    "temperature": 0.1,
                    "topP": 0.9
                }
            )

            message = response["output"]["message"]
            messages.append(message)

            tool_use = next(
                (
                    block["toolUse"]
                    for block in message.get("content", [])
                    if "toolUse" in block
                ),
                None
            )

            if tool_use is None:
                reply = next(
                    (
                        block["text"]
                        for block in message.get("content", [])
                        if "text" in block
                    ),
                    ""
                )

                return _response(200, {
                    "correlation_id": correlation_id,
                    "status": "completed",
                    "reply": reply
                })

            tool_name = tool_use.get("name")
            tool_arguments = tool_use.get("input", {})
            tool_use_id = tool_use.get("toolUseId")

            if tool_name not in TOOL_REGISTRY:
                return _response(422, {
                    "correlation_id": correlation_id,
                    "status": "rejected",
                    "reason": "unknown_tool",
                    "tool": tool_name
                })

            if not isinstance(tool_arguments, dict):
                return _response(422, {
                    "correlation_id": correlation_id,
                    "status": "rejected",
                    "reason": "invalid_tool_arguments"
                })

            if tool_name == "generate_terraform":
                try:
                    validated_plan = validate_plan(
                        tool_arguments.get("plan", {})
                    )
                except PlanRejectedError as exc:
                    return _response(422, {
                        "correlation_id": correlation_id,
                        "status": "rejected",
                        "reason": "plan_validation_failed",
                        "details": getattr(exc, "details", [])
                    })

            tool_handler = TOOL_REGISTRY[tool_name]["handler"]
            tool_output = tool_handler(tool_arguments)

            messages.append({
                "role": "user",
                "content": [{
                    "toolResult": {
                        "toolUseId": tool_use_id,
                        "content": [{"json": tool_output}]
                    }
                }]
            })

        return _response(422, {
            "correlation_id": correlation_id,
            "status": "rejected",
            "reason": "max_tool_iterations_reached"
        })

    except Exception:
        logger.exception(json.dumps({
            "event": "agent_request_failed",
            "correlation_id": correlation_id
        }))

        return _response(500, {
            "correlation_id": correlation_id,
            "error": "internal_error"
        })


def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body)
    }
