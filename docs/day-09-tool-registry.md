# Architectural Evolution: Tool Registry and Tool-Use Loop

This document outlines the architectural changes implemented to move the agent from raw JSON output to structured Tool-Use.

---
Day 09 is closed. The tool registry, Converse tool-use loop, plan validator, iteration guard, and security controls are implemented and verified through mocked unit tests. A live Bedrock tool-loop smoke test remains pending because of an authentication issue; basic Mistral Large 3 Converse access was previously verified. Resolving live authentication is the first Day 10 task before implementing UC1 Terraform generation.

## 1. Summary of Changes
*   **Tool Registry**: Implemented `src/agent/tool_registry.py` to define the `generate_terraform` tool schema.
*   **Tool-Use Loop**: Refactored `src/agent/handler.py` to use Bedrock's `toolConfig`. The handler now:
    1.  Invokes Mistral Large 3 with tool definitions.
    2.  Checks the agent's response for `toolUse`.
    3.  Extracts the `plan` from the tool input.
    4.  Runs the `plan_validator` on the extracted plan.
    5.  Returns the validated plan or a rejection response.

## 2. Why Tool-Use? (Project Rationale)
*   **Improved Instruction Adherence**: Forcing the agent to call a specific tool (`generate_terraform`) significantly reduces hallucinated formatting and ensures the agent provides structured data in the format our `plan_validator` expects.
*   **Separation of Concerns**: The "Brain" (LLM) now focuses on the planning, while the "Tool" (a future implementation of `generate_terraform`) focuses on HCL production.
*   **Extensibility**: This architecture allows us to easily add more tools (e.g., `validate_terraform`, `summarise_plan`) in the future without changing the core invocation logic.

## 3. Security
*   The agent is strictly instructed to only use approved tools.
*   The agent does not have permissions to execute these tools; it only requests them. 
*   The `plan_validator` acts as the final gatekeeper for the tool input.
