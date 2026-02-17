# Pre-commit Hooks Cheatsheet

## Installation

```bash
# Automated (recommended)
bash scripts/setup-precommit.sh

# Manual
pip install pre-commit && pre-commit install
```

## Run Hooks

```bash
# Automatic (on commit)
git commit -m "message"

# Manual - on staged files
pre-commit run

# Manual - on all files
pre-commit run --all-files

# Manual - specific hook
pre-commit run ruff --all-files

# Manual - specific file
pre-commit run --files path/to/file.py
```

## Hook Issues & Fixes

### Ruff Linter Errors

**Issue**: `E501 Line too long`
```bash
# Auto-fixed or manually shorten to 100 chars
pre-commit run --all-files
```

**Issue**: `F841 Local variable assigned but never used`
```bash
# Remove the unused variable, then:
git add .
git commit -m "fix: remove unused variable"
```

### Secrets Detected

**Issue**: `Potential secrets found`
```bash
# If real secret: Remove it immediately and rotate credential
# If false positive: Update baseline
detect-secrets scan --baseline .secrets.baseline
git add .secrets.baseline
```

### File Too Large

**Issue**: `FILE LARGER THAN 500KB ADDED`
```bash
# Remove the file
git rm --cached large_file.csv
echo "large_file.csv" >> .gitignore
git add .gitignore
```

### Docstring Missing

**Issue**: `interrogate: Missing docstrings`
```python
# Add docstring following Google format
def my_function(arg1: str) -> bool:
    """Brief description.

    Longer description if needed.

    Args:
        arg1: Description of arg1.

    Returns:
        True if successful, False otherwise.
    """
    return True
```

## Common Commands

| Command | Purpose |
|---------|---------|
| `pre-commit run` | Check staged files |
| `pre-commit run --all-files` | Check entire repo |
| `pre-commit run ruff --all-files` | Lint Python only |
| `pre-commit install` | Register git hooks |
| `pre-commit uninstall` | Unregister git hooks |
| `git commit --no-verify` | Skip hooks (emergency only!) |
| `pre-commit autoupdate` | Update hooks to latest versions |

## Code Standards

### Python Style

```python
# Line length: 100 chars max
# Imports: grouped and sorted automatically
from pathlib import Path
from typing import Dict, List

import requests

# Docstring: Google format
def process_data(input_file: str) -> Dict[str, int]:
    """Process input file and return statistics.

    Args:
        input_file: Path to input file.

    Returns:
        Dictionary with processing statistics.

    Raises:
        FileNotFoundError: If file doesn't exist.
    """
    ...

# Variable naming: snake_case
device_code = "OVE"
CONSTANT_VALUE = 42
```

### File Format

```
1. Standard header (shebang + module docstring)
2. Imports (sorted by: stdlib, third-party, local)
3. Constants
4. Classes
5. Functions
6. Main block
7. Newline at end of file
```

## Commit Messages

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Code style (formatting)
- `refactor`: Code refactoring
- `perf`: Performance improvement
- `test`: Tests
- `chore`: Build, dependencies
- `ci`: CI/CD

### Examples

```
feat(predicate): add lineage tracing

Implement new method to trace predicate lineage across
510(k) submissions for competitor analysis.

Closes #123
```

```
fix(api): handle rate limit headers

Parse X-RateLimit-Remaining header to prevent
false API failures when approaching rate limits.
```

## FAQ

**Q: Do I need to run hooks manually?**
A: No, they run automatically on commit. Manual run is optional for early checking.

**Q: Can I skip hooks?**
A: Yes, with `--no-verify`, but only use sparingly. Fix issues immediately after.

**Q: How long do hooks take?**
A: First run: 30-60 seconds. Subsequent: 2-5 seconds.

**Q: Why is my hook failing?**
A: Run `pre-commit run --all-files` to see details, or check CONTRIBUTING.md troubleshooting.

**Q: How do I update hooks?**
A: Run `pre-commit autoupdate` and commit the changes.

## Help

- **Quick start**: `PRECOMMIT_QUICK_START.md`
- **Full guide**: `docs/CONTRIBUTING.md`
- **Setup script**: `bash scripts/setup-precommit.sh`
- **This cheatsheet**: `PRECOMMIT_CHEATSHEET.md`

---

**Print this for your desk!** Quick reference for daily development.
