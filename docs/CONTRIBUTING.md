# Contributing to FDA Tools

Thank you for your interest in contributing to FDA Tools! This document provides guidelines and setup instructions for developers.

## Table of Contents

- [Development Setup](#development-setup)
- [Code Quality](#code-quality)
- [Pre-commit Hooks](#pre-commit-hooks)
- [Testing](#testing)
- [Commit Conventions](#commit-conventions)
- [Pull Request Process](#pull-request-process)
- [Troubleshooting](#troubleshooting)

## Development Setup

### Prerequisites

- Python 3.9 or higher
- Git
- pip or pipenv

### Clone the Repository

```bash
git clone https://github.com/andrewlasiter/fda-tools.git
cd fda-tools
```

### Create Virtual Environment

```bash
# Using venv
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Or using pipenv
pipenv install --dev
pipenv shell
```

### Install Development Dependencies

```bash
# Install the package in development mode with all dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pip install pre-commit
pre-commit install
```

## Code Quality

We maintain high code quality standards using automated tools. All contributions must pass these checks.

### Code Standards

- **Language**: Python 3.9+
- **Linter**: Ruff (replaces flake8, isort, pyupgrade)
- **Formatter**: Ruff format
- **Line Length**: 100 characters
- **Docstring Style**: Google format
- **Type Hints**: Required for public APIs

### Example Code Style

```python
"""Module docstring in Google format.

Brief description of module purpose.

Attributes:
    CONSTANT_NAME: Description of constant.
"""

from typing import Dict, List, Optional


def process_device(
    device_code: str,
    include_history: bool = False,
) -> Dict[str, List[str]]:
    """Process a FDA device code and return results.

    Args:
        device_code: Three-letter FDA product code (e.g., 'OVE').
        include_history: Whether to include historical records.

    Returns:
        Dictionary with device information and associated predicates.

    Raises:
        ValueError: If device_code is not valid.

    Examples:
        >>> result = process_device('OVE')
        >>> len(result['predicates']) > 0
        True
    """
    if not device_code or len(device_code) != 3:
        raise ValueError(f"Invalid device code: {device_code}")

    return {"predicates": []}
```

## Pre-commit Hooks

Pre-commit hooks automatically check your code before each commit. They help catch issues early and maintain code quality.

### First-Time Setup

```bash
# Install pre-commit framework (if not already installed)
pip install pre-commit

# Install git hooks from configuration
pre-commit install

# Verify installation
pre-commit run --all-files
```

### What Hooks Do

| Hook | Purpose | Auto-fix? |
|------|---------|-----------|
| **ruff linter** | Detect Python code issues (unused imports, undefined names, etc.) | Yes |
| **ruff formatter** | Format Python code consistently | Yes |
| **trailing-whitespace** | Remove trailing whitespace | Yes |
| **end-of-file-fixer** | Ensure files end with newline | Yes |
| **check-yaml** | Validate YAML syntax | No |
| **check-json** | Validate JSON syntax | No |
| **check-merge-conflict** | Detect unresolved merge conflicts | No |
| **check-case-conflict** | Prevent case-sensitive filename conflicts | No |
| **mixed-line-ending** | Normalize line endings (LF) | Yes |
| **detect-secrets** | Prevent accidental credential commits | No |
| **check-added-large-files** | Block files larger than 500KB | No |
| **check-ast** | Verify Python syntax is valid | No |
| **interrogate** | Check docstring coverage (>75%) | No |

### Running Hooks Manually

```bash
# Run all hooks on staged files (default)
pre-commit run

# Run all hooks on all files in repository
pre-commit run --all-files

# Run specific hook
pre-commit run ruff --all-files

# Run hooks on specific file
pre-commit run --files path/to/file.py
```

### Fixing Common Issues

#### "trailing-whitespace" or "end-of-file-fixer" failures

These are automatically fixed. If they fail:

```bash
# Run the hooks with auto-fix enabled (hooks do this by default)
pre-commit run --all-files

# Stage the fixed files
git add .
```

#### "ruff linter" failures

Many issues are automatically fixed:

```bash
# Auto-fix will be applied during hook run
# Stage the changes
git add .
```

For issues that require manual fixes, the hook will display:

```
E501 Line too long  # Shorten the line to 100 characters
F841 Local variable assigned but never used  # Remove unused variable
```

#### "detect-secrets" failures

If a potential secret is detected:

```
ERROR: Potential secrets found in:
  file.py: (line 42) Possible hardcoded password or API key
```

**Solutions:**

1. **If it's a real secret**: Remove it immediately, update `.secrets.baseline`, and rotate the credential
2. **If it's a false positive**:
   ```bash
   # Update baseline to allow the false positive
   detect-secrets scan --baseline .secrets.baseline
   git add .secrets.baseline
   ```

#### "check-added-large-files" failures

If you accidentally add a file larger than 500KB:

```
FILE LARGER THAN 500KB ADDED: data/large_file.csv
```

**Solutions:**

1. Remove the file:
   ```bash
   git rm --cached data/large_file.csv
   echo "data/large_file.csv" >> .gitignore
   git add .gitignore
   ```

2. Or use Git LFS (Large File Storage):
   ```bash
   git lfs install
   git lfs track "*.csv"
   git add .gitattributes data/large_file.csv
   ```

#### "interrogate" docstring failures

If docstring coverage is below 75%:

```
FAILED: Missing docstrings in 3 functions
Coverage: 60% (3 of 5 documented)
```

**Solution**: Add docstrings following Google format:

```python
def new_function(arg1: str, arg2: int) -> bool:
    """Brief one-line description.

    Longer description if needed, explaining what the function does
    and how to use it.

    Args:
        arg1: Description of arg1.
        arg2: Description of arg2.

    Returns:
        True if successful, False otherwise.
    """
    return True
```

### Bypassing Hooks (When Necessary)

In rare cases, you may need to bypass hooks:

```bash
# Commit without running hooks (NOT recommended)
git commit --no-verify

# If you use this, ensure:
# 1. You manually ran all checks: pre-commit run --all-files
# 2. You have a valid reason for bypassing
# 3. You document the reason in your commit message
```

### Updating Hook Configuration

If you need to update the pre-commit configuration:

```bash
# Update hook versions to latest
pre-commit autoupdate

# Test updated hooks
pre-commit run --all-files

# Commit changes
git add .pre-commit-config.yaml
git commit -m "chore: update pre-commit hooks to latest versions"
```

## Testing

All code changes should include tests.

### Running Tests

```bash
# Run all tests
pytest

# Run tests with coverage report
pytest --cov=plugins --cov-report=html

# Run specific test file
pytest tests/test_api_contracts.py

# Run specific test
pytest tests/test_api_contracts.py::Test510kEndpoint::test_510k_has_k_number

# Run tests by marker
pytest -m "not slow"  # Skip slow tests (API calls)
pytest -m "phase1"    # Only Phase 1 tests
```

### Writing Tests

Follow existing test patterns:

```python
"""Tests for module_name module."""

import pytest
from unittest.mock import Mock, patch


class TestFunctionName:
    """Tests for function_name function."""

    def test_returns_expected_value(self):
        """Test that function returns expected value."""
        result = function_name("input")
        assert result == "expected_output"

    def test_raises_on_invalid_input(self):
        """Test that function raises ValueError for invalid input."""
        with pytest.raises(ValueError):
            function_name(None)

    @patch("module.external_api")
    def test_calls_external_api(self, mock_api):
        """Test that function calls external API."""
        mock_api.return_value = {"status": "success"}
        result = function_name("input")
        mock_api.assert_called_once()
```

### Test Coverage

We target >80% code coverage. To check:

```bash
pytest --cov=plugins --cov-report=term-missing
```

## Commit Conventions

Use clear, descriptive commit messages following conventional commits:

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting, missing semicolons, etc.)
- **refactor**: Code refactoring without changing functionality
- **perf**: Performance improvements
- **test**: Test additions or modifications
- **chore**: Build, dependency, or tooling changes
- **ci**: CI/CD configuration changes

### Examples

```bash
# Feature
git commit -m "feat(predicate): add predicate lineage tracing"

# Bug fix
git commit -m "fix(api): handle rate limit headers correctly"

# Documentation
git commit -m "docs: add contributing guide"

# Breaking change
git commit -m "feat!: change API response format

BREAKING CHANGE: Device data structure now uses snake_case instead of camelCase"
```

## Pull Request Process

1. **Create a feature branch** from `master`:
   ```bash
   git checkout -b feat/your-feature-name
   ```

2. **Make your changes** and ensure:
   - Pre-commit hooks pass: `pre-commit run --all-files`
   - Tests pass: `pytest`
   - Coverage is maintained: `pytest --cov`

3. **Commit your changes** with clear messages (see Commit Conventions)

4. **Push to your fork**:
   ```bash
   git push origin feat/your-feature-name
   ```

5. **Create a Pull Request** with:
   - Clear title describing the change
   - Description explaining what and why
   - Link to related issue (if applicable)
   - List of changes and test coverage

6. **Address review feedback** and update your PR

7. **Merge** once approved and all checks pass

## Troubleshooting

### "pre-commit is not installed"

```bash
pip install pre-commit
pre-commit install
```

### "No module named 'ruff'"

```bash
pip install ruff
# Or reinstall dev dependencies
pip install -e ".[dev]"
```

### Hooks run very slowly

This is normal on first run. Subsequent runs will be much faster:

- First run: ~30-60 seconds (installs hooks)
- Subsequent runs: ~2-5 seconds (cached)

To speed up checks:

```bash
# Only run on changed files (not entire repo)
pre-commit run  # No --all-files flag
```

### "Hook failed but I need to commit now"

Use `--no-verify` sparingly:

```bash
git commit --no-verify
```

Then fix issues immediately:

```bash
# Fix the problems
pre-commit run --all-files
git add .
git commit -m "fix: address pre-commit issues"
```

### Python version issues

If you see "Python 3.X not found":

```bash
# Check your Python version
python3 --version

# Create virtual environment with specific version
python3.9 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

### pytest can't find modules

```bash
# Ensure you're in the project root
cd /path/to/fda-tools

# Reinstall in editable mode
pip install -e .

# Run tests
pytest
```

## Questions?

- Check [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for common issues
- Review existing issues in GitHub
- Open a new issue with detailed information
- Check project [README.md](../README.md) for context

## Code of Conduct

Be respectful and constructive in all interactions. We welcome contributions from everyone.
