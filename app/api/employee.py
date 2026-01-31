from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.employee import Employee

router = APIRouter(prefix="/employee", tags=["employee"])


# ------------------------------------------------------------------
# Helper (intentionally weak)
# ------------------------------------------------------------------

def get_employee_or_404(db: Session, employee_id: int) -> Employee:
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee


# ------------------------------------------------------------------
# APIs
# ------------------------------------------------------------------

@router.get("/me")
def get_my_profile(
    employee_id: int | None = None,
    db: Session = Depends(get_db),
):
    """
    Return the profile of the authenticated employee.

    NOTE (Phase 1):
    - employee_id is trusted if provided
    - No authentication token is verified
    """
    if employee_id is None:
        raise HTTPException(status_code=400, detail="employee_id is required")

    return get_employee_or_404(db, employee_id)


@router.get("/{employee_id}")
def get_employee(
    employee_id: int,
    db: Session = Depends(get_db),
):
    """
    Return any employee by ID.

    NOTE (Phase 1):
    - No role checks
    - No ownership checks
    """
    return get_employee_or_404(db, employee_id)


@router.put("/{employee_id}")
def update_employee(
    employee_id: int,
    payload: dict,
    db: Session = Depends(get_db),
):
    """
    Update employee details.

    Intended:
    - HR-only operation

    Phase 1 reality:
    - Caller is trusted
    - No role validation
    """
    employee = get_employee_or_404(db, employee_id)

    # Update only fields provided
    for field, value in payload.items():
        if hasattr(employee, field):
            setattr(employee, field, value)

    db.commit()
    db.refresh(employee)

    return employee


@router.delete("/{employee_id}")
def delete_employee(
    employee_id: int,
    db: Session = Depends(get_db),
):
    """
    Delete an employee.

    Intended:
    - HR-only
    - Destructive

    Phase 1 reality:
    - No authorization enforcement
    - Agent-mediated HITL happens upstream
    """
    employee = get_employee_or_404(db, employee_id)

    db.delete(employee)
    db.commit()

    return {"status": "deleted", "employee_id": employee_id}
