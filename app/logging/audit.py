import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

# ------------------------------------------------------------------
# Logger configuration
# ------------------------------------------------------------------

logger = logging.getLogger("agent_audit")

if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

logger.setLevel(logging.INFO)

# ------------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------------

def log_event(
    event_type: str,
    session_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
):
    """
    Log a structured audit event.

    NOTE:
    - This is NOT the authoritative audit log
    - SQLite tables remain the source of truth
    - This is for observability and debugging
    """

    payload = {
        "event_type": event_type,
        "session_id": session_id,
        "timestamp": datetime.utcnow().isoformat(),
        "details": details or {},
    }

    logger.info(json.dumps(payload))


def log_agent_decision(
    session_id: str,
    intent: Optional[str],
    selected_api: Optional[str],
):
    log_event(
        event_type="agent_decision",
        session_id=session_id,
        details={
            "intent": intent,
            "selected_api": selected_api,
        },
    )


def log_hitl(
    session_id: str,
    awaiting_confirmation: bool,
):
    log_event(
        event_type="hitl_state",
        session_id=session_id,
        details={
            "awaiting_confirmation": awaiting_confirmation,
        },
    )


def log_execution(
    session_id: str,
    action: str,
    args: Optional[Dict[str, Any]] = None,
):
    log_event(
        event_type="execution",
        session_id=session_id,
        details={
            "action": action,
            "args": args or {},
        },
    )


def log_error(
    session_id: Optional[str],
    error: Exception,
):
    log_event(
        event_type="error",
        session_id=session_id,
        details={
            "error": str(error),
            "type": type(error).__name__,
        },
    )
