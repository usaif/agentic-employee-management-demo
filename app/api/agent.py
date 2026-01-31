import json
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.agent.graph import agent_graph
from app.agent.state import AgentState
from app.models.agent_session import AgentSession
from app.models.agent_message import AgentMessage
from app.logging.audit import log_error

router = APIRouter(prefix="/agent", tags=["agent"])


# ------------------------------------------------------------------
# Create a new agent session
# ------------------------------------------------------------------

@router.post("/session")
def create_session(db: Session = Depends(get_db)):
    session_id = str(uuid.uuid4())

    initial_state = AgentState(session_id=session_id)

    agent_session = AgentSession(
        session_id=session_id,
        state_json=json.dumps(initial_state.to_dict()),
    )

    db.add(agent_session)
    db.commit()

    return {"session_id": session_id}


# ------------------------------------------------------------------
# Chat with the agent
# ------------------------------------------------------------------

@router.post("/chat/{session_id}")
def chat(session_id: str, payload: dict, db: Session = Depends(get_db)):
    user_message = payload.get("message", "").strip()

    if not user_message:
        return {
            "session_id": session_id,
            "message": "Please enter a message.",
        }

    # --------------------------------------------------------------
    # Load agent session
    # --------------------------------------------------------------

    agent_session = (
        db.query(AgentSession)
        .filter(AgentSession.session_id == session_id)
        .first()
    )

    if not agent_session:
        return {
            "session_id": session_id,
            "message": "Invalid session.",
        }

    # --------------------------------------------------------------
    # Rehydrate agent state
    # --------------------------------------------------------------

    state_data = json.loads(agent_session.state_json)
    state = AgentState.from_dict(state_data)
    state.session_id = session_id
    state.user_input = user_message

    # --------------------------------------------------------------
    # Persist user message (audit log)
    # --------------------------------------------------------------

    db.add(
        AgentMessage(
            session_id=session_id,
            sender="user",
            message=user_message,
        )
    )
    db.commit()

    # --------------------------------------------------------------
    # Run agent graph with FULL error protection
    # --------------------------------------------------------------

    try:
        result = agent_graph.invoke(state)

        # LangGraph may return AgentState OR dict
        if isinstance(result, AgentState):
            result_state = result
        else:
            result_state = AgentState.from_dict(result)
        
        # print("DEBUG AFTER GRAPH:", result_state.to_dict())
        # Only default if NO node set a response at all
        if result_state.response is None:
            result_state.response = "Done."

    except PermissionError as e:
        # Expected authorization failure
        result_state = state
        result_state.response = str(e)
        # print("DEBUG PERMISSION STATE:", result_state.to_dict())

    except Exception as e:
        # Never leak internal errors to UI
        result_state = state
        result_state.response = (
            "Sorry, something went wrong while processing your request."
        )
        log_error(session_id, e)
        # print("DEBUG ERROR STATE:", result_state.to_dict())

    # --------------------------------------------------------------
    # Persist state no matter what
    # --------------------------------------------------------------

    agent_session.state_json = json.dumps(result_state.to_dict())
    db.commit()

    # --------------------------------------------------------------
    # Persist agent response (audit log)
    # --------------------------------------------------------------

    db.add(
        AgentMessage(
            session_id=session_id,
            sender="agent",
            message=result_state.response,
        )
    )
    db.commit()

    return {
        "session_id": session_id,
        "message": result_state.response,
    }
