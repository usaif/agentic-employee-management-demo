# Pre-Commit Hooks for Employee Agent App

## Overview

Three sophisticated AST-based pre-commit hooks that provide comprehensive security enforcement for your agent-based system.

## 🎯 The Three Hooks

### 1. Write Capability Detection
**Purpose:** Ensure new data mutations have tests

Detects additions of:
- Database operations (`db.add`, `db.delete`, `db.commit`)
- HTTP mutation endpoints (`@router.post/put/patch/delete`)
- Mutation functions (`create_*`, `update_*`, `delete_*`)
- Agent state changes

📖 **Documentation:** [docs/write-capabilities.md](docs/write-capabilities.md)

### 2. Authorization Change Detection (AST-based)
**Purpose:** Ensure RBAC changes have authorization tests

Detects modifications to:
- Role checks (`if state.role == "employee"`)
- Authentication checks (`if not state.authenticated`)
- Permission errors (`raise PermissionError(...)`)
- Authorization functions
- Action whitelists

📖 **Documentation:** [docs/authorization-changes.md](docs/authorization-changes.md)

### 3. Security Deletion Detection (AST-based) ⭐
**Purpose:** Prevent accidental removal of security controls

Detects deletions of:
- Authentication checks
- Authorization checks
- Audit logging (`log_event`, `log_execution`)
- Input validation functions
- Rate limiting logic
- Error handling

📖 **Documentation:** [docs/security-deletions.md](docs/security-deletions.md)

## 🚀 Quick Start

### Installation

```bash
# Automated
./INSTALL_HOOK.sh

# Manual
pip install pre-commit
pre-commit install
```

### Testing

```bash
# Test all hooks
python hooks/scripts/test_hook.py
python hooks/scripts/test_auth_hook.py
python hooks/scripts/test_security_deletions.py

# Run demos
bash hooks/scripts/demo.sh
bash hooks/scripts/demo_auth_hook.sh
```

### Usage

Hooks run automatically on every commit:

```bash
git add app/your_file.py
git commit -m "Your changes"

# Hooks analyze your changes automatically
# If violations found → commit blocked
# If all pass → commit succeeds
```

## 📊 Comparison

| Hook | Detects | Method | Speed | Test Required |
|------|---------|--------|-------|---------------|
| **Write Capabilities** | Additions | Regex + AST | ~50-100ms | Any test |
| **Authorization Changes** | Modifications | AST | ~15-50ms | Auth test |
| **Security Deletions** | Deletions | AST + diff | ~20-50ms | Review + doc |

**Combined:** ~140ms per commit, complete security coverage!

## 📁 Directory Structure

```
hooks/
├── README.md                    # This file
├── scripts/                     # Hook implementations
│   ├── check_write_capabilities.py
│   ├── check_authorization_changes.py
│   ├── check_security_deletions.py
│   ├── test_hook.py
│   ├── test_auth_hook.py
│   ├── test_security_deletions.py
│   ├── demo.sh
│   ├── demo_auth_hook.sh
│   └── README.md                # Implementation details
└── docs/                        # Documentation
    ├── quickstart.md            # Quick start guide
    ├── all-hooks-summary.md     # Overview of all hooks
    ├── write-capabilities.md    # Write hook detailed guide
    ├── authorization-changes.md # Auth hook detailed guide
    ├── security-deletions.md    # Deletion hook detailed guide
    └── complete-reference.md    # Complete reference
```

## 📖 Documentation

### Getting Started
- **[Quickstart Guide](docs/quickstart.md)** - Get up and running in 5 minutes
- **[All Hooks Summary](docs/all-hooks-summary.md)** - Overview and comparison

### Detailed Guides
- **[Write Capabilities](docs/write-capabilities.md)** - Detecting new mutations
- **[Authorization Changes](docs/authorization-changes.md)** - Detecting auth logic changes
- **[Security Deletions](docs/security-deletions.md)** - Detecting security removals

### Reference
- **[Complete Reference](docs/complete-reference.md)** - All hooks, all features
- **[Implementation Details](scripts/README.md)** - Technical implementation

## 🔍 What Gets Detected

### Write Capabilities Hook
```python
# This triggers the hook:
@router.post("/employee/promote")
def promote_employee(emp_id: int):
    emp.role = "manager"
    db.commit()  # ← Detected

# Requires test in tests/ directory
```

