from tests.conftest import chat


def test_hr_can_view_employee(agent_session):
    chat(
        agent_session,
        "Login with email mark.jensen@company.com and access code 123456",
    )

    r = chat(agent_session, "Show employee Priya Nair")
    assert "priya nair" in r["message"].lower()
    assert "location" in r["message"].lower()
