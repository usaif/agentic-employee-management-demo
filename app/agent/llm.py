import os
import json
from typing import Dict, Any
from openai import OpenAI

if not os.getenv("OPENAI_API_KEY"):
    raise RuntimeError("OPENAI_API_KEY is not set")

# ------------------------------------------------------------------
# OpenAI client
# ------------------------------------------------------------------

client = OpenAI()

# ------------------------------------------------------------------
# Prompt
# ------------------------------------------------------------------

INTENT_SYSTEM_PROMPT = """
You are an intent classification engine for an internal employee management system.

Your task:
- Read the user input
- Classify the intent into ONE of the following values:

Allowed intents:
- onboarding
- authenticate
- view_self
- view_employee
- update_employee
- delete_employee
- unknown

Rules:
- Do NOT infer authorization or role.
- Do NOT decide whether the action is allowed.
- Do NOT suggest alternatives.
- Do NOT add explanations.

Return ONLY valid JSON in the following format:

{
  "intent": "<one of the allowed intents>"
}
""".strip()


# ------------------------------------------------------------------
# Intent classification
# ------------------------------------------------------------------

def classify_intent(user_input: str) -> Dict[str, Any]:
    """
    Call the LLM to classify user intent.

    Phase 1 characteristics:
    - Deterministic (temperature = 0)
    - Narrow scope (classification only)
    - Output is trusted by downstream logic
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=[
            {"role": "system", "content": INTENT_SYSTEM_PROMPT},
            {"role": "user", "content": user_input},
        ],
    )

    content = response.choices[0].message.content

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        # Fail open (intentionally unsafe)
        return {"intent": "unknown"}

    return parsed
