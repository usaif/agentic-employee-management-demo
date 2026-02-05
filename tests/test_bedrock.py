import os
os.environ['AWS_REGION'] = 'us-east-1'

from app.agent.llm import classify_intent

print("Testing Bedrock LLM classification...")
result = classify_intent("Login with email mark.jensen@company.com and access code 123456")
print(f"\n✅ Result: {result}")
print(f"✅ Intent: {result.get('intent')}")
