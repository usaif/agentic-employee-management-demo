from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

def create_new_session():
    r = client.post("/agent/session")
    assert r.status_code == 200
    return r.json()["session_id"]


def chat(session_id, message):
    r = client.post(
        f"/agent/chat/{session_id}",
        json={"message": message},
    )
    assert r.status_code == 200
    return r.json()
