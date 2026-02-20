# CI/CD Pipeline Documentation

This document describes the Continuous Integration and Continuous Deployment (CI/CD) pipeline for the FDA Tools project.

## Overview

The FDA Tools project uses GitHub Actions for automated testing, security scanning, and deployment. The CI/CD pipeline ensures code quality, security, and reliability across all contributions.

## Pipeline Architecture

### Workflow Files

All workflows are located in `.github/workflows/`:

1. **`ci.yml`** - Continuous Integration (runs on every push and PR)
2. **`security.yml`** - Security scanning (daily + on push)
3. **`release.yml`** - Release automation (on version tags)

## Continuous Integration (ci.yml)

**Triggers:**
- Push to `master`, `develop`, `feature/**`, `bugfix/**`
- Pull requests to `master`, `develop`
- Manual dispatch

### Jobs

#### 1. Lint & Code Quality
**Purpose:** Ensure code style and quality standards

**Steps:**
- Ruff linting (fast Python linter)
- Ruff formatting check
- Black formatting check
- mypy type checking (informational)
- Docstring coverage check (75% threshold)

**Matrix:** Python 3.11 (default)

**Runtime:** ~2-3 minutes

#### 2. Security Scan
**Purpose:** Identify security vulnerabilities

**Steps:**
- Bandit security linting
- Safety dependency vulnerability check
- pip-audit dependency scanning

**Artifacts:**
- `security-reports/` (30-day retention)

**Runtime:** ~1-2 minutes

#### 3. Test Matrix
**Purpose:** Run comprehensive test suite across Python versions

**Matrix:**
- Python 3.10
- Python 3.11
- Python 3.12

**Steps:**
- Install system dependencies (tesseract, poppler-utils)
- Install Python dependencies
- Run unit tests (excluding slow/e2e tests)
- Generate coverage reports (XML, HTML)
- Upload to Codecov

**Coverage Requirements:**
- Minimum: 80%
- Target: 90%+

**Artifacts:**
- `test-results-{python-version}/` (30 days)
- `coverage-report/` (30 days)

**Runtime:** ~5-8 minutes per Python version

#### 4. Integration Tests
**Purpose:** Test component integration

**Triggers:** Push to branches, manual dispatch

**Steps:**
- Run integration tests with real dependencies
- Test API clients, data flows, end-to-end scenarios

**Environment Variables Required:**
- `FDA_API_KEY` (optional, uses public endpoints if missing)
- `GEMINI_API_KEY` (optional, for AI features)

**Runtime:** ~3-5 minutes

#### 5. E2E Tests (Fast)
**Purpose:** Run quick end-to-end workflow tests

**Triggers:** Push to `master` or `develop` only

**Steps:**
- Run tests marked with `e2e_fast` marker
- Validate complete workflows

**Runtime:** ~5-10 minutes

#### 6. Build Distribution
**Purpose:** Validate package builds correctly

**Dependencies:** Requires `lint` and `test` jobs to pass

**Steps:**
- Build wheel and sdist
- Run `twine check` for PyPI compliance

**Artifacts:**
- `dist/` (30 days)

**Runtime:** ~1 minute

#### 7. Docker Build Test
**Purpose:** Ensure Docker image builds successfully

**Triggers:** Push events only

**Steps:**
- Set up Docker Buildx
- Create Dockerfile (if not exists)
- Build Docker image with caching

**Runtime:** ~3-5 minutes

#### 8. Status Check
**Purpose:** Aggregate status of required jobs

**Dependencies:** All previous jobs

**Behavior:**
- Fails if any required job fails
- Reports overall CI status

## Security Scanning (security.yml)

**Triggers:**
- Push to `master`, `develop`
- Pull requests to `master`
- Daily at 2 AM UTC
- Manual dispatch

### Jobs

#### 1. Dependency Scan
**Tools:** Safety, pip-audit

**Checks:**
- Known CVEs in dependencies
- Outdated vulnerable packages
- License compliance

**Artifacts:**
- `dependency-scan-reports/` (90 days)

#### 2. SAST Analysis
**Tool:** Bandit

**Checks:**
- Hardcoded secrets
- SQL injection risks
- Command injection risks
- Insecure cryptography
- Unsafe deserialization

**Artifacts:**
- `sast-reports/` (90 days)

#### 3. Secret Scanning
**Tool:** TruffleHog OSS

**Checks:**
- API keys
- Private keys
- Tokens
- Passwords

**Behavior:** Only verified secrets trigger alerts

#### 4. CodeQL Analysis
**Tool:** GitHub CodeQL

**Languages:** Python

**Queries:** security-and-quality

**Integration:** Results sent to GitHub Security tab

#### 5. Docker Image Scan
**Tool:** Trivy

**Checks:**
- OS vulnerabilities
- Language-specific vulnerabilities
- Configuration issues

**Severity Levels:** CRITICAL, HIGH, MEDIUM

**Integration:** Results sent to GitHub Security tab

