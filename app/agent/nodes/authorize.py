from app.agent.state import AgentState
from app.logging.audit import log_event


def authorize_action(state: AgentState) -> AgentState:
    """
    Authorization gate for agent actions.

    Rules:
    - Authorization is enforced ONLY when an action is selected
    - Login and onboarding are allowed pre-auth
    - RBAC is enforced strictly on `selected_api`
    """

    session_id = state.session_id
    role = state.role
    action = state.selected_api

    # --------------------------------------------------
    # 1. No action selected yet → nothing to authorize
    # --------------------------------------------------
    if action is None:
        return state

    # --------------------------------------------------
    # 2. Allow pre-auth flows
    # --------------------------------------------------
    if action in ("login", "authenticate", "onboard_user"):
        log_event(
            "authorization_allow",
            session_id,
            {"action": action, "reason": "pre-auth flow"},
        )
        return state

    # --------------------------------------------------
    # 3. Must be authenticated for everything else
    # --------------------------------------------------
    if not state.authenticated:
        log_event(
            "authorization_deny",
            session_id,
            {"action": action, "reason": "unauthenticated"},
        )
        raise PermissionError("User not authenticated")

    # --------------------------------------------------
    # 4. Employee permissions
    # --------------------------------------------------
    if role == "employee":
        if action == "get_my_profile":
            log_event(
                "authorization_allow",
                session_id,
                {"role": role, "action": action},
            )
            return state

        log_event(
            "authorization_deny",
            session_id,
            {"role": role, "action": action},
        )
        raise PermissionError("Employees may only view their own profile")

    # --------------------------------------------------
    # 5. Manager permissions (read-only)
    # --------------------------------------------------
    if role == "manager":
        if action in ("get_my_profile", "get_employee"):
            log_event(
                "authorization_allow",
                session_id,
                {"role": role, "action": action},
            )
            return state

        log_event(
            "authorization_deny",
            session_id,
            {"role": role, "action": action},
        )
        raise PermissionError("Managers have read-only access")

    # --------------------------------------------------
    # 6. HR permissions (full access)
    # --------------------------------------------------
    if role == "hr":
        log_event(
            "authorization_allow",
            session_id,
            {"role": role, "action": action},
        )
        return state

    # --------------------------------------------------
    # 7. Unknown role
    # --------------------------------------------------
    log_event(
        "authorization_deny",
        session_id,
        {"role": role, "action": action},
    )
    raise PermissionError("Unknown role")
