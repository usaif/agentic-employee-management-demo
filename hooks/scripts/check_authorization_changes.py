#!/usr/bin/env python3
"""
AST-based pre-commit hook to detect authorization logic changes.

This hook uses Abstract Syntax Tree (AST) parsing to reliably detect
changes to RBAC and permission logic, then verifies that authorization
tests are updated accordingly.

Unlike regex-based approaches, AST parsing:
- Understands Python syntax correctly
- Avoids false positives from comments/strings
- Detects semantic changes, not just text patterns
- Provides precise line numbers and context
"""

import argparse
import ast
import sys
from pathlib import Path
from typing import List, Set, Tuple, Dict, Optional
import subprocess
from dataclasses import dataclass


@dataclass
class AuthorizationPattern:
    """Represents an authorization-related code pattern."""
    file_path: str
    line_number: int
    pattern_type: str
    context: str
    node_type: str


class AuthorizationASTVisitor(ast.NodeVisitor):
    """
    AST visitor that identifies authorization-related code patterns.

    Detects:
    1. Role checks (state.role comparisons)
    2. Authentication checks (state.authenticated)
    3. Permission errors being raised
    4. Action whitelist checks
    5. Authorization functions
    """

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.patterns: List[AuthorizationPattern] = []
        self.in_auth_function = False
        self.current_function = None

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Track functions, especially authorization-related ones."""
        old_function = self.current_function
        old_in_auth = self.in_auth_function

        self.current_function = node.name

        # Detect authorization functions by name
        auth_function_names = [
            'authorize', 'check_permission', 'check_auth',
            'verify_access', 'validate_role', 'check_role',
            'authorize_action', 'require_role', 'has_permission'
        ]

        if any(auth_name in node.name.lower() for auth_name in auth_function_names):
            self.in_auth_function = True
            self.patterns.append(AuthorizationPattern(
                file_path=self.file_path,
                line_number=node.lineno,
                pattern_type="authorization_function",
                context=f"Function: {node.name}",
                node_type="FunctionDef"
            ))

        self.generic_visit(node)

        self.current_function = old_function
        self.in_auth_function = old_in_auth

    def visit_Attribute(self, node: ast.Attribute):
        """Detect attribute accesses like state.role, state.authenticated."""
        # Check for state.role or state.authenticated
        if isinstance(node.value, ast.Name):
            if node.value.id == 'state' and node.attr in ('role', 'authenticated'):
                self.patterns.append(AuthorizationPattern(
                    file_path=self.file_path,
                    line_number=node.lineno,
                    pattern_type=f"state_access_{node.attr}",
                    context=f"Access to state.{node.attr}",
                    node_type="Attribute"
                ))

        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare):
        """Detect comparison operations, especially role checks."""
        # Check if we're comparing against role strings
        role_values = {'employee', 'manager', 'hr', 'admin'}

        # Check comparators for role values
        for comparator in node.comparators:
            if isinstance(comparator, ast.Constant):
                if comparator.value in role_values:
                    self.patterns.append(AuthorizationPattern(
                        file_path=self.file_path,
                        line_number=node.lineno,
                        pattern_type="role_check",
                        context=f"Role comparison with '{comparator.value}'",
                        node_type="Compare"
                    ))

        # Check for state.role comparisons
        if isinstance(node.left, ast.Attribute):
            if (isinstance(node.left.value, ast.Name) and
                node.left.value.id == 'state' and
                node.left.attr == 'role'):
                self.patterns.append(AuthorizationPattern(
                    file_path=self.file_path,
                    line_number=node.lineno,
                    pattern_type="role_comparison",
                    context="Comparison with state.role",
                    node_type="Compare"
                ))

        self.generic_visit(node)

    def visit_Raise(self, node: ast.Raise):
        """Detect PermissionError raises."""
        if node.exc:
            # Check if raising PermissionError
            if isinstance(node.exc, ast.Call):
                if isinstance(node.exc.func, ast.Name):
                    if node.exc.func.id == 'PermissionError':
                        # Extract error message if available
                        msg = "Unknown"
                        if node.exc.args and isinstance(node.exc.args[0], ast.Constant):
                            msg = node.exc.args[0].value

                        self.patterns.append(AuthorizationPattern(
                            file_path=self.file_path,
                            line_number=node.lineno,
                            pattern_type="permission_error",
                            context=f"PermissionError: {msg}",
                            node_type="Raise"
                        ))

        self.generic_visit(node)

    def visit_If(self, node: ast.If):
        """Detect if statements that check authentication or roles."""
        # Check for authentication checks
        if isinstance(node.test, ast.UnaryOp):
            if isinstance(node.test.op, ast.Not):
                # Check for "if not state.authenticated"
                if isinstance(node.test.operand, ast.Attribute):
                    if (isinstance(node.test.operand.value, ast.Name) and
                        node.test.operand.value.id == 'state' and
                        node.test.operand.attr == 'authenticated'):
                        self.patterns.append(AuthorizationPattern(
                            file_path=self.file_path,
                            line_number=node.lineno,
                            pattern_type="auth_check",
                            context="Authentication check (not authenticated)",
                            node_type="If"
                        ))

        # Check for "if state.authenticated"
        if isinstance(node.test, ast.Attribute):
            if (isinstance(node.test.value, ast.Name) and
                node.test.value.id == 'state' and
                node.test.attr == 'authenticated'):
                self.patterns.append(AuthorizationPattern(
                    file_path=self.file_path,
                    line_number=node.lineno,
                    pattern_type="auth_check",
                    context="Authentication check (is authenticated)",
                    node_type="If"
                ))

        # Check for action whitelist checks (if action in (...))
        if isinstance(node.test, ast.Compare):
            for op in node.test.ops:
                if isinstance(op, (ast.In, ast.NotIn)):
                    if isinstance(node.test.left, ast.Name):
                        if node.test.left.id == 'action':
                            self.patterns.append(AuthorizationPattern(
                                file_path=self.file_path,
                                line_number=node.lineno,
                                pattern_type="action_whitelist",
                                context="Action whitelist check",
                                node_type="If"
                            ))

        self.generic_visit(node)


class AuthorizationChangeDetector:
    """Detects changes to authorization logic using AST analysis."""

    def __init__(self, files: List[str]):
        self.files = files
        self.violations: List[Tuple[str, str, int]] = []
        self.auth_patterns: Dict[str, List[AuthorizationPattern]] = {}

    def run(self) -> int:
        """Run the detector on staged files."""
        for file_path in self.files:
            if not file_path.endswith('.py'):
                continue

            # Skip test files
            if self._is_test_file(file_path):
                continue

            # Analyze the file for authorization patterns
            patterns = self._analyze_file(file_path)

            if patterns:
                self.auth_patterns[file_path] = patterns

                # Check if authorization tests were updated
                if not self._has_updated_auth_tests():
                    for pattern in patterns:
                        # Check if this pattern is in changed lines
                        if self._is_line_changed(file_path, pattern.line_number):
                            self.violations.append((
                                file_path,
                                f"{pattern.pattern_type}: {pattern.context}",
                                pattern.line_number
                            ))

        return self._report_violations()

    def _is_test_file(self, file_path: str) -> bool:
        """Check if file is a test file."""
        return 'test_' in file_path or '/tests/' in file_path

    def _analyze_file(self, file_path: str) -> List[AuthorizationPattern]:
        """Analyze a file using AST to find authorization patterns."""
        try:
            with open(file_path, 'r') as f:
                source_code = f.read()

            # Parse the file into an AST
            tree = ast.parse(source_code, filename=file_path)

            # Visit the AST to find authorization patterns
            visitor = AuthorizationASTVisitor(file_path)
            visitor.visit(tree)

            return visitor.patterns

        except SyntaxError as e:
            print(f"Warning: Syntax error in {file_path}: {e}")
            return []
        except Exception as e:
            print(f"Warning: Could not analyze {file_path}: {e}")
            return []

    def _is_line_changed(self, file_path: str, line_number: int) -> bool:
        """Check if a specific line was changed in the staged diff."""
        try:
            result = subprocess.run(
                ['git', 'diff', '--cached', '--unified=0', file_path],
                capture_output=True,
                text=True,
                check=True
            )

            current_line = 0
            in_change_block = False

            for line in result.stdout.split('\n'):
                # Parse unified diff format
                if line.startswith('@@'):
                    # Extract the new file line numbers
                    import re
                    match = re.search(r'\+(\d+),?(\d+)?', line)
                    if match:
                        start = int(match.group(1))
                        count = int(match.group(2)) if match.group(2) else 1

                        # Check if our line is in this change block
                        if start <= line_number < start + count:
                            return True

                        current_line = start
                        in_change_block = True
                elif line.startswith('+') and not line.startswith('+++'):
                    if in_change_block and current_line == line_number:
                        return True
                    current_line += 1
                elif line.startswith('-') and not line.startswith('---'):
                    # Line was removed, don't increment counter
                    pass
                elif in_change_block and not line.startswith('\\'):
                    current_line += 1

            return False

        except subprocess.CalledProcessError:
            # File might be newly added, consider all lines changed
            return True

    def _has_updated_auth_tests(self) -> bool:
        """Check if authorization test files were updated in this commit."""
        try:
            result = subprocess.run(
                ['git', 'diff', '--cached', '--name-only'],
                capture_output=True,
                text=True,
                check=True
            )

            changed_files = result.stdout.strip().split('\n')

            # Check for authorization test files
            auth_test_files = [
                'test_authorization',
                'test_auth',
                'test_rbac',
                'test_permission',
                'test_access'
            ]

            for file in changed_files:
                if any(test_name in file.lower() for test_name in auth_test_files):
                    return True

            return False

        except subprocess.CalledProcessError:
            return False

    def _report_violations(self) -> int:
        """Report violations and return exit code."""
        if not self.violations:
            if self.auth_patterns:
                print("✓ Authorization changes detected WITH test updates")
            else:
                print("✓ No authorization logic changes detected")
            return 0

        print("\n" + "=" * 80)
        print("⚠️  AUTHORIZATION LOGIC CHANGES WITHOUT TEST UPDATES")
        print("=" * 80)
        print("\nThe following authorization logic was changed without updating")
        print("authorization tests:\n")

        # Group violations by file
        violations_by_file: Dict[str, List[Tuple[str, int]]] = {}
        for file_path, message, line_num in self.violations:
            if file_path not in violations_by_file:
                violations_by_file[file_path] = []
            violations_by_file[file_path].append((message, line_num))

        for file_path, violations in violations_by_file.items():
            print(f"  {file_path}")
            for message, line_num in violations:
                print(f"    Line {line_num}: {message}")
            print()

        print("=" * 80)
        print("AUTHORIZATION PATTERNS DETECTED:")
        print("=" * 80)

        pattern_types = set(v[1].split(':')[0] for v in self.violations)
        print("\nThis commit modifies:")
        for pattern in sorted(pattern_types):
            print(f"  • {pattern.replace('_', ' ').title()}")

        print("\n" + "=" * 80)
        print("REMEDIATION:")
        print("=" * 80)
        print("""
