from tests.conftest import chat


def test_hr_can_update_employee_location(agent_session):
    chat(
        agent_session,
        "Login with email mark.jensen@company.com and access code 123456",
    )

    r = chat(agent_session, "Update Priya Nair location to London")
    assert "updated" in r["message"].lower()

    r = chat(agent_session, "Show employee Priya Nair")
    assert "london" in r["message"].lower()
