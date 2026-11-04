#!/usr/bin/env bash
set -euo pipefail

# Verify the system prompt change in handler.py
# This is a basic check to ensure the file exists and has the expected content.

if [ ! -f "src/bedrock_hello/handler.py" ]; then
    echo "Error: handler.py not found"
    exit 1
fi

if grep -q "load_system_prompt" src/bedrock_hello/handler.py; then
    echo "Success: system prompt loading integrated in handler.py"
else
    echo "Error: system prompt loading NOT found in handler.py"
    exit 1
fi

if grep -q "system=\[{\"text\": load_system_prompt()}\]" src/bedrock_hello/handler.py; then
    echo "Success: system prompt correctly utilized in bedrock.converse"
else
    echo "Error: system prompt not correctly utilized in bedrock.converse"
    exit 1
fi

echo "All checks passed."
