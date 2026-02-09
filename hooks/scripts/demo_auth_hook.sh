#!/bin/bash
# Demo script for authorization change detection hook

set -e

echo "=========================================================="
echo "Authorization Change Detection Hook Demo (AST-Based)"
echo "=========================================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}This demo shows AST-based authorization detection${NC}"
echo ""

# Create a temporary branch
DEMO_BRANCH="demo-auth-hook-$(date +%s)"
echo "Creating demo branch: $DEMO_BRANCH"
git checkout -b "$DEMO_BRANCH" 2>/dev/null || echo "Using current branch"

echo ""
echo "=========================================================="
echo "Demo 1: Modify Role Permissions WITHOUT Test Update"
echo "=========================================================="
echo ""

# Backup original file
cp app/agent/nodes/authorize.py app/agent/nodes/authorize.py.backup

# Modify authorization logic
echo "Modifying authorization logic..."
cat > app/agent/nodes/authorize_demo.py << 'EOF'
from app.agent.state import AgentState

def authorize_action(state: AgentState) -> AgentState:
    """Authorization with MODIFIED employee permissions."""

    role = state.role
    action = state.selected_api

    if not state.authenticated:
        raise PermissionError("User not authenticated")

    # CHANGE: Allow employees to update their own profile
    if role == "employee":
        if action in ("get_my_profile", "update_my_profile"):  # ← ADDED update_my_profile
            return state
        raise PermissionError("Employees may only view their own profile")

    if role == "manager":
        if action in ("get_my_profile", "get_employee"):
            return state
        raise PermissionError("Managers have read-only access")

    if role == "hr":
        return state

    raise PermissionError("Unknown role")
EOF

mv app/agent/nodes/authorize_demo.py app/agent/nodes/authorize.py

echo "Modified code (employee permissions):"
echo "----------------------------------------"
grep -A 3 "if role == \"employee\"" app/agent/nodes/authorize.py
echo "----------------------------------------"
echo ""

git add app/agent/nodes/authorize.py

echo -e "${YELLOW}Running: git commit -m 'Allow employees to update own profile'${NC}"
echo ""

if git commit -m "Allow employees to update own profile" 2>&1; then
    echo -e "${RED}❌ UNEXPECTED: Commit should have been blocked!${NC}"
else
    echo -e "${GREEN}✅ EXPECTED: Commit blocked due to authorization change without test${NC}"
fi

# Restore original
mv app/agent/nodes/authorize.py.backup app/agent/nodes/authorize.py
git reset HEAD app/agent/nodes/authorize.py 2>/dev/null || true

echo ""
echo "=========================================================="
echo "Demo 2: Add New Role WITHOUT Test Update"
echo "=========================================================="
echo ""

cat > app/agent/nodes/authorize_demo2.py << 'EOF'
from app.agent.state import AgentState

def authorize_action(state: AgentState) -> AgentState:
    """Authorization with NEW admin role."""

    role = state.role
    action = state.selected_api

    if not state.authenticated:
        raise PermissionError("User not authenticated")

    # NEW ROLE ADDED
    if role == "admin":  # ← NEW ROLE
        return state  # Admin can do anything

    if role == "employee":
        if action == "get_my_profile":
            return state
        raise PermissionError("Employees may only view their own profile")

    if role == "hr":
        return state

    raise PermissionError("Unknown role")
EOF

mv app/agent/nodes/authorize_demo2.py app/agent/nodes/authorize.py

echo "Added new admin role:"
echo "----------------------------------------"
grep -A 2 "if role == \"admin\"" app/agent/nodes/authorize.py
echo "----------------------------------------"
echo ""

git add app/agent/nodes/authorize.py

echo -e "${YELLOW}Running: git commit -m 'Add admin role'${NC}"
echo ""

if git commit -m "Add admin role" 2>&1; then
    echo -e "${RED}❌ UNEXPECTED: Commit should have been blocked!${NC}"
