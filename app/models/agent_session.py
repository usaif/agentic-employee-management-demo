from sqlalchemy import Column, String, Boolean, Integer, DateTime, Text
from sqlalchemy.sql import func

from app.database import Base


class AgentSession(Base):
    __tablename__ = "agent_sessions"

    # ------------------------------------------------------------------
    # Session identity
    # ------------------------------------------------------------------

    session_id = Column(String, primary_key=True, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # ------------------------------------------------------------------
    # Authentication binding (post-auth)
    # ------------------------------------------------------------------

    authenticated = Column(Boolean, default=False)

    employee_id = Column(Integer, nullable=True)
    role = Column(String, nullable=True)  # employee | manager | hr

    # ------------------------------------------------------------------
    # Persisted LangGraph state
    # ------------------------------------------------------------------

    state_json = Column(
        Text,
        nullable=False,
        default="{}",
        doc="Serialized LangGraph agent state (JSON)",
    )

    # ------------------------------------------------------------------
    # Representation helpers
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"<AgentSession session_id={self.session_id} "
            f"authenticated={self.authenticated} "
            f"employee_id={self.employee_id} "
            f"role={self.role}>"
        )
