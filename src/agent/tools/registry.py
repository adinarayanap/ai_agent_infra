from .get_approved_modules import get_approved_modules_tool

TOOL_REGISTRY = {
    "get_approved_modules": get_approved_modules_tool
}


def get_tool_specs() -> list[dict]:
    return [
        {"toolSpec": tool["toolSpec"]}
        for tool in TOOL_REGISTRY.values()
    ]
