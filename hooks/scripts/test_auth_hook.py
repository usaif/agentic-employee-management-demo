#!/usr/bin/env python3
"""
Test script for the authorization change detection hook.

This demonstrates the AST-based detection capabilities.
"""

import ast
import tempfile
from pathlib import Path
import sys

# Import the hook
sys.path.insert(0, str(Path(__file__).parent))
from check_authorization_changes import AuthorizationASTVisitor


def test_ast_detection():
    """Test that AST detection finds authorization patterns."""

    test_cases = [
        # Test 1: Role check
        ("""
def authorize(state):
    if state.role == "employee":
        return True
""", ["role_comparison", "state_access_role"]),

        # Test 2: Authentication check
        ("""
def check_auth(state):
    if not state.authenticated:
        raise PermissionError("Not authenticated")
""", ["auth_check", "state_access_authenticated", "permission_error"]),

        # Test 3: Permission error
        ("""
def deny_access():
    raise PermissionError("Access denied")
""", ["permission_error"]),

        # Test 4: Authorization function
        ("""
def authorize_action(state):
    if state.role == "hr":
        return True
    raise PermissionError("Not authorized")
""", ["authorization_function", "role_comparison", "permission_error"]),

        # Test 5: Action whitelist
        ("""
def check_action(action):
    if action in ("read", "write"):
        return True
""", ["action_whitelist"]),

        # Test 6: Multiple roles
        ("""
def check_roles(state):
    if state.role == "manager":
        return True
    if state.role == "hr":
        return True
    if state.role == "employee":
        return False
""", ["role_comparison", "state_access_role"]),
    ]

    print("Testing AST Detection Capabilities")
    print("=" * 80)

    all_passed = True

    for i, (code, expected_patterns) in enumerate(test_cases, 1):
        print(f"\nTest Case {i}:")
        print("-" * 40)
        print(code.strip())
        print("-" * 40)

        # Parse the code
        try:
            tree = ast.parse(code)
            visitor = AuthorizationASTVisitor("test.py")
            visitor.visit(tree)

            # Get detected pattern types
            detected = set(p.pattern_type for p in visitor.patterns)

            print(f"Expected patterns: {', '.join(expected_patterns)}")
            print(f"Detected patterns: {', '.join(detected)}")

            # Check if all expected patterns were found
            expected_set = set(expected_patterns)
            if expected_set.issubset(detected):
                print("✓ PASS")
            else:
                print(f"✗ FAIL - Missing: {expected_set - detected}")
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


def test_real_world_example():
    """Test on actual authorization code from the project."""

    print("\n" + "=" * 80)
    print("Testing Real-World Authorization Code")
    print("=" * 80)

    # Simulate the authorize.py file
    code = """
from app.agent.state import AgentState

def authorize_action(state: AgentState) -> AgentState:
    session_id = state.session_id
    role = state.role
    action = state.selected_api

    if action is None:
        return state

    if action in ("login", "authenticate", "onboard_user"):
        return state

    if not state.authenticated:
        raise PermissionError("User not authenticated")

    if role == "employee":
        if action == "get_my_profile":
            return state
        raise PermissionError("Employees may only view their own profile")

    if role == "manager":
        if action in ("get_my_profile", "get_employee"):
            return state
        raise PermissionError("Managers have read-only access")

    if role == "hr":
        return state

    raise PermissionError("Unknown role")
"""

    try:
        tree = ast.parse(code)
        visitor = AuthorizationASTVisitor("app/agent/nodes/authorize.py")
        visitor.visit(tree)

        print("\nDetected Authorization Patterns:")
        print("-" * 80)

        pattern_counts = {}
        for pattern in visitor.patterns:
            pattern_counts[pattern.pattern_type] = pattern_counts.get(pattern.pattern_type, 0) + 1
            print(f"  Line {pattern.line_number}: {pattern.pattern_type}")
            print(f"    Context: {pattern.context}")

        print("\n" + "-" * 80)
        print("Summary:")
        for pattern_type, count in sorted(pattern_counts.items()):
            print(f"  {pattern_type}: {count} occurrence(s)")

        # Verify we found the expected patterns
        expected_patterns = {
            'authorization_function',
            'state_access_role',
            'state_access_authenticated',
            'auth_check',
            'permission_error',
            'role_comparison',
            'action_whitelist'
        }

        detected_patterns = set(pattern_counts.keys())

        print("\n" + "=" * 80)
        if expected_patterns.issubset(detected_patterns):
            print("✓ Successfully detected all authorization patterns!")
            return 0
        else:
            print(f"✗ Missing patterns: {expected_patterns - detected_patterns}")
            return 1

    except Exception as e:
        print(f"✗ Error: {e}")
        return 1


def main():
    print("Authorization Hook AST Detection Tests")
    print("=" * 80)
    print("\nThis demonstrates the AST-based authorization detection.\n")

    result1 = test_ast_detection()
    result2 = test_real_world_example()

    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)
    print("\nThe AST-based hook can detect:")
    print("  ✓ Role comparisons (state.role == 'employee')")
    print("  ✓ Authentication checks (state.authenticated)")
    print("  ✓ PermissionError raises")
    print("  ✓ Authorization functions (by name)")
    print("  ✓ Action whitelist checks")
    print("\nAdvantages over regex:")
    print("  ✓ Understands Python syntax")
    print("  ✓ Ignores comments and strings")
    print("  ✓ Accurate line numbers")
    print("  ✓ No false positives from similar text")

    return max(result1, result2)


if __name__ == "__main__":
    sys.exit(main())
