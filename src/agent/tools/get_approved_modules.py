get_approved_modules_tool = {
    "toolSpec": {
        "name": "get_approved_modules",
        "description": (
            "Return metadata for approved infrastructure modules "
            "available to the agent."
        ),
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    "handler": lambda arguments: {
        "modules": [
            {
                "name": "encrypted_s3_bucket",
                "use_case": "UC1",
                "status": "approved"
            },
            {
                "name": "vpc_public_private",
                "use_case": "UC2",
                "status": "approved"
            },
            {
                "name": "serverless_api",
                "use_case": "UC3",
                "status": "approved"
            }
        ]
    }
}
