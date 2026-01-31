from fastapi import FastAPI
from dotenv import load_dotenv

from app.database import init_db
from app.api.auth import router as auth_router
from app.api.employee import router as employee_router
from app.api.agent import router as agent_router
from fastapi.staticfiles import StaticFiles

# ------------------------------------------------------------------
# Environment
# ------------------------------------------------------------------

# Load .env file (OPENAI_API_KEY, etc.)
load_dotenv()

# ------------------------------------------------------------------
# FastAPI app
# ------------------------------------------------------------------

app = FastAPI(
    title="Employee Agent App",
    description="Workday-like employee management app with LangGraph agent",
    version="0.1.0",
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# ------------------------------------------------------------------
# Startup
# ------------------------------------------------------------------

@app.on_event("startup")
def startup_event():
    """
    Initialize database schema on startup.
    """
    init_db()

# ------------------------------------------------------------------
# Routers
# ------------------------------------------------------------------

app.include_router(auth_router)
app.include_router(employee_router)
app.include_router(agent_router)

# ------------------------------------------------------------------
# Health check
# ------------------------------------------------------------------

@app.get("/")
def health():
    return {"status": "ok"}
