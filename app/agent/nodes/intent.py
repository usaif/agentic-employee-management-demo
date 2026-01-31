from app.agent.state import AgentState
from app.logging.audit import log_event


def extract_intent(state: AgentState) -> AgentState:
    """
    Classify high-level user intent.

    This is intentionally simple and deterministic
    for demo and testing purposes.
    """

    user_input = (state.user_input or "").lower()

    # --------------------------------------------------
    # ONBOARDING
    # --------------------------------------------------
    if any(kw in user_input for kw in ["onboard", "sign up", "register"]):
        state.intent = "onboard"
        log_event(
            "intent_onboard",
            state.session_id,
            {"input": state.user_input},
        )
        return state

    # --------------------------------------------------
    # AUTHENTICATION
    # --------------------------------------------------
    if any(kw in user_input for kw in ["login", "log in", "sign in"]):
        state.intent = "authenticate"
        log_event(
            "intent_authenticate",
            state.session_id,
            {"input": state.user_input},
        )
        return state

    # --------------------------------------------------
    # DELETE
    # --------------------------------------------------
    if "delete" in user_input or "remove" in user_input:
        state.intent = "delete_employee"
        log_event(
            "intent_delete_employee",
            state.session_id,
            {"input": state.user_input},
        )
        return state

    # --------------------------------------------------
    # UPDATE
    # --------------------------------------------------
    if "update" in user_input or "change" in user_input:
        state.intent = "update_employee"
        log_event(
            "intent_update_employee",
            state.session_id,
            {"input": state.user_input},
        )
        return state

    # --------------------------------------------------
    # VIEW SELF
    # --------------------------------------------------
    if any(kw in user_input for kw in ["my profile", "show my", "me"]):
        state.intent = "view_self"
        log_event(
            "intent_view_self",
            state.session_id,
            {"input": state.user_input},
        )
        return state

    # --------------------------------------------------
    # VIEW EMPLOYEE
    # --------------------------------------------------
    if "show" in user_input or "view" in user_input:
        state.intent = "view_employee"
        log_event(
            "intent_view_employee",
            state.session_id,
            {"input": state.user_input},
        )
        return state

    # --------------------------------------------------
    # DEFAULT
    # --------------------------------------------------
    state.intent = "unknown"
    log_event(
        "intent_unknown",
        state.session_id,
        {"input": state.user_input},
    )
    return state
