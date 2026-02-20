# GitHub Actions Workflows Setup Guide

This guide explains how to complete the CI/CD pipeline setup by creating the GitHub Actions workflow files.

## Overview

The CI/CD pipeline consists of three main workflows:

1. **ci.yml** - Continuous Integration (runs on every push/PR)
2. **security.yml** - Security Scanning (runs daily + on push)
3. **release.yml** - Release Automation (runs on version tags)

Due to security validation in the development environment, these workflow files must be created manually. Complete workflow specifications are provided in `CI_CD_README.md`.

## Quick Setup

### Option 1: Copy from CI_CD_README.md

1. Open `CI_CD_README.md`
2. Copy the workflow configurations from the documentation
3. Create files in `.github/workflows/`:
   - `ci.yml`
   - `security.yml`
   - `release.yml`

### Option 2: Use Git Worktree (Recommended)

```bash
# Create the workflow files in a separate worktree
git worktree add /tmp/workflows
cd /tmp/workflows

# Create workflow files
cat > .github/workflows/ci.yml << 'EOF'
# Copy content from CI_CD_README.md Section "Continuous Integration"
EOF

cat > .github/workflows/security.yml << 'EOF'
# Copy content from CI_CD_README.md Section "Security Scanning"
EOF

cat > .github/workflows/release.yml << 'EOF'
# Copy content from CI_CD_README.md Section "Release Automation"
EOF

# Commit and merge
git add .github/workflows/
git commit -m "feat(devops): Add GitHub Actions workflows"
git push
cd -
git worktree remove /tmp/workflows
```

## Workflow File Templates

The complete, production-ready workflow files are documented in `CI_CD_README.md`. Key features:

### ci.yml Features
- Multi-version Python testing (3.10, 3.11, 3.12)
- Parallel job execution
- Code coverage reporting (80% minimum)
- Build validation
- Docker image testing
- Fast feedback on PRs

### security.yml Features
- Daily automated security scans
- Bandit SAST analysis
- Safety dependency scanning
- CodeQL analysis
- Docker image scanning with Trivy
- Secret detection with TruffleHog
- License compliance checking

### release.yml Features
- Automated version validation
- Full test suite execution
- Changelog generation
- GitHub release creation
- Optional PyPI publishing
- Tag-triggered automation

## Required GitHub Secrets

Configure these in your GitHub repository settings (Settings → Secrets and variables → Actions):

### Optional (for enhanced features):
- `CODECOV_TOKEN` - Coverage reporting (get from codecov.io)
- `FDA_API_KEY` - FDA API access for integration tests
- `GEMINI_API_KEY` - Google Gemini API for AI features
- `PYPI_API_TOKEN` - PyPI publishing (if enabled)
- `TEST_PYPI_API_TOKEN` - Test PyPI publishing

### Auto-provided:
- `GITHUB_TOKEN` - Automatically provided by GitHub Actions

## Verification

After creating the workflows:

```bash
# Verify workflows are valid YAML
python3 -c "
import yaml
from pathlib import Path

for workflow in ['.github/workflows/ci.yml', '.github/workflows/security.yml', '.github/workflows/release.yml']:
    with open(workflow) as f:
        yaml.safe_load(f)
    print(f'✓ {workflow} is valid')
"

# Run verification script
python3 scripts/verify_cicd.py

# Test locally (if act is installed)
act -l  # List available jobs
act pull_request  # Test PR workflow
```

## Troubleshooting

### Workflow not triggering
- Check that workflow file is in `.github/workflows/`
- Verify YAML syntax is valid
- Ensure trigger conditions match (branch names, tags)
- Check GitHub Actions is enabled in repository settings

### Permission errors
- Ensure workflow has required permissions
- Check `GITHUB_TOKEN` has necessary scopes
- Verify secrets are configured correctly

### Test failures
- Run tests locally first: `./scripts/ci_helper.sh test`
- Check Python version compatibility
- Verify all dependencies are in `pyproject.toml`

## Next Steps

1. Create the three workflow files
2. Configure required GitHub secrets
3. Push to GitHub to trigger first CI run
4. Add status badges to README.md (see `.github/README_BADGES.md`)
5. Configure branch protection rules
6. Set up required status checks

## Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Workflow Syntax](https://docs.github.com/en/actions/reference/workflow-syntax-for-github-actions)
- [Security Best Practices](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions)
- Project CI/CD documentation: `CI_CD_README.md`

## Security Notes

The workflows follow GitHub Actions security best practices:

- No untrusted input in shell commands
- Environment variables for user-controlled data
- Minimal token permissions
- Secret scanning enabled
- Regular dependency updates via Dependabot

## Maintenance

The workflows are designed to be:

- **Self-documenting** - Clear job names and descriptions
- **Fast** - Parallel execution, caching, selective testing
- **Reliable** - Retry logic, timeout controls
- **Secure** - Security scans, secret protection
- **Maintainable** - Modular jobs, clear dependencies

Review and update workflows quarterly or when:
- Adding new Python versions
- Changing test structure
- Updating security tools
- Modifying release process
