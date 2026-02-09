#!/usr/bin/env python3
"""
Pre-commit hook to detect removal of security-relevant code.

This hook analyzes git diffs to identify when security controls are deleted:
1. Input validation functions
2. Authentication/authorization checks
3. Audit logging calls
4. Rate limiting logic
5. Error handling (HTTPException, try/except)

Uses AST parsing for accuracy and git diff analysis to track deletions.
"""

import argparse
import ast
import re
import sys
import subprocess
from pathlib import Path
from typing import List, Set, Tuple, Dict, Optional
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class SecurityPattern:
    """Represents a security-relevant code pattern."""
    line_number: int
    pattern_type: str
    code_snippet: str
    context: str
    severity: str  # 'critical', 'high', 'medium'


class SecurityASTAnalyzer(ast.NodeVisitor):
    """
    AST analyzer that identifies security-relevant code patterns.

    Security patterns detected:
    1. Input validation functions
    2. Authentication checks
    3. Authorization checks
    4. Audit logging calls
    5. Rate limiting
    6. Error handling
    """

    def __init__(self, source_lines: List[str]):
        self.source_lines = source_lines
        self.security_patterns: Dict[int, List[SecurityPattern]] = defaultdict(list)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Detect security-related functions."""
        func_name = node.name.lower()

        # Input validation functions
        validation_keywords = [
            'validate', 'sanitize', 'check', 'verify',
            'clean', 'escape', 'filter', 'parse'
        ]

        if any(keyword in func_name for keyword in validation_keywords):
            if any(term in func_name for term in ['input', 'data', 'param', 'arg', 'value']):
                self.security_patterns[node.lineno].append(SecurityPattern(
                    line_number=node.lineno,
                    pattern_type="input_validation",
                    code_snippet=self._get_line(node.lineno),
                    context=f"Input validation function: {node.name}",
                    severity="high"
                ))

        # Authorization functions
        auth_keywords = ['authorize', 'check_permission', 'require_role', 'has_permission']
        if any(keyword in func_name for keyword in auth_keywords):
            self.security_patterns[node.lineno].append(SecurityPattern(
                line_number=node.lineno,
                pattern_type="authorization_function",
                code_snippet=self._get_line(node.lineno),
                context=f"Authorization function: {node.name}",
                severity="critical"
            ))

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        """Detect security-relevant function calls."""
        func_name = self._get_call_name(node)

        if func_name:
            # Audit logging calls
            if func_name in ['log_event', 'log_execution', 'log_audit', 'audit_log']:
                self.security_patterns[node.lineno].append(SecurityPattern(
                    line_number=node.lineno,
                    pattern_type="audit_logging",
                    code_snippet=self._get_line(node.lineno),
                    context=f"Audit logging: {func_name}()",
                    severity="high"
                ))

            # Rate limiting
            elif 'limit' in func_name.lower() or 'throttle' in func_name.lower():
                self.security_patterns[node.lineno].append(SecurityPattern(
                    line_number=node.lineno,
                    pattern_type="rate_limiting",
                    code_snippet=self._get_line(node.lineno),
                    context=f"Rate limiting: {func_name}()",
                    severity="high"
                ))

            # HTTPException (error handling)
            elif func_name == 'HTTPException':
                self.security_patterns[node.lineno].append(SecurityPattern(
                    line_number=node.lineno,
                    pattern_type="error_handling",
                    code_snippet=self._get_line(node.lineno),
                    context="HTTP error handling",
                    severity="medium"
                ))

        self.generic_visit(node)

    def visit_Raise(self, node: ast.Raise):
        """Detect security-related exceptions."""
        if node.exc:
            exc_name = None

            if isinstance(node.exc, ast.Call):
                if isinstance(node.exc.func, ast.Name):
                    exc_name = node.exc.func.id
            elif isinstance(node.exc, ast.Name):
                exc_name = node.exc.id

            if exc_name:
                # Permission errors
                if exc_name == 'PermissionError':
                    self.security_patterns[node.lineno].append(SecurityPattern(
                        line_number=node.lineno,
                        pattern_type="authorization_check",
                        code_snippet=self._get_line(node.lineno),
                        context="Authorization denial (PermissionError)",
                        severity="critical"
                    ))

                # Validation errors
                elif 'Validation' in exc_name or 'ValueError' in exc_name:
                    self.security_patterns[node.lineno].append(SecurityPattern(
                        line_number=node.lineno,
                        pattern_type="input_validation",
                        code_snippet=self._get_line(node.lineno),
                        context=f"Validation error: {exc_name}",
                        severity="high"
                    ))

        self.generic_visit(node)

    def visit_If(self, node: ast.If):
        """Detect security-relevant conditional checks."""
        # Authentication checks
        if self._is_auth_check(node.test):
            self.security_patterns[node.lineno].append(SecurityPattern(
                line_number=node.lineno,
                pattern_type="authentication_check",
                code_snippet=self._get_line(node.lineno),
                context="Authentication check",
                severity="critical"
            ))

        # Authorization checks (role checks)
        if self._is_role_check(node.test):
            self.security_patterns[node.lineno].append(SecurityPattern(
                line_number=node.lineno,
                pattern_type="authorization_check",
                code_snippet=self._get_line(node.lineno),
                context="Role/permission check",
                severity="critical"
            ))

        # Defensive null checks
        if isinstance(node.test, ast.Compare):
            if any(isinstance(op, (ast.Is, ast.IsNot)) for op in node.test.ops):
                self.security_patterns[node.lineno].append(SecurityPattern(
                    line_number=node.lineno,
                    pattern_type="defensive_check",
                    code_snippet=self._get_line(node.lineno),
                    context="Defensive null/None check",
                    severity="medium"
                ))

        self.generic_visit(node)

    def visit_Try(self, node: ast.Try):
        """Detect try/except blocks (error handling)."""
        if node.handlers:
            for handler in node.handlers:
                if handler.type:
                    self.security_patterns[node.lineno].append(SecurityPattern(
                        line_number=node.lineno,
                        pattern_type="error_handling",
                        code_snippet=self._get_line(node.lineno),
                        context="Exception handling (try/except)",
                        severity="medium"
                    ))
                    break

        self.generic_visit(node)

    def _is_auth_check(self, node: ast.expr) -> bool:
        """Check if node is an authentication check."""
        # if not state.authenticated
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            if isinstance(node.operand, ast.Attribute):
                if node.operand.attr == 'authenticated':
                    return True

        # if state.authenticated
        if isinstance(node, ast.Attribute):
            if node.attr == 'authenticated':
                return True

        return False

    def _is_role_check(self, node: ast.expr) -> bool:
        """Check if node is a role/permission check."""
        if isinstance(node, ast.Compare):
            # Check if comparing state.role or role variable
            if isinstance(node.left, ast.Attribute):
                if node.left.attr == 'role':
                    return True
            elif isinstance(node.left, ast.Name):
                if node.left.id == 'role':
                    return True

        return False

    def _get_call_name(self, node: ast.Call) -> Optional[str]:
        """Extract function name from Call node."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            return node.func.attr
        return None

    def _get_line(self, line_num: int) -> str:
        """Get source line by number."""
        if 1 <= line_num <= len(self.source_lines):
            return self.source_lines[line_num - 1].strip()
        return ""


