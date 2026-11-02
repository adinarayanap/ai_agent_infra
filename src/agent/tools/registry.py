from .get_approved_modules import get_approved_modules_tool

TOOL_REGISTRY = {
    "get_approved_modules": get_approved_modules_tool,
    # "generate_terraform": generate_terraform_tool, # Pending implementation
}

def get_tool_specs():
    return [
        {"toolSpec": tool["toolSpec"]} for tool in TOOL_REGISTRY.values()
    ]
