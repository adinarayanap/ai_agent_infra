# Architectural Evolution Report: Agent Brain Decoupling

This report details the architectural changes implemented to decouple the "Agent Brain" from the initial `bedrock_hello` Lambda implementation and provides the rationale behind this transformation to meet project requirements.

---

## 1. Summary of Changes

*   **Logic Extraction**: The agent logic was extracted from `src/bedrock_hello/handler.py` and moved into a new, dedicated module structure at `src/agent/`.
*   **New Module Structure**:
    *   `src/agent/handler.py`: Dedicated entry point for agent orchestration.
    *   `src/agent/config.py`: Centralized configuration (model selection, region).
    *   `src/agent/prompts.py`: Externalized system prompt definitions.
    *   `src/agent/schemas/`: Placeholder for infrastructure plan validation schemas.
    *   `src/agent/validators/`: Placeholder for IaC compliance validation logic.
*   **Refined Persona**: The system prompt was significantly evolved from a generic assistant to a specialized **AWS Infrastructure Planning Assistant**, restricted to specific, approved infrastructure use cases (UC1–UC5).

---

## 2. Why Decouple? (Project Rationale)

The decision to move away from a monolithic Lambda handler (`bedrock_hello`) to an independent Agent module (`src/agent/`) was driven by three primary project requirements:

### A. Independent Testability
The original `bedrock_hello` was tightly coupled to API Gateway events and DynamoDB auditing. By decoupling the agent logic into its own module, we can now write **unit tests** for the `plan_validator` and the `handler` without needing to mock complex infrastructure interactions (like database PUTs or API event structures). This drastically improves development velocity and reliability.

### B. Scalable Governance
The new `prompts.py` and `schemas/` directory allow us to enforce strict governance. Instead of relying on a prompt hardcoded within an application file, the agent now operates based on a clear JSON-constrained contract. This allows us to evolve the "Agent Brain" (e.g., adding UC6) without risking side effects in the surrounding application logic (e.g., logging or API authentication).

### C. Evaluation Capability (The "Brain" Requirements)
To support the future requirements of Sprint 2 (Agent Brain), the agent must be able to:
1.  Receive an infrastructure request.
2.  Generate a JSON plan.
3.  **Validate** that plan against security guardrails *before* generating Terraform.

The new `src/agent/validators/` and `evals/` structure provides the necessary "hook" points to implement automated evaluation harnesses in Day 09, ensuring that our agent's output is consistently compliant with our security policies (encryption, least privilege, etc.) before any infrastructure is provisioned.
