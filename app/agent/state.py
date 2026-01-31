from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class AgentState(BaseModel):
    """
    Persistent state for a single agent session.

    This state is:
    - Loaded at the start of every agent invocation
    - Mutated by LangGraph nodes
    - Serialized and persisted after execution

    Phase 1 characteristics:
    - State is trusted across runs
    - No automatic reset on authentication
    - No provenance tracking
    """
    
    # ------------------------------------------------------------------
    # Session context
    # ------------------------------------------------------------------

    session_id: Optional[str] = None
    
    # ------------------------------------------------------------------
    # Current user input
    # ------------------------------------------------------------------

    user_input: str | None = None
    
    # ------------------------------------------------------------------
    # Agent response to user
    # ------------------------------------------------------------------

    response: str | None = None

    # ------------------------------------------------------------------
    # Identity / authentication context
    # ------------------------------------------------------------------

    authenticated: bool = False
    employee_id: Optional[int] = None
    role: Optional[str] = None  # employee | manager | hr

    # ------------------------------------------------------------------
    # Agent reasoning & planning
    # ------------------------------------------------------------------

    intent: Optional[str] = None
    selected_api: Optional[str] = None
    api_args: Optional[Dict[str, Any]] = None

    # ------------------------------------------------------------------
    # Human-in-the-loop (self-confirmation)
    # ------------------------------------------------------------------
    hitl_confirmed: bool = False
    awaiting_confirmation: bool = False
    pending_action: Optional[str] = None

    # ------------------------------------------------------------------
    # Workflow progression / onboarding
    # ------------------------------------------------------------------

    onboarding_complete: bool = False
    current_step: Optional[str] = None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def reset_plan(self):
        """
        Reset only execution-related fields.

        NOTE:
        - Identity is preserved
        - Historical context is preserved
        - This is intentionally partial
        """
        self.intent = None
        self.selected_api = None
        self.api_args = None
        self.awaiting_confirmation = False
        self.pending_action = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize state for persistence.
        """
        return self.dict()

    @classmethod
    def from_dict(cls, data: dict):
        """
        Rehydrate AgentState from persisted dict WITHOUT
        resetting missing fields to defaults.
        """
        state = cls()  # start with defaults
        for key, value in data.items():
            if hasattr(state, key):
                setattr(state, key, value)
        return state

