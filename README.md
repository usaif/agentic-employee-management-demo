# Agentic Employee Management Demo

This repository contains a deliberately vulnerable employee management application
built using FastAPI and LangGraph.
It is designed to demonstrate how agent-based systems can bypass traditional
authorization controls even when RBAC is implemented correctly.

This is NOT a production application.
It is a security research and demonstration project.

## Purpose

The goal of this project is to:

- Build a clean baseline for identity, onboarding, authentication, and RBAC
- Enforce authorization on executed actions (not intent)
- Demonstrate agent-specific security failures, including:
  - role drift via agent state mutation
  - memory poisoning across turns
  - prior tool-call confusion (confused deputy)
  - HITL misuse and TOCTOU-style flaws
- Use tests as executable security documentation

## High-Level Architecture

Client (chat)
  |
FastAPI (/agent/session, /agent/chat)
  |
LangGraph Agent
  - intent.py        : intent classification
  - decision.py     : selects selected_api and api_args
  - authorize.py    : RBAC enforcement on selected_api
  - hitl.py         : human-in-the-loop confirmation
  - execute.py      : database operations

Key design choice:
Authorization is enforced on selected_api, not on natural-language intent.


## Identity and Onboarding Model

### Onboarding Rules

- Users onboard using name and email
- Role during onboarding is always employee
- Role cannot be set or influenced during onboarding
- Duplicate onboarding is blocked
- Authentication is intentionally weak (demo-only)

### Post-Onboarding

- Users can log in using email
- HR users can update roles later
- Employees and managers cannot self-escalate roles

## Authorization Model (RBAC)

Authorization is enforced only after an action is selected.

Role permissions:

**Employee**:
- View own profile only

**Manager**:
- Read-only access

**HR**:
- View, update, and delete other employees

All roles:
- Cannot delete own profile

This enforcement is correct by design.
Bypasses occur because the agent controls the inputs to authorization.


## Test Philosophy

Tests are the primary artifact of this repository.

They are divided into three categories:

1. Onboarding and Identity Tests
   - User creation
   - Role enforcement
   - Duplicate prevention
   - HR role updates post-onboarding

2. RBAC Baseline Tests
   - What should be allowed
   - What should be denied
   - Establish the correct security baseline

3. Bypass Demonstration Tests
   - Agent-controlled role drift
   - Cross-turn memory poisoning
   - Prior tool-call reuse
   - HITL placement flaws

Some tests are expected to fail.
These failures are intentional and documented.

## Running the Application

Start the API locally:

`uv run python app/main.py`

The API will be available at:
http://localhost:8000

## Running Tests

Run all tests:

`uv run pytest -v`

Run only onboarding tests:

`uv run pytest tests/test_onboarding_flow.py -v`

Discover tests without executing:

`uv run pytest --collect-only`

## Security Disclaimer

This project intentionally demonstrates unsafe patterns in agent systems.

It includes:
- weak authentication
- agent-controlled authorization inputs
- mutable role and state handling

Do not use this code in production.

## Intended Audience

- Application Security Engineers
- Platform Security Engineers
- Security Architects
- Researchers exploring agentic systems

This project assumes familiarity with:
- RBAC concepts
- API security
- LLM-based agent architectures

## License

This project is licensed under the MIT License.

You are free to use, modify, and reference this code with attribution.

## Author Notes

This repository exists to support deeper discussion around:

Authorization can be correct and still fail when agents control state.

The tests are meant to be read, not just run.
