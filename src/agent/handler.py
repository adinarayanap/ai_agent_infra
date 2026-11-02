import boto3
import json
import logging
import os
from .prompts import SYSTEM_PROMPT
from .config import MODEL_ID
from .validators.plan_validator import validate_plan, PlanRejectedError
from .tools.registry import TOOL_REGISTRY, get_tool_specs

logger = logging.getLogger()
logger.setLevel(logging.INFO)

bedrock = boto3.client("bedrock-runtime", region_name=os.environ.get("BEDROCK_REGION", "ap-south-1"))

def handler(event, context):
    correlation_id = context.aws_request_id
    body = json.loads(event.get("body") or "{}")
    prompt = body.get("prompt")

    if not isinstance(prompt, str) or not prompt.strip():
        return _response(400, {"error": "prompt must be a non-empty string"})

    messages = [{"role": "user", "content": [{"text": prompt}]}]
    max_iterations = 3

    for i in range(max_iterations):
        response = bedrock.converse(
            modelId=MODEL_ID,
            system=[{"text": SYSTEM_PROMPT}],
            messages=messages,
            toolConfig={"tools": get_tool_specs()},
            inferenceConfig={"maxTokens": 1000, "temperature": 0.2},
        )

        message = response["output"]["message"]
        messages.append(message)

        if message["content"][0].get("toolUse"):
            tool_use = message["content"][0]["toolUse"]
            tool_name = tool_use["name"]

            if tool_name not in TOOL_REGISTRY:
                return _response(422, {"status": "rejected", "reason": "unknown_tool"})

            # For Day 09, we only support get_approved_modules
            if tool_name == "get_approved_modules":
                tool_result = {
                    "toolUseId": tool_use["toolUseId"],
                    "content": [{"json": {"modules": ["s3_bucket", "vpc", "lambda_api"]}}]
                }
                messages.append({"role": "user", "content": [{"toolResult": tool_result}]})
                continue # Loop again

            return _response(422, {"status": "rejected", "reason": "tool_not_implemented"})

        # If no tool use, return final reply
        return _response(200, {"reply": message["content"][0]["text"]})

    return _response(422, {"status": "rejected", "reason": "max_iterations_reached"})

def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body)
    }
