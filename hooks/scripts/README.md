# Write Capability Detection Hook

## Overview

This directory contains a custom pre-commit hook that detects when new write capabilities (data mutations) are added to the employee-agent-app without corresponding tests.

## Architecture

```
.pre-commit-hooks/
├── check_write_capabilities.py  # Main hook implementation
├── test_hook.py                 # Unit tests for the hook
├── demo.sh                      # Interactive demonstration
└── README.md                    # This file
```

## Hook Implementation

### File: `check_write_capabilities.py`

The main hook script that:

1. **Analyzes staged Python files** for write capabilities
2. **Detects mutation patterns**:
   - Database operations: `db.add()`, `db.delete()`, `db.commit()`, `setattr()`
   - HTTP endpoints: `@router.post/put/patch/delete()`
   - Function names: `create_*`, `update_*`, `delete_*`, etc.
   - Agent state mutations: `state.field =`, `state.api_args`

3. **Checks for test coverage** by:
   - Searching the `tests/` directory
   - Looking for function names and keywords
   - Verifying tests exist for each detected write capability

4. **Reports violations** with:
   - File path and line number
   - Type of mutation detected
   - Remediation steps

### Detection Strategy

The hook uses multiple strategies to identify write capabilities:

#### 1. Keyword Detection
```python
MUTATION_KEYWORDS = {
    "db.add",      # Creating records
    "db.delete",   # Deleting records
    "db.commit",   # Committing transactions
    "setattr",     # Modifying attributes
}
```

#### 2. Decorator Pattern Matching
```python
HTTP_MUTATION_METHODS = {
    "post",   # Create
    "put",    # Full update
    "patch",  # Partial update
    "delete", # Delete
}
```

#### 3. Function Name Patterns
```python
MUTATION_FUNCTION_PATTERNS = [
    r"def\s+(create_|update_|delete_)\w+",
    r"def\s+\w+_(create|update|delete)\w*",
]
```

#### 4. Agent State Patterns
```python
AGENT_STATE_MUTATIONS = [
    r"state\.\w+\s*=",
    r"state\.api_args",
    r"selected_api\s*=",
]
```

### Test Coverage Detection

The hook searches for tests using these heuristics:

1. **Direct function name match**: `test_create_employee` for `create_employee()`
2. **Keyword matching**: Tests containing relevant keywords
3. **Module-based matching**:
   - `app/api/*` → looks for tests with "test_api"
   - `app/agent/*` → looks for tests with "test_agent"

## Usage

### Installation

```bash
# Install pre-commit framework
pip install pre-commit

# Install git hooks
pre-commit install
```

### Running the Hook

```bash
# Automatic (on every commit)
git commit -m "Your message"

# Manual (all files)
pre-commit run check-write-capabilities --all-files

# Manual (specific file)
python .pre-commit-hooks/check_write_capabilities.py app/api/employee.py
```

### Demo

```bash
# Run interactive demonstration
./.pre-commit-hooks/demo.sh
```

This will show:
1. Blocking a commit with write capabilities but no tests
2. Allowing a commit with write capabilities and tests
3. Allowing a commit with read-only operations

## Configuration

### Excluded Files

The hook automatically excludes:

- Test files: `test_*.py`, `/tests/*`
- Setup files: `__init__.py`, `conftest.py`
- Database setup: `database.py`
- Migrations: `/migrations/*`
- Seed data: `/seed/*`

### Customization

Edit `check_write_capabilities.py` to customize:

```python
# Add custom mutation keywords
MUTATION_KEYWORDS.add("your_custom_pattern")

# Add custom function patterns
MUTATION_FUNCTION_PATTERNS.append(r"def\s+your_pattern\w+")

# Modify exclusions
def _is_excluded_file(self, file_path: str) -> bool:
    excluded_patterns.append("/your_excluded_path/")
```

## Testing the Hook

### Unit Tests

```bash
python .pre-commit-hooks/test_hook.py
```

This creates temporary test scenarios and verifies the hook behaves correctly.

