import json
from unittest.mock import MagicMock, patch

from src.agent.handler import handler
from src.agent.tools.registry import TOOL_REGISTRY, get_tool_specs


class FakeContext:
    aws_request_id = "test-correlation-id"


def make_event(prompt="Use the approved modules tool."):
    return {
        "body": json.dumps({"prompt": prompt})
    }


def test_no_deployment_tool_is_registered():
    forbidden = {
        "apply_terraform",
        "destroy_terraform",
        "assume_deployment_role"
    }

    assert forbidden.isdisjoint(TOOL_REGISTRY.keys())


def test_tool_specs_match_registry():
    specs = get_tool_specs()
    spec_names = {
        spec["toolSpec"]["name"]
        for spec in specs
    }

    assert spec_names == set(TOOL_REGISTRY.keys())


def test_unknown_tool_is_rejected():
    bedrock = MagicMock()
    bedrock.converse.return_value = {
        "output": {
            "message": {
                "role": "assistant",
                "content": [{
                    "toolUse": {
                        "name": "apply_terraform",
                        "input": {},
                        "toolUseId": "tool-1"
                    }
                }]
            }
        }
    }

    with patch("src.agent.handler.get_bedrock", return_value=bedrock):
        result = handler(make_event(), FakeContext())

    assert result["statusCode"] == 422
    assert json.loads(result["body"])["reason"] == "unknown_tool"


def test_tool_result_uses_original_tool_use_id():
    bedrock = MagicMock()
    bedrock.converse.return_value = {
        "output": {
            "message": {
                "role": "assistant",
                "content": [{
                    "toolUse": {
                        "name": "get_approved_modules",
                        "input": {},
                        "toolUseId": "tool-123"
                    }
                }]
            }
        }
    }

    with patch("src.agent.handler.get_bedrock", return_value=bedrock):
        handler(make_event(), FakeContext())

    second_call = bedrock.converse.call_args_list[0]
    messages = second_call.kwargs["messages"]

    tool_result = messages[-1]["content"][0]["toolResult"]
    assert tool_result["toolUseId"] == "tool-123"


def test_agent_returns_final_reply_after_tool_result():
    bedrock = MagicMock()
    bedrock.converse.side_effect = [
        {
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [{
                        "toolUse": {
                            "name": "get_approved_modules",
                            "input": {},
                            "toolUseId": "tool-123"
                        }
                    }]
                }
            }
        },
        {
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [{
                        "text": "Approved modules are available."
                    }]
                }
            }
        }
    ]

    with patch("src.agent.handler.get_bedrock", return_value=bedrock):
        result = handler(make_event(), FakeContext())

    assert result["statusCode"] == 200
    assert json.loads(result["body"])["reply"] == (
        "Approved modules are available."
    )


def test_agent_stops_after_max_iterations():
    bedrock = MagicMock()

    tool_use_response = {
        "output": {
            "message": {
                "role": "assistant",
                "content": [{
                    "toolUse": {
                        "name": "get_approved_modules",
                        "input": {},
                        "toolUseId": "tool-123"
                    }
                }]
            }
        }
    }

    bedrock.converse.side_effect = [tool_use_response] * 3

    with patch("src.agent.handler.get_bedrock", return_value=bedrock):
        result = handler(make_event(), FakeContext())

    assert result["statusCode"] == 422
    assert json.loads(result["body"])["reason"] == (
        "max_tool_iterations_reached"
    )