else
    echo -e "${GREEN}✅ EXPECTED: Commit blocked - new role requires tests${NC}"
fi

# Restore original
mv app/agent/nodes/authorize.py.backup app/agent/nodes/authorize.py
git reset HEAD app/agent/nodes/authorize.py 2>/dev/null || true

echo ""
echo "=========================================================="
echo "Demo 3: Modify Authorization WITH Test Update"
echo "=========================================================="
echo ""

# Create a test for the new functionality
cat > tests/test_auth_demo.py << 'EOF'
from tests.conftest import chat

def test_employee_can_update_own_location(agent_session):
    """Test that employees can update their own location."""
    chat(agent_session, "Login with email priya.nair@company.com")
    r = chat(agent_session, "Update my location to London")
    assert "updated" in r["message"].lower() or "success" in r["message"].lower()

def test_employee_cannot_update_other_location(agent_session):
    """Test that employees cannot update other employees."""
    chat(agent_session, "Login with email priya.nair@company.com")
    r = chat(agent_session, "Update John Miller location to London")
    assert "not authorized" in r["message"].lower()
EOF

echo "Created authorization test:"
echo "----------------------------------------"
cat tests/test_auth_demo.py | head -15
echo "----------------------------------------"
echo ""

# Now modify the authorization logic
cat > app/agent/nodes/authorize_demo3.py << 'EOF'
from app.agent.state import AgentState

def authorize_action(state: AgentState) -> AgentState:
    """Authorization with updated employee permissions."""

    role = state.role
    action = state.selected_api

    if not state.authenticated:
        raise PermissionError("User not authenticated")

    if role == "employee":
        # Allow employees to update their own profile
        if action in ("get_my_profile", "update_my_profile"):
            return state
        raise PermissionError("Employees may only view their own profile")

    if role == "hr":
        return state

    raise PermissionError("Unknown role")
EOF

mv app/agent/nodes/authorize_demo3.py app/agent/nodes/authorize.py

# Commit both the test and the code
git add tests/test_auth_demo.py app/agent/nodes/authorize.py

echo -e "${YELLOW}Running: git commit -m 'Allow employees to update profile with tests'${NC}"
echo ""

if git commit -m "Allow employees to update profile with tests" 2>&1; then
    echo -e "${GREEN}✅ EXPECTED: Commit succeeded with test update${NC}"
else
    echo -e "${RED}❌ UNEXPECTED: Should have succeeded with tests${NC}"
fi

# Restore and clean up
mv app/agent/nodes/authorize.py.backup app/agent/nodes/authorize.py
rm -f tests/test_auth_demo.py
git reset --soft HEAD~1 2>/dev/null || true
git reset HEAD tests/test_auth_demo.py app/agent/nodes/authorize.py 2>/dev/null || true

echo ""
echo "=========================================================="
echo "Demo 4: Show AST Detection Capabilities"
echo "=========================================================="
echo ""

echo "Running AST detection test..."
python3 .pre-commit-hooks/test_auth_hook.py | head -50

echo ""
echo "=========================================================="
echo "Demo Complete!"
echo "=========================================================="
echo ""
echo "Summary:"
echo "  1. ❌ Role permission change WITHOUT tests → BLOCKED"
echo "  2. ❌ New role added WITHOUT tests → BLOCKED"
echo "  3. ✅ Authorization change WITH tests → ALLOWED"
echo "  4. ✅ AST detection accurately identifies patterns"
echo ""
echo "Key Advantages of AST-based Detection:"
echo "  • Understands Python syntax (no false positives from comments)"
echo "  • Detects semantic changes (not just text patterns)"
echo "  • Provides accurate line numbers"
echo "  • More reliable than regex-based approaches"
echo ""
echo "For more information:"
echo "  - README_AUTH_HOOK.md (complete guide)"
echo "  - .pre-commit-hooks/check_authorization_changes.py (source)"
