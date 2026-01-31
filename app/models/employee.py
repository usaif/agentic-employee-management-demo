from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class Employee(Base):
    __tablename__ = "employees"

    # ------------------------------------------------------------------
    # Core identifiers
    # ------------------------------------------------------------------

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)

    # ------------------------------------------------------------------
    # Role & hierarchy
    # ------------------------------------------------------------------

    role = Column(String, nullable=False)  # employee | manager | hr
    manager_id = Column(Integer, ForeignKey("employees.id"), nullable=True)

    # Self-referential relationship (manager -> reports)
    manager = relationship(
        "Employee",
        remote_side=[id],
        backref="reports",
    )

    # ------------------------------------------------------------------
    # Sensitive / HR data
    # ------------------------------------------------------------------

    salary = Column(Integer, nullable=False)
    status = Column(String, nullable=False)  # active | terminated
    location = Column(String, nullable=False)

    # ------------------------------------------------------------------
    # Representation helpers
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"<Employee id={self.id} "
            f"name={self.name} "
            f"email={self.email} "
            f"role={self.role}>"
        )
