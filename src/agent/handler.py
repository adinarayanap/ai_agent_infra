import boto3
import json
import logging
import os
from .prompts import SYSTEM_PROMPT
from .config import MODEL_ID
from .validators.plan_validator import validate_plan, PlanRejectedError
from .tool_registry import TOOLS

logger = logging.getLogger()
logger.setLevel(logging.INFO)

bedrock = boto3.client("bedrock-runtime", region_name=os.environ.get("BEDROCK_REGION", "ap-south-1"))

def invoke_planner(prompt, system_prompt):
    # Updated to support toolConfig
    response = bedrock.converse(
        modelId=MODEL_ID,
        system=[{"text": system_prompt}],
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        toolConfig={"tools": TOOLS},
        inferenceConfig={"maxTokens": 1000, "temperature": 0.2},
    )
    return response

def handler(event, context):
    correlation_id = context.aws_request_id

    try:
        body = json.loads(event.get("body") or "{}")
        prompt = body.get("prompt")

        if not isinstance(prompt, str) or not prompt.strip():
            return _response(400, {"error": "prompt must be a non-empty string"})

        # Get response from Bedrock with tool support
        response = invoke_planner(prompt, SYSTEM_PROMPT)
        message = response["output"]["message"]

        # Check if the model wants to use a tool
        if "toolUse" in message["content"][0]:
            tool_use = message["content"][0]["toolUse"]
            plan = tool_use["input"]["plan"]

            # Validate plan
            try:
                validated_plan = validate_plan(plan)
            except PlanRejectedError as exc:
                return _response(422, {"status": "rejected", "reason": str(exc)})

            # If valid, we would proceed to generate_terraform
            return _response(200, {"status": "plan_validated", "plan": validated_plan})

        # Fallback if no tool was used
        return _response(422, {"status": "rejected", "reason": "no_tool_use"})

    except Exception:
        logger.exception("Agent request failed")
        return _response(500, {"error": "internal_error"})


def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body)
    }
