# Quick Start: Pre-Commit Hook for Write Capabilities

## 1. Install Pre-Commit (One-Time Setup)

```bash
# Using uv (recommended for this project)
uv pip install pre-commit

# Or using pip
pip install pre-commit
```

## 2. Install Git Hooks

```bash
# Install the pre-commit hook into your git repository
pre-commit install

# You should see:
# pre-commit installed at .git/hooks/pre-commit
```

## 3. Test the Installation

```bash
# Run on all files to test
pre-commit run check-write-capabilities --all-files
```

Expected output (for current codebase with tests):
```
Check Write Capabilities.........................................................Passed
```

## 4. How It Works

### Example 1: Adding Code Without Tests ❌

Let's say you add a new endpoint to `app/api/employee.py`:

```python
@router.post("/employee/bulk-update")
def bulk_update_employees(employee_ids: List[int], payload: dict, db: Session = Depends(get_db)):
    for emp_id in employee_ids:
        emp = db.query(Employee).filter(Employee.id == emp_id).first()
        for field, value in payload.items():
            setattr(emp, field, value)
    db.commit()
    return {"status": "updated", "count": len(employee_ids)}
```

When you try to commit:

```bash
git add app/api/employee.py
git commit -m "Add bulk update endpoint"
```

The hook will **BLOCK** the commit and output:

```
================================================================================
⚠️  WRITE CAPABILITY VIOLATIONS DETECTED
================================================================================

The following write capabilities were added without corresponding tests:

  app/api/employee.py:110
    → HTTP POST endpoint detected: bulk_update_employees

  app/api/employee.py:114
    → Database mutation detected: setattr

================================================================================
REMEDIATION:
================================================================================
1. Add tests for the new write capabilities in the tests/ directory
...
```

### Example 2: Adding Code With Tests ✅

First, create the test in `tests/test_bulk_update.py`:

```python
def test_hr_can_bulk_update_employees(agent_session):
    chat(agent_session, "Login with email mark.jensen@company.com")

    r = chat(agent_session, "Update locations for employees 6 and 7 to London")
    assert "updated" in r["message"].lower()
```

Then commit both files:

```bash
git add app/api/employee.py tests/test_bulk_update.py
git commit -m "Add bulk update endpoint with tests"
```

The hook will **PASS**:

```
Check Write Capabilities.........................................................Passed
✓ No new write capabilities detected without tests
```

## 5. Common Scenarios

### Scenario A: Work-in-Progress Commit

If you're working on a feature and want to commit without tests temporarily:

```bash
# Bypass the hook (use sparingly!)
git commit --no-verify -m "WIP: Add feature skeleton"
```

⚠️ Remember to add tests before the final commit!

### Scenario B: Updating Existing Code

The hook only checks **newly added lines**. If you're modifying existing code, it won't flag it unless you add new mutation operations.

### Scenario C: Read-Only Operations

The hook ignores read-only operations:

```python
# These will NOT be flagged:
def get_employee(db: Session, emp_id: int):
    return db.query(Employee).filter(Employee.id == emp_id).first()

@router.get("/employee/{employee_id}")
def get_employee(employee_id: int):
    # ...
```

## 6. What Gets Detected?

### ✓ Database Mutations
- `db.add()` - Creating records
- `db.delete()` - Deleting records
- `db.commit()` - Committing changes
- `setattr()` - Modifying attributes

### ✓ HTTP Mutation Endpoints
- `@router.post()`
- `@router.put()`
- `@router.patch()`
- `@router.delete()`

### ✓ Mutation Functions
- `create_*()`, `update_*()`, `delete_*()`
- `insert_*()`, `remove_*()`, `onboard_*()`

### ✓ Agent State Mutations
- `state.field = value`
- `state.api_args = {...}`
- `selected_api = "..."`

## 7. Troubleshooting

### Hook Not Running?

```bash
# Check if installed
ls -la .git/hooks/pre-commit

# Reinstall
pre-commit uninstall
pre-commit install
```

### False Positive?

The hook looks for test files in `tests/` that contain relevant keywords. Make sure:

1. Test file is named `test_*.py`
2. Test file is in the `tests/` directory
3. Test contains function names or keywords matching your code

Example matching patterns:
- Function `update_employee()` → test should contain "update_employee" or "update" + "employee"
- File `app/api/employee.py` → looks for tests containing "test_api"
- File `app/agent/nodes/execute.py` → looks for tests containing "test_agent"

### Still Having Issues?

```bash
# Run with verbose output
pre-commit run check-write-capabilities --all-files --verbose

# Test the hook directly
python .pre-commit-hooks/check_write_capabilities.py app/api/employee.py
```

## 8. Best Practices

### 1. Test-Driven Development (TDD)
Write tests **before** implementing the feature:

```bash
# Step 1: Write test
vim tests/test_new_feature.py

# Step 2: Implement feature
vim app/api/employee.py

# Step 3: Commit together
git add tests/test_new_feature.py app/api/employee.py
git commit -m "Add new feature with tests"
```

### 2. Security-Focused Tests
For write operations, ensure tests cover:

- ✅ **Authorization**: Can only authorized roles perform the action?
- ✅ **Self-modification**: Can users modify their own sensitive data?
- ✅ **Validation**: Are inputs validated?
- ✅ **HITL**: Do destructive actions require confirmation?

Example:

```python
def test_employee_cannot_update_own_role(agent_session):
    chat(agent_session, "Login with email priya.nair@company.com")
    r = chat(agent_session, "Update my role to HR")
    assert "not authorized" in r["message"].lower()

def test_hr_can_update_employee_role(agent_session):
    chat(agent_session, "Login with email mark.jensen@company.com")
    r = chat(agent_session, "Update Priya Nair role to manager")
    assert "updated" in r["message"].lower()

def test_delete_requires_confirmation(agent_session):
    chat(agent_session, "Login with email mark.jensen@company.com")
    r = chat(agent_session, "Delete employee John Miller")
    assert "are you sure" in r["message"].lower()
```

### 3. Meaningful Test Names
Use descriptive test names that explain the security invariant:

```python
# ✅ Good
def test_employee_cannot_delete_other_employees()

# ❌ Bad
def test_delete()
```

## 9. Integration with CI/CD

Add to your CI pipeline (e.g., GitHub Actions):

```yaml
# .github/workflows/ci.yml
- name: Run pre-commit hooks
  run: |
    pip install pre-commit
    pre-commit run --all-files
```

## 10. Updating the Hook

To get the latest version:

```bash
# Update all hooks
pre-commit autoupdate

# Or manually update
git pull origin main
pre-commit install --install-hooks
```

## Summary

| Action | Command |
|--------|---------|
| Install | `pre-commit install` |
| Run on all files | `pre-commit run --all-files` |
| Run on staged files | `pre-commit run` |
| Bypass once | `git commit --no-verify` |
| Uninstall | `pre-commit uninstall` |
| Update | `pre-commit autoupdate` |

---

**Remember**: This hook is designed to enforce a security-critical practice. Write operations in agent systems can bypass authorization if not properly tested. Always include comprehensive tests for mutations! 🔒
