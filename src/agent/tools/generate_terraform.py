import os
import json
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
from src.agent.validators.plan_validator import validate_plan, PlanRejectedError

MANDATORY_TAGS = ["project", "environment", "owner", "cost-center", "managed-by"]

class TerraformGenerationError(Exception):
    """Raised when Terraform generation fails validation or formatting."""
    def __init__(self, message: str, details: Optional[list] = None):
        super().__init__(message)
        self.details = details or []

def sanitize_identifier(name: str) -> str:
    """Sanitize resource name for HCL identifier."""
    return name.replace("-", "_").replace(".", "_")

def generate_terraform(plan: dict, output_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Converts a validated UC1 JSON infrastructure plan into deterministic Terraform files.

    Args:
        plan: Validated infrastructure plan dictionary.
        output_dir: Optional directory path to write generated Terraform files.

    Returns:
        dict containing 'files', 'output_dir', and 'status'.
    """
    resources = plan.get("resources", [])
    if not resources:
        raise TerraformGenerationError("No resources found in plan.")

    # Find S3 bucket resource
    bucket_resource = None
    for res in resources:
        if res.get("type") == "aws_s3_bucket":
            bucket_resource = res
            break

    if not bucket_resource:
        raise TerraformGenerationError("UC1 plan must contain an aws_s3_bucket resource.")

    # Validate mandatory tags
    tags = bucket_resource.get("tags", {})
    missing_tags = [tag for tag in MANDATORY_TAGS if not tags.get(tag)]
    if missing_tags:
        raise TerraformGenerationError(
            f"Missing mandatory tags: {missing_tags}",
            details=[f"Tag '{t}' is required." for t in missing_tags]
        )

    # Validate security rules (N1 control: no public access)
    if bucket_resource.get("public_access") is True:
        raise TerraformGenerationError("Public S3 access is strictly prohibited (N1 control).")

    if not bucket_resource.get("encryption_enabled", False):
        raise TerraformGenerationError("S3 bucket must have server-side encryption enabled.")

    if not bucket_resource.get("versioning_enabled", False):
        raise TerraformGenerationError("S3 bucket must have versioning enabled.")

    if not bucket_resource.get("public_access_blocked", False):
        raise TerraformGenerationError("S3 bucket must have public access blocked.")

    # 1. Validate plan against schema and business rules
    try:
        validated_plan = validate_plan(plan)
    except Exception as e:
        raise TerraformGenerationError(f"Plan validation failed: {e}", details=[str(e)])

    region = validated_plan.get("region", "ap-south-1")
    if region != "ap-south-1":
        raise TerraformGenerationError(f"Invalid region: {region}. Must be ap-south-1.")

    bucket_name = bucket_resource.get("name", "app-data-bucket")
    hcl_name = sanitize_identifier(bucket_name)
    environment = tags.get("environment", "dev")

    # Generate deterministic HCL templates
    main_tf = f"""terraform {{
  required_version = ">= 1.6.0"
  required_providers {{
    aws = {{
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }}
  }}
  backend "s3" {{
    bucket       = "ai-agent-infra-state-{environment}"
    key          = "ai-agent-infra/{environment}/terraform.tfstate"
    region       = "{region}"
    encrypt      = true
    use_lockfile = true
  }}
}}

provider "aws" {{
  region = var.aws_region
  default_tags {{
    tags = {{
      project     = var.project
      environment = var.environment
      owner       = var.owner
      cost-center = var.cost_center
      managed-by  = var.managed_by
    }}
  }}
}}

resource "aws_s3_bucket" "{hcl_name}" {{
  bucket = var.bucket_name

  tags = {{
    Name        = var.bucket_name
    project     = var.project
    environment = var.environment
    owner       = var.owner
    cost-center = var.cost_center
    managed-by  = var.managed_by
  }}
}}

resource "aws_s3_bucket_versioning" "{hcl_name}" {{
  bucket = aws_s3_bucket.{hcl_name}.id
  versioning_configuration {{
    status = "Enabled"
  }}
}}

resource "aws_s3_bucket_server_side_encryption_configuration" "{hcl_name}" {{
  bucket = aws_s3_bucket.{hcl_name}.id

  rule {{
    apply_server_side_encryption_by_default {{
      sse_algorithm = "AES256"
    }}
  }}
}}

resource "aws_s3_bucket_public_access_block" "{hcl_name}" {{
  bucket                  = aws_s3_bucket.{hcl_name}.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}}
"""

    variables_tf = f"""variable "aws_region" {{
  type    = string
  default = "{region}"
}}

variable "bucket_name" {{
  type        = string
  description = "Name of the S3 bucket"
  default     = "{bucket_name}"
}}

variable "project" {{
  type        = string
  description = "Project name tag"
  default     = "{tags.get('project', 'ai-infra')}"
}}

variable "environment" {{
  type        = string
  description = "Environment tag"
  default     = "{environment}"
}}

variable "owner" {{
  type        = string
  description = "Owner tag"
  default     = "{tags.get('owner', 'platform-team')}"
}}

variable "cost_center" {{
  type        = string
  description = "Cost center tag"
  default     = "{tags.get('cost-center', '123')}"
}}

variable "managed_by" {{
  type        = string
  description = "Managed by tag"
  default     = "{tags.get('managed-by', 'claude')}"
}}
"""

    outputs_tf = f"""output "bucket_id" {{
  description = "ID of the S3 bucket"
  value       = aws_s3_bucket.{hcl_name}.id
}}

output "bucket_arn" {{
  description = "ARN of the S3 bucket"
  value       = aws_s3_bucket.{hcl_name}.arn
}}
"""

    files = {
        "main.tf": main_tf,
        "variables.tf": variables_tf,
        "outputs.tf": outputs_tf
    }

    # Handle output directory
    if output_dir is None:
        target_dir = tempfile.mkdtemp(prefix="tf_gen_")
    else:
        target_dir = output_dir
        os.makedirs(target_dir, exist_ok=True)

    for filename, content in files.items():
        file_path = os.path.join(target_dir, filename)
        with open(file_path, "w") as f:
            f.write(content)

    return {
        "files": files,
        "output_dir": os.path.abspath(target_dir),
        "status": "success"
    }
