from sqlalchemy.orm import Session

from app.agent.state import AgentState
from app.database import SessionLocal
from app.models.employee import Employee
from app.logging.audit import log_event, log_execution


def execute_action(state: AgentState):
    """
    Execute the selected backend action.

    RULES:
    - Never crash
    - Never silently succeed
    - Always set state.response
    - Log everything
    """

    if not state.selected_api:
        state.response = "No action was selected."
        return state

    db: Session = SessionLocal()

    try:
        # --------------------------------------------------------
        # LOGIN
        # --------------------------------------------------------
        if state.selected_api == "login":
            user_input = state.user_input or ""
            email = None

            tokens = user_input.lower().split()
            if "email" in tokens:
                idx = tokens.index("email")
                if idx + 1 < len(tokens):
                    email = tokens[idx + 1]

            if not email:
                state.response = "Could not determine email for login."
                log_event(
                    "auth_failed",
                    state.session_id,
                    {"reason": "email not found"},
                )
                return state

            employee = db.query(Employee).filter(Employee.email == email).first()
            if not employee:
                state.response = "Invalid credentials."
                log_event(
                    "auth_failed",
                    state.session_id,
                    {"reason": "employee not found", "email": email},
                )
                return state

            state.authenticated = True
            state.employee_id = employee.id
            state.role = employee.role
            state.response = "Authenticated successfully."

            log_event(
                "auth_success",
                state.session_id,
                {"employee_id": employee.id, "role": employee.role},
            )
            return state

        # --------------------------------------------------------
        # ONBOARDING
        # --------------------------------------------------------
        if state.selected_api == "onboard_user":
            try:
                user_input = state.user_input or ""
                lower_input = user_input.lower()

                # -----------------------------
                # Extract email
                # -----------------------------
                tokens = lower_input.split()
                email = next((t for t in tokens if "@" in t), None)

                if not email:
                    state.response = "Email is required for onboarding."
                    log_event(
                        "onboarding_failed",
                        state.session_id,
                        {"reason": "email_missing"},
                    )
                    return state

                existing = db.query(Employee).filter(Employee.email == email).first()
                if existing:
                    state.response = "User already onboarded."
                    log_event(
                        "onboarding_failed",
                        state.session_id,
                        {"reason": "user_exists", "email": email},
                    )
                    return state

                # -----------------------------
                # Extract name (deterministic)
                # -----------------------------
                name = "New Employee"
                if "name is" in lower_input:
                    after = lower_input.split("name is", 1)[1]
                    stop_words = [" and", " email", " my email"]
                    for sw in stop_words:
                        if sw in after:
                            after = after.split(sw, 1)[0]
                            break
                    name = after.strip().title()

                # -----------------------------
                # Create employee
                # -----------------------------
                emp = Employee(
                    name=name,
                    email=email,
                    role="employee",  # enforced
                    manager_id=None,
                    salary=0,
                    status="active",
                    location="Unknown",
                )

                db.add(emp)
                db.commit()

                log_event(
                    "onboarding_success",
                    state.session_id,
                    {"employee_id": emp.id, "email": email},
                )

                state.response = "You have been onboarded successfully as an employee."
                return state

            except Exception as e:
                log_event(
                    "onboarding_exception",
                    state.session_id,
                    {"error": str(e)},
                )
                state.response = "Onboarding failed due to a system error."
                return state

        # --------------------------------------------------------
        # VIEW OWN PROFILE
        # --------------------------------------------------------
        if state.selected_api == "get_my_profile":
            emp = db.query(Employee).filter(Employee.id == state.employee_id).first()
            if not emp:
                state.response = "Profile not found."
                return state

            state.response = (
                f"Name: {emp.name} "
                f"Email: {emp.email} "
                f"Role: {emp.role} "
                f"Location: {emp.location}"
            )
            return state

        # --------------------------------------------------------
        # VIEW EMPLOYEE
        # --------------------------------------------------------
        if state.selected_api == "get_employee":
            emp_id = state.api_args.get("employee_id") if state.api_args else None
            if not emp_id:
                state.response = "No employee specified."
                return state

            emp = db.query(Employee).filter(Employee.id == emp_id).first()
            if not emp:
                state.response = "Employee not found."
                return state

            state.response = (
                f"Name: {emp.name} "
                f"Email: {emp.email} "
                f"Role: {emp.role} "
                f"Location: {emp.location}"
            )
            return state

        # --------------------------------------------------------
        # UPDATE EMPLOYEE (GENERIC)
        # --------------------------------------------------------
        if state.selected_api == "update_employee":
            if not state.api_args or "employee_id" not in state.api_args:
                state.response = "Could not determine which employee to update."
                return state

            emp = (
                db.query(Employee)
                .filter(Employee.id == state.api_args["employee_id"])
                .first()
            )

            if not emp:
                state.response = "Employee not found."
                return state

            # Fields that are allowed to be updated
            ALLOWED_FIELDS = {"location", "status", "salary", "name", "role"}

            updated_fields = {}

            for field, value in state.api_args.items():
                if field == "employee_id":
                    continue
                if field not in ALLOWED_FIELDS:
                    log_event(
                        "update_field_blocked",
                        state.session_id,
                        {"field": field},
                    )
                    continue
                setattr(emp, field, value)
                updated_fields[field] = value

            if not updated_fields:
                state.response = "No valid fields to update."
                return state

            db.commit()

            state.response = f"Updated fields: {', '.join(updated_fields.keys())}"

            log_execution(
                state.session_id,
                "update_employee",
                updated_fields,
            )
            return state

        # --------------------------------------------------------
        # DELETE EMPLOYEE (MANDATORY HITL)
        # --------------------------------------------------------
        if state.selected_api == "delete_employee":
            # 1️⃣ Mandatory HITL gate (ABSOLUTE)
            if not state.hitl_confirmed:
                state.response = (
                    "Are you sure you want to delete this employee? "
                    "Reply 'Yes' to confirm."
                )
                log_event(
                    "delete_hitl_required",
                    state.session_id,
                    {"confirmed": False},
                )
                return state

            # 2️⃣ Target must be resolved
            if not state.api_args or "employee_id" not in state.api_args:
                state.response = "Could not determine which employee to delete."
                log_event(
                    "delete_failed_no_target",
                    state.session_id,
                    {},
                )
                return state

            target_id = state.api_args["employee_id"]

            # 3️⃣ Self-delete is ALWAYS forbidden
            if target_id == state.employee_id:
                state.response = "You cannot delete your own profile."
                log_event(
                    "delete_denied_self",
                    state.session_id,
                    {"employee_id": target_id},
                )
                return state

            # 4️⃣ Employee must exist
            emp = db.query(Employee).filter(Employee.id == target_id).first()
            if not emp:
                state.response = "Employee not found."
                log_event(
                    "delete_failed_not_found",
                    state.session_id,
                    {"employee_id": target_id},
                )
                return state

            # 5️⃣ Perform delete
            db.delete(emp)
            db.commit()

            state.response = "Employee deleted successfully."
            log_execution(
                state.session_id,
                "delete_employee",
                {"employee_id": target_id},
            )
            return state

        # --------------------------------------------------------
        # DEFAULT
        # --------------------------------------------------------
        state.response = "Action could not be completed."
        return state

    finally:
        db.close()