### Manual Testing

```bash
# Create a test file with a mutation
cat > app/test_mutation.py << 'EOF'
def create_something(db):
    db.add(Something())
    db.commit()
EOF

# Stage and test
git add app/test_mutation.py
pre-commit run check-write-capabilities

# Expected: Hook should fail (no tests)

# Add a test
cat > tests/test_something.py << 'EOF'
def test_create_something():
    pass
EOF

git add tests/test_something.py
pre-commit run check-write-capabilities

# Expected: Hook should pass (tests exist)
```

## Integration

### With CI/CD

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: pip install pre-commit
      - name: Run pre-commit
        run: pre-commit run --all-files
```

### With Other Hooks

This hook is designed to work alongside:

- **Black**: Code formatting
- **Ruff**: Linting
- **Pytest**: Test execution
- **MyPy**: Type checking

See `.pre-commit-config.yaml` for the full configuration.

## Output Examples

### Success

```
✓ No new write capabilities detected without tests
```

### Failure

```
================================================================================
⚠️  WRITE CAPABILITY VIOLATIONS DETECTED
================================================================================

The following write capabilities were added without corresponding tests:

  app/api/employee.py:58
    → HTTP PUT endpoint detected: update_employee

  app/agent/nodes/execute.py:194
    → Mutation function detected: update_employee

  app/agent/nodes/execute.py:230
    → Database mutation detected: db.commit

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
```

## Security Rationale

This hook enforces a critical security practice for agent-based systems:

### Why Test Coverage Matters for Agents

1. **Agents can manipulate authorization inputs**
   - Traditional RBAC checks the selected_api
   - But the agent controls what gets selected
   - Tests verify the agent can't bypass authorization

2. **State mutations are high-risk**
   - Agent state carries across turns
   - Memory poisoning can escalate privileges
   - Tests document expected state transitions

3. **Write operations are irreversible**
   - Data deletion can't be undone
   - Role escalation creates security holes
   - Tests prevent regressions in security controls

### Test Requirements for Write Operations

Every write capability should have tests for:

- ✅ **Success path**: Authorized user can perform operation
- ✅ **Authorization**: Unauthorized user is blocked
- ✅ **Self-modification**: Users can't escalate own privileges
- ✅ **HITL**: Destructive operations require confirmation
- ✅ **Edge cases**: Invalid inputs, missing data, etc.

## Performance

### Optimization Strategies

1. **Only checks staged files**: Not the entire codebase
2. **Git diff analysis**: Only inspects added lines
3. **Early exclusion**: Skips test files immediately
4. **Parallel checks**: Could be enhanced for large changesets

### Typical Performance

- Single file: < 100ms
- Small commit (2-5 files): < 500ms
- Large commit (10+ files): < 2s

## Troubleshooting

### Common Issues

**Issue**: Hook doesn't run
```bash
# Solution: Verify installation
pre-commit install
ls -la .git/hooks/pre-commit
```

**Issue**: False positives
```bash
# Solution: Check test naming
# Tests must be in tests/ directory
# Tests must contain relevant keywords
```

**Issue**: Hook is slow
```bash
# Solution: Run on specific files only
pre-commit run check-write-capabilities --files app/api/employee.py
```

### Debug Mode

```bash
# Run with verbose output
python .pre-commit-hooks/check_write_capabilities.py app/api/employee.py

# Or use pre-commit verbose mode
pre-commit run check-write-capabilities --verbose --all-files
```

## Contributing

To improve this hook:

1. **Add new detection patterns** for mutation types
2. **Improve test discovery** heuristics
3. **Add AST-based analysis** for more accurate detection
4. **Support additional frameworks** (SQLAlchemy async, etc.)

## License

MIT License - See main project LICENSE file.

## References

- [Pre-commit framework](https://pre-commit.com/)
- [Main project README](../README.md)
- [Test philosophy](../README.md#test-philosophy)
- [Quickstart guide](../QUICKSTART_HOOK.md)
- [Detailed documentation](../README_PRECOMMIT.md)