#### 6. License Check
**Tool:** pip-licenses

**Checks:**
- Dependency licenses
- License compatibility
- OSS compliance

**Artifacts:**
- `license-reports/` (90 days)

#### 7. Security Summary
**Purpose:** Aggregate security scan results

**Behavior:**
- Generates summary report
- Fails if critical issues found

## Release Automation (release.yml)

**Triggers:**
- Push tags matching `v*.*.*`
- Manual dispatch with version input

### Jobs

#### 1. Validate Release
**Purpose:** Ensure release readiness

**Steps:**
- Extract version from tag
- Verify version matches `pyproject.toml`
- Run full test suite
- Check coverage threshold (80%)

**Behavior:** Blocks release if:
- Version mismatch
- Tests fail
- Coverage below 80%

#### 2. Build Distribution
**Purpose:** Build release artifacts

**Dependencies:** `validate` job

**Steps:**
- Build wheel and source distribution
- Validate with `twine check`

**Artifacts:**
- `dist/` (90 days)

#### 3. Security Check
**Purpose:** Final security validation

**Dependencies:** `validate` job

**Steps:**
- Run Bandit security scan
- Run Safety check

#### 4. Create GitHub Release
**Purpose:** Publish release on GitHub

**Dependencies:** `validate`, `build`, `security-check` jobs

**Steps:**
- Download build artifacts
- Generate changelog from commits
- Create GitHub release
- Upload distribution files

**Permissions Required:** `contents: write`

#### 5. Publish to PyPI (Optional)
**Purpose:** Publish to Python Package Index

**Dependencies:** `create-release` job

**Requirements:**
- Repository must be `your-org/fda-tools`
- `PYPI_API_TOKEN` secret configured
- Environment: `pypi`

**Behavior:** Skips if already published

#### 6. Publish to Test PyPI
**Purpose:** Test PyPI publication

**Dependencies:** `create-release` job

**Requirements:**
- `TEST_PYPI_API_TOKEN` secret configured

**Environment:** `https://test.pypi.org/`

#### 7. Release Summary
**Purpose:** Report release status

**Dependencies:** All previous jobs

**Behavior:**
- Generates release summary
- Provides release links

## Pre-commit Hooks

Pre-commit hooks run locally before commits to catch issues early.

### Installation

```bash
pip install pre-commit
pre-commit install
```

### Hooks Enabled

1. **Ruff** - Linting and formatting
2. **Trailing whitespace** - Remove trailing spaces
3. **End of file fixer** - Ensure newline at EOF
4. **YAML check** - Validate YAML syntax
5. **JSON check** - Validate JSON syntax
6. **Merge conflict check** - Detect merge markers
7. **Case conflict check** - Prevent case-sensitive filename issues
8. **Mixed line endings** - Normalize to LF
9. **detect-secrets** - Prevent secret commits
10. **Large files** - Block files >500KB
11. **Python syntax** - AST validation
12. **Docstring coverage** - 75% threshold
13. **Bandit** - Security scanning
14. **mypy** - Type checking (manual stage)

### Running Hooks

```bash
# Run all hooks on all files
pre-commit run --all-files

# Run specific hook
pre-commit run ruff --all-files

# Run mypy (manual stage)
pre-commit run mypy --hook-stage manual --all-files

# Skip hooks for a commit (use sparingly)
git commit --no-verify
```

### Updating Hooks

```bash
pre-commit autoupdate
```

## Code Quality Configuration

### Ruff (pyproject.toml)
- Line length: 100
- Target: Python 3.9+
- Enabled rules: F, E, W, I, N, C, UP, B, A, C4, ISC, PIE, PT, RUF, SIM, PERF, LOG, D
- Max complexity: 15

### Black (pyproject.toml)
- Line length: 100
- Quote style: double
- Target: Python 3.9+

### mypy (pyproject.toml)
- Python version: 3.9
- Strict mode: lib/ modules only
- Relaxed: scripts/, tests/

### Bandit (.bandit)
- Severity: Medium, High
- Confidence: Medium, High
- Skipped tests: B404, B603, B607

### Coverage (.coveragerc)
- Minimum: 80%
- Branch coverage: enabled
- Parallel: enabled

## Badge Integration

Add these badges to your README.md:

```markdown
![CI](https://github.com/your-org/fda-tools/workflows/CI/badge.svg)
![Security](https://github.com/your-org/fda-tools/workflows/Security%20Scanning/badge.svg)
![Coverage](https://codecov.io/gh/your-org/fda-tools/branch/master/graph/badge.svg)
![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)
![License](https://img.shields.io/badge/license-MIT-green)
```

## Secrets Configuration

### Required Secrets

Configure these in GitHub Settings → Secrets and variables → Actions:

#### CI/CD Secrets
- `CODECOV_TOKEN` - Codecov upload token (optional)
- `FDA_API_KEY` - FDA API key for integration tests (optional)
- `GEMINI_API_KEY` - Google Gemini API key for AI features (optional)

