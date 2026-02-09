# Authorization Change Detection Hook (AST-Based)

## Overview

This pre-commit hook uses **Abstract Syntax Tree (AST)** parsing to detect changes to authorization and RBAC logic, then verifies that corresponding authorization tests are updated.

**Why AST instead of regex?**
- ✅ Understands Python syntax correctly
- ✅ Ignores comments and docstrings
- ✅ Avoids false positives from string literals
- ✅ Provides accurate line numbers
- ✅ Detects semantic changes, not just text patterns

## Authorization Patterns Detected

### 1. Authorization Functions
Functions with authorization-related names:
```python
def authorize_action(state):  # ✓ Detected
def check_permission(user):   # ✓ Detected
def verify_access(role):      # ✓ Detected
def validate_role(state):     # ✓ Detected
```

### 2. Role Checks
Comparisons with role values:
```python
if state.role == "employee":  # ✓ Detected
if role == "manager":         # ✓ Detected
if state.role == "hr":        # ✓ Detected
```

### 3. Authentication Checks
Access to authentication state:
```python
if not state.authenticated:   # ✓ Detected
if state.authenticated:       # ✓ Detected
state.authenticated = True    # ✓ Detected (via state_access)
```

### 4. Permission Errors
Raising permission-related exceptions:
```python
raise PermissionError("Not authorized")           # ✓ Detected
raise PermissionError("Employees cannot access")  # ✓ Detected
```

### 5. Action Whitelists
Checking actions against allowed lists:
```python
if action in ("login", "onboard_user"):           # ✓ Detected
if action in allowed_actions:                     # ✓ Detected
```

### 6. State Access
Direct access to authorization-related state:
```python
role = state.role             # ✓ Detected
auth = state.authenticated    # ✓ Detected
```

## How It Works

### AST Parsing Flow

```
Python Code
    ↓
AST Parse (ast.parse)
    ↓
AST Visitor (AuthorizationASTVisitor)
    ↓
Pattern Detection
    ↓
Changed Line Check (git diff)
    ↓
Test Update Verification
    ↓
Report Violations or Pass
```

### Example: What Gets Detected

**Before (original code):**
```python
def authorize_action(state):
    if state.role == "employee":
        if action == "get_my_profile":
            return state
        raise PermissionError("Employees may only view their own profile")
```

**After (modified code):**
```python
def authorize_action(state):
    if state.role == "employee":
        if action in ("get_my_profile", "update_my_profile"):  # ← CHANGED
            return state
        raise PermissionError("Employees may only view their own profile")
```

**Hook Detection:**
```
⚠️ AUTHORIZATION LOGIC CHANGES WITHOUT TEST UPDATES

  app/agent/nodes/authorize.py
    Line 52: action_whitelist: Action whitelist check
    Line 50: role_comparison: Comparison with state.role
```

## Installation

The hook is already included in `.pre-commit-config.yaml`:

```yaml
- id: check-authorization-changes
  name: Check Authorization Changes
  entry: python .pre-commit-hooks/check_authorization_changes.py
  language: system
  types: [python]
  pass_filenames: true
  stages: [commit]
```

Install with:
```bash
pre-commit install
```

## Usage Examples

### Example 1: Authorization Change Without Test Update ❌

```bash
# Modify authorization logic
vim app/agent/nodes/authorize.py

# Change: Allow employees to update their own profile
# if state.role == "employee":
#     if action in ("get_my_profile", "update_my_profile"):  # ADDED update
#         return state

git add app/agent/nodes/authorize.py
git commit -m "Allow employees to update their own profile"
```

**Output:**
```
⚠️ AUTHORIZATION LOGIC CHANGES WITHOUT TEST UPDATES

The following authorization logic was changed without updating
authorization tests:

  app/agent/nodes/authorize.py
    Line 52: action_whitelist: Action whitelist check
    Line 50: role_comparison: Comparison with state.role

AUTHORIZATION PATTERNS DETECTED:

This commit modifies:
  • Action Whitelist
  • Role Comparison

REMEDIATION:

1. Update authorization tests in tests/test_authorization_rbac.py

2. Ensure tests cover the changed authorization logic:
   ...
```

### Example 2: Authorization Change WITH Test Update ✅

```bash
# Step 1: Update the test
cat >> tests/test_authorization_rbac.py << 'EOF'

def test_employee_can_update_own_profile(agent_session):
    """Test that employees can update their own profile."""
    chat(agent_session, "Login with email priya.nair@company.com")
    r = chat(agent_session, "Update my location to London")
    assert "updated" in r["message"].lower()

def test_employee_cannot_update_other_profile(agent_session):
    """Test that employees cannot update other profiles."""
    chat(agent_session, "Login with email priya.nair@company.com")
    r = chat(agent_session, "Update John Miller location to London")
    assert "not authorized" in r["message"].lower()
EOF

# Step 2: Modify authorization logic
vim app/agent/nodes/authorize.py

# Step 3: Commit both
git add tests/test_authorization_rbac.py app/agent/nodes/authorize.py
git commit -m "Allow employees to update own profile with tests"
```

