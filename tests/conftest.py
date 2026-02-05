import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, engine, SessionLocal
from unittest.mock import patch, MagicMock
from app.models.employee import Employee

client = TestClient(app)

@pytest.fixture(autouse=True)
def mock_classify_intent():
    def smart_classifier(user_input: str) -> dict:
        """Return appropriate intent based on keywords in user input"""
        msg = user_input.lower()
        
        # Login/Authentication intent
        if "login" in msg or "authenticate" in msg:
            return {"intent": "authenticate"}  # ✅ Changed from "login"
        
        # View intents
        if "show" in msg or "view" in msg or "display" in msg:
            if "my profile" in msg or "my information" in msg:
                return {"intent": "view_self"}  # ✅ Matches decision.py
            elif "employee" in msg:
                return {"intent": "view_employee"}  # ✅ Matches decision.py
            else:
                return {"intent": "view_self"}
        
        # Update intent
        if "update" in msg or "change" in msg or "modify" in msg:
            return {"intent": "update_employee"}  # ✅ Matches decision.py
        
        # Delete intent
        if "delete" in msg or "remove" in msg:
            return {"intent": "delete_employee"}  # ✅ Matches decision.py
        
        # Onboard intent
        if "onboard" in msg:
            return {"intent": "onboard"}  # ✅ Matches decision.py
        
        # Confirmation (for HITL)
        if msg.strip() in ["yes", "y", "confirm"]:
            return {"intent": "confirm"}
        
        # Default
        return {"intent": "unknown"}
    
    with patch('app.agent.nodes.intent.classify_intent') as mock:
        mock.side_effect = smart_classifier
        yield mock

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """
    Create tables and seed test data ONCE for all tests.
    """
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        db.add_all(
            [
                Employee(
                    name="Mark Jensen",
                    email="mark.jensen@company.com",
                    role="hr",
                    location="New York",
                    status="active",
                    salary=150000,
                ),
                Employee(
                    name="Priya Nair",
                    email="priya.nair@company.com",
                    role="employee",
                    location="Bangalore",
                    status="active",
                    salary=90000,
                ),
                Employee(
                    name="John Miller",
                    email="john.miller@company.com",
                    role="employee",
                    location="London",
                    status="active",
                    salary=100000,
                ),
                Employee(
                    name="Alice HR",
                    email="alice.hr@company.com",
                    role="hr",
                    location="Seattle",
                    status="active",
                    salary=100000,
                ),
            ]
        )
        db.commit()
    finally:
        db.close()

    yield

    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def agent_session():
    response = client.post("/agent/session")
    assert response.status_code == 200
    return response.json()["session_id"]


def chat(session_id: str, message: str):
    response = client.post(
        f"/agent/chat/{session_id}",
        json={"message": message},
    )
    assert response.status_code == 200
    return response.json()