#### Release Secrets
- `GITHUB_TOKEN` - Automatically provided by GitHub Actions
- `PYPI_API_TOKEN` - PyPI API token for package publishing (optional)
- `TEST_PYPI_API_TOKEN` - Test PyPI API token (optional)

### Secret Security

- Never commit secrets to the repository
- Use environment-specific secrets
- Rotate secrets regularly
- Use minimal scope tokens
- Enable secret scanning in repository settings

## Troubleshooting

### Common Issues

#### 1. Test Failures

**Symptom:** Tests pass locally but fail in CI

**Solutions:**
- Check Python version compatibility
- Verify system dependencies installed
- Check environment variables
- Review test logs in Actions tab

#### 2. Coverage Below Threshold

**Symptom:** Coverage check fails at 80%

**Solutions:**
- Add tests for uncovered code
- Check coverage report in artifacts
- Run locally: `pytest --cov --cov-report=html`
- Review `htmlcov/index.html`

#### 3. Linting Failures

**Symptom:** Ruff/Black formatting issues

**Solutions:**
- Run locally: `ruff check --fix .`
- Run locally: `ruff format .`
- Run locally: `black .`
- Check `.flake8` and `pyproject.toml` config

#### 4. Security Scan Alerts

**Symptom:** Bandit or Safety reports issues

**Solutions:**
- Review security report in artifacts
- Update vulnerable dependencies
- Add exceptions in `.bandit` if false positive
- Document security decisions

#### 5. Docker Build Failures

**Symptom:** Docker image build fails

**Solutions:**
- Test locally: `docker build -t fda-tools:test .`
- Check Dockerfile syntax
- Verify base image availability
- Review build logs

#### 6. Pre-commit Hooks Failing

**Symptom:** Commit blocked by pre-commit

**Solutions:**
- Run: `pre-commit run --all-files`
- Fix reported issues
- Update hooks: `pre-commit autoupdate`
- Skip if necessary: `git commit --no-verify` (use sparingly)

#### 7. Release Tag Mismatch

**Symptom:** Release workflow fails on version check

**Solutions:**
- Ensure `pyproject.toml` version matches tag
- Tag format: `v5.37.0`
- Update version before tagging
- Use manual dispatch if needed

### Getting Help

1. Check workflow logs in GitHub Actions tab
2. Download artifacts for detailed reports
3. Run jobs locally to reproduce issues
4. Review this documentation
5. Contact DevOps team

## Performance Optimization

### Caching

All workflows use caching:
- Python pip cache
- Docker layer cache (BuildKit)
- Pre-commit hook cache

### Parallelization

Jobs run in parallel when possible:
- Test matrix (3 Python versions)
- Security scans (independent)
- Build and security checks

### Selective Testing

```bash
# Unit tests only (fast)
pytest -m "not slow and not e2e"

# Integration tests
pytest -m "not slow and not e2e"

# Fast E2E tests
pytest -m "e2e_fast"

# All tests
pytest
```

## Maintenance

### Regular Tasks

**Weekly:**
- Review security scan results
- Check dependency updates
- Monitor coverage trends

**Monthly:**
- Update pre-commit hooks: `pre-commit autoupdate`
- Review and update dependencies
- Audit test performance

**Quarterly:**
- Review CI/CD pipeline performance
- Update GitHub Actions versions
- Audit security configurations

### Metrics to Monitor

1. **Build Times**
   - Target: <10 minutes for CI
   - Alert: >15 minutes

2. **Test Coverage**
   - Target: >90%
   - Minimum: 80%

3. **Security Issues**
   - Target: 0 critical/high
   - Review: All medium issues

4. **Deployment Frequency**
   - Target: Weekly releases
   - Track: Release cadence

## Best Practices

1. **Keep CI Fast**
   - Use test markers to skip slow tests
   - Cache dependencies
   - Run expensive tests only on main branches

2. **Write Good Tests**
   - Unit tests: fast, isolated
   - Integration tests: realistic scenarios
   - E2E tests: critical user flows

3. **Security First**
   - Never commit secrets
   - Review security scans
   - Update dependencies promptly

4. **Version Control**
   - Semantic versioning (MAJOR.MINOR.PATCH)
   - Tag releases: `v5.37.0`
   - Update CHANGELOG

5. **Documentation**
   - Document breaking changes
   - Update README badges
   - Maintain this document

## References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [pytest Documentation](https://docs.pytest.org/)
- [pre-commit Documentation](https://pre-commit.com/)
- [Codecov Documentation](https://docs.codecov.com/)

## Version History

- **1.0.0** (2026-02-20) - Initial CI/CD pipeline implementation (FDA-189)
  - GitHub Actions workflows (CI, Security, Release)
  - Pre-commit hooks configuration
  - Code quality tools (Ruff, Black, mypy, Bandit)
  - Coverage reporting (80% minimum)
  - Security scanning (Bandit, Safety, CodeQL, Trivy, TruffleHog)
  - Release automation with changelog generation
