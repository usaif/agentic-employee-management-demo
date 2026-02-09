#!/bin/bash
# Demo script showing the pre-commit hook in action

set -e

echo "=================================================="
echo "Pre-Commit Hook Demo: Write Capability Detection"
echo "=================================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}This demo shows how the hook detects write capabilities${NC}"
echo ""

# Create a temporary branch for demo
DEMO_BRANCH="demo-precommit-hook-$(date +%s)"
echo "Creating demo branch: $DEMO_BRANCH"
git checkout -b "$DEMO_BRANCH" 2>/dev/null || echo "Using current branch"

echo ""
echo "=================================================="
echo "Demo 1: Adding write capability WITHOUT tests"
echo "=================================================="
echo ""

# Create a new file with a write capability
cat > app/demo_mutation.py << 'EOF'
from sqlalchemy.orm import Session
from app.models.employee import Employee

def promote_employee(db: Session, employee_id: int, new_role: str):
    """Promote an employee to a new role (WRITE OPERATION)."""
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    emp.role = new_role
    db.commit()
    return emp
EOF

echo "Created file with mutation: app/demo_mutation.py"
echo ""
echo "File contents:"
echo "----------------------------------------"
cat app/demo_mutation.py
echo "----------------------------------------"
echo ""

# Try to commit without test
git add app/demo_mutation.py
echo -e "${YELLOW}Running: git commit -m 'Add employee promotion feature'${NC}"
echo ""

if git commit -m "Add employee promotion feature" 2>&1; then
    echo -e "${RED}❌ UNEXPECTED: Commit should have been blocked!${NC}"
else
    echo -e "${GREEN}✅ EXPECTED: Commit was blocked due to missing tests${NC}"
fi

echo ""
echo "=================================================="
echo "Demo 2: Adding write capability WITH tests"
echo "=================================================="
echo ""

# Create a corresponding test
cat > tests/test_demo_promotion.py << 'EOF'
from tests.conftest import chat

def test_hr_can_promote_employee(agent_session):
    """Test that HR can promote employees."""
    chat(agent_session, "Login with email mark.jensen@company.com")

    r = chat(agent_session, "Promote Priya Nair to manager")
    assert "updated" in r["message"].lower() or "promoted" in r["message"].lower()

def test_employee_cannot_promote_self(agent_session):
    """Test that employees cannot promote themselves."""
    chat(agent_session, "Login with email priya.nair@company.com")

    r = chat(agent_session, "Promote myself to manager")
    assert "not authorized" in r["message"].lower()
EOF

echo "Created test file: tests/test_demo_promotion.py"
echo ""
echo "Test contents:"
echo "----------------------------------------"
cat tests/test_demo_promotion.py
echo "----------------------------------------"
echo ""

# Try to commit with test
git add tests/test_demo_promotion.py
echo -e "${YELLOW}Running: git commit -m 'Add employee promotion feature with tests'${NC}"
echo ""

if git commit -m "Add employee promotion feature with tests" 2>&1; then
    echo -e "${GREEN}✅ EXPECTED: Commit succeeded with tests included${NC}"
else
    echo -e "${RED}❌ UNEXPECTED: Commit should have succeeded with tests${NC}"
fi

echo ""
echo "=================================================="
echo "Demo 3: Read-only operation (should pass)"
echo "=================================================="
echo ""

# Create a read-only function
cat > app/demo_readonly.py << 'EOF'
from sqlalchemy.orm import Session
from app.models.employee import Employee

def get_employee_by_role(db: Session, role: str):
    """Get all employees with a specific role (READ-ONLY)."""
    return db.query(Employee).filter(Employee.role == role).all()
EOF

echo "Created file with read-only operation: app/demo_readonly.py"
echo ""
echo "File contents:"
echo "----------------------------------------"
cat app/demo_readonly.py
echo "----------------------------------------"
echo ""

git add app/demo_readonly.py
echo -e "${YELLOW}Running: git commit -m 'Add read-only employee query'${NC}"
echo ""

if git commit -m "Add read-only employee query" 2>&1; then
    echo -e "${GREEN}✅ EXPECTED: Read-only operation committed without tests${NC}"
else
    echo -e "${RED}❌ UNEXPECTED: Read-only should not require tests for hook${NC}"
fi

echo ""
echo "=================================================="
echo "Demo Complete!"
echo "=================================================="
echo ""
echo "Summary:"
echo "  1. ❌ Write operations WITHOUT tests → BLOCKED"
echo "  2. ✅ Write operations WITH tests → ALLOWED"
echo "  3. ✅ Read-only operations → ALLOWED"
echo ""
echo "Cleaning up demo files..."

# Clean up
git reset --soft HEAD~3 2>/dev/null || true
git reset HEAD app/demo_mutation.py tests/test_demo_promotion.py app/demo_readonly.py 2>/dev/null || true
rm -f app/demo_mutation.py tests/test_demo_promotion.py app/demo_readonly.py

echo "Demo files removed."
echo ""
echo "To install the hook for real use:"
echo "  pre-commit install"
echo ""
echo "For more information, see:"
echo "  - QUICKSTART_HOOK.md"
echo "  - README_PRECOMMIT.md"