**Output:**
```
✓ Authorization changes detected WITH test updates
[main abc1234] Allow employees to update own profile with tests
```

### Example 3: Non-Authorization Change (Ignored) ✅

```bash
# Changes to non-authorization code are ignored
vim app/api/employee.py

# Add a helper function that doesn't touch auth
git add app/api/employee.py
git commit -m "Add helper function"
```

**Output:**
```
✓ No authorization logic changes detected
```

## AST Detection vs Regex

### Why AST is Superior

**Regex Approach (Unreliable):**
```python
# ❌ Regex: if.*state\.role.*==.*"employee"
# Problems:
# - Matches comments: # if state.role == "employee"
# - Matches strings: print("if state.role == 'employee'")
# - Misses variations: if "employee" == state.role
# - Can't understand context
```

**AST Approach (Reliable):**
```python
# ✓ AST: Parse syntax tree, find Compare nodes
# Benefits:
# - Understands Python syntax
# - Ignores comments and strings
# - Catches all variations
# - Provides precise context
```

### Real Example

**Code:**
```python
def authorize(state):
    # This comment mentions state.role == "employee" but isn't checked
    description = "Check if state.role == 'manager'"  # String literal

    # ✓ AST detects this:
    if state.role == "employee":
        return True

    # ✓ AST detects this too (different order):
    if "hr" == state.role:
        return True
```

**Regex:** Would match all 4 occurrences (2 false positives)
**AST:** Matches only the 2 actual comparisons ✓

## Architecture Integration

### Files Analyzed

The hook analyzes these files for authorization patterns:

✅ **Checked:**
- `app/agent/nodes/authorize.py` - Main authorization logic
- `app/agent/nodes/execute.py` - May contain auth checks
- `app/api/*.py` - API endpoint authorization
- Any file with authorization functions

❌ **Excluded:**
- `tests/test_*.py` - Test files (obviously)
- Files without authorization patterns

### Test File Requirements

When authorization logic changes, the hook expects updates to:

1. **Primary:** `tests/test_authorization_rbac.py`
2. **Or:** Any test file with "authorization", "auth", "rbac", or "permission" in the name

Examples:
- `tests/test_authorization_rbac.py` ✓
- `tests/test_auth.py` ✓
- `tests/test_rbac_employee.py` ✓
- `tests/test_permission_checks.py` ✓

## What Tests Should Cover

When you change authorization logic, your tests MUST cover:

### 1. Positive Cases (What SHOULD work)
```python
def test_hr_can_delete_employees(agent_session):
    """Verify HR role can perform the action."""
    chat(agent_session, "Login with email hr@company.com")
    r = chat(agent_session, "Delete employee John")
    assert "deleted" in r["message"].lower()
```

### 2. Negative Cases (What should NOT work)
```python
def test_employee_cannot_delete_employees(agent_session):
    """Verify employee role cannot perform the action."""
    chat(agent_session, "Login with email employee@company.com")
    r = chat(agent_session, "Delete employee John")
    assert "not authorized" in r["message"].lower()
```

### 3. Edge Cases
```python
def test_unauthenticated_user_denied(agent_session):
    """Verify unauthenticated users are denied."""
    # Don't log in
    r = chat(agent_session, "View profile")
    assert "not authenticated" in r["message"].lower()

def test_unknown_role_denied(agent_session):
    """Verify unknown roles are denied."""
    # Simulate unknown role
    assert "permission" in response.lower()
```

### 4. Self-Modification Cases
```python
def test_user_cannot_escalate_own_role(agent_session):
    """Verify users cannot escalate their own privileges."""
    chat(agent_session, "Login with email employee@company.com")
    r = chat(agent_session, "Update my role to HR")
    assert "not authorized" in r["message"].lower()
```

## Testing the Hook

### Run Tests
```bash
# Test the AST detection
python .pre-commit-hooks/test_auth_hook.py
```

**Output:**
```
Authorization Hook AST Detection Tests
================================================================================

Testing AST Detection Capabilities
Test Case 1: ✓ PASS
Test Case 2: ✓ PASS
...
✓ All tests passed!
```

### Manual Testing
```bash
# Test on specific file
python .pre-commit-hooks/check_authorization_changes.py app/agent/nodes/authorize.py

# Test on all staged files
pre-commit run check-authorization-changes
```

## Customization

### Adding New Authorization Patterns

Edit `.pre-commit-hooks/check_authorization_changes.py`:

```python
class AuthorizationASTVisitor(ast.NodeVisitor):

    def visit_FunctionDef(self, node: ast.FunctionDef):
        # Add custom function names
        auth_function_names = [
            'authorize', 'check_permission',
            'your_custom_auth_function',  # ← ADD HERE
        ]
```

### Adding New Role Values

