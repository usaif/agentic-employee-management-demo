# Security Code Deletion Detection Hook

## Overview

AST-based pre-commit hook that detects when security-relevant code is **removed** from your codebase. This hook prevents accidental security regressions by flagging deletions of:

1. **Input Validation** - Functions that validate/sanitize user input
2. **Authentication Checks** - `state.authenticated` checks
3. **Authorization Checks** - Role checks, `PermissionError` raises
4. **Audit Logging** - `log_event()`, `log_execution()` calls
5. **Rate Limiting** - Rate limit decorators/functions
6. **Error Handling** - `try/except` blocks, `HTTPException`

## Why This Matters

**Security code is often deleted accidentally:**
- During refactoring
- When "simplifying" code
- By developers unfamiliar with security requirements
- When merging branches

**One deleted check can compromise your entire system:**
```python
# Before: Secure
if not state.authenticated:
    raise PermissionError("Not authenticated")

# After: INSECURE (check removed)
# Anyone can access!
```

## Security Patterns Detected

### 1. Input Validation Functions

**What it detects:**
```python
def validate_user_input(data):     # ✓ Detected
def sanitize_email(email):         # ✓ Detected
def check_parameter(param):        # ✓ Detected
def verify_data_format(data):      # ✓ Detected
```

**Severity:** HIGH

**Why it matters:** Missing input validation → SQL injection, XSS, command injection

### 2. Authentication Checks

**What it detects:**
```python
if not state.authenticated:        # ✓ Detected
if state.authenticated:            # ✓ Detected
if not user.is_authenticated():    # ✓ Detected
```

**Severity:** CRITICAL

**Why it matters:** Missing auth checks → unauthorized access to system

### 3. Authorization Checks

**What it detects:**
```python
if state.role == "admin":          # ✓ Detected
if role != "employee":             # ✓ Detected
raise PermissionError("...")       # ✓ Detected
if has_permission(user, action):   # ✓ Detected
```

**Severity:** CRITICAL

**Why it matters:** Missing authz checks → privilege escalation

### 4. Audit Logging

**What it detects:**
```python
log_event("action", session_id)   # ✓ Detected
log_execution(session, action)    # ✓ Detected
audit_log(user, operation)        # ✓ Detected
```

**Severity:** HIGH

**Why it matters:** Missing audit logs → no evidence trail for security incidents

### 5. Rate Limiting

**What it detects:**
```python
@limiter.limit("5 per minute")    # ✓ Detected
@rate_limit(10, per_minute=True)  # ✓ Detected
if check_rate_limit(user):        # ✓ Detected
```

**Severity:** HIGH

**Why it matters:** Missing rate limits → DoS attacks, brute force attacks

### 6. Error Handling

**What it detects:**
```python
try:                               # ✓ Detected
    risky_operation()
except Exception as e:
    handle_error(e)

raise HTTPException(status=400)    # ✓ Detected
```

**Severity:** MEDIUM

**Why it matters:** Missing error handling → information leakage, crashes

## How It Works

### Detection Flow

```
Staged Changes
    ↓
Git Diff Analysis
    ↓
Extract Deleted Lines (-)
    ↓
Get OLD File Version (HEAD)
    ↓
AST Parse Old Version
    ↓
Identify Security Patterns
    ↓
Check if Patterns Were Deleted
    ↓
Report Violations with Context
```

### Example Detection

**Original Code (HEAD):**
```python
def update_employee(emp_id, data):
    # Security: Audit logging
    log_event("employee_update", session_id, {"emp_id": emp_id})

    # Security: Authorization check
    if state.role != "hr":
        raise PermissionError("Only HR can update employees")

    # Update logic
    employee.update(data)
```

**Modified Code (after deletions):**
```python
def update_employee(emp_id, data):
    # Update logic
    employee.update(data)
```

**Hook Output:**
```
⚠️  SECURITY CODE DELETION DETECTED

🔴 CRITICAL Severity Deletions:

  File: app/api/employee.py
  Line: 7
  Type: Authorization Check
  Context: Authorization check (PermissionError)

  Deleted code:
      7→     if state.role != "hr":
      8→         raise PermissionError("Only HR can update employees")

🟠 HIGH Severity Deletions:

  File: app/api/employee.py
  Line: 4
  Type: Audit Logging
  Context: Audit logging: log_event()

  Deleted code:
      4→     log_event("employee_update", session_id, {"emp_id": emp_id})
```

## Installation

Already configured in `.pre-commit-config.yaml`:

```yaml
- id: check-security-deletions
  name: Check Security Code Deletions
  entry: python .pre-commit-hooks/check_security_deletions.py
  language: system
  types: [python]
```

## Usage

### Automatic (on every commit)

