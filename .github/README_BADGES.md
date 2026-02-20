# GitHub Actions Badge Integration

Add these badges to your main README.md to display CI/CD status.

## Available Badges

### CI Status
```markdown
![CI](https://github.com/your-org/fda-tools/workflows/CI/badge.svg)
```
![CI](https://github.com/your-org/fda-tools/workflows/CI/badge.svg)

### Security Scanning Status
```markdown
![Security](https://github.com/your-org/fda-tools/workflows/Security%20Scanning/badge.svg)
```
![Security](https://github.com/your-org/fda-tools/workflows/Security%20Scanning/badge.svg)

### Release Status
```markdown
![Release](https://github.com/your-org/fda-tools/workflows/Release/badge.svg)
```
![Release](https://github.com/your-org/fda-tools/workflows/Release/badge.svg)

### Code Coverage (Codecov)
```markdown
[![codecov](https://codecov.io/gh/your-org/fda-tools/branch/master/graph/badge.svg)](https://codecov.io/gh/your-org/fda-tools)
```
[![codecov](https://codecov.io/gh/your-org/fda-tools/branch/master/graph/badge.svg)](https://codecov.io/gh/your-org/fda-tools)

### Python Version
```markdown
![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)
```
![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)

### License
```markdown
![License](https://img.shields.io/badge/license-MIT-green)
```
![License](https://img.shields.io/badge/license-MIT-green)

### Latest Release
```markdown
![Release](https://img.shields.io/github/v/release/your-org/fda-tools)
```
![Release](https://img.shields.io/github/v/release/your-org/fda-tools)

### Code Style: Ruff
```markdown
![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)
```
![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)

### Pre-commit
```markdown
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
```
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)

## Complete Badge Set

Copy this complete set to your README.md:

```markdown
# FDA Tools

![CI](https://github.com/your-org/fda-tools/workflows/CI/badge.svg)
![Security](https://github.com/your-org/fda-tools/workflows/Security%20Scanning/badge.svg)
[![codecov](https://codecov.io/gh/your-org/fda-tools/branch/master/graph/badge.svg)](https://codecov.io/gh/your-org/fda-tools)
![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Release](https://img.shields.io/github/v/release/your-org/fda-tools)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)
```

## Customization

Replace `your-org` with your actual GitHub organization or username.

## Advanced Badges

### Test Results
```markdown
![Tests](https://img.shields.io/github/actions/workflow/status/your-org/fda-tools/ci.yml?label=tests)
```

### Last Commit
```markdown
![Last Commit](https://img.shields.io/github/last-commit/your-org/fda-tools)
```

### Issues
```markdown
![Issues](https://img.shields.io/github/issues/your-org/fda-tools)
```

### Pull Requests
```markdown
![Pull Requests](https://img.shields.io/github/issues-pr/your-org/fda-tools)
```

### Contributors
```markdown
![Contributors](https://img.shields.io/github/contributors/your-org/fda-tools)
```

### Stars
```markdown
![Stars](https://img.shields.io/github/stars/your-org/fda-tools?style=social)
```

## Status Check Context

The following status checks are enforced in CI:

- `lint` - Code quality and formatting
- `security` - Security vulnerability scanning
- `test` - Test suite (Python 3.10, 3.11, 3.12)
- `build` - Package build validation
- `status-check` - Overall CI status

These checks must pass before merging pull requests.
