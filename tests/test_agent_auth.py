from tests.conftest import chat


def test_hr_login_persists(agent_session):
    r = chat(
        agent_session,
        "Login with email mark.jensen@company.com and access code 123456",
    )
    assert "authenticated" in r["message"].lower()

    r = chat(agent_session, "Show my profile")
    assert "mark jensen" in r["message"].lower()
    assert "role: hr" in r["message"].lower()
