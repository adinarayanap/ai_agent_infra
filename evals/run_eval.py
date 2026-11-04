import json
import os
import subprocess
from pathlib import Path

# Configure path to the agent handler
AGENT_HANDLER = "src.agent.handler.handler"

def run_eval():
    prompts_dir = Path("evals/prompts")
    results = []

    # 1. Load all prompt files
    prompt_files = list(prompts_dir.glob("*.json"))

    total_prompts = 0
    passed_valid = 0
    passed_rejected = 0
    total_valid = 0
    total_rejected = 0

    print(f"Starting evaluation of {len(prompt_files)} prompts...")

    for file_path in prompt_files:
        if file_path.name == "README.md":
            continue

        with open(file_path, "r") as f:
            test_case = json.load(f)

        total_prompts += 1
        expected = test_case["expected_outcome"]

        # 2. Invoke Agent Handler (simulate Lambda invocation)
        # Note: In a real environment, we'd use a lambda test runner or mock
        # For now, we import and call the handler directly
        from src.agent.handler import handler

        event = {"message": test_case["prompt"]}
        response = handler(event, {})
        response_body = json.loads(response["body"])

        # 3. Analyze response (simplified logic)
        actual_status = "approved" if "resources" in response_body else "rejected"

        result = {
            "id": test_case["id"],
            "expected": expected,
            "actual": actual_status,
            "pass": expected == actual_status
        }
        results.append(result)

        if expected == "approved":
            total_valid += 1
            if result["pass"]: passed_valid += 1
        else:
            total_rejected += 1
            if result["pass"]: passed_rejected += 1

    # 4. Generate report
    report_path = Path("evals/results/day08-eval-report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)

    with open(report_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nEvaluation Summary:")
    print(f"Total prompts: {total_prompts}")
    print(f"Schema-valid approved plans: {passed_valid}/{total_valid}")
    print(f"Correctly rejected prompts: {passed_rejected}/{total_rejected}")

    if passed_valid == total_valid and passed_rejected == total_rejected:
        print("Overall pass rate: 100%")
        exit(0)
    else:
        print("Overall pass rate: < 100%")
        exit(1)

if __name__ == "__main__":
    run_eval()
