#!/usr/bin/env python3
"""
Test script for security deletion detection hook.

Demonstrates AST-based detection of removed security controls.
"""

import ast
import sys
from pathlib import Path

# Import the hook
sys.path.insert(0, str(Path(__file__).parent))
from check_security_deletions import SecurityASTAnalyzer


def test_security_pattern_detection():
    """Test that security patterns are correctly identified."""

    test_cases = [
        # Test 1: Audit logging
        ("""
def process_action(data):
    log_event("action_executed", session_id, {"data": data})
    return result
""", ["audit_logging"]),

        # Test 2: Authentication check
        ("""
def secure_endpoint(state):
    if not state.authenticated:
        raise PermissionError("Not authenticated")
    return data
""", ["authentication_check", "authorization_check"]),

        # Test 3: Authorization check
        ("""
def check_access(state):
    if state.role == "admin":
        return True
    raise PermissionError("Unauthorized")
""", ["authorization_check"]),

        # Test 4: Input validation function
        ("""
def validate_user_input(data):
    if not data:
        raise ValueError("Invalid input")
    return sanitized
""", ["input_validation"]),

        # Test 5: Error handling
        ("""
def safe_operation():
    try:
        risky_operation()
    except Exception as e:
        log_error(e)
""", ["error_handling"]),

        # Test 6: HTTPException
        ("""
def api_endpoint(user_id):
    if not user_id:
        raise HTTPException(status_code=400, detail="Missing user_id")
""", ["error_handling"]),

        # Test 7: Multiple security patterns
        ("""
def authorize_action(state):
    log_event("authorization_check", state.session_id)

    if not state.authenticated:
        log_event("auth_denied", state.session_id)
        raise PermissionError("Not authenticated")

    if state.role != "admin":
        raise PermissionError("Insufficient privileges")
""", ["audit_logging", "authentication_check", "authorization_check"]),
    ]

    print("Testing Security Pattern Detection")
    print("=" * 80)

    all_passed = True

    for i, (code, expected_types) in enumerate(test_cases, 1):
        print(f"\nTest Case {i}:")
        print("-" * 40)
        print(code.strip())
        print("-" * 40)

        try:
            lines = code.strip().split('\n')
            tree = ast.parse(code)

            analyzer = SecurityASTAnalyzer(lines)
            analyzer.visit(tree)

            # Get all detected pattern types
            detected_types = set()
            for patterns in analyzer.security_patterns.values():
                for pattern in patterns:
                    detected_types.add(pattern.pattern_type)

            print(f"Expected: {', '.join(expected_types)}")
            print(f"Detected: {', '.join(detected_types)}")

            # Check if all expected patterns were found
            expected_set = set(expected_types)
            if expected_set.issubset(detected_types):
                print("✓ PASS")
            else:
                missing = expected_set - detected_types
                print(f"✗ FAIL - Missing: {missing}")
                all_passed = False

        except Exception as e:
            print(f"✗ FAIL - Exception: {e}")
            all_passed = False

    print("\n" + "=" * 80)
    if all_passed:
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed")
        return 1


