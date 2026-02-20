#!/usr/bin/env python3
"""Verify CI/CD pipeline configuration.

This script checks that all CI/CD components are properly configured.
"""

import subprocess
import sys
from pathlib import Path
from typing import List, Tuple


def run_command(cmd: List[str]) -> Tuple[int, str, str]:
    """Run a command and return exit code, stdout, stderr."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)


def check_file_exists(path: Path, description: str) -> bool:
    """Check if a file exists."""
    if path.exists():
        print(f"✓ {description}: {path}")
        return True
    else:
        print(f"✗ {description} missing: {path}")
        return False


def check_command_available(cmd: str, description: str) -> bool:
    """Check if a command is available."""
    code, _, _ = run_command(["which", cmd])
    if code == 0:
        print(f"✓ {description} available")
        return True
    else:
        print(f"✗ {description} not found (install with: pip install {cmd})")
        return False


def main():
    """Main entry point."""
    project_root = Path(__file__).parent.parent
    checks_passed = 0
    checks_failed = 0

    print("FDA Tools CI/CD Configuration Verification")
    print("=" * 60)
    print()

    # Check configuration files
    print("Configuration Files:")
    print("-" * 60)
    config_files = [
        (project_root / "pyproject.toml", "pyproject.toml"),
        (project_root / "pytest.ini", "pytest.ini"),
        (project_root / ".pre-commit-config.yaml", "Pre-commit config"),
        (project_root / ".flake8", "Flake8 config"),
        (project_root / ".bandit", "Bandit config"),
        (project_root / ".coveragerc", "Coverage config"),
        (project_root / ".yamllint.yml", "YAML lint config"),
        (project_root / ".secrets.baseline", "Secrets baseline"),
    ]

    for path, description in config_files:
        if check_file_exists(path, description):
            checks_passed += 1
        else:
            checks_failed += 1
    print()

    # Check GitHub Actions workflows
    print("GitHub Actions Workflows:")
    print("-" * 60)
    workflow_dir = project_root / ".github" / "workflows"
    workflow_dir.mkdir(parents=True, exist_ok=True)

    workflows = [
        ("ci.yml", "CI workflow"),
        ("security.yml", "Security workflow"),
        ("release.yml", "Release workflow"),
    ]

    for filename, description in workflows:
        path = workflow_dir / filename
        if check_file_exists(path, description):
            checks_passed += 1
        else:
            checks_failed += 1
            print(f"  Note: Create this file from CI_CD_README.md documentation")
    print()

    # Check automation scripts
    print("Automation Scripts:")
    print("-" * 60)
    scripts = [
        ("scripts/bump_version.py", "Version bumping script"),
        ("scripts/generate_changelog.py", "Changelog generator"),
        ("scripts/ci_helper.sh", "CI helper script"),
        ("scripts/setup_workflows.sh", "Workflow setup script"),
        ("CI_CD_README.md", "CI/CD documentation"),
    ]

    for filename, description in scripts:
        path = project_root / filename
        if check_file_exists(path, description):
            checks_passed += 1
            # Check if script is executable
            if filename.endswith(".sh") or filename.endswith(".py"):
                if path.stat().st_mode & 0o111:
                    print(f"  ✓ Script is executable")
                else:
                    print(f"  ⚠ Script is not executable (run: chmod +x {path})")
        else:
            checks_failed += 1
    print()

    # Check required tools
    print("Required Tools:")
    print("-" * 60)
    tools = [
        ("python3", "python3"),
        ("pip", "pip"),
        ("git", "git"),
        ("ruff", "ruff"),
        ("black", "black"),
        ("pytest", "pytest"),
        ("mypy", "mypy"),
        ("bandit", "bandit"),
        ("pre-commit", "pre-commit"),
    ]

    for cmd, description in tools:
        if check_command_available(cmd, description):
            checks_passed += 1
        else:
            checks_failed += 1
    print()

    # Check pre-commit installation
    print("Pre-commit Hooks:")
    print("-" * 60)
    git_hooks = project_root / ".git" / "hooks" / "pre-commit"
    if git_hooks.exists():
        print("✓ Pre-commit hooks installed")
        checks_passed += 1
    else:
        print("✗ Pre-commit hooks not installed")
        print("  Run: pre-commit install")
        checks_failed += 1
    print()

    # Run basic validation
    print("Configuration Validation:")
    print("-" * 60)

    # Check pyproject.toml version
    pyproject = project_root / "pyproject.toml"
    if pyproject.exists():
        content = pyproject.read_text()
        if 'version = "' in content:
            print("✓ Version found in pyproject.toml")
            checks_passed += 1
        else:
            print("✗ Version not found in pyproject.toml")
            checks_failed += 1

    # Check if in git repository
    code, _, _ = run_command(["git", "rev-parse", "--git-dir"])
    if code == 0:
        print("✓ Git repository detected")
        checks_passed += 1
    else:
        print("✗ Not a git repository")
        checks_failed += 1

    print()

    # Summary
    print("=" * 60)
    print(f"Checks passed: {checks_passed}")
    print(f"Checks failed: {checks_failed}")
    print()

    if checks_failed == 0:
        print("✓ CI/CD configuration is complete and ready!")
        print()
        print("Next steps:")
        print("1. Review CI_CD_README.md for workflow setup")
        print("2. Create GitHub Actions workflows (if missing)")
        print("3. Configure GitHub repository secrets")
        print("4. Run: ./scripts/ci_helper.sh ci")
        return 0
    else:
        print("✗ Some CI/CD components are missing or misconfigured")
        print()
        print("Please address the failed checks above.")
        print("Refer to CI_CD_README.md for detailed setup instructions.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
