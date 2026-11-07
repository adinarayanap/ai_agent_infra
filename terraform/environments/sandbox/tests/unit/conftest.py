import os
import sys

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
SANDBOX_DIR = os.path.abspath(os.path.join(TEST_DIR, "..", ".."))
SRC_DIR = os.path.join(SANDBOX_DIR, "src")
AGENT_DIR = os.path.join(SRC_DIR, "agent")

for path in (SRC_DIR, AGENT_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)
