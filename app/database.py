from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from pathlib import Path

# ------------------------------------------------------------------
# Database configuration
# ------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DATABASE_URL = f"sqlite:///{DATA_DIR / 'app.db'}"

# ------------------------------------------------------------------
# SQLAlchemy engine & session
# ------------------------------------------------------------------

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # required for SQLite + FastAPI
    echo=False,  # set to True if you want SQL logs
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()

# ------------------------------------------------------------------
# Dependency helper
# ------------------------------------------------------------------

def get_db():
    """
    FastAPI dependency that provides a DB session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ------------------------------------------------------------------
# Initialization
# ------------------------------------------------------------------

def init_db():
    """
    Import all models and create tables.
    This must be called once at startup.
    """
    from app.models.employee import Employee  # noqa
    from app.models.agent_session import AgentSession  # noqa
    from app.models.agent_message import AgentMessage  # noqa

    Base.metadata.create_all(bind=engine)
