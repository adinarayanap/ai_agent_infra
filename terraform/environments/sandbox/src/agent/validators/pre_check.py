"""Local, deterministic pre-checks before Bedrock Guardrails."""

import json
import os


class LocalRejectionError(Exception):
    """Raised when a request fails a local pre-check."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def _get_max_request_size() -> int:
    raw_value = os.environ.get("MAX_REQUEST_SIZE_BYTES", "10240")
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return 10240


def pre_check_request(body: dict) -> None:
    """Validate a request before calling Bedrock Guardrails.

    Raises:
        LocalRejectionError: If the request is malformed, oversized, or
            outside the supported UC1-UC3 scope.
    """
    if not isinstance(body, dict):
        raise LocalRejectionError("Invalid request structure.")

    try:
        serialized_body = json.dumps(body)
    except (TypeError, ValueError) as error:
        raise LocalRejectionError("Invalid request structure.") from error

    if len(serialized_body.encode("utf-8")) > _get_max_request_size():
        raise LocalRejectionError("Request size exceeds the configured limit.")

    prompt = body.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise LocalRejectionError("Missing or empty prompt.")

    normalized_prompt = prompt.strip().lower()

    forbidden_terms = (
        "ec2 instance",
        "rds",
        "kubernetes",
        "iam user",
        "secret access key",
        "access key",
        "password",
        "ssh key",
        "cryptocurrency",
        "bitcoin",
        "crypto mining",
        "malware",
        "delete all",
        "terminate all",
        "completely public",
        "publicly accessible",
        "public s3 bucket",
        "public bucket",
    )

    if any(term in normalized_prompt for term in forbidden_terms):
        raise LocalRejectionError("Request is outside the supported scope.")

    supported_terms = (
        "s3",
        "bucket",
        "storage",
        "vpc",
        "subnet",
        "network",
        "lambda",
        "api gateway",
        "dynamodb",
    )

    if not any(term in normalized_prompt for term in supported_terms):
        raise LocalRejectionError(
            "Request does not match a supported UC1-UC3 use case."
        )
