from sqlalchemy.orm import Session

from app.database import SessionLocal, init_db
from app.models.employee import Employee


def seed_employees(db: Session):
    """
    Populate the database with sample employees.
    This function is idempotent — it will not insert duplicates.
    """

    existing = db.query(Employee).count()
    if existing > 0:
        print("Employees already seeded. Skipping.")
        return

    employees = [
        # ------------------------------------------------------------------
        # HR users
        # ------------------------------------------------------------------
        Employee(
            id=1,
            name="Anita Rao",
            email="anita.rao@company.com",
            role="hr",
            manager_id=None,
            salary=180000,
            status="active",
            location="Bangalore",
        ),
        Employee(
            id=2,
            name="Mark Jensen",
            email="mark.jensen@company.com",
            role="hr",
            manager_id=None,
            salary=190000,
            status="active",
            location="New York",
        ),

        # ------------------------------------------------------------------
        # Managers
        # ------------------------------------------------------------------
        Employee(
            id=3,
            name="Ravi Mehta",
            email="ravi.mehta@company.com",
            role="manager",
            manager_id=1,
            salary=150000,
            status="active",
            location="Bangalore",
        ),
        Employee(
            id=4,
            name="Susan Lee",
            email="susan.lee@company.com",
            role="manager",
            manager_id=2,
            salary=155000,
            status="active",
            location="San Francisco",
        ),
        Employee(
            id=5,
            name="Daniel Kim",
            email="daniel.kim@company.com",
            role="manager",
            manager_id=2,
            salary=145000,
            status="active",
            location="Seattle",
        ),

        # ------------------------------------------------------------------
        # Employees (reports)
        # ------------------------------------------------------------------
        Employee(
            id=6,
            name="Priya Nair",
            email="priya.nair@company.com",
            role="employee",
            manager_id=3,
            salary=90000,
            status="active",
            location="Bangalore",
        ),
        Employee(
            id=7,
            name="Arjun Patel",
            email="arjun.patel@company.com",
            role="employee",
            manager_id=3,
            salary=95000,
            status="active",
            location="Bangalore",
        ),
        Employee(
            id=8,
            name="Neha Sharma",
            email="neha.sharma@company.com",
            role="employee",
            manager_id=4,
            salary=105000,
            status="active",
            location="San Francisco",
        ),
        Employee(
            id=9,
            name="Kevin Brown",
            email="kevin.brown@company.com",
            role="employee",
            manager_id=4,
            salary=100000,
            status="active",
            location="San Francisco",
        ),
        Employee(
            id=10,
            name="Emily Chen",
            email="emily.chen@company.com",
            role="employee",
            manager_id=5,
            salary=98000,
            status="active",
            location="Seattle",
        ),
        Employee(
            id=11,
            name="Michael Torres",
            email="michael.torres@company.com",
            role="employee",
            manager_id=5,
            salary=102000,
            status="active",
            location="Seattle",
        ),

        # ------------------------------------------------------------------
        # Terminated employee (edge case)
        # ------------------------------------------------------------------
        Employee(
            id=12,
            name="John Miller",
            email="john.miller@company.com",
            role="employee",
            manager_id=3,
            salary=92000,
            status="terminated",
            location="Bangalore",
        ),
    ]

    db.add_all(employees)
    db.commit()
    print(f"Seeded {len(employees)} employees.")


def run():
    """
    Initialize DB schema and seed data.
    """
    init_db()
    db = SessionLocal()
    try:
        seed_employees(db)
    finally:
        db.close()


if __name__ == "__main__":
    run()
