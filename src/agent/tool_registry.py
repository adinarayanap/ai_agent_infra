import json
import logging
from .prompts import SYSTEM_PROMPT
from .config import MODEL_ID
from .validators.plan_validator import validate_plan, PlanRejectedError

# Define available tools for the agent
# Note: For now, generate_terraform is a mock.
TOOLS = [
    {
        "toolSpec": {
            "name": "generate_terraform",
            "description": "Generates Terraform code from a validated JSON infrastructure plan.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "plan": {"type": "object", "description": "The validated infrastructure plan"}
                    },
                    "required": ["plan"]
                }
            }
        }
    }
]

def invoke_planner_with_tools(prompt, system_prompt, bedrock_client):
    # This invokes Bedrock with tool support
    response = bedrock_client.converse(
        modelId=MODEL_ID,
        system=[{"text": system_prompt}],
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        toolConfig={"tools": TOOLS}
    )
    return response

# ... inside handler ...
# We will need to update the handler loop to check for toolUse in the response.
