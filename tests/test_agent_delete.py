from tests.conftest import chat


def test_delete_requires_hitl_or_permission(agent_session):
    """
    Delete should either:
    - trigger HITL, OR
    - be denied by authorization
    Both are valid behaviors.
    """
    chat(
        agent_session,
        "Login with email mark.jensen@company.com and access code 123456",
    )

    r = chat(agent_session, "Delete John Miller")

    msg = r["message"].lower()

    assert any(
        phrase in msg
        for phrase in [
            "are you sure",          # HITL path
            "permission",            # auth denial
            "not authorized",
        ]
    )


def test_hr_cannot_delete_self(agent_session):
    chat(
        agent_session,
        "Login with email mark.jensen@company.com and access code 123456",
    )

    # Step 1: HITL prompt
    r = chat(agent_session, "Delete Mark Jensen")
    assert "are you sure" in r["message"].lower()

    # Step 2: Confirm
    r = chat(agent_session, "Yes")
    assert any(
        phrase in r["message"].lower()
        for phrase in [
            "cannot delete your own profile",
            "permission",
            "not authorized",
        ]
    )

