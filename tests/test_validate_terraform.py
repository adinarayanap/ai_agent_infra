import pytest
import subprocess
import textwrap
from unittest.mock import patch, MagicMock
from pathlib import Path
from src.agent.tools.validate_terraform import validate_terraform, TerraformValidationError

def test_validate_terraform_missing_inputs():
    with pytest.raises(ValueError, match="Either 'files' or 'directory' must be provided"):
        validate_terraform(files=None, directory=None)

    with pytest.raises(ValueError, match="Only one of 'files' or 'directory' can be provided"):
        validate_terraform(files={"main.tf": ""}, directory="/some/path")

def test_validate_terraform_invalid_directory():
    with pytest.raises(ValueError, match="Provided directory does not exist"):
        validate_terraform(directory="/nonexistent/path/12345")

@patch("subprocess.run")
def test_validate_terraform_mock_success(mock_run):
    # Mock successful run for init, fmt, and validate
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "Success"
    mock_result.stderr = ""
    mock_run.return_value = mock_result

    files = {"main.tf": 'resource "aws_s3_bucket" "b" { bucket = "test" }'}
    result = validate_terraform(files=files)

    assert result["valid"] is True
    assert result["fmt_passed"] is True
    assert result["validate_passed"] is True
    assert result["errors"] == []

@patch("subprocess.run")
def test_validate_terraform_mock_fmt_failure(mock_run):
    # Mock fmt failure (returncode 1)
    mock_init = MagicMock(returncode=0, stdout="", stderr="")
    mock_fmt = MagicMock(returncode=1, stdout="main.tf\n", stderr="")
    mock_val = MagicMock(returncode=0, stdout="Success", stderr="")

    mock_run.side_effect = [mock_init, mock_fmt, mock_val]

    files = {"main.tf": 'resource "aws_s3_bucket" "b" {bucket = "test"}'}
    result = validate_terraform(files=files)

    assert result["valid"] is False
    assert result["fmt_passed"] is False
    assert result["validate_passed"] is True
    assert len(result["errors"]) > 0

@patch("subprocess.run")
def test_validate_terraform_mock_validate_failure(mock_run):
    # Mock validate failure (returncode 1)
    mock_init = MagicMock(returncode=0, stdout="", stderr="")
    mock_fmt = MagicMock(returncode=0, stdout="", stderr="")
    mock_val = MagicMock(returncode=1, stdout="", stderr="Error: Missing required argument")

    mock_run.side_effect = [mock_init, mock_fmt, mock_val]

    files = {"main.tf": 'resource "aws_s3_bucket" "b" {}'}
    result = validate_terraform(files=files)

    assert result["valid"] is False
    assert result["fmt_passed"] is True
    assert result["validate_passed"] is False
    assert len(result["errors"]) > 0

@patch("subprocess.run")
def test_validate_terraform_mock_terraform_not_found(mock_run):
    mock_run.side_effect = FileNotFoundError("terraform not found")

    files = {"main.tf": 'resource "aws_s3_bucket" "b" {}'}
    with pytest.raises(TerraformValidationError, match="Terraform executable not found"):
        validate_terraform(files=files)

def test_validate_terraform_real_valid_hcl():
    # Real test using terraform binary if installed
    try:
        subprocess.run(["terraform", "--version"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        pytest.skip("Terraform binary not available for real test.")

    valid_hcl = {
        "main.tf": textwrap.dedent('''\
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "ap-south-1"
}

resource "aws_s3_bucket" "test_bucket" {
  bucket = "ai-agent-infra-test-bucket-123456"
}
'''),
        "variables.tf": textwrap.dedent('''\
variable "environment" {
  type    = string
  default = "dev"
}
'''),
        "outputs.tf": textwrap.dedent('''\
output "bucket_id" {
  value = aws_s3_bucket.test_bucket.id
}
''')
    }

    result = validate_terraform(files=valid_hcl)
    assert result["valid"] is True
    assert result["fmt_passed"] is True
    assert result["validate_passed"] is True
    assert result["errors"] == []

def test_validate_terraform_real_syntax_error():
    try:
        subprocess.run(["terraform", "--version"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        pytest.skip("Terraform binary not available for real test.")

    invalid_hcl = {
        "main.tf": '''
resource "aws_s3_bucket" "test_bucket" {
  bucket = "ai-agent-infra-test-bucket-123456"
  # Missing closing brace
'''}

    result = validate_terraform(files=invalid_hcl)
    assert result["valid"] is False
    assert result["validate_passed"] is False
    assert len(result["errors"]) > 0
