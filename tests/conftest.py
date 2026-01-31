import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, engine, SessionLocal
from app.models.employee import Employee

client = TestClient(app)


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
