# Pre-commit Hooks — Quick Start Guide

Get pre-commit hooks running in 2 minutes.

## Installation (One Time)

### Option 1: Automated Setup (Recommended)

```bash
bash scripts/setup-precommit.sh
```

This script will:
- Create a virtual environment (if needed)
- Install pre-commit framework
- Install development dependencies
- Set up git hooks
- Optionally test all files

### Option 2: Manual Setup

```bash
# 1. Install pre-commit
pip install pre-commit

# 2. Install git hooks
pre-commit install

# 3. (Optional) Install dev dependencies
pip install -e ".[dev]"
```

## Daily Usage

### Automatic (Default)

Hooks run automatically when you commit:

```bash
git add your_changes.py
git commit -m "feat: your change"
# Hooks run automatically ✓
```

If hooks block your commit, fix the issues and retry:

```bash
git add .
git commit -m "feat: your change"
```

### Manual (Anytime)

```bash
# Check staged files
pre-commit run

# Check all files
pre-commit run --all-files

# Check specific file
pre-commit run --files path/to/file.py

# Run specific hook
pre-commit run ruff --all-files
```

## What Hooks Do

| Hook | Purpose | Auto-fix? |
|------|---------|-----------|
| ruff | Python linter (imports, syntax, naming) | Yes |
| ruff-format | Python code formatter | Yes |
| trailing-whitespace | Remove extra whitespace | Yes |
| end-of-file-fixer | Add newline at end of file | Yes |
| check-yaml | Validate YAML syntax | No |
| check-json | Validate JSON syntax | No |
| detect-secrets | Prevent API keys from being committed | No |
| check-added-large-files | Block files larger than 500KB | No |
| check-ast | Verify Python syntax | No |
| interrogate | Check docstring coverage (>75%) | No |

## Common Issues & Solutions

### "pre-commit is not installed"

```bash
pip install pre-commit
pre-commit install
```

### Hooks are failing

**Ruff issues:**
```bash
# Auto-fixes many issues automatically
pre-commit run --all-files
git add .
git commit -m "fix: address pre-commit issues"
```

**Secret detected:**
```bash
# If it's a false positive:
detect-secrets scan --baseline .secrets.baseline
git add .secrets.baseline
```

**Large file blocked:**
```bash
# Use Git LFS or remove the file
git lfs install
git lfs track "*.csv"
```

### Hooks running too slowly

First run is slow (installs hooks). Subsequent runs are fast (~2-5 seconds).

To speed up checks, only run on staged files:

```bash
pre-commit run  # No --all-files flag
```

### Need to skip hooks

Use only when necessary:

```bash
git commit --no-verify
```

Then fix issues immediately:

```bash
pre-commit run --all-files
git add .
git commit -m "fix: address pre-commit issues"
```

## Documentation

- **Full guide**: [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md)
- **Troubleshooting**: [docs/CONTRIBUTING.md#troubleshooting](docs/CONTRIBUTING.md#troubleshooting)
- **Code style**: [docs/CONTRIBUTING.md#code-standards](docs/CONTRIBUTING.md#code-standards)

## Next Steps

1. Run automated setup: `bash scripts/setup-precommit.sh`
2. Read [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) for detailed info
3. Configure your IDE to use the same settings (optional)
4. Ask questions if needed

---

**Ready?** Run `bash scripts/setup-precommit.sh` now!