```python
def visit_Compare(self, node: ast.Compare):
    # Add custom role values
    role_values = {
        'employee', 'manager', 'hr',
        'admin', 'superuser',  # ← ADD HERE
    }
```

### Adding New Test File Patterns

```python
def _has_updated_auth_tests(self):
    auth_test_files = [
        'test_authorization',
        'test_auth',
        'test_your_custom_pattern',  # ← ADD HERE
    ]
```

## Performance

### Benchmarks

- **Single file analysis:** ~10-50ms
- **Full codebase (all .py files):** ~200-500ms
- **Typical commit (2-3 files):** ~30-100ms

### Why It's Fast

1. **Only analyzes staged files** (not entire repo)
2. **AST parsing is native Python** (fast C implementation)
3. **Early exclusion** of test files
4. **Minimal git operations**

## Troubleshooting

### Hook Not Detecting Changes

**Check if the file contains authorization patterns:**
```bash
python .pre-commit-hooks/check_authorization_changes.py app/your_file.py
```

**Debug AST parsing:**
```python
import ast
from check_authorization_changes import AuthorizationASTVisitor

with open('app/agent/nodes/authorize.py') as f:
    tree = ast.parse(f.read())
    visitor = AuthorizationASTVisitor('authorize.py')
    visitor.visit(tree)

    for pattern in visitor.patterns:
        print(f"Line {pattern.line_number}: {pattern.pattern_type}")
```

### False Positives

AST-based detection has **very few false positives** because it understands syntax.

If you get a false positive:
1. Check if the line actually contains authorization logic
2. If not, file an issue with the code example
3. Temporarily bypass with `--no-verify`

### False Negatives

If authorization changes aren't detected:
1. Check if the pattern is in the visitor's detection list
2. Add the pattern (see Customization above)
3. Run `test_auth_hook.py` to verify

## Comparison: Write Capability Hook vs Auth Hook

| Feature | Write Capability Hook | Auth Hook |
|---------|----------------------|-----------|
| **Detection Method** | Regex + keyword matching | AST parsing |
| **Accuracy** | Good for keywords | Excellent (syntax-aware) |
| **False Positives** | Some (comments, strings) | Very few |
| **What It Detects** | DB mutations, HTTP endpoints | Authorization logic |
| **Test Required** | Any test mentioning capability | Authorization test specifically |
| **Use Case** | New data mutations | Auth/RBAC changes |

## Security Rationale

This hook is critical for agent-based systems because:

### 1. Authorization Bypasses are Common in Agent Systems
- Agents can manipulate state to bypass checks
- Role drift via state mutation
- Prior tool-call confusion

### 2. Tests Document Security Invariants
```python
# This test documents: "Employees cannot delete others"
def test_employee_cannot_delete(agent_session):
    assert "not authorized" in response
```

### 3. Prevents Regressions
- Authorization bugs are often subtle
- Easy to accidentally remove a check
- Tests catch regressions immediately

### 4. Forces Security Thinking
- Developers must write tests for auth changes
- Tests make security requirements explicit
- Code review can focus on test quality

## Best Practices

### 1. Write Tests First (TDD)
```bash
# Step 1: Write failing test
vim tests/test_authorization_rbac.py

# Step 2: Implement authorization change
vim app/agent/nodes/authorize.py

# Step 3: Verify test passes
pytest tests/test_authorization_rbac.py -v

# Step 4: Commit together
git add tests/test_authorization_rbac.py app/agent/nodes/authorize.py
git commit -m "Add new authorization rule with tests"
```

### 2. Test Both Directions
```python
# ✓ Good: Test allowed AND denied
def test_hr_can_delete():
    assert "deleted" in response

def test_employee_cannot_delete():
    assert "not authorized" in response

# ✗ Bad: Only test allowed
def test_delete():
    assert "deleted" in response
```

### 3. Use Descriptive Test Names
```python
# ✓ Good: Explains the security invariant
def test_employee_cannot_escalate_own_role()
def test_hr_required_for_deletion()
def test_unauthenticated_users_denied()

# ✗ Bad: Unclear what's being tested
def test_auth()
def test_delete()
```

### 4. Keep Authorization Tests Separate
```python
# ✓ Good: Dedicated authorization test file
tests/test_authorization_rbac.py

# ✗ Bad: Mixed with other tests
tests/test_everything.py
```

## Summary

- ✅ **AST-based**: More reliable than regex
- ✅ **Authorization-focused**: Detects RBAC changes specifically
- ✅ **Test-enforcing**: Requires auth test updates
- ✅ **Fast**: ~50ms per file
- ✅ **Accurate**: Few false positives/negatives
- ✅ **Customizable**: Easy to add new patterns

**Next Steps:**
1. Install: Already configured in `.pre-commit-config.yaml`
2. Test: Run `python .pre-commit-hooks/test_auth_hook.py`
3. Use: Make auth changes and see the hook in action

---

**Remember**: Authorization is the last line of defense in your system. This hook ensures that defense is always tested. 🔒