```bash
git add app/api/employee.py
git commit -m "Refactor employee update"

# Hook runs automatically
# ⚠️  SECURITY CODE DELETION DETECTED (if security code removed)
```

### Manual Testing

```bash
# Test the hook
python .pre-commit-hooks/test_security_deletions.py

# Run on specific file
python .pre-commit-hooks/check_security_deletions.py app/api/employee.py
```

## Severity Levels

### 🔴 CRITICAL
- **Authentication checks** - Blocks unauthorized access
- **Authorization checks** - Prevents privilege escalation
- **Authorization functions** - Core RBAC logic

**Action:** Almost always reject the commit

### 🟠 HIGH
- **Audit logging** - Security event tracking
- **Input validation** - Prevents injection attacks
- **Rate limiting** - DoS/brute force protection

**Action:** Review carefully, usually reject

### 🟡 MEDIUM
- **Error handling** - Prevents information leakage
- **Defensive checks** - Prevents crashes

**Action:** Review and verify not security-critical

## Real-World Examples

### Example 1: Removed Auth Check

**Before:**
```python
def delete_employee(emp_id):
    if not state.authenticated:
        raise PermissionError("Authentication required")

    db.delete(Employee).filter_by(id=emp_id)
```

**After (INSECURE):**
```python
def delete_employee(emp_id):
    db.delete(Employee).filter_by(id=emp_id)
```

**Hook Detection:**
```
🔴 CRITICAL: Authentication check removed
→ Missing check: if not state.authenticated
→ SECURITY IMPACT: Unauthenticated users can delete employees!
```

### Example 2: Removed Audit Logging

**Before:**
```python
def change_role(emp_id, new_role):
    log_event("role_change", session_id, {
        "emp_id": emp_id,
        "old_role": emp.role,
        "new_role": new_role
    })
    emp.role = new_role
```

**After (INSECURE):**
```python
def change_role(emp_id, new_role):
    emp.role = new_role
```

**Hook Detection:**
```
🟠 HIGH: Audit logging removed
→ Missing: log_event("role_change", ...)
→ SECURITY IMPACT: Role changes won't be audited!
```

### Example 3: Removed Input Validation

**Before:**
```python
def update_profile(data):
    validated_data = validate_user_input(data)
    user.update(validated_data)
```

**After (INSECURE):**
```python
def update_profile(data):
    user.update(data)
```

**Hook Detection:**
```
🟠 HIGH: Input validation removed
→ Missing: validate_user_input(data)
→ SECURITY IMPACT: SQL injection, XSS attacks possible!
```

## When Deletions Are Acceptable

### Legitimate Scenarios

**1. Moving Code to Another File**
```python
# Old file: utils.py (being deleted)
def validate_email(email):
    ...

# New file: validators.py (new)
def validate_email(email):
    # Same validation, just moved
```

**Verification:** Ensure the security control exists in the new location

**2. Upgrading to Better Security**
```python
# Before: Manual role check
if state.role != "admin":
    raise PermissionError()

# After: Using proper authorization framework
@require_role("admin")
def secure_endpoint():
    ...
```

**Verification:** Ensure the new approach is actually more secure

**3. Feature Removal**
```python
# Removing deprecated feature entirely
# Old: delete_employee() - feature being removed
# The entire feature is deprecated, security checks no longer needed
```

**Verification:** Document the feature removal in commit message

## Remediation Guide

When the hook flags security deletions:

### Step 1: Review Each Deletion

```bash
# View the actual diff
git diff --cached app/your_file.py

# Check what was deleted
git show HEAD:app/your_file.py | grep -A5 -B5 "security_pattern"
```

### Step 2: Determine If Deletion Is Safe

**Questions to ask:**
- [ ] Is this security control still needed?
- [ ] Is there equivalent protection elsewhere?
- [ ] Was this moved to another file?
- [ ] Is this a refactoring or actual removal?
- [ ] Have I updated the threat model?

### Step 3: Take Appropriate Action

**If deletion was accidental:**
```bash
# Restore the file
git checkout HEAD -- app/your_file.py

# Re-apply changes carefully
vim app/your_file.py
```

**If deletion is legitimate:**
```bash
# Document WHY in commit message
git commit -m "Remove deprecated feature X

Security checks for feature X removed because:
- Feature is completely deprecated
- No longer accessible via any API
- Replaced by feature Y with equivalent security
- Threat model updated (see docs/threats.md)
"
```

**If refactoring:**
```bash
# Verify security control exists in new location
grep -r "validate_user_input" app/

# Commit with clear message
git commit -m "Refactor: Move validation to validators.py"
```

### Step 4: Bypass Hook (If Necessary)

**Only after security team approval:**
```bash
git commit --no-verify -m "Approved by security team: ticket #123"
```

