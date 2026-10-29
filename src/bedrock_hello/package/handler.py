import json
import logging
import os

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "us-east-1")
MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID",
    "anthropic.claude-haiku-4-5-20251001-v1:0",
)

bedrock = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)


def handler(event, context):
    correlation_id = context.aws_request_id
    logger.info(
        json.dumps(
            {
                "event": "bedrock_request_received",
                "correlation_id": correlation_id,
            }
        )
    )

    body = json.loads(event.get("body") or "{}")
    prompt = body.get("prompt", "Say hello and introduce yourself in one sentence.")

    if not isinstance(prompt, str) or not prompt.strip():
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "prompt must be a non-empty string"}),
        }

    try:
        response = bedrock.converse(
            modelId=MODEL_ID,
            messages=[
                {
                    "role": "user",
                    "content": [{"text": prompt}],
                }
            ],
            inferenceConfig={"maxTokens": 256, "temperature": 0.2},
        )

        reply = response["output"]["message"]["content"][0]["text"]

        logger.info(
            json.dumps(
                {
                    "event": "bedrock_request_completed",
                    "correlation_id": correlation_id,
                    "model_id": MODEL_ID,
                }
            )
        )

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "correlation_id": correlation_id,
                    "model_id": MODEL_ID,
                    "reply": reply,
                }
            ),
        }

    except Exception as exc:
        logger.exception(
            json.dumps(
                {
                    "event": "bedrock_request_failed",
                    "correlation_id": correlation_id,
                }
            )
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