def test_real_world_security_code():
    """Test on actual security code from the project."""

    print("\n" + "=" * 80)
    print("Testing Real-World Security Code Detection")
    print("=" * 80)

    # Simulate code from authorize.py with logging
    code = """
from app.logging.audit import log_event

def authorize_action(state):
    session_id = state.session_id
    role = state.role
    action = state.selected_api

    # Pre-auth flows allowed
    if action in ("login", "onboard_user"):
        log_event("authorization_allow", session_id, {"action": action})
        return state

    # Authentication required
    if not state.authenticated:
        log_event("authorization_deny", session_id, {"reason": "unauthenticated"})
        raise PermissionError("User not authenticated")

    # Employee permissions
    if role == "employee":
        if action == "get_my_profile":
            log_event("authorization_allow", session_id, {"role": role})
            return state
        log_event("authorization_deny", session_id, {"role": role})
        raise PermissionError("Employees may only view their own profile")

    # HR permissions
    if role == "hr":
        log_event("authorization_allow", session_id, {"role": role})
        return state

    raise PermissionError("Unknown role")
"""

    try:
        lines = code.strip().split('\n')
        tree = ast.parse(code)

        analyzer = SecurityASTAnalyzer(lines)
        analyzer.visit(tree)

        print("\nDetected Security Patterns:")
        print("-" * 80)

        pattern_counts = {}
        severity_counts = {'critical': 0, 'high': 0, 'medium': 0}

        for line_num, patterns in sorted(analyzer.security_patterns.items()):
            for pattern in patterns:
                pattern_type = pattern.pattern_type
                pattern_counts[pattern_type] = pattern_counts.get(pattern_type, 0) + 1
                severity_counts[pattern.severity] += 1

                print(f"  Line {line_num}: {pattern.pattern_type} ({pattern.severity})")
                print(f"    → {pattern.context}")

        print("\n" + "-" * 80)
        print("Summary:")
        print(f"  Total security patterns: {sum(pattern_counts.values())}")
        for pattern_type, count in sorted(pattern_counts.items()):
            print(f"    {pattern_type}: {count}")

        print(f"\n  By severity:")
        for severity in ['critical', 'high', 'medium']:
            if severity_counts[severity] > 0:
                print(f"    {severity.upper()}: {severity_counts[severity]}")

        # Verify expected patterns
        expected_patterns = {
            'authorization_function',
            'audit_logging',
            'authentication_check',
            'authorization_check'
        }

        detected = set(pattern_counts.keys())

        print("\n" + "=" * 80)
        if expected_patterns.issubset(detected):
            print("✓ Successfully detected all expected security patterns!")
            return 0
        else:
            print(f"✗ Missing patterns: {expected_patterns - detected}")
            return 1

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


def demonstrate_severity_levels():
    """Demonstrate severity level classification."""

    print("\n" + "=" * 80)
    print("Security Pattern Severity Levels")
    print("=" * 80)

    severity_examples = {
        'critical': [
            'Authentication checks (if not state.authenticated)',
            'Authorization checks (PermissionError raises)',
            'Role-based access control (if state.role == ...)',
        ],
        'high': [
            'Audit logging (log_event, log_execution)',
            'Input validation functions (validate_*, sanitize_*)',
            'Rate limiting decorators',
        ],
        'medium': [
            'Error handling (try/except, HTTPException)',
            'Defensive null checks (if x is None)',
        ]
    }

    for severity, examples in severity_examples.items():
        icon = {'critical': '🔴', 'high': '🟠', 'medium': '🟡'}[severity]
        print(f"\n{icon} {severity.upper()}:")
        for example in examples:
            print(f"  • {example}")

    print("\n" + "=" * 80)
    print("\nDeleting CRITICAL severity code will block commits by default.")
    print("Deletions should be carefully reviewed and documented.")


def main():
    print("Security Deletion Detection Hook - Test Suite")
    print("=" * 80)

    result1 = test_security_pattern_detection()
    result2 = test_real_world_security_code()
    demonstrate_severity_levels()

    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)
    print("\nThe security deletion hook can detect removal of:")
    print("  ✓ Authentication checks (state.authenticated)")
    print("  ✓ Authorization checks (PermissionError, role checks)")
    print("  ✓ Audit logging (log_event, log_execution)")
    print("  ✓ Input validation functions")
    print("  ✓ Error handling (try/except, HTTPException)")
    print("  ✓ Rate limiting logic")
    print("\nAdvantages:")
    print("  ✓ AST-based detection (accurate)")
    print("  ✓ Severity classification (critical/high/medium)")
    print("  ✓ Context-aware (shows surrounding code)")
    print("  ✓ Prevents accidental security regressions")

    return max(result1, result2)


if __name__ == "__main__":
    sys.exit(main())
