import json
from src.agent.handler import handler

class FakeContext:
    def __init__(self):
        self.aws_request_id = "test-123"

def test_handler_rejects_invalid_plan():
    # Public S3 bucket request violates security rules
    event = {
        "body": json.dumps({
            "prompt": "Create a public S3 bucket without encryption"
        })
    }

    result = handler(event, FakeContext())

    assert result["statusCode"] == 422
    body = json.loads(result["body"])
    assert body["status"] == "rejected"
    print("test_handler_rejects_invalid_plan passed")

# Note: Valid path test requires a mocked Bedrock response
# because we haven't implemented the tool-use loop yet.
# We will focus on this after ensuring the validator works in the handler.
