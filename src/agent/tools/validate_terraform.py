# src/agent/tools/validate_terraform.py
import os
import subprocess
import tempfile
from typing import Dict, Any, Optional

class TerraformValidationError(Exception):
    """Raised when an environment error occurs during Terraform validation."""
    pass

def validate_terraform(files: Optional[Dict[str, str]] = None, directory: Optional[str] = None) -> Dict[str, Any]:
    """
    Validates Terraform configuration files by running:
    1. terraform init -backend=false
    2. terraform fmt -check -recursive
    3. terraform validate

    Args:
        files: Optional dictionary mapping filenames to content.
        directory: Optional path to an existing directory containing Terraform files.

    Returns:
        dict with validation results: valid, fmt_passed, validate_passed, errors, details.
    """
    if files is None and directory is None:
        raise ValueError("Either 'files' or 'directory' must be provided")

    if files is not None and directory is not None:
        raise ValueError("Only one of 'files' or 'directory' can be provided")

    if directory is not None and not os.path.exists(directory):
        raise ValueError("Provided directory does not exist")

    target_dir = directory
    temp_dir_obj = None

    # Ensure isolated temp dir is created where sufficient disk space exists
    cache_tmp = os.path.expanduser("~/.cache/ai_agent_infra/tmp")
    os.makedirs(cache_tmp, exist_ok=True)
    plugin_cache = os.path.expanduser("~/.terraform.d/plugin-cache")
    os.makedirs(plugin_cache, exist_ok=True)

    env = os.environ.copy()
    env["TF_PLUGIN_CACHE_DIR"] = plugin_cache

    if files is not None:
        temp_dir_obj = tempfile.TemporaryDirectory(dir=cache_tmp, prefix="tf_val_")
        target_dir = temp_dir_obj.name
        for fname, content in files.items():
            file_path = os.path.join(target_dir, fname)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w") as f:
                f.write(content)

    errors = []
    fmt_passed = False
    validate_passed = False

    try:
        # 1. terraform init -backend=false
        try:
            init_res = subprocess.run(
                ["terraform", "init", "-backend=false"],
                cwd=target_dir,
                capture_output=True,
                text=True,
                env=env
            )
        except FileNotFoundError as e:
            raise TerraformValidationError(f"Terraform executable not found: {e}")

        if init_res.returncode != 0:
            errors.append(f"Terraform init failed:\n{init_res.stderr}")

        # 2. terraform fmt check
        fmt_res = subprocess.run(
            ["terraform", "fmt", "-check", "-recursive"],
            cwd=target_dir,
            capture_output=True,
            text=True,
            env=env
        )
        if fmt_res.returncode == 0:
            fmt_passed = True
        else:
            errors.append(f"Terraform formatting check failed:\n{fmt_res.stdout}\n{fmt_res.stderr}")

        # 3. terraform validate
        val_res = subprocess.run(
            ["terraform", "validate"],
            cwd=target_dir,
            capture_output=True,
            text=True,
            env=env
        )
        if val_res.returncode == 0:
            validate_passed = True
        else:
            errors.append(f"Terraform validate failed:\n{val_res.stderr}")

    finally:
        if temp_dir_obj:
            temp_dir_obj.cleanup()

    is_valid = fmt_passed and validate_passed and not errors

    return {
        "valid": is_valid,
        "fmt_passed": fmt_passed,
        "validate_passed": validate_passed,
        "errors": errors,
        "details": "\n".join(errors) if errors else "Terraform validation succeeded."
    }
