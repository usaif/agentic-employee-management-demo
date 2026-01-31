import os
import json
from typing import Dict, Any
import boto3
from botocore.exceptions import ClientError

# Initialize Bedrock client (no API key needed!)
bedrock_client = boto3.client(
    'bedrock-runtime',
    region_name=os.getenv('AWS_REGION', 'us-east-1')
)

# Model configuration
CLAUDE_MODEL_ID = "anthropic.claude-3-5-sonnet-20240620-v1:0"

# ------------------------------------------------------------------
# Prompt (same as before)
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
  "intent": "<intent_value>"
}
""".strip()

# ------------------------------------------------------------------
# Intent classification using Claude on Bedrock
# ------------------------------------------------------------------
def classify_intent(user_input: str) -> Dict[str, Any]:
    """
    Call Claude on Bedrock to classify user intent.
    
    Security benefits over OpenAI:
    - No data leaves AWS network
    - Automatic encryption at rest/transit
    - CloudWatch logging for audit
    - No external API keys to manage
    """
    try:
        # Prepare request body for Claude
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 200,  # Intent classification is short
            "temperature": 0,   # Deterministic output
            "messages": [
                {
                    "role": "user",
                    "content": f"{INTENT_SYSTEM_PROMPT}\n\nUser input: {user_input}"
                }
            ]
        }
        
        # Invoke Claude on Bedrock
        response = bedrock_client.invoke_model(
            modelId=CLAUDE_MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body)
        )
        
        # Parse response
        response_body = json.loads(response['body'].read())
        
        # Extract text from Claude's response
        # Claude returns: {"content": [{"type": "text", "text": "..."}]}
        content = response_body.get('content', [])
        if content and content[0].get('type') == 'text':
            text_response = content[0]['text']
            
            try:
                # Parse JSON from Claude's response
                parsed = json.loads(text_response)
                return parsed
            except json.JSONDecodeError:
                print(f"⚠️  Claude returned non-JSON: {text_response}")
                return {"intent": "unknown"}
        
        return {"intent": "unknown"}
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        print(f"❌ Bedrock error ({error_code}): {e}")
        
        # Handle specific errors
        if error_code == 'AccessDeniedException':
            print("💡 Ensure your IAM role has bedrock:InvokeModel permission")
        elif error_code == 'ResourceNotFoundException':
            print("💡 Ensure model access is enabled in Bedrock console")
        elif error_code == 'ThrottlingException':
            print("💡 Rate limit exceeded, implement exponential backoff")
        
        return {"intent": "unknown"}
    
    except Exception as e:
        print(f"❌ Unexpected error calling Claude: {e}")
        return {"intent": "unknown"}


# ------------------------------------------------------------------
# Optional: Enhanced intent classification with reasoning
# ------------------------------------------------------------------
def classify_intent_with_reasoning(user_input: str) -> Dict[str, Any]:
    """
    Enhanced version that asks Claude to explain its reasoning.
    Useful for debugging and audit logs.
    """
    enhanced_prompt = INTENT_SYSTEM_PROMPT + """

Additionally, provide a brief reasoning for your classification.

Return format:
{
  "intent": "<intent_value>",
  "reasoning": "<brief explanation>"
}
"""
    
    try:
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 300,
            "temperature": 0,
            "messages": [
                {
                    "role": "user",
                    "content": f"{enhanced_prompt}\n\nUser input: {user_input}"
                }
            ]
        }
        
        response = bedrock_client.invoke_model(
            modelId=CLAUDE_MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response['body'].read())
        content = response_body.get('content', [])
        
        if content and content[0].get('type') == 'text':
            text_response = content[0]['text']
            try:
                parsed = json.loads(text_response)
                print(f"🧠 Claude reasoning: {parsed.get('reasoning', 'N/A')}")
                return parsed
            except json.JSONDecodeError:
                return {"intent": "unknown", "reasoning": "Parse error"}
        
        return {"intent": "unknown", "reasoning": "No response"}
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return {"intent": "unknown", "reasoning": str(e)}
