# terraform/environments/sandbox/src/agent/modules/approved_modules.py

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
        "required_tags": [
            "project",
            "environment",
            "owner",
            "cost-center",
            "managed-by",
        ],
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
        "required_tags": [
            "project",
            "environment",
            "owner",
            "cost-center",
            "managed-by",
        ],
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
        "required_tags": [
            "project",
            "environment",
            "owner",
            "cost-center",
            "managed-by",
        ],
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
    """Return the approved module matching an infrastructure prompt."""
    if not isinstance(prompt, str) or not prompt.strip():
        return None

    prompt_lower = prompt.lower()

    s3_keywords = (
        "s3 bucket",
        "s3",
        "bucket",
        "object storage",
        "secure storage",
    )

    vpc_keywords = (
        "vpc",
        "subnet",
        "network",
        "networking",
    )

    api_keywords = (
        "serverless api",
        "api gateway",
        "lambda",
        "dynamodb",
        "serverless",
    )

    if any(keyword in prompt_lower for keyword in s3_keywords):
        return next(
            (
                module
                for module in approved_modules_catalog
                if module["module_name"] == "encrypted_s3_bucket"
            ),
            None,
        )

    if any(keyword in prompt_lower for keyword in vpc_keywords):
        return next(
            (
                module
                for module in approved_modules_catalog
                if module["module_name"] == "vpc_public_private"
            ),
            None,
        )

    if any(keyword in prompt_lower for keyword in api_keywords):
        return next(
            (
                module
                for module in approved_modules_catalog
                if module["module_name"] == "serverless_api"
            ),
            None,
        )

    return None
