import subprocess
import os
import tempfile
import shutil

def validate_terraform(files: dict) -> dict:
    """
    Validates Terraform files using only terraform fmt -check -recursive.
    'terraform validate' is deferred to a prepared pipeline directory.
    The agent never runs terraform init.
    """
    tmp_dir = tempfile.mkdtemp()
    try:
        for name, content in files.items():
            with open(os.path.join(tmp_dir, name), "w") as f:
                f.write(content)

        # Only run fmt -check
        result = subprocess.run(
            ["terraform", "fmt", "-check", "-recursive"],
            cwd=tmp_dir,
            capture_output=True,
            text=True
        )

        # Filter empty stderr lines
        errors = [line for line in result.stderr.splitlines() if line.strip()]

        return {
            "valid": result.returncode == 0,
            "fmt_passed": result.returncode == 0,
            "validate_passed": None, # Deferred
            "errors": errors
        }
    finally:
        shutil.rmtree(tmp_dir)
