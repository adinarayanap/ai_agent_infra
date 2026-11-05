# src/modules/approved_modules.py

approved_modules_catalog = [
    {
        "module_name": "encrypted_s3_bucket",
        "description": "Provides a secure, versioned, and private S3 bucket with server-side encryption.",
        "approved_use_cases": ["UC1: Encrypted, versioned, private S3 bucket"],
        "security_constraints": [
            "Server-side encryption enabled",
            "Versioning enabled",
            "Public access fully blocked",
            "Private access",
            "No public policy or ACL",
        ],
        "required_tags": ["project", "environment", "owner", "cost-center", "managed-by"],
        "allowed_resource_types": [
            "aws_s3_bucket",
            "aws_s3_bucket_versioning",
            "aws_s3_bucket_public_access_block",
            "aws_s3_bucket_policy",
        ],
        "usage_guidance": "Ensure mandatory tags are provided. Bucket policy may be required for specific private access patterns.",
    },
    {
        "module_name": "vpc_public_private",
        "description": "Creates a VPC with public and private subnets, configured for network isolation.",
        "approved_use_cases": ["UC2: VPC with public and private subnets"],
        "security_constraints": [
            "Private subnets for compute",
            "Restricted security groups",
            "No SSH/RDP from 0.0.0.0/0",
        ],
        "required_tags": ["project", "environment", "owner", "cost-center", "managed-by"],
        "allowed_resource_types": [
            "aws_vpc",
            "aws_subnet",
            "aws_internet_gateway",
            "aws_route_table",
            "aws_security_group",
        ],
        "usage_guidance": "Specify CIDR blocks carefully. Ensure appropriate routing and security group rules are defined.",
    },
    {
        "module_name": "serverless_api",
        "description": "Sets up a Lambda function integrated with API Gateway and DynamoDB for serverless applications.",
        "approved_use_cases": ["UC3: Lambda + API Gateway + DynamoDB"],
        "security_constraints": [
            "Least-privilege IAM for Lambda",
            "HTTPS/TLS for API Gateway",
            "KMS encryption for DynamoDB",
        ],
        "required_tags": ["project", "environment", "owner", "cost-center", "managed-by"],
        "allowed_resource_types": [
            "aws_lambda_function",
            "aws_api_gateway_rest_api",
            "aws_api_gateway_deployment",
            "aws_api_gateway_integration",
            "aws_api_gateway_route",
            "aws_dynamodb_table",
        ],
        "usage_guidance": "Configure Lambda memory and timeout appropriately. Define DynamoDB schema with provisioned or on-demand capacity.",
    },
]

def get_module_by_prompt(prompt: str) -> dict | None:
    """
    Retrieves the most relevant approved module based on the user's prompt.
    Returns None if no module matches.
    """
    if not prompt:
        return None

    prompt_lower = prompt.lower()

    # Direct matches
    if "s3" in prompt_lower or "bucket" in prompt_lower:
        if "encrypt" in prompt_lower or "secure" in prompt_lower or "version" in prompt_lower or "private" in prompt_lower:
            return next((m for m in approved_modules_catalog if m["module_name"] == "encrypted_s3_bucket"), None)

    if "vpc" in prompt_lower or "subnet" in prompt_lower or "network" in prompt_lower:
        return next((m for m in approved_modules_catalog if m["module_name"] == "vpc_public_private"), None)

    if "api" in prompt_lower or "lambda" in prompt_lower or "dynamodb" in prompt_lower or "serverless" in prompt_lower:
        return next((m for m in approved_modules_catalog if m["module_name"] == "serverless_api"), None)

    return None
