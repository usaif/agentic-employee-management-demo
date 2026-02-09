import os
import json
import sys
from typing import Dict, Any
import boto3
from botocore.exceptions import ClientError

# Initialize Bedrock client
bedrock_client = boto3.client(
    "bedrock-runtime", region_name=os.getenv("AWS_REGION", "us-east-1")
)

# Model configuration
CLAUDE_MODEL_ID = "anthropic.claude-3-5-sonnet-20240620-v1:0"

# Guardrail configuration
GUARDRAIL_ID = "[UPDATE_ID_HERE]"
GUARDRAIL_VERSION = "1"

# Intent System Prompt
INTENT_SYSTEM_PROMPT = """
You are an intent classification engine for an internal employee management system.

Your task:
- Read the user input
- Classify the intent into ONE of the following values:

Allowed intents:
- onboard
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
  "intent": "<intent>"
}
""".strip()


def classify_intent(user_input: str) -> Dict[str, Any]:
    """
    Call Claude on Bedrock to classify user intent with Guardrails.
    """
    print(f"🔍 LLM: Starting classification for: {user_input}", file=sys.stderr)

    try:
        # Prepare request body for Claude
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 200,
            "temperature": 0,
            "messages": [
                {
                    "role": "user",
                    "content": f"{INTENT_SYSTEM_PROMPT}\n\nUser input: {user_input}",
                }
            ],
        }

        print(f"🔍 LLM: Calling Bedrock with model {CLAUDE_MODEL_ID}", file=sys.stderr)
        print(
            f"🔍 LLM: Using guardrail {GUARDRAIL_ID} version {GUARDRAIL_VERSION}",
            file=sys.stderr,
        )

        # Invoke Claude on Bedrock with Guardrails
        response = bedrock_client.invoke_model(
            modelId=CLAUDE_MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body),
            guardrailIdentifier=GUARDRAIL_ID,
            guardrailVersion=GUARDRAIL_VERSION,
        )

        # Parse the response body
        response_body = json.loads(response["body"].read())

        # ✅ CHECK FOR GUARDRAIL INTERVENTION
        guardrail_action = response_body.get("amazon-bedrock-guardrailAction")

        if guardrail_action == "INTERVENED":
            print("🛡️ GUARDRAIL BLOCKED THIS REQUEST!", file=sys.stderr)
            print(
                f"🛡️ Trace: {json.dumps(response_body.get('amazon-bedrock-trace', {}))}",
                file=sys.stderr,
            )

            return {
                "intent": "blocked",
                "reason": "Guardrail intervention - potentially harmful content detected",
            }

        print(f"🔍 LLM: Response keys: {list(response_body.keys())}", file=sys.stderr)

        # Extract text from Claude's response
        content = response_body.get("content", [])
        if content and len(content) > 0 and content[0].get("type") == "text":
            text_response = content[0]["text"]
            print(f"🔍 LLM: Claude returned: {text_response}", file=sys.stderr)

            try:
                parsed = json.loads(text_response)

                # ✅ UPDATED: Add "blocked" to valid intents
                valid_intents = {
                    "onboard",
                    "authenticate",
                    "view_self",
                    "view_employee",
                    "update_employee",
                    "delete_employee",
                    "unknown",
                    "blocked",
                }

                intent = parsed.get("intent", "unknown")

                if intent not in valid_intents:
                    print(
                        f"⚠️ Invalid intent '{intent}', defaulting to 'unknown'",
                        file=sys.stderr,
                    )
                    return {"intent": "unknown"}

                print(f"✅ LLM: Successfully classified as '{intent}'", file=sys.stderr)
                return parsed

            except json.JSONDecodeError as e:
                print(f"⚠️ Claude returned non-JSON: {text_response}", file=sys.stderr)
                print(f"   Parse error: {e}", file=sys.stderr)
                return {"intent": "unknown"}

        print(
            f"⚠️ No valid content in Claude response. Full response: {json.dumps(response_body)[:500]}",
            file=sys.stderr,
        )
        return {"intent": "unknown"}

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_msg = e.response["Error"].get("Message", str(e))
        print(f"❌ Bedrock ClientError ({error_code}): {error_msg}", file=sys.stderr)

        # Handle specific errors
        if error_code == "AccessDeniedException":
            print(
                "💡 Ensure your IAM role has bedrock:InvokeModel and bedrock:ApplyGuardrail permissions",
                file=sys.stderr,
            )
        elif error_code == "ResourceNotFoundException":
            print(
                "💡 Check: 1) Model access enabled in Bedrock console, 2) Guardrail ID is correct",
                file=sys.stderr,
            )
        elif error_code == "ThrottlingException":
            print("💡 Rate limit exceeded", file=sys.stderr)
        elif error_code == "ValidationException":
            print("💡 Check guardrail version and model ID", file=sys.stderr)

        return {"intent": "unknown"}

    except Exception as e:
        print(f"❌ Unexpected error: {type(e).__name__}: {e}", file=sys.stderr)
        import traceback

        print(traceback.format_exc(), file=sys.stderr)
        return {"intent": "unknown"}


# Optional: Enhanced intent classification with reasoning
def classify_intent_with_reasoning(user_input: str) -> Dict[str, Any]:
    """
    Enhanced version that asks Claude to explain its reasoning.
    Useful for debugging and audit logs.
    """
    enhanced_prompt = (
        INTENT_SYSTEM_PROMPT
        + """
Additionally, provide a brief reasoning for your classification.

Return format:
{
  "intent": "<intent>",
  "reasoning": "<brief_explanation>"
}
"""
    )

    try:
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 300,
            "temperature": 0,
            "messages": [
                {
                    "role": "user",
                    "content": f"{enhanced_prompt}\n\nUser input: {user_input}",
                }
            ],
        }

        response = bedrock_client.invoke_model(
            modelId=CLAUDE_MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body),
            guardrailIdentifier=GUARDRAIL_ID,
            guardrailVersion=GUARDRAIL_VERSION,
        )

        response_body = json.loads(response["body"].read())

        # Check for guardrail intervention
        guardrail_action = response_body.get("amazon-bedrock-guardrailAction")
        if guardrail_action == "INTERVENED":
            return {
                "intent": "blocked",
                "reasoning": "Guardrail blocked potentially harmful content",
            }

        content = response_body.get("content", [])
        if content and content[0].get("type") == "text":
            text_response = content[0]["text"]
            try:
                parsed = json.loads(text_response)
                print(
                    f"🧠 Claude reasoning: {parsed.get('reasoning', 'N/A')}",
                    file=sys.stderr,
                )
                return parsed
            except json.JSONDecodeError:
                return {"intent": "unknown", "reasoning": "Parse error"}

        return {"intent": "unknown", "reasoning": "No response"}

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return {"intent": "unknown", "reasoning": str(e)}
