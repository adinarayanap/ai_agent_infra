import json
import pytest
from src.agent.handler import handler
from src.agent.tools.registry import TOOL_REGISTRY

class FakeContext:
    def __init__(self):
        self.aws_request_id = "test-123"

def test_no_deployment_tool_is_registered():
    forbidden = {"apply_terraform", "destroy_terraform", "assume_deployment_role"}
    assert forbidden.isdisjoint(TOOL_REGISTRY.keys())

def test_unknown_tool_is_rejected():
    # This requires mocking bedrock.converse to return a toolUse for an unknown tool
    pass

# Further tests will need bedrock mocking
