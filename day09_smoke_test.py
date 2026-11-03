import os
import json
import boto3
import time
import sys
sys.path.append("/home/naghi/ai_agent_infra")
from src.agent.validators.plan_validator import validate_plan, PlanRejectedError

# Mocking TOOL_REGISTRY for Day 09 Smoke Test
def get_approved_modules(use_case: str):
    """
    Returns the list of approved modules/schemas for a given use case.
    This is the tool Mistral will call during the smoke test.
    """
    modules = {
        "UC1": ["aws_s3_bucket", "aws_s3_bucket_versioning", "aws_s3_bucket_server_side_encryption_configuration", "aws_s3_bucket_public_access_block"],
        "UC2": ["aws_vpc", "aws_subnet", "aws_route_table", "aws_internet_gateway", "aws_nat_gateway"],
        "UC3": ["aws_lambda_function", "aws_apigatewayv2_api", "aws_dynamodb_table"]
    }
    return modules.get(use_case, [])

TOOL_REGISTRY = {
    "get_approved_modules": get_approved_modules
}

def get_tool_specs():
    return [
        {
            "toolSpec": {
                "name": "get_approved_modules",
                "description": "Get the list of approved infrastructure modules for a specific use case (UC1, UC2, UC3).",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "use_case": {
                                "type": "string",
                                "enum": ["UC1", "UC2", "UC3"],
                                "description": "The use case identifier."
                            }
                        },
                        "required": ["use_case"]
                    }
                }
            }
        }
    ]

def load_system_prompt():
    prompt_path = "/home/naghi/ai_agent_infra/src/agents/prompts/system_prompt.txt"
    with open(prompt_path, 'r') as f:
        return f.read()

def run_smoke_test():
    region = "ap-south-1"
    model_id = "mistral.mistral-large-2402-v1:0" # Adjusted for India region availability if needed

    # Try to find valid mistral model in ap-south-1
    client = boto3.client("bedrock-runtime", region_name=region)

    prompt = "I need to deploy UC1: a secure S3 bucket for data storage. What modules are approved?"

    print(f"--- Calling Bedrock Converse with Tool: {model_id} ---")

    system_prompt = load_system_prompt() + "\nIf a user asks for a specific use case, use the 'get_approved_modules' tool to find out what is allowed."

    try:
        response = client.converse(
            modelId=model_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            system=[{"text": system_prompt}],
            toolConfig={
                "tools": get_tool_specs()
            }
        )

        output_message = response['output']['message']
        print(f"Model Output Message: {json.dumps(output_message, indent=2)}")

        # Check for Tool Use
        tool_use = next((c['toolUse'] for c in output_message['content'] if 'toolUse' in c), None)

        if tool_use:
            print(f"SUCCESS: Received toolUse block for {tool_use['name']}")

            tool_id = tool_use['toolUseId']
            tool_name = tool_use['name']
            tool_input = tool_use['input']

            # Execute tool
            tool_result_data = TOOL_REGISTRY[tool_name](**tool_input)
            print(f"Tool Execution Result: {tool_result_data}")

            # Send Tool Result back to Model
            follow_up_messages = [
                {"role": "user", "content": [{"text": prompt}]},
                output_message,
                {
                    "role": "user",
                    "content": [
                        {
                            "toolResult": {
                                "toolUseId": tool_id,
                                "content": [{"json": {"modules": tool_result_data}}]
                            }
                        }
                    ]
                }
            ]

            print("--- Sending Tool Result back to Model ---")
            final_response = client.converse(
                modelId=model_id,
                messages=follow_up_messages,
                system=[{"text": system_prompt}],
                toolConfig={"tools": get_tool_specs()}
            )

            final_text = final_response['output']['message']['content'][0]['text']
            print(f"Final Model Response: {final_text}")

        else:
            print("FAILURE: No toolUse block received.")

    except Exception as e:
        print(f"Error during smoke test: {e}")

if __name__ == "__main__":
    # Ensure TOOL_REGISTRY and get_tool_specs consistency check
    tool_names_registry = set(TOOL_REGISTRY.keys())
    tool_names_specs = set([t['toolSpec']['name'] for t in get_tool_specs()])

    if tool_names_registry == tool_names_specs:
        print("TOOL_REGISTRY and get_tool_specs() are consistent.")
        run_smoke_test()
    else:
        print(f"Inconsistency detected! Registry: {tool_names_registry}, Specs: {tool_names_specs}")
