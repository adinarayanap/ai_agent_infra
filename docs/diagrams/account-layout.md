# Account Layout

## Objective

Separate the Prompt-to-Infra control plane from the environment where
generated infrastructure is deployed.

## Accounts

| Account | Account ID | Purpose |
|---|---:|---|
| Management | 569757034140 | IAM Identity Center, platform identity, future control plane |
| Sandbox | 140023407747 | Safe target account for approved infrastructure deployments |

## Access model

- `ahmed` signs in through IAM Identity Center.
- The Identity Center permission set provides administrative access to both accounts.
- `PromptInfraSandboxBoundary` limits the sandbox automation role.
- The boundary denies IAM user/role creation, Organizations changes, and account-management actions.

## Diagram

```mermaid
flowchart TD
    U[User: ahmed] --> SSO[IAM Identity Center]
    SSO --> M[Management Account\n569757034140]
    SSO --> SB[Sandbox Account\n140023407747]

    M --> ORG[AWS Organization]
    ORG --> SB

    SB --> R[prompt-infra-sandbox-test-role]
    R --> PB[PromptInfraSandboxBoundary]
    PB -->|Allows| INFRA[S3, DynamoDB, Lambda, API Gateway, EC2, CloudWatch]
    PB -->|Denies| IAM[IAM users/roles, Organizations, account settings]
```

## Validation

- SSO login works for both accounts.
- The sandbox test role can create allowed infrastructure resources.
- `iam:CreateUser` is explicitly denied by the permissions boundary.
