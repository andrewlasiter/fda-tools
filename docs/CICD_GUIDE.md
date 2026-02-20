# FDA Tools CI/CD Pipeline Guide

Complete guide for the Continuous Integration and Continuous Deployment pipeline for FDA Tools.

## Table of Contents

- [Overview](#overview)
- [Workflows](#workflows)
- [Setup](#setup)
- [Usage](#usage)
- [Secrets Management](#secrets-management)
- [Deployment Environments](#deployment-environments)
- [Rollback Procedures](#rollback-procedures)
- [Troubleshooting](#troubleshooting)

## Overview

The FDA Tools CI/CD pipeline provides automated testing, building, and deployment with the following features:

- **Continuous Integration** - Automated testing on every PR and push
- **Continuous Deployment** - Automated deployment to staging and production
- **Release Automation** - Automated GitHub releases and package publishing
- **Security Scanning** - Integrated security and vulnerability scanning
- **Rollback Support** - Emergency rollback capabilities
- **Multi-environment** - Staging and production environments

### Pipeline Architecture

```
┌─────────────┐
│   PR/Push   │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────────────┐
│              CI Pipeline (ci.yml)                    │
├─────────────────────────────────────────────────────┤
│  1. Code Quality & Linting (Ruff, Black)            │
│  2. Type Checking (mypy)                            │
│  3. Security Scanning (Bandit, Trivy, Snyk)         │
│  4. Unit Tests (Python 3.9-3.12, Ubuntu/Mac/Win)    │
│  5. Integration Tests (PostgreSQL, Redis)           │
│  6. Build & Package Validation                      │
│  7. Docker Build & Security Scan                    │
└────────────┬────────────────────────────────────────┘
             │ (on master merge)
             ▼
┌─────────────────────────────────────────────────────┐
│          CD Pipeline (cd.yml)                        │
├─────────────────────────────────────────────────────┤
│  1. Pre-deployment Validation                       │
│  2. Build & Push Docker Image to GHCR              │
│  3. Deploy to Staging (automatic)                   │
│  4. Deploy to Production (manual approval)          │
│  5. Rollback on Failure                             │
└────────────┬────────────────────────────────────────┘
             │ (on version tag)
             ▼
┌─────────────────────────────────────────────────────┐
│       Release Pipeline (release.yml)                 │
├─────────────────────────────────────────────────────┤
│  1. Prepare Release & Validate                      │
│  2. Build Release Artifacts                         │
│  3. Generate Changelog                              │
│  4. Create GitHub Release                           │
│  5. Publish to PyPI                                 │
│  6. Publish Docker Images (GHCR + Docker Hub)       │
│  7. Notifications (Slack, Linear)                   │
└─────────────────────────────────────────────────────┘
```

## Workflows

### 1. CI Workflow (`ci.yml`)

**Triggers:**
- Push to `master`, `main`, `develop`, `feature/**`, `hotfix/**`
- Pull requests to `master`, `main`, `develop`
- Manual dispatch

**Jobs:**
1. **Lint** - Code quality checks (Ruff, Black, YAML, JSON, docstrings)
2. **TypeCheck** - Static type checking with mypy (non-blocking)
3. **Security** - Security scanning (Bandit, Safety, detect-secrets, Trivy)
4. **Test** - Unit tests across Python 3.9-3.12 on Ubuntu/Mac/Windows
5. **Integration** - Integration tests with PostgreSQL and Redis
6. **Build** - Package building and validation
7. **Docker** - Docker image building and security scanning

**Coverage Requirements:**
- Minimum 80% code coverage
- Coverage reports uploaded to Codecov

### 2. CD Workflow (`cd.yml`)

**Triggers:**
- Push to `master`/`main` branches
- Version tags (`v*.*.*`)
- Manual dispatch

**Jobs:**
1. **Validate** - Pre-deployment validation and version extraction
2. **Build-Push-Docker** - Build and push to GitHub Container Registry
3. **Deploy-Staging** - Automated deployment to staging
4. **Deploy-Production** - Manual approval deployment to production
5. **Rollback** - Automatic rollback on failure

**Deployment Strategies:**
- **Staging**: Automatic on master merge
- **Production**: Manual approval required
- **Blue-Green**: Supported for Kubernetes deployments
- **Docker Compose**: Rolling updates

### 3. Release Workflow (`release.yml`)

**Triggers:**
- Version tags (`v*.*.*`)
- Manual dispatch

**Jobs:**
1. **Prepare-Release** - Version validation and consistency checks
2. **Build-Release** - Build distribution packages
3. **Generate-Changelog** - Automated changelog from git commits
4. **Create-Release** - GitHub release creation
5. **Publish-PyPI** - Publish to PyPI (stable releases)
6. **Publish-TestPyPI** - Publish to TestPyPI (pre-releases)
7. **Publish-Docker** - Multi-platform Docker images
8. **Notify-Release** - Slack/Linear/Email notifications

### 4. Rollback Workflow (`rollback.yml`)

**Triggers:**
- Manual dispatch only

**Inputs:**
- `environment`: staging or production
- `target_version`: Version to rollback to
- `reason`: Reason for rollback
- `skip_health_check`: Skip health checks

**Jobs:**
1. **Validate** - Validate rollback request and target version
2. **Rollback** - Execute rollback
3. **Verify** - Post-rollback health checks
4. **Notify** - Rollback notifications

## Setup

### Prerequisites

1. **GitHub Secrets** - Configure required secrets
2. **Environment Protection** - Set up environment protection rules
3. **Branch Protection** - Enable branch protection on `master`/`main`
4. **Container Registry** - Enable GitHub Container Registry

### 1. Configure GitHub Secrets

Navigate to **Settings → Secrets and variables → Actions** and add:

#### Required Secrets

```bash
# Docker/Container Registry
GITHUB_TOKEN                  # Automatically provided by GitHub

# PyPI Publishing
PYPI_API_TOKEN               # From pypi.org account settings
TEST_PYPI_API_TOKEN          # From test.pypi.org account settings

# Notifications (optional)
SLACK_WEBHOOK_URL            # Slack incoming webhook URL
LINEAR_API_KEY               # Linear API key (optional)
```

#### Deployment Secrets (if using cloud providers)

```bash
# AWS
AWS_ACCESS_KEY_ID            # AWS access key
AWS_SECRET_ACCESS_KEY        # AWS secret key

# GCP
GCP_CREDENTIALS              # GCP service account JSON

# SSH (for Docker Compose deployments)
STAGING_SSH_USER             # SSH username for staging
STAGING_HOST                 # Staging server hostname
STAGING_SSH_KEY              # SSH private key
PRODUCTION_SSH_USER          # SSH username for production
PRODUCTION_HOST              # Production server hostname
PRODUCTION_SSH_KEY           # SSH private key

# Docker Hub (optional)
DOCKERHUB_USERNAME           # Docker Hub username
DOCKERHUB_TOKEN              # Docker Hub access token

# Security scanning
SNYK_TOKEN                   # Snyk API token (optional)
CODECOV_TOKEN                # Codecov upload token
```

### 2. Configure GitHub Variables

Navigate to **Settings → Secrets and variables → Actions → Variables** and add:

```bash
# Deployment configuration
CLOUD_PROVIDER=aws           # Options: aws, gcp, azure
DEPLOYMENT_TYPE=kubernetes   # Options: kubernetes, docker-compose
AWS_REGION=us-east-1        # Cloud region

# Application configuration
OPENFDA_API_KEY=<optional>  # OpenFDA API key for rate limits
```

### 3. Set Up Environment Protection Rules

Configure protection rules for production environment:

1. Navigate to **Settings → Environments**
2. Create `production` environment
3. Enable **Required reviewers** (at least 1 reviewer)
4. Set **Wait timer** (optional, e.g., 5 minutes)
5. Enable **Prevent self-review**

Create `staging` environment with less restrictive rules:
- No required reviewers
- Shorter deployment delay

### 4. Enable Branch Protection

For `master`/`main` branch:

1. **Settings → Branches → Add rule**
2. Branch name pattern: `master` or `main`
3. Enable:
   - ✓ Require a pull request before merging
   - ✓ Require approvals (minimum 1)
   - ✓ Require status checks to pass before merging
     - Select: `CI Pipeline Status`
   - ✓ Require branches to be up to date before merging
   - ✓ Do not allow bypassing the above settings

### 5. Enable GitHub Container Registry

1. **Settings → Packages**
2. Ensure GitHub Container Registry is enabled
3. Set package visibility (public or private)

## Usage

### Running CI on Pull Requests

CI automatically runs when you:

1. **Create a PR**:
   ```bash
   git checkout -b feature/my-feature
   # Make changes
   git add .
   git commit -m "feat: add new feature"
   git push origin feature/my-feature
   # Create PR on GitHub
   ```

2. **CI checks run automatically**:
   - Linting
   - Type checking
   - Security scanning
   - Unit tests (all Python versions)
   - Integration tests
   - Build validation
   - Docker build

3. **View results**:
   - Check marks appear on PR
   - Click "Details" for full logs
   - Fix any failures and push again

### Deploying to Staging

Staging deployment happens automatically when:

1. **Merge to master**:
   ```bash
   # After PR approval
   git checkout master
   git pull origin master
   # Automatic deployment triggered
   ```

2. **Monitor deployment**:
   - Go to **Actions** tab
   - Select "Continuous Deployment" workflow
   - Watch deployment progress

3. **Verify staging**:
   ```bash
   curl https://staging-fda-tools.example.com/health
   curl https://staging-fda-tools.example.com/version
   ```

### Deploying to Production

Production requires manual approval:

1. **Create release tag**:
   ```bash
   # Bump version first
   ./scripts/ci_helper.sh bump minor  # or major/patch
   git push origin master --tags
   ```

2. **Approve deployment**:
   - Go to **Actions** tab
   - Select running "Continuous Deployment" workflow
   - Click **Review deployments**
   - Select `production`
   - Click **Approve and deploy**

3. **Monitor deployment**:
   - Watch blue-green deployment progress
   - Health checks run automatically
   - Rollback triggered on failure

### Creating a Release

#### Automatic Release (Recommended)

1. **Bump version**:
   ```bash
   ./scripts/ci_helper.sh bump minor
   ```

2. **Create and push tag**:
   ```bash
   git tag -a v5.37.0 -m "Release 5.37.0"
   git push origin master --tags
   ```

3. **Automatic steps**:
   - Release workflow triggers
   - Builds packages
   - Generates changelog
   - Creates GitHub release
   - Publishes to PyPI
   - Pushes Docker images
   - Sends notifications

#### Manual Release

1. **Go to Actions tab**
2. **Select "Release Automation"**
3. **Click "Run workflow"**
4. **Enter version** (e.g., `5.37.0`)
5. **Select pre-release** (if applicable)
6. **Click "Run workflow"**

### Running Tests Locally

Before pushing, run CI checks locally:

```bash
# Run full CI pipeline
./scripts/ci_helper.sh ci

# Individual checks
./scripts/ci_helper.sh lint
./scripts/ci_helper.sh security
./scripts/ci_helper.sh test
./scripts/ci_helper.sh build

# Format code
./scripts/ci_helper.sh format
```

## Secrets Management

### Best Practices

1. **Never commit secrets** to repository
2. **Use GitHub Secrets** for CI/CD secrets
3. **Rotate secrets regularly** (every 90 days)
4. **Use least-privilege** access
5. **Audit secret usage** regularly

### Secret Rotation

To rotate secrets:

1. **Generate new secret**:
   ```bash
   # Example: Generate new API token
   openssl rand -hex 32
   ```

2. **Update GitHub Secret**:
   - Settings → Secrets → Edit secret
   - Paste new value
   - Save

3. **Update deployed environments**:
   - Deploy new version with updated secrets
   - Verify functionality

4. **Revoke old secret**:
   - Only after successful deployment

### Secret Scanning

Automated secret scanning:
- **detect-secrets** in pre-commit hooks
- **Trivy** in CI pipeline
- **GitHub Secret Scanning** (if enabled)

## Deployment Environments

### Staging Environment

**Purpose**: Pre-production testing

**Configuration**:
- URL: `https://staging-fda-tools.example.com`
- Auto-deploy: Yes (on master merge)
- Approval: Not required
- Database: Staging PostgreSQL
- Cache: Staging Redis

**When to use**:
- Test new features before production
- Validate hotfixes
- Integration testing
- Performance testing

### Production Environment

**Purpose**: Live user-facing deployment

**Configuration**:
- URL: `https://fda-tools.example.com`
- Auto-deploy: No (manual approval required)
- Approval: Required (1+ reviewers)
- Database: Production PostgreSQL (HA)
- Cache: Production Redis (clustered)

**Deployment strategy**:
- Blue-green deployment (Kubernetes)
- Rolling updates (Docker Compose)
- Automated rollback on failure

## Rollback Procedures

### When to Rollback

Rollback if:
- ✗ Critical bugs in production
- ✗ Performance degradation
- ✗ Security vulnerabilities
- ✗ Data corruption risks
- ✗ Service unavailability

### Automatic Rollback

Automatic rollback triggers on:
- Health check failures
- Deployment timeout
- Post-deployment verification failure

### Manual Rollback

1. **Navigate to Actions tab**
2. **Select "Emergency Rollback" workflow**
3. **Click "Run workflow"**
4. **Configure rollback**:
   - Environment: `production` or `staging`
   - Target version: `previous` or specific version (e.g., `5.36.0`)
   - Reason: Describe the issue
   - Skip health check: Usually `false`
5. **Click "Run workflow"**
6. **Monitor progress**
7. **Verify rollback**:
   ```bash
   curl https://fda-tools.example.com/version
   ```

### Rollback Example

```bash
# Rollback production to previous version
# Via GitHub UI: Actions → Emergency Rollback
Environment: production
Target Version: previous
Reason: Critical bug in user authentication
Skip Health Check: false

# Or rollback to specific version
Environment: production
Target Version: 5.36.0
Reason: Regression in data processing
Skip Health Check: false
```

### Post-Rollback Actions

After rollback:

1. **Investigate root cause**
2. **Create hotfix branch**
3. **Test fix thoroughly**
4. **Deploy hotfix to staging**
5. **Verify fix**
6. **Deploy hotfix to production**
7. **Document incident**

## Troubleshooting

### CI Failures

#### Linting Failures

**Error**: Ruff or Black formatting issues

**Solution**:
```bash
# Auto-fix formatting
./scripts/ci_helper.sh format

# Check what would change
ruff check plugins/fda-tools/ --diff
black --check plugins/fda-tools/
```

#### Test Failures

**Error**: Unit tests failing

**Solution**:
```bash
# Run tests locally
pytest plugins/fda-tools/tests/ -v

# Run specific test
pytest plugins/fda-tools/tests/test_file.py::test_function -v

# Check coverage
pytest --cov=plugins/fda-tools/lib --cov-report=html
```

#### Security Failures

**Error**: Bandit or Trivy findings

**Solution**:
```bash
# Run Bandit locally
bandit -r plugins/fda-tools/lib plugins/fda-tools/scripts -ll

# Check for secrets
detect-secrets scan --baseline .secrets.baseline
```

### CD Failures

#### Docker Build Failures

**Error**: Docker build fails

**Solution**:
```bash
# Build locally
docker build -t fda-tools:test .

# Check Dockerfile syntax
docker build --dry-run .

# View build logs
docker build --progress=plain -t fda-tools:test .
```

#### Deployment Failures

**Error**: Kubernetes deployment fails

**Solution**:
```bash
# Check deployment status
kubectl get deployments -n fda-tools-production
kubectl describe deployment fda-tools -n fda-tools-production

# Check pod status
kubectl get pods -n fda-tools-production
kubectl logs -f <pod-name> -n fda-tools-production

# Rollback manually
kubectl rollout undo deployment/fda-tools -n fda-tools-production
```

#### Health Check Failures

**Error**: Post-deployment health checks fail

**Solution**:
```bash
# Check service health
curl -v https://fda-tools.example.com/health

# Check logs
kubectl logs -f deployment/fda-tools -n fda-tools-production

# Check resource usage
kubectl top pods -n fda-tools-production
```

### Release Failures

#### Version Mismatch

**Error**: Tag version doesn't match pyproject.toml

**Solution**:
```bash
# Update version in pyproject.toml
./scripts/bump_version.py 5.37.0

# Create matching tag
git tag -d v5.37.0  # Delete old tag
git tag -a v5.37.0 -m "Release 5.37.0"
git push origin master --tags --force
```

#### PyPI Publishing Failures

**Error**: Package upload fails

**Solution**:
```bash
# Verify package locally
twine check dist/*

# Test upload to TestPyPI
twine upload --repository testpypi dist/*

# Check PyPI token
# Settings → Secrets → PYPI_API_TOKEN
```

## Performance Optimization

### Build Caching

Workflows use caching for:
- Python pip packages
- Docker layers
- Pre-commit environments
- GitHub Actions cache

### Parallelization

Jobs run in parallel:
- Lint + TypeCheck + Security (simultaneously)
- Multi-platform Docker builds (amd64 + arm64)
- Tests across Python versions (3.9-3.12)

### Resource Limits

Configured timeouts:
- CI jobs: 10-30 minutes
- CD jobs: 30-45 minutes
- Tests: Per-test timeouts (pytest-timeout)

## Monitoring & Alerts

### GitHub Actions Monitoring

Monitor workflows:
- **Actions tab**: View all workflow runs
- **Insights**: Workflow usage statistics
- **Email notifications**: On workflow failure

### External Monitoring

Integration with:
- **Slack**: Deployment notifications
- **Linear**: Release updates
- **Codecov**: Coverage tracking
- **Snyk**: Vulnerability monitoring

### Metrics

Track:
- Deployment frequency
- Lead time for changes
- Mean time to recovery (MTTR)
- Change failure rate

## Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Documentation](https://docs.docker.com/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [PyPI Publishing Guide](https://packaging.python.org/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/)

## Support

For CI/CD issues:

1. **Check workflow logs** in Actions tab
2. **Review this guide** for common issues
3. **Check recent commits** for breaking changes
4. **Contact DevOps team** via Slack or Linear
5. **Create incident** for critical production issues

---

**Last Updated**: 2026-02-20
**Pipeline Version**: 1.0.0
**Maintained by**: DevOps Team
