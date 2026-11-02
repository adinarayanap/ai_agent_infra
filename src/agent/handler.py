import boto3
import json
import logging
import os
from .prompts import SYSTEM_PROMPT
from .config import MODEL_ID
from .validators.plan_validator import validate_plan, PlanRejectedError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

bedrock = boto3.client("bedrock-runtime", region_name=os.environ.get("BEDROCK_REGION", "ap-south-1"))

def invoke_planner(prompt, system_prompt):
    response = bedrock.converse(
        modelId=MODEL_ID,
        system=[{"text": system_prompt}],
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": 1000, "temperature": 0.2},
    )
    return response["output"]["message"]["content"][0]["text"]

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

        logger.info(json.dumps({
            "event": "agent_request_received",
            "correlation_id": correlation_id
        }))

        raw_response = invoke_planner(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT
        )

        try:
            # Basic cleanup: remove markdown code fences if present
            clean_json = raw_response.replace("```json", "").replace("```", "").strip()
            plan = json.loads(clean_json)
        except json.JSONDecodeError as exc:
            logger.warning(json.dumps({
                "event": "agent_plan_parse_failed",
                "correlation_id": correlation_id,
                "error": str(exc)
            }))
            return _response(422, {
                "correlation_id": correlation_id,
                "status": "rejected",
                "reason": "invalid_json_response"
            })

        try:
            validated_plan = validate_plan(plan)
        except PlanRejectedError as exc:
            logger.warning(json.dumps({
                "event": "agent_plan_validation_failed",
                "correlation_id": correlation_id,
                "reason": str(exc)
            }))
            return _response(422, {
                "correlation_id": correlation_id,
                "status": "rejected",
                "reason": "plan_validation_failed",
                "details": getattr(exc, "details", [])
            })

        logger.info(json.dumps({
            "event": "agent_plan_validated",
            "correlation_id": correlation_id,
            "use_case": validated_plan.get("use_case", "unknown")
        }))

        return _response(200, {
            "correlation_id": correlation_id,
            "status": "plan_validated",
            "plan": validated_plan
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
