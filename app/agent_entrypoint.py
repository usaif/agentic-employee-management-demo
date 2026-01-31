import json
import uuid
import traceback

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
import uvicorn
from sqlalchemy.orm import Session

# Import SessionLocal - THIS WAS MISSING!
from app.database import get_db, init_db, SessionLocal
from app.agent.graph import agent_graph
from app.agent.state import AgentState
from app.models.agent_session import AgentSession
from app.models.agent_message import AgentMessage
from app.logging.audit import log_error
from app.seed.seed_data import seed_employees

app = FastAPI()

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database tables and seed data on startup"""
    try:
        # Create all tables
        init_db()
        print("✅ Database initialized successfully")
        
        # Seed test employees
        db = SessionLocal()
        try:
            seed_employees(db)
        finally:
            db.close()
        
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
        traceback.print_exc()

class InvocationRequest(BaseModel):
    """AgentCore invocation payload"""
    input: dict

class InvocationResponse(BaseModel):
    """AgentCore response payload"""
    output: dict

@app.post("/invocations")
async def invocations(request: InvocationRequest, db: Session = Depends(get_db)):
    """
    REQUIRED endpoint for AgentCore
    Handles both session creation and chat
    """
    try:
        payload = request.input
        action = payload.get("action", "chat")
        
        if action == "create_session":
            session_id = str(uuid.uuid4())
            initial_state = AgentState(session_id=session_id)
            
            agent_session = AgentSession(
                session_id=session_id,
                authenticated=False,
                employee_id=None,
                role=None,
                state_json=json.dumps(initial_state.to_dict()),
            )
            db.add(agent_session)
            db.commit()
            db.refresh(agent_session)
            
            return InvocationResponse(output={
                "session_id": session_id,
                "status": "created"
            })
        
        elif action == "chat":
            session_id = payload.get("session_id")
            user_message = payload.get("prompt", "")
            
            if not session_id:
                raise HTTPException(status_code=400, detail="session_id required")
            
            if not user_message or not user_message.strip():
                return InvocationResponse(output={
                    "session_id": session_id,
                    "message": "Please enter a message."
                })
            
            agent_session = (
                db.query(AgentSession)
                .filter(AgentSession.session_id == session_id)
                .first()
            )
            
            if not agent_session:
                return InvocationResponse(output={
                    "session_id": session_id,
                    "message": "Invalid session."
                })
            
            state_data = json.loads(agent_session.state_json)
            state = AgentState.from_dict(state_data)
            state.session_id = session_id
            state.user_input = user_message
            
            db.add(
                AgentMessage(
                    session_id=session_id,
                    sender="user",
                    message=user_message,
                )
            )
            db.commit()
            
            try:
                result = agent_graph.invoke(state)
                if isinstance(result, AgentState):
                    result_state = result
                else:
                    result_state = AgentState.from_dict(result)
                
                if result_state.response is None:
                    result_state.response = "Done."
                    
            except PermissionError as e:
                result_state = state
                result_state.response = str(e)
                
            except Exception as e:
                result_state = state
                result_state.response = (
                    "Sorry, something went wrong while processing your request."
                )
                log_error(session_id, e)
            
            agent_session.state_json = json.dumps(result_state.to_dict())
            
            # Update session authentication state if login was successful
            if result_state.authenticated:
                agent_session.authenticated = result_state.authenticated
                agent_session.employee_id = result_state.employee_id
                agent_session.role = result_state.role
            
            db.commit()
            
            db.add(
                AgentMessage(
                    session_id=session_id,
                    sender="agent",
                    message=result_state.response,
                )
            )
            db.commit()
            
            return InvocationResponse(output={
                "session_id": session_id,
                "message": result_state.response,
                "response": result_state.response
            })
        
        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {action}")
            
    except HTTPException as he:
        return InvocationResponse(output={
            "error": he.detail,
            "status_code": he.status_code
        })
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {str(e)}")
        print(traceback.format_exc())
        
        return InvocationResponse(output={
            "error": f"{type(e).__name__}: {str(e)}",
            "type": type(e).__name__
        })

@app.get("/ping")
async def health_check():
    """
    REQUIRED health check endpoint for AgentCore
    """
    try:
        return {"status": "healthy"}
    except Exception:
        return {"status": "unhealthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
