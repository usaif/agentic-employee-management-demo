from app.agent.state import AgentState
from app.logging.audit import log_event


def handle_hitl(state: AgentState):
    """
    Human-in-the-loop confirmation for destructive actions.

    RULE:
    - HITL must NOT mutate selected_api
    - It must block execution by setting response and a flag
    """

    if state.selected_api != "delete_employee":
        return state

    # Already confirmed → allow execution
    if state.hitl_confirmed:
        return state

    user_input = (state.user_input or "").strip().lower()

    # Confirmation message
    if user_input in {"yes", "y", "confirm"}:
        state.hitl_confirmed = True
        log_event(
            "hitl_confirmed",
            state.session_id,
            {"action": "delete_employee"},
        )
        return state

    # First delete attempt → ask for confirmation
    state.response = (
        "Are you sure you want to delete this employee? "
        "Reply 'Yes' to confirm."
    )

    log_event(
        "hitl_prompted",
        state.session_id,
        {"action": "delete_employee"},
    )

    # IMPORTANT: do NOT clear selected_api
    # Execution node will check hitl_confirmed
    return state
