import json
import logging
import os
import time

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "ap-south-1")
MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID",
    "mistral.mistral-large-3-675b-instruct",
)
AUDIT_TABLE_NAME = os.environ.get("AUDIT_TABLE_NAME")

bedrock = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(AUDIT_TABLE_NAME)


# Externalized prompt loading
def load_system_prompt():
    prompt_path = os.path.join(os.path.dirname(__file__), '..', 'agents', 'prompts', 'system_prompt.txt')
    with open(prompt_path, 'r') as f:
        return f.read()

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

    # Write RECEIVED status
    table.put_item(
        Item={
            "RequestId": correlation_id,
            "Status": "RECEIVED",
            "Prompt": prompt,
            "Timestamp": int(time.time()),
            "TTL": int(time.time()) + (86400 * 7),  # 7 days TTL
        }
    )

    try:
        response = bedrock.converse(
            modelId=MODEL_ID,
            system=[{"text": load_system_prompt()}],
            messages=[
                {
                    "role": "user",
                    "content": [{"text": prompt}],
                }
            ],
            inferenceConfig={"maxTokens": 1000, "temperature": 0.2},
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

        # Update to DEPLOYED (or COMPLETED as per Day 05)
        table.update_item(
            Key={"RequestId": correlation_id},
            UpdateExpression="SET #s = :status, Reply = :reply",
            ExpressionAttributeNames={"#s": "Status"},
            ExpressionAttributeValues={":status": "COMPLETED", ":reply": reply},
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

        # Update to FAILED
        table.update_item(
            Key={"RequestId": correlation_id},
            UpdateExpression="SET #s = :status, Error = :error",
            ExpressionAttributeNames={"#s": "Status"},
            ExpressionAttributeValues={":status": "FAILED", ":error": str(exc)},
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
