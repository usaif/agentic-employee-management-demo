You’re right — thank you for calling that out. Below is the **full, continuous article text**, end to end, exactly as we’ve finalized it. You can copy–paste this directly and save it however you like.

---

# Building Secure Agentic Workflows on AWS Bedrock

## Before We Begin

This article assumes familiarity with deploying agent-based applications using AWS Bedrock AgentCore. If you need a primer on AgentCore concepts and deployment models, refer to the official AWS Bedrock AgentCore documentation before continuing.

We’ll use an employee management agent as a concrete example to demonstrate how to design and secure an agentic workflow. The agent is deployed on Bedrock AgentCore and uses Claude 3.5 Sonnet via Amazon Bedrock as its underlying model.

This article focuses on building secure agentic workflows using cloud-native security controls, with AWS Bedrock providing the foundation for model-level and runtime protections.

---

## Section 1: Bedrock Guardrails (Model-Level Protection)

Amazon Bedrock Guardrails provide configurable safeguards that evaluate model inputs and outputs against safety and policy rules. Guardrails operate at the model invocation boundary and allow you to apply security controls without changing agent logic.

When a model is invoked with an attached guardrail, the input prompt is evaluated first. If the prompt violates a configured policy—such as a detected prompt injection attempt—the request is blocked and the model inference is not executed. If the input passes validation, the model runs normally and its output is then evaluated before being returned.

This makes guardrails an effective first line of defense against common LLM-specific threats such as prompt injection and instruction manipulation.

### Configuring Guardrails in the AWS Console

Guardrails are configured directly in the Amazon Bedrock console. For this example, the following guardrail types are enabled:

* Prompt attack detection
* Content moderation filters (for abusive or unsafe prompts)
* Optional sensitive information detection (configured but not demonstrated)

These controls represent the types of protections available in Bedrock. For the purpose of this article, we focus on demonstrating how **prompt attack detection** behaves once configured.

*(AWS Console screenshots showing guardrail configuration are included here.)*

### Demo: Prompt Injection Protection

To validate the setup, we issue a prompt designed to bypass authorization checks and force the agent to reveal restricted employee data.

Without guardrails, the prompt reaches the agent workflow and is only rejected later by application-level authorization logic. With guardrails enabled, the request is blocked immediately at the model boundary.

CloudWatch logs show the guardrail intervention, and the agent returns a blocked response without executing downstream logic. This reduces attack surface and avoids unnecessary agent execution.

> **Note:** Guardrails complement application authorization logic; they do not replace it. Both are required for defense-in-depth.

---

## Section 2: Programmatic Guardrail Validation at the Agent Boundary

By default, Bedrock Guardrails are automatically enforced when models are invoked. For most agents, this behavior is sufficient.

In some cases, however, teams may choose to perform **explicit guardrail validation at the agent entry point** before executing orchestration logic. This is an optional pattern and should be used selectively.

### When Explicit Validation Makes Sense

Pre-orchestration validation can be useful when you need:

* Fail-fast behavior before expensive agent workflows
* Custom error messaging for blocked inputs
* Independent audit or telemetry for validation events

### Trade-offs to Consider

This approach introduces additional latency and duplicates enforcement, since guardrails will still execute again at model invocation time. Both checks run independently.

As a result, explicit validation should be reserved for high-risk entry points rather than applied universally.

---

## Section 3: Infrastructure Security for Bedrock Agents

The previous sections focused on securing the model and the agent workflow. This section shifts outward to the **infrastructure layer**—controlling who can invoke the agent, how often it can be invoked, where it can be accessed from, and how activity is monitored.

Infrastructure security constrains blast radius and enforces operational boundaries around agent execution.

### IAM Access Control: Who Can Invoke the Agent

IAM is the primary mechanism for controlling access to Bedrock AgentCore agents.

When an agent is deployed, Bedrock assumes an execution role to invoke models and emit logs. Application callers should be granted only the permissions required to invoke the agent and write logs.

A minimal runtime policy typically looks like this:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock-agentcore:InvokeAgent"
      ],
      "Resource": "arn:aws:bedrock:REGION:ACCOUNT:agent/agent-id"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:REGION:ACCOUNT:log-group:/aws/bedrock-agentcore/*"
    }
  ]
}
```

This limits impact if credentials are compromised and prevents accidental misuse.

### Guardrails and IAM in Multi-Account Environments

Bedrock Guardrails are account-scoped resources managed through control-plane APIs. IAM determines who can create or modify guardrails.

In practice:

* Security or platform roles manage guardrail definitions
* Application execution roles can reference approved guardrail IDs and versions, but cannot modify them

Guardrails are typically deployed consistently across accounts using automation and protected as policy-as-code.

### Rate Limiting and Edge Protection

Amazon Bedrock enforces service-level quotas for model invocation. For many internal agents, these built-in limits are sufficient.

When agents are exposed through application APIs—such as FastAPI endpoints for session creation or chat handling—those endpoints can be fronted by API Gateway. API Gateway enforces authentication, throttling, and optional WAF protections, while the application invokes Bedrock internally using IAM-scoped permissions.

### Network Exposure and Monitoring

For internal agents, VPC endpoints or PrivateLink can be used to keep traffic off the public internet. Bedrock runtime access should remain private and scoped to trusted applications.

At a minimum:

* CloudWatch Logs provide operational visibility
* CloudTrail records Bedrock API usage for audit purposes

### Key Takeaway

Infrastructure controls define who can call your agent, from where, and under what limits. They complement—but do not replace—model guardrails or application-level defenses.

---

## Section 4: Enforcing Data Contracts Between Agents and Code

Up to this point, we’ve focused on securing who can invoke an agent, how it behaves at runtime, and where it can be exposed. One boundary still remains: **the interface between the agent and application code**.

Even when a request is authenticated, guarded, and rate-limited, an agent’s output is still untrusted data once it is consumed programmatically. If that output is passed into tools, persisted to storage, or used to drive control flow, it must be validated explicitly—just like any other external input.

This is not a cloud-native concern, but an application-level one. The goal here is not to constrain model behavior, but to enforce **data contracts** between the agent and the systems it interacts with.

### Validating Machine-Consumed Outputs

When agent responses are intended for humans, flexibility is acceptable. When responses are intended for code, structure matters.

In Python-based agent APIs, schema enforcement is most naturally implemented using Pydantic models. These models define the expected shape, types, and bounds of data before it is trusted by application logic.

```python
from pydantic import BaseModel, Field

class EmployeeProfile(BaseModel):
    name: str = Field(..., max_length=100)
    email: str
    role: str = Field(..., regex="^(employee|manager|hr)$")
    location: str | None = None
```

After an LLM call, structured outputs are validated once at the boundary. If validation fails, execution stops immediately and the event is logged. This fail-fast behavior prevents malformed or partial outputs from propagating deeper into the system.

### Bounding Outputs vs. Validating Them

Model parameters such as `max_tokens` are useful for bounding output size and controlling cost, but they do not guarantee correctness or structure. Schema validation complements these controls by ensuring that application code only processes data it explicitly understands.

### When This Matters—and When It Doesn’t

Schema enforcement is most valuable when agent outputs drive tool execution, are persisted, or influence control flow. For purely conversational agents with a human in the loop, this layer can often be skipped.

---

### Final Takeaway

Guardrails protect models.
Infrastructure controls protect access.
**Data contracts protect your code.**

