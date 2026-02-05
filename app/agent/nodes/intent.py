import sys
from app.agent.state import AgentState
from app.logging.audit import log_event
from app.agent.llm import classify_intent

def extract_intent(state: AgentState) -> AgentState:
    # Debug logging to stderr (appears in CloudWatch)
    print(f"🔍 DEBUG: Calling LLM with input: '{state.user_input}'", file=sys.stderr)
    
    result = classify_intent(state.user_input)
    state.intent = result.get("intent", "unknown")
    
    print(f"🔍 DEBUG: Classified intent = '{state.intent}'", file=sys.stderr)
    
    # Proper audit log
    log_event("intent_classified", state.session_id, {"intent": state.intent})
    
    return state
