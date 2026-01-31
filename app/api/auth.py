from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.employee import Employee

router = APIRouter(prefix="/auth", tags=["auth"])

# ------------------------------------------------------------------
# Demo-only authentication config
# ------------------------------------------------------------------

DEMO_ACCESS_CODE = "123456"


@router.post("/login")
def login(
    payload: dict,
    db: Session = Depends(get_db),
):
    """
    Authenticate a user by email and access code.

    Phase 1 characteristics:
    - Shared static access code for all users
    - No tokens or sessions issued
    - Returns identity context only
    """

    email = payload.get("email")
    access_code = payload.get("access_code")

    if not email or not access_code:
        raise HTTPException(status_code=400, detail="email and access_code required")

    if access_code != DEMO_ACCESS_CODE:
        raise HTTPException(status_code=401, detail="Invalid access code")

    employee = db.query(Employee).filter(Employee.email == email).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    return {
        "employee_id": employee.id,
        "email": employee.email,
        "role": employee.role,
        "status": employee.status,
    }