### Authorization Hook
```python
# This triggers the hook:
def authorize_action(state):
    if state.role == "employee":  # ← Detected
        if action in ("view", "update"):  # ← Detected
            return state
    raise PermissionError("Denied")  # ← Detected

# Requires auth test in tests/test_authorization_rbac.py
```

### Security Deletion Hook
```python
# BEFORE (secure):
def update_employee(data):
    log_event("update", session_id)  # Audit logging
    if state.role != "hr":           # Authorization
        raise PermissionError("Only HR")
    update(data)

# AFTER (if security removed):
def update_employee(data):
    update(data)

# Hook blocks this and shows:
# 🔴 CRITICAL: Authorization check removed
# 🟠 HIGH: Audit logging removed
```

## 💡 Real-World Workflow

```bash
# 1. Write tests first (TDD)
vim tests/test_authorization_rbac.py

# 2. Add authorization
vim app/agent/nodes/authorize.py

# 3. Implement feature
vim app/agent/nodes/execute.py

# 4. Commit everything together
git add tests/ app/agent/nodes/
git commit -m "Add promotion feature with security"

# ✅ All hooks pass
```

## ⚙️ Configuration

Hooks are configured in `.pre-commit-config.yaml`:

```yaml
- repo: local
  hooks:
    - id: check-write-capabilities
      entry: python hooks/scripts/check_write_capabilities.py

    - id: check-authorization-changes
      entry: python hooks/scripts/check_authorization_changes.py

    - id: check-security-deletions
      entry: python hooks/scripts/check_security_deletions.py
```

## 🎯 Commands

### Run All Hooks
```bash
pre-commit run --all-files
```

### Run Specific Hook
```bash
pre-commit run check-write-capabilities
pre-commit run check-authorization-changes
pre-commit run check-security-deletions
```

### Manual Testing
```bash
python hooks/scripts/check_write_capabilities.py app/api/employee.py
python hooks/scripts/check_authorization_changes.py app/agent/nodes/authorize.py
python hooks/scripts/check_security_deletions.py app/agent/nodes/execute.py
```

### Bypass (Emergency Only)
```bash
git commit --no-verify -m "Emergency fix - approved by security team"
```

## 🔒 Security Benefits

### Why These Hooks Matter

**For Agent-Based Systems:**
- Agents can manipulate state across turns
- Authorization can be bypassed through state mutation
- Write operations can be triggered without proper checks
- Security controls can be accidentally removed during refactoring

**These Hooks Provide:**
- ✅ Enforced test coverage for security-critical code
- ✅ Prevention of authorization bypasses
- ✅ Detection of security regressions
- ✅ Audit trail of security changes
- ✅ Security by default

## 📈 Performance

| Operation | Time |
|-----------|------|
| Single file | ~50ms |
| Typical commit (2-3 files) | ~140ms |
| Large commit (10+ files) | ~500ms |

Fast enough to not impact development! ⚡

## 🛠️ Troubleshooting

### Hooks Not Running
```bash
# Check installation
ls -la .git/hooks/pre-commit

# Reinstall
pre-commit uninstall
pre-commit install
```

### False Positives
- Write hook: Usually from comments containing keywords
- Auth hook: Very rare (AST-based)
- Deletion hook: Very rare (AST-based)

### Update Hooks
```bash
# Pull latest changes
git pull

# Reinstall
pre-commit install --install-hooks
```

## 🎨 Customization

All hooks support customization. Edit the scripts in `hooks/scripts/` to:
- Add new detection patterns
- Modify severity levels
- Adjust exclusion rules
- Customize error messages

See individual hook documentation for details.

## 📝 Best Practices

### 1. Test-Driven Development
Write tests before implementing features.

### 2. Never Delete Security Without Review
Always document why security controls are removed.

### 3. Keep All Hooks Enabled
Don't disable security hooks in production.

### 4. Document Security Changes
Include security impact in commit messages.

## 🆘 Support

- **Documentation:** See `docs/` directory
- **Implementation:** See `scripts/README.md`
- **Issues:** Review troubleshooting sections in docs

## 📜 License

MIT License - See main project LICENSE file.

---

**Three hooks. Complete security. One commit at a time.** 🔒

For detailed documentation, start with [docs/quickstart.md](docs/quickstart.md)