class SecurityDeletionDetector:
    """Detects deletion of security-relevant code."""

    def __init__(self, files: List[str]):
        self.files = files
        self.violations: List[Tuple[str, SecurityPattern, str]] = []

    def run(self) -> int:
        """Run the detector on staged files."""
        for file_path in self.files:
            if not file_path.endswith('.py'):
                continue

            if self._is_excluded_file(file_path):
                continue

            self._analyze_file(file_path)

        return self._report_violations()

    def _is_excluded_file(self, file_path: str) -> bool:
        """Check if file should be excluded."""
        excluded = ['test_', '/tests/', '__init__.py', 'conftest.py']
        return any(pattern in file_path for pattern in excluded)

    def _analyze_file(self, file_path: str):
        """Analyze a file for security code deletions."""
        try:
            # Get the diff
            diff_result = subprocess.run(
                ['git', 'diff', '--cached', '--unified=0', file_path],
                capture_output=True,
                text=True,
                check=True
            )

            diff_output = diff_result.stdout
            if not diff_output:
                return

            # Get the OLD version of the file (before changes)
            old_content = self._get_old_file_content(file_path)
            if not old_content:
                return  # New file, no deletions to check

            # Parse old content for security patterns
            old_lines = old_content.split('\n')
            security_patterns = self._find_security_patterns(old_lines)

            # Find deleted lines
            deleted_lines = self._get_deleted_lines(diff_output)

            # Check if any security patterns were deleted
            for line_num in deleted_lines:
                if line_num in security_patterns:
                    for pattern in security_patterns[line_num]:
                        # Get surrounding context
                        context_lines = self._get_context_lines(old_lines, line_num)

                        self.violations.append((
                            file_path,
                            pattern,
                            context_lines
                        ))

        except subprocess.CalledProcessError:
            pass  # File might be new or untracked
        except Exception as e:
            print(f"Warning: Could not analyze {file_path}: {e}")

    def _get_old_file_content(self, file_path: str) -> Optional[str]:
        """Get the old version of a file from git."""
        try:
            result = subprocess.run(
                ['git', 'show', f'HEAD:{file_path}'],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError:
            return None

    def _find_security_patterns(self, source_lines: List[str]) -> Dict[int, List[SecurityPattern]]:
        """Find security patterns in source code using AST."""
        try:
            source_code = '\n'.join(source_lines)
            tree = ast.parse(source_code)

            analyzer = SecurityASTAnalyzer(source_lines)
            analyzer.visit(tree)

            return analyzer.security_patterns

        except SyntaxError:
            # If AST parsing fails, fall back to regex patterns
            return self._find_patterns_regex(source_lines)

    def _find_patterns_regex(self, source_lines: List[str]) -> Dict[int, List[SecurityPattern]]:
        """Fallback: Find security patterns using regex."""
        patterns: Dict[int, List[SecurityPattern]] = defaultdict(list)

        security_regexes = [
            (r'log_event|log_execution|log_audit', 'audit_logging', 'high'),
            (r'raise\s+PermissionError', 'authorization_check', 'critical'),
            (r'if\s+not\s+.*\.authenticated', 'authentication_check', 'critical'),
            (r'if\s+.*\.role\s*==', 'authorization_check', 'critical'),
            (r'@.*limiter|@rate_limit', 'rate_limiting', 'high'),
            (r'def\s+validate_|def\s+sanitize_', 'input_validation', 'high'),
            (r'HTTPException', 'error_handling', 'medium'),
            (r'try:', 'error_handling', 'medium'),
        ]

        for line_num, line in enumerate(source_lines, 1):
            for regex, pattern_type, severity in security_regexes:
                if re.search(regex, line):
                    patterns[line_num].append(SecurityPattern(
                        line_number=line_num,
                        code_snippet=line.strip(),
                        pattern_type=pattern_type,
                        context=f"Detected via regex: {regex}",
                        severity=severity
                    ))

        return patterns

    def _get_deleted_lines(self, diff_output: str) -> Set[int]:
        """Extract line numbers that were deleted from diff."""
        deleted_lines = set()
        current_line = 0

        for line in diff_output.split('\n'):
            if line.startswith('@@'):
                # Parse hunk header: @@ -old_start,old_count +new_start,new_count @@
                match = re.search(r'-(\d+),?(\d+)?', line)
                if match:
                    current_line = int(match.group(1))
            elif line.startswith('-') and not line.startswith('---'):
                # This is a deleted line
                deleted_lines.add(current_line)
                current_line += 1
            elif not line.startswith('+'):
                current_line += 1

        return deleted_lines

    def _get_context_lines(self, source_lines: List[str], line_num: int, context: int = 3) -> str:
        """Get surrounding context for a line."""
        start = max(0, line_num - context - 1)
        end = min(len(source_lines), line_num + context)

        context_lines = []
        for i in range(start, end):
            marker = '→' if i == line_num - 1 else ' '
            context_lines.append(f"{i+1:4d}{marker} {source_lines[i]}")

        return '\n'.join(context_lines)

    def _report_violations(self) -> int:
        """Report violations and return exit code."""
        if not self.violations:
            print("✓ No security code deletions detected")
            return 0

        # Group by severity
        by_severity = {
            'critical': [],
            'high': [],
            'medium': []
        }

        for file_path, pattern, context in self.violations:
            by_severity[pattern.severity].append((file_path, pattern, context))

        print("\n" + "=" * 80)
        print("⚠️  SECURITY CODE DELETION DETECTED")
        print("=" * 80)
        print("\nSecurity-relevant code has been removed from your commit.")
        print("This may weaken your application's security posture.\n")

        # Report by severity
        for severity in ['critical', 'high', 'medium']:
            violations = by_severity[severity]
            if not violations:
                continue

            severity_icon = {
                'critical': '🔴 CRITICAL',
                'high': '🟠 HIGH',
                'medium': '🟡 MEDIUM'
            }

            print(f"\n{severity_icon[severity]} Severity Deletions:")
            print("-" * 80)

            for file_path, pattern, context in violations:
                print(f"\n  File: {file_path}")
                print(f"  Line: {pattern.line_number}")
                print(f"  Type: {pattern.pattern_type.replace('_', ' ').title()}")
                print(f"  Context: {pattern.context}")
                print(f"\n  Deleted code:")
                print("  " + "  ".join(context.split('\n')))
                print()

        print("=" * 80)
        print("SECURITY IMPLICATIONS:")
        print("=" * 80)

        pattern_types = set(p[1].pattern_type for p in self.violations)

        implications = {
            'audit_logging': '• Reduced audit trail - security events may go unlogged',
            'authentication_check': '• Weakened authentication - unauthorized access possible',
            'authorization_check': '• Bypassed authorization - privilege escalation risk',
            'input_validation': '• Missing input validation - injection attacks possible',
            'rate_limiting': '• Removed rate limiting - DoS/brute force attacks easier',
            'error_handling': '• Poor error handling - information leakage risk',
            'defensive_check': '• Missing defensive checks - potential crashes/errors'
        }

        print()
        for pattern_type in pattern_types:
            if pattern_type in implications:
                print(implications[pattern_type])

        print("\n" + "=" * 80)
        print("REMEDIATION:")
        print("=" * 80)
        print("""
1. Review each deletion carefully
2. If the security control is no longer needed:
   - Document WHY it was removed
   - Update threat model accordingly
   - Consider compensating controls

3. If refactoring/moving code:
   - Verify the security control exists elsewhere
   - Ensure equivalent protection is maintained

4. If this is a mistake:
   - Restore the deleted security code
   - Review your changes before committing

5. To proceed with this commit (NOT RECOMMENDED):
   git commit --no-verify

For security review questions, consult your security team.
""")
        print("=" * 80 + "\n")

        return 1


def main():
    parser = argparse.ArgumentParser(
        description="Detect removal of security-relevant code"
    )
    parser.add_argument(
        'files',
        nargs='*',
        help='Files to check (typically provided by pre-commit)'
    )

    args = parser.parse_args()

    # Get staged files if none specified
    if not args.files:
        result = subprocess.run(
            ['git', 'diff', '--cached', '--name-only', '--diff-filter=M'],
            capture_output=True,
            text=True
        )
        files = [f for f in result.stdout.split('\n') if f.endswith('.py')]
    else:
        files = args.files

    if not files:
        print("No Python files to check")
        return 0

    detector = SecurityDeletionDetector(files)
    return detector.run()


if __name__ == '__main__':
    sys.exit(main())
