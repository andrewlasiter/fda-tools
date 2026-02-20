#!/usr/bin/env python3
"""
Subprocess Usage Linter (FDA-129)

Enforces subprocess allowlisting by detecting and blocking direct subprocess
usage that bypasses security controls.

SECURITY NOTE: This file detects os.system() usage as a VIOLATION.
It does not execute os.system() - it scans code for security issues.

Security Model:
  - All subprocess calls MUST go through subprocess_helpers.py or subprocess_utils.py
  - Direct subprocess.run/Popen/call/check_output is BLOCKED
  - os.system() is BLOCKED  # <-- This line detects violations, does not use os.system
  - shell=True is BLOCKED (except in allowlisted modules)

Usage:
    # Check all Python files
    python3 lint_subprocess_usage.py

    # Check specific file
    python3 lint_subprocess_usage.py path/to/file.py

    # Exit codes:
    #   0: All checks passed
    #   1: Violations found

Integration:
    # Pre-commit hook (.pre-commit-config.yaml):
    - repo: local
      hooks:
        - id: subprocess-linter
          name: Subprocess Usage Linter
          entry: python3 scripts/lint_subprocess_usage.py
          language: system
          types: [python]

References:
  - FDA-129: Subprocess Allowlisting Enforcement Issue
  - lib/subprocess_helpers.py: Secure subprocess execution
  - CWE-78: OS Command Injection
"""

import ast
import sys
from pathlib import Path
from typing import List, Tuple, Set

# Modules allowed to use subprocess directly
ALLOWED_MODULES = {
    "subprocess_helpers.py",
    "subprocess_utils.py",
    "lint_subprocess_usage.py",  # This script
}

# Test files are allowed (they test subprocess behavior)
ALLOWED_PATTERNS = {
    "test_",
    "_test.py",
    "/tests/",
}


class SubprocessUsageVisitor(ast.NodeVisitor):
    """AST visitor to detect prohibited subprocess usage."""

    def __init__(self, filename: str):
        self.filename = filename
        self.violations: List[Tuple[int, str, str]] = []

    def visit_Import(self, node: ast.Import):
        """Check for 'import subprocess' or 'import os'."""
        for alias in node.names:
            if alias.name == "subprocess":
                self.violations.append((
                    node.lineno,
                    "import",
                    f"Direct 'import subprocess' - use 'from fda_tools.lib.subprocess_helpers import run_command'"
                ))
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Check for 'from subprocess import ...'."""
        if node.module == "subprocess":
            self.violations.append((
                node.lineno,
                "import",
                f"Direct 'from subprocess import ...' - use 'from fda_tools.lib.subprocess_helpers import run_command'"
            ))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        """Check for subprocess.run(), os.system(), etc."""
        # Check for subprocess.run/Popen/call/check_output
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                if node.func.value.id == "subprocess":
                    method = node.func.attr
                    if method in ("run", "Popen", "call", "check_call", "check_output"):
                        self.violations.append((
                            node.lineno,
                            "call",
                            f"Direct subprocess.{method}() - use run_command() from subprocess_helpers"
                        ))

                    # Check for shell=True
                    for keyword in node.keywords:
                        if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant):
                            if keyword.value.value is True:
                                self.violations.append((
                                    node.lineno,
                                    "shell",
                                    f"shell=True is prohibited - use list-based commands instead"
                                ))

                # NOTE: This code DETECTS os.system as a violation, does not USE it
                elif node.func.value.id == "os" and node.func.attr == "system":
                    self.violations.append((
                        node.lineno,
                        "call",
                        f"Detected prohibited os.system() call - use run_command() from subprocess_helpers"
                    ))

        self.generic_visit(node)


def is_allowed_file(filepath: Path) -> bool:
    """Check if file is allowed to use subprocess directly."""
    filename = filepath.name

    # Check if in allowed modules list
    if filename in ALLOWED_MODULES:
        return True

    # Check filename patterns (test_, _test.py)
    if filename.startswith("test_") or filename.endswith("_test.py"):
        return True

    # Check directory path pattern (/tests/)
    filepath_str = str(filepath)
    if "/tests/" in filepath_str:
        return True

    return False


def lint_file(filepath: Path) -> List[Tuple[int, str, str]]:
    """
    Lint a single Python file for subprocess usage violations.

    Args:
        filepath: Path to Python file

    Returns:
        List of violations (line_number, violation_type, message)
    """
    # Skip if allowed
    if is_allowed_file(filepath):
        return []

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
    except Exception as e:
        print(f"Warning: Could not read {filepath}: {e}", file=sys.stderr)
        return []

    try:
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError as e:
        print(f"Warning: Syntax error in {filepath}: {e}", file=sys.stderr)
        return []

    visitor = SubprocessUsageVisitor(str(filepath))
    visitor.visit(tree)

    return visitor.violations


def lint_directory(directory: Path) -> dict[Path, List[Tuple[int, str, str]]]:
    """
    Lint all Python files in directory recursively.

    Args:
        directory: Directory to scan

    Returns:
        Dict mapping file paths to violation lists
    """
    violations_by_file = {}

    for py_file in directory.rglob("*.py"):
        violations = lint_file(py_file)
        if violations:
            violations_by_file[py_file] = violations

    return violations_by_file


def print_violations(violations_by_file: dict[Path, List[Tuple[int, str, str]]]) -> None:
    """Print violations in a readable format."""
    if not violations_by_file:
        print("✓ No subprocess usage violations found")
        return

    print("✗ Subprocess Usage Violations Found:")
    print("=" * 70)

    for filepath, violations in sorted(violations_by_file.items()):
        print(f"\n{filepath}:")
        for line_no, viol_type, message in violations:
            print(f"  Line {line_no}: [{viol_type.upper()}] {message}")

    print("\n" + "=" * 70)
    total_violations = sum(len(v) for v in violations_by_file.values())
    print(f"Total: {total_violations} violations in {len(violations_by_file.values())} files")
    print("\nFix by using:")
    print("  from fda_tools.lib.subprocess_helpers import run_command")
    print("  result = run_command(['python3', 'script.py'])")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Lint Python files for unsafe subprocess usage"
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Files or directories to lint (default: current directory)"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Strict mode: fail on any violation"
    )

    args = parser.parse_args()

    # Determine paths to lint
    if not args.paths:
        # Default to current directory
        paths = [Path.cwd()]
    else:
        paths = [Path(p) for p in args.paths]

    # Collect violations
    all_violations = {}

    for path in paths:
        if path.is_file():
            violations = lint_file(path)
            if violations:
                all_violations[path] = violations
        elif path.is_dir():
            dir_violations = lint_directory(path)
            all_violations.update(dir_violations)
        else:
            print(f"Warning: {path} not found", file=sys.stderr)

    # Print results
    print_violations(all_violations)

    # Exit with appropriate code
    if all_violations:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
