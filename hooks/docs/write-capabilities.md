# Pre-Commit Hook: Write Capability Detection

## Overview

This pre-commit hook automatically detects when new write capabilities (data mutations) are added to the system and ensures corresponding tests exist.

## What It Detects

The hook analyzes staged changes to identify:

### 1. Database Mutations
- `db.add()` - Creating new records
- `db.delete()` - Deleting records
- `db.commit()` - Committing transactions
- `setattr()` / `delattr()` - Modifying object attributes

### 2. HTTP Mutation Endpoints
- `@router.post()` - Create operations
- `@router.put()` - Update operations
- `@router.patch()` - Partial update operations
- `@router.delete()` - Delete operations

### 3. Mutation Functions
Functions with names indicating write operations:
- `create_*`, `*_create*`
- `update_*`, `*_update*`
- `delete_*`, `*_delete*`
- `insert_*`, `*_insert*`
- `remove_*`, `*_remove*`
- `onboard_*`, `*_onboard*`

### 4. Agent State Mutations
In agent code (`/agent/` directory):
- Direct state assignments: `state.field =`
- API args manipulation: `state.api_args`
- API selection: `selected_api =`

## Installation

### Option 1: Local Installation (Recommended)

```bash
# Install pre-commit (if not already installed)
pip install pre-commit

# Or using uv
uv pip install pre-commit

# Install the git hooks
pre-commit install
```

### Option 2: Manual Installation

```bash
# Make the hook executable
chmod +x .pre-commit-hooks/check_write_capabilities.py

# Copy to git hooks directory
cp .git/hooks/pre-commit.sample .git/hooks/pre-commit

# Add the following to .git/hooks/pre-commit:
python .pre-commit-hooks/check_write_capabilities.py
```

## Usage

### Automatic (on commit)

Once installed, the hook runs automatically on every `git commit`:

```bash
git add app/api/employee.py
git commit -m "Add new employee update endpoint"

# Hook will run and check for tests
```

### Manual Execution

Run on all files:
```bash
pre-commit run check-write-capabilities --all-files
```

Run on specific files:
```bash
python .pre-commit-hooks/check_write_capabilities.py app/api/employee.py
```

Run only on staged files:
```bash
pre-commit run check-write-capabilities
```

## Example Output

### When violations are found:

```
================================================================================
⚠️  WRITE CAPABILITY VIOLATIONS DETECTED
================================================================================

The following write capabilities were added without corresponding tests:

  app/api/employee.py:58
    → HTTP PUT endpoint detected: update_employee

  app/agent/nodes/execute.py:194
    → Mutation function detected: update_employee

================================================================================
REMEDIATION:
================================================================================
1. Add tests for the new write capabilities in the tests/ directory
2. Ensure tests cover:
   - Successful operations
   - Authorization checks (RBAC)
   - Edge cases and error conditions
3. Run: uv run pytest tests/ -v
4. Re-run: git commit

To bypass this check (NOT RECOMMENDED):
  git commit --no-verify
================================================================================
```

### When no violations found:

```
✓ No new write capabilities detected without tests
```

## Test Requirements

For a write capability to pass the hook, corresponding tests must exist in the `tests/` directory.

### Test Naming Conventions

The hook searches for tests using these patterns:

1. **Function name matches**: `test_update_employee`
2. **Keyword matches**: Function/capability keywords appear in test file
3. **Module matches**:
   - API changes → looks for tests containing `test_api`
   - Agent changes → looks for tests containing `test_agent`

### Example Test Structure

For a new `delete_employee` capability:

```python
# tests/test_agent_delete.py

def test_hr_can_delete_employee(agent_session):
    """Test that HR role can delete employees."""
    chat(agent_session, "Login with email mark.jensen@company.com")

    r = chat(agent_session, "Delete employee John Miller")
    assert "are you sure" in r["message"].lower()

    r = chat(agent_session, "Yes")
    assert "deleted successfully" in r["message"].lower()


def test_employee_cannot_delete_others(agent_session):
    """Test that employees cannot delete other employees."""
    chat(agent_session, "Login with email priya.nair@company.com")

    r = chat(agent_session, "Delete employee John Miller")
    assert "not authorized" in r["message"].lower()


def test_cannot_delete_self(agent_session):
    """Test that users cannot delete their own profile."""
    chat(agent_session, "Login with email mark.jensen@company.com")

    r = chat(agent_session, "Delete myself")
    assert "cannot delete your own" in r["message"].lower()
```

## Customization

### Adjusting Detection Patterns

Edit `.pre-commit-hooks/check_write_capabilities.py`:

```python
# Add custom mutation keywords
MUTATION_KEYWORDS = {
    "db.add",
    "db.delete",
    "db.commit",
    "setattr",
    "your_custom_pattern",
}

# Add custom function patterns
MUTATION_FUNCTION_PATTERNS = [
    r"def\s+(create_|update_|delete_)\w+",
    r"def\s+your_custom_pattern\w+",
]
```

### Excluding Files

Edit `.pre-commit-config.yaml`:

```yaml
exclude: |
  (?x)(
    ^\.venv/|
    ^migrations/|
    ^your_excluded_directory/
  )
```

Or in the Python script:

```python
def _is_excluded_file(self, file_path: str) -> bool:
    excluded_patterns = [
        "test_",
        "/tests/",
        "/your_excluded_path/",
    ]
    return any(pattern in file_path for pattern in excluded_patterns)
```

## Bypassing the Hook

### Temporary Bypass (single commit)

```bash
git commit --no-verify -m "WIP: Add feature without tests"
```

⚠️ **Warning**: Only use for work-in-progress commits that will be amended later.

### Permanent Bypass (not recommended)

```bash
pre-commit uninstall
```

## Architecture Integration

This hook is specifically designed for the employee-agent-app architecture:

- **FastAPI** routes in `app/api/`
- **LangGraph** agent nodes in `app/agent/nodes/`
- **SQLAlchemy** models in `app/models/`
- **Tests** in `tests/`

### Files Checked

✅ **Checked**:
- `app/api/*.py` - API endpoints
- `app/agent/nodes/*.py` - Agent execution nodes
- `app/models/*.py` - Model definitions

❌ **Excluded**:
- `tests/` - Test files
- `app/seed/` - Data seeding scripts
- `app/database.py` - Database setup
- `migrations/` - Database migrations

## Troubleshooting

### Hook not running

```bash
# Verify installation
pre-commit run check-write-capabilities --all-files

# Reinstall
pre-commit uninstall
pre-commit install
```

### False positives

If the hook flags legitimate code that has tests:

1. Check test naming conventions match patterns
2. Ensure test files are in `tests/` directory
3. Verify test content includes relevant keywords

### Performance issues

For large commits:

```bash
# Run on specific files only
pre-commit run check-write-capabilities --files app/api/employee.py
```

## Best Practices

1. **Write tests first** (TDD approach) to avoid hook violations
2. **Commit tests with code** in the same commit when possible
3. **Use descriptive test names** that include the capability name
4. **Cover security aspects**:
   - Authorization (RBAC) checks
   - Self-modification prevention
   - HITL confirmation for destructive operations

## Security Rationale

This hook enforces test coverage for write operations because:

1. **Agent systems can bypass authorization** through state manipulation
2. **Write operations are high-risk** (data loss, privilege escalation)
3. **Tests serve as security documentation** of intended behavior
4. **Prevents regression** when fixing security issues

See `README.md` for more details on the security model.

## Contributing

To improve the hook:

1. Add detection patterns for new mutation types
2. Improve test discovery heuristics
3. Add support for additional frameworks
4. Report issues or false positives

## License

MIT License - See LICENSE file for details