1. Update authorization tests in tests/test_authorization_rbac.py

2. Ensure tests cover the changed authorization logic:

   For role changes:
   - Test that the role CAN perform allowed actions
   - Test that the role CANNOT perform denied actions

   For permission checks:
   - Test authenticated vs unauthenticated paths
   - Test edge cases (missing roles, unknown roles)

   For action whitelists:
   - Test all actions in the whitelist
   - Test actions NOT in the whitelist are denied

3. Run authorization tests:
   uv run pytest tests/test_authorization_rbac.py -v

4. Add the test file to your commit:
   git add tests/test_authorization_rbac.py

5. Re-run the commit:
   git commit

Example test structure:

   def test_new_role_can_perform_action(agent_session):
       chat(agent_session, "Login with email user@company.com")
       r = chat(agent_session, "Perform new action")
       assert "success" in r["message"].lower()

   def test_unauthorized_role_cannot_perform_action(agent_session):
       chat(agent_session, "Login with email employee@company.com")
       r = chat(agent_session, "Perform restricted action")
       assert "not authorized" in r["message"].lower()

To bypass this check (NOT RECOMMENDED):
  git commit --no-verify
""")
        print("=" * 80 + "\n")

        return 1


def main():
    parser = argparse.ArgumentParser(
        description="Detect authorization logic changes without test updates"
    )
    parser.add_argument(
        'files',
        nargs='*',
        help='Files to check (typically provided by pre-commit)'
    )

    args = parser.parse_args()

    # If no files specified, get all staged Python files
    if not args.files:
        result = subprocess.run(
            ['git', 'diff', '--cached', '--name-only', '--diff-filter=AM'],
            capture_output=True,
            text=True
        )
        files = [f for f in result.stdout.split('\n') if f.endswith('.py')]
    else:
        files = args.files

    if not files:
        print("No Python files to check")
        return 0

    detector = AuthorizationChangeDetector(files)
    return detector.run()


if __name__ == '__main__':
    sys.exit(main())
