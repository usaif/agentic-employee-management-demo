#!/usr/bin/env python3
"""
Pre-commit hook to detect new write capabilities without corresponding tests.

This hook analyzes staged changes to identify:
1. New database mutations (CREATE, UPDATE, DELETE operations)
2. New API endpoints that modify data
3. New agent actions that mutate state

It then verifies that corresponding tests exist for these capabilities.
"""

import argparse
import ast
import re
import sys
from pathlib import Path
from typing import List, Set, Tuple
import subprocess


# Configuration
MUTATION_KEYWORDS = {
    "db.add",
    "db.delete",
    "db.commit",
    "setattr",
    "delattr",
}

HTTP_MUTATION_METHODS = {
    "post",
    "put",
    "patch",
    "delete",
}

MUTATION_FUNCTION_PATTERNS = [
    r"def\s+(create_|update_|delete_|insert_|remove_|onboard_)\w+",
    r"def\s+\w+_(create|update|delete|insert|remove|onboard)\w*",
]

# Patterns for agent state mutations
AGENT_STATE_MUTATIONS = [
    r"state\.\w+\s*=",  # Direct state assignment
    r"state\.api_args",  # API args manipulation
    r"selected_api\s*=",  # API selection
]


class WriteCapabilityDetector:
    """Detects new write capabilities in staged changes."""

    def __init__(self, files: List[str]):
        self.files = files
        self.violations: List[Tuple[str, str, int]] = []

    def run(self) -> int:
        """Run the detector on staged files."""
        for file_path in self.files:
            if not file_path.endswith(".py"):
                continue

            # Skip test files, migrations, and seed data
            if self._is_excluded_file(file_path):
                continue

            self._check_file(file_path)

        return self._report_violations()

    def _is_excluded_file(self, file_path: str) -> bool:
        """Check if file should be excluded from analysis."""
        excluded_patterns = [
            "test_",
            "/tests/",
            "conftest.py",
            "/migrations/",
            "/seed/",
            "__init__.py",
            "database.py",  # DB setup file, not mutations
        ]
        return any(pattern in file_path for pattern in excluded_patterns)

    def _check_file(self, file_path: str):
        """Check a single file for new write capabilities."""
        try:
            with open(file_path, "r") as f:
                content = f.read()
                lines = content.split("\n")

            # Get the diff to identify added lines
            added_lines = self._get_added_lines(file_path)

            # Check for database mutations
            self._check_db_mutations(file_path, added_lines, lines)

            # Check for HTTP mutation endpoints
            self._check_http_mutations(file_path, added_lines, lines)

            # Check for mutation functions
            self._check_mutation_functions(file_path, added_lines, lines)

            # Check for agent state mutations
            self._check_agent_mutations(file_path, added_lines, lines)

        except Exception as e:
            print(f"Warning: Could not analyze {file_path}: {e}")

    def _get_added_lines(self, file_path: str) -> Set[int]:
        """Get line numbers of added lines from git diff."""
        try:
            result = subprocess.run(
                ["git", "diff", "--cached", "--unified=0", file_path],
                capture_output=True,
                text=True,
                check=True,
            )

            added_lines = set()
            current_line = 0

            for line in result.stdout.split("\n"):
                # Parse unified diff format: @@ -old_start,old_count +new_start,new_count @@
                if line.startswith("@@"):
                    match = re.search(r"\+(\d+)", line)
                    if match:
                        current_line = int(match.group(1))
                elif line.startswith("+") and not line.startswith("+++"):
                    added_lines.add(current_line)
                    current_line += 1
                elif not line.startswith("-"):
                    current_line += 1

            return added_lines
        except subprocess.CalledProcessError:
            # File might be newly added
            return set(range(1, 10000))  # Consider all lines as new

    def _check_db_mutations(self, file_path: str, added_lines: Set[int], lines: List[str]):
        """Check for database mutation operations."""
        for line_num in added_lines:
            if line_num > len(lines):
                continue

            line = lines[line_num - 1]

            for keyword in MUTATION_KEYWORDS:
                if keyword in line and not self._is_comment(line):
                    # Check if there's a corresponding test
                    if not self._has_test_coverage(file_path, keyword):
                        self.violations.append(
                            (
                                file_path,
                                f"Database mutation detected: {keyword}",
                                line_num,
                            )
                        )

    def _check_http_mutations(self, file_path: str, added_lines: Set[int], lines: List[str]):
        """Check for HTTP mutation endpoints."""
        for line_num in added_lines:
            if line_num > len(lines):
                continue

            line = lines[line_num - 1]

            for method in HTTP_MUTATION_METHODS:
                pattern = rf"@router\.{method}\("
                if re.search(pattern, line) and not self._is_comment(line):
                    # Extract endpoint name from next few lines
                    endpoint_name = self._extract_endpoint_name(lines, line_num)

                    if not self._has_test_coverage(file_path, f"{method}_{endpoint_name}"):
                        self.violations.append(
                            (
                                file_path,
                                f"HTTP {method.upper()} endpoint detected: {endpoint_name}",
                                line_num,
                            )
                        )

    def _check_mutation_functions(self, file_path: str, added_lines: Set[int], lines: List[str]):
        """Check for functions that likely perform mutations."""
        for line_num in added_lines:
            if line_num > len(lines):
                continue

            line = lines[line_num - 1]

            for pattern in MUTATION_FUNCTION_PATTERNS:
                match = re.search(pattern, line)
                if match and not self._is_comment(line):
                    func_name = match.group(0).replace("def ", "").split("(")[0]

                    if not self._has_test_coverage(file_path, func_name):
                        self.violations.append(
                            (
                                file_path,
                                f"Mutation function detected: {func_name}",
                                line_num,
                            )
                        )

    def _check_agent_mutations(self, file_path: str, added_lines: Set[int], lines: List[str]):
        """Check for agent-specific mutations."""
        if "/agent/" not in file_path:
            return

        for line_num in added_lines:
            if line_num > len(lines):
                continue

            line = lines[line_num - 1]

            for pattern in AGENT_STATE_MUTATIONS:
                if re.search(pattern, line) and not self._is_comment(line):
                    # Check if this is in execute.py node (critical mutation path)
                    if "execute.py" in file_path:
                        if not self._has_agent_test_coverage():
                            self.violations.append(
                                (
                                    file_path,
                                    "Agent state mutation detected in execute node",
                                    line_num,
                                )
                            )

    def _is_comment(self, line: str) -> bool:
        """Check if line is a comment."""
        stripped = line.strip()
        return stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''")

    def _extract_endpoint_name(self, lines: List[str], start_line: int) -> str:
        """Extract endpoint function name from decorator."""
        # Look at the next few lines for the function definition
        for i in range(start_line, min(start_line + 5, len(lines))):
            match = re.search(r"def\s+(\w+)", lines[i])
            if match:
                return match.group(1)
        return "unknown"

    def _has_test_coverage(self, file_path: str, capability_name: str) -> bool:
        """Check if tests exist for the given capability."""
        test_dir = Path("tests")
        if not test_dir.exists():
            return False

        # Derive potential test patterns
        test_patterns = self._get_test_patterns(file_path, capability_name)

        # Search for tests
        for test_file in test_dir.glob("test_*.py"):
            try:
                with open(test_file, "r") as f:
                    test_content = f.read().lower()

                    # Check if any pattern matches
                    for pattern in test_patterns:
                        if pattern.lower() in test_content:
                            return True
            except Exception:
                continue

        return False

    def _has_agent_test_coverage(self) -> bool:
        """Check if agent tests exist."""
        test_dir = Path("tests")
        if not test_dir.exists():
            return False

        agent_test_files = [
            "test_agent_update.py",
            "test_agent_delete.py",
            "test_agent_auth.py",
        ]

        for test_file in agent_test_files:
            if (test_dir / test_file).exists():
                return True

        return False

    def _get_test_patterns(self, file_path: str, capability_name: str) -> List[str]:
        """Generate potential test patterns for a capability."""
        patterns = [capability_name]

        # Extract module name
        if "app/api/" in file_path:
            patterns.append("test_api")
        elif "app/agent/" in file_path:
            patterns.append("test_agent")

        # Add variations
        base_name = capability_name.replace("_", " ")
        patterns.extend(
            [
                f"test_{capability_name}",
                f"def test_{capability_name}",
                base_name,
            ]
        )

        return patterns

    def _report_violations(self) -> int:
        """Report violations and return exit code."""
        if not self.violations:
            print("✓ No new write capabilities detected without tests")
            return 0

        print("\n" + "=" * 80)
        print("⚠️  WRITE CAPABILITY VIOLATIONS DETECTED")
        print("=" * 80)
        print(
            "\nThe following write capabilities were added without corresponding tests:\n"
        )

        for file_path, message, line_num in self.violations:
            print(f"  {file_path}:{line_num}")
            print(f"    → {message}")
            print()

        print("=" * 80)
        print("REMEDIATION:")
        print("=" * 80)
        print("1. Add tests for the new write capabilities in the tests/ directory")
        print("2. Ensure tests cover:")
        print("   - Successful operations")
        print("   - Authorization checks (RBAC)")
        print("   - Edge cases and error conditions")
        print("3. Run: uv run pytest tests/ -v")
        print("4. Re-run: git commit")
        print("\nTo bypass this check (NOT RECOMMENDED):")
        print("  git commit --no-verify")
        print("=" * 80 + "\n")

        return 1


def main():
    parser = argparse.ArgumentParser(
        description="Check for new write capabilities without tests"
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Files to check (typically provided by pre-commit)",
    )

    args = parser.parse_args()

    # If no files specified, get all staged Python files
    if not args.files:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=AM"],
            capture_output=True,
            text=True,
        )
        files = [f for f in result.stdout.split("\n") if f.endswith(".py")]
    else:
        files = args.files

    if not files:
        print("No Python files to check")
        return 0

    detector = WriteCapabilityDetector(files)
    return detector.run()


if __name__ == "__main__":
    sys.exit(main())
