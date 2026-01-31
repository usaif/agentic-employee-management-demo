from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func

from app.database import Base


class AgentMessage(Base):
    __tablename__ = "agent_messages"

    # ------------------------------------------------------------------
    # Primary key
    # ------------------------------------------------------------------

    id = Column(Integer, primary_key=True, index=True)

    # ------------------------------------------------------------------
    # Session association
    # ------------------------------------------------------------------

    session_id = Column(
        String,
        ForeignKey("agent_sessions.session_id"),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # Message metadata
    # ------------------------------------------------------------------

    sender = Column(
        String,
        nullable=False,
        doc="user | agent | system",
    )

    message = Column(
        Text,
        nullable=False,
    )

    timestamp = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # ------------------------------------------------------------------
    # Representation helpers
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"<AgentMessage id={self.id} "
            f"session_id={self.session_id} "
            f"sender={self.sender}>"
        )
