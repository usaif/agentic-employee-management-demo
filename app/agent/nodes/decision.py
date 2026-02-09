from app.agent.state import AgentState
from app.database import SessionLocal
from app.models.employee import Employee
from app.logging.audit import log_event


def decide_action(state: AgentState) -> AgentState:
    """
    Decide which backend API to invoke and populate api_args.

    HARD RULES:
    - NEVER mutate authentication or role
    - NEVER infer privilege
    - NEVER silently fall back for destructive actions
    - ALWAYS log decisions
    """

    user_input = (state.user_input or "").lower().strip()
    intent = state.intent

    log_event(
        "decision_start",
        state.session_id,
        {"intent": intent, "input": state.user_input},
    )

    # Handle blocked requests
    if intent == "blocked":
        state.selected_api = None
        state.response = "Your request was blocked due to policy violations."
        log_event(
            "decision_blocked",
            state.session_id,
            {"reason": "guardrail_intervention"},
        )
        return state

    # ------------------------------------------------------------
    # AUTHENTICATION
    # ------------------------------------------------------------
    if intent == "authenticate":
        state.selected_api = "login"
        state.api_args = {}
        log_event(
            "decision_authenticate",
            state.session_id,
            {"selected_api": "login"},
        )
        return state

    # ------------------------------------------------------------
    # ONBOARDING (pre-auth only)
    # ------------------------------------------------------------
    if intent == "onboard":
        state.selected_api = "onboard_user"
        state.api_args = {}
        log_event(
            "decision_onboard",
            state.session_id,
            {"selected_api": "onboard_user"},
        )
        return state

    db = SessionLocal()
    try:
        # --------------------------------------------------------
        # VIEW OWN PROFILE
        # --------------------------------------------------------
        if intent == "view_self":
            state.selected_api = "get_my_profile"
            state.api_args = {}
            log_event(
                "decision_view_self",
                state.session_id,
                {"selected_api": "get_my_profile"},
            )
            return state

        # --------------------------------------------------------
        # VIEW EMPLOYEE
        # --------------------------------------------------------
        if intent == "view_employee":
            state.selected_api = "get_employee"

            for emp in db.query(Employee).all():
                if emp.name.lower() in user_input:
                    state.api_args = {"employee_id": emp.id}
                    log_event(
                        "decision_view_employee",
                        state.session_id,
                        {"employee_id": emp.id},
                    )
                    return state

            # No fallback
            state.api_args = {}
            log_event(
                "decision_view_employee_failed",
                state.session_id,
                {"reason": "employee not resolved"},
            )
            return state

        # --------------------------------------------------------
        # UPDATE EMPLOYEE (GENERIC)
        # --------------------------------------------------------
        if intent == "update_employee":
            state.selected_api = "update_employee"

            # Resolve employee
            target_emp = None
            for emp in db.query(Employee).all():
                if emp.name.lower() in user_input:
                    target_emp = emp
                    break

            if not target_emp:
                state.api_args = {}
                log_event(
                    "decision_update_failed",
                    state.session_id,
                    {"reason": "employee not resolved"},
                )
                return state

            # Expect "update <name> <field> to <value>"
            if "to" not in user_input:
                state.api_args = {}
                log_event(
                    "decision_update_failed",
                    state.session_id,
                    {"reason": "missing value"},
                )
                return state

            before, value = user_input.split("to", 1)
            value = value.strip().title()

            tokens = before.split()
            field = tokens[-1]  # naive but deterministic

            state.api_args = {
                "employee_id": target_emp.id,
                field: value,
            }

            log_event(
                "decision_update_employee",
                state.session_id,
                state.api_args,
            )
            return state

        # --------------------------------------------------------
        # DELETE EMPLOYEE (STRICT)
        # --------------------------------------------------------
        if intent == "delete_employee":
            state.selected_api = "delete_employee"

            for emp in db.query(Employee).all():
                if emp.name.lower() in user_input:
                    state.api_args = {"employee_id": emp.id}
                    log_event(
                        "decision_delete_employee",
                        state.session_id,
                        state.api_args,
                    )
                    return state

            # ❌ No fallback for delete
            state.api_args = {}
            log_event(
                "decision_delete_failed",
                state.session_id,
                {"reason": "employee not resolved"},
            )
            return state

        # --------------------------------------------------------
        # NO-OP
        # --------------------------------------------------------
        log_event(
            "decision_noop",
            state.session_id,
            {"reason": "no actionable intent"},
        )
        return state

    finally:
        db.close()