## Architecture Integration

### Files Analyzed

✅ **Checked:**
- `app/api/*.py` - API endpoints
- `app/agent/nodes/*.py` - Agent logic
- `app/models/*.py` - Model files
- Any file with security patterns

❌ **Excluded:**
- `tests/` - Test files
- `app/seed/` - Seed data
- `__init__.py` - Init files
- `conftest.py` - Test configuration

### Integration with Other Hooks

This hook complements the other hooks:

| Hook | Purpose | Timing |
|------|---------|--------|
| **Write Capability** | Detects new mutations | On addition |
| **Authorization Changes** | Detects auth logic changes | On modification |
| **Security Deletions** | Detects security removal | On deletion |

**Together they provide:** Complete coverage of security changes

## Performance

### Benchmarks

- **Single file analysis:** ~20-50ms
- **Typical commit (2-3 files):** ~50-150ms
- **Large commit (10+ files):** ~200-500ms

### Why It's Fast

1. **Only modified files** - Not entire repo
2. **AST caching** - Parse once per file
3. **Early exclusion** - Skip test files
4. **Efficient diff parsing** - Only analyze deleted lines

## Troubleshooting

### Hook Not Detecting Deletions

**Check if security patterns exist:**
```bash
# View old version of file
git show HEAD:app/your_file.py

# Check for patterns
grep -E "log_event|PermissionError|authenticated" app/your_file.py
```

### False Positives

Very rare with AST-based detection. If you encounter one:

1. Verify the pattern is actually deleted
2. Check if it's truly security-relevant
3. Document in commit message
4. Use `--no-verify` if approved

### False Negatives

If security deletions aren't caught:

1. Check if pattern is in detection list
2. Verify file isn't excluded
3. Report pattern for addition

## Customization

### Add Custom Security Patterns

```python
# In check_security_deletions.py

class SecurityASTAnalyzer(ast.NodeVisitor):

    def visit_FunctionDef(self, node: ast.FunctionDef):
        # Add custom validation function names
        validation_keywords = [
            'validate', 'sanitize',
            'your_custom_validator',  # ← Add here
        ]
```

### Add Custom Severity

```python
# Add new logging pattern
if func_name in ['your_custom_log_function']:
    self.security_patterns[node.lineno].append(SecurityPattern(
        line_number=node.lineno,
        pattern_type="custom_audit",
        code_snippet=self._get_line(node.lineno),
        context=f"Custom audit: {func_name}()",
        severity="high"  # critical, high, or medium
    ))
```

## Best Practices

### 1. Never Delete Security Code Without Review

```bash
# ✗ Bad: Delete without thinking
git add -A
git commit -m "cleanup"

# ✓ Good: Review deletions
git diff --cached
# See security code being deleted
# Pause and review
```

### 2. Document Security Removals

```bash
# ✓ Good commit message
git commit -m "Remove deprecated admin override

Security impact:
- Removed check: if user.is_admin_override
- Reason: Admin override feature deprecated
- Compensating control: All admin actions now require 2FA
- Threat model: Updated in docs/security.md
- Approved by: security-team (ticket #456)
"
```

### 3. Verify Refactorings

```python
# ✓ Good: Ensure security moved, not removed
# Before (old_file.py):
if not state.authenticated:
    raise PermissionError()

# After (new_file.py):
@require_authentication  # Equivalent protection
def endpoint():
    ...
```

### 4. Keep Audit Trail

```python
# ✓ Good: Maintain audit logging
log_event("action_performed", session_id, details)

# ✗ Bad: Remove logging during "cleanup"
# (Removes evidence trail for security incidents)
```

## Security Benefits

### Prevents Common Mistakes

**1. Refactoring Gone Wrong**
```python
# Developer removes "duplicate" code
# Not realizing one is security check, other is business logic
```

**2. Copy-Paste Errors**
```python
# Developer copies function
# Forgets to include security checks
```

**3. "Simplification" Attacks**
```python
# "Simplifying" code by removing "unnecessary" checks
# Actually removes critical security controls
```

### Enforces Security by Default

- Security must be explicitly removed (not accidentally)
- Deletions require documentation
- Code review focuses on security implications
- Audit trail of security changes

## Summary

✅ **AST-Based Detection** - Accurate, syntax-aware
✅ **Severity Classification** - Critical/High/Medium
✅ **Context Preservation** - Shows surrounding code
✅ **Comprehensive Coverage** - 6 security pattern types
✅ **Fast Performance** - ~50-150ms per commit
✅ **Production Ready** - Tested and documented

**This hook prevents the #1 cause of security regressions: accidental deletion of security controls.** 🔒

---

**Remember:** It's easier to prevent security code from being deleted than to notice and fix the breach later!
