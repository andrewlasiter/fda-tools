# CI/CD Quick Start Guide

Fast-track guide to get FDA Tools CI/CD pipeline up and running in 30 minutes.

## Prerequisites Checklist

- [ ] GitHub repository with admin access
- [ ] GitHub Container Registry enabled
- [ ] PyPI account with API token (for releases)
- [ ] Deployment infrastructure (Kubernetes or Docker servers)
- [ ] Slack webhook (optional but recommended)

## Step 1: Configure GitHub Secrets (10 minutes)

### Required Secrets

Navigate to **Settings → Secrets and variables → Actions → New repository secret**

```bash
# Docker/Container Registry
GITHUB_TOKEN                  # ✅ Automatically provided by GitHub

# PyPI Publishing
PYPI_API_TOKEN               # Get from https://pypi.org/manage/account/token/
TEST_PYPI_API_TOKEN          # Get from https://test.pypi.org/manage/account/token/

# Notifications
SLACK_WEBHOOK_URL            # Get from Slack → Apps → Incoming Webhooks
```

### Deployment Secrets (Choose One)

**Option A: Kubernetes**
```bash
AWS_ACCESS_KEY_ID            # AWS credentials for EKS
AWS_SECRET_ACCESS_KEY
AWS_REGION=us-east-1        # Variable, not secret
```

**Option B: Docker Compose**
```bash
STAGING_SSH_USER             # SSH username for staging server
STAGING_HOST                 # Staging server IP/hostname
STAGING_SSH_KEY              # Private SSH key (entire key content)
PRODUCTION_SSH_USER          # SSH username for production server
PRODUCTION_HOST              # Production server IP/hostname
PRODUCTION_SSH_KEY           # Private SSH key
```

## Step 2: Configure GitHub Variables (2 minutes)

Navigate to **Settings → Secrets and variables → Actions → Variables → New repository variable**

```bash
# Deployment configuration
CLOUD_PROVIDER=aws           # Options: aws, gcp, azure, none
DEPLOYMENT_TYPE=kubernetes   # Options: kubernetes, docker-compose
AWS_REGION=us-east-1        # Your cloud region
```

## Step 3: Set Up Environment Protection (5 minutes)

### Create Staging Environment

1. **Settings → Environments → New environment**
2. Name: `staging`
3. Protection rules:
   - ✓ Wait timer: 0 minutes
   - ✗ Required reviewers: None
4. Click **Save protection rules**

### Create Production Environment

1. **Settings → Environments → New environment**
2. Name: `production`
3. Protection rules:
   - ✓ Required reviewers: Select at least 1
   - ✓ Wait timer: 5 minutes (optional)
   - ✓ Prevent self-review
4. Deployment branches: `master` and/or `main`
5. Click **Save protection rules**

## Step 4: Enable Branch Protection (5 minutes)

1. **Settings → Branches → Add rule**
2. Branch name pattern: `master` (or `main`)
3. Enable:
   - ✓ Require pull request before merging
   - ✓ Require approvals: 1
   - ✓ Require status checks: `CI Pipeline Status`
   - ✓ Require up-to-date branches
4. Click **Create**

## Step 5: Test CI Pipeline (5 minutes)

```bash
# 1. Create test branch
git checkout -b feature/test-ci
echo "# CI Test" >> README.md
git add README.md
git commit -m "test: verify CI pipeline"
git push origin feature/test-ci

# 2. Create PR on GitHub
# 3. Watch Actions tab - all checks should pass
# 4. Merge PR
```

## Step 6: Test Deployment (3 minutes)

```bash
# Verify staging deployment
curl https://staging-fda-tools.example.com/health
curl https://staging-fda-tools.example.com/version
```

## Quick Troubleshooting

**Linting errors**: `./scripts/ci_helper.sh format && git push`
**Test failures**: `pytest plugins/fda-tools/tests/ -v`
**Deployment issues**: Check logs in Actions tab

## Resources

- **Full Guide**: [docs/CICD_GUIDE.md](docs/CICD_GUIDE.md) (5,200+ words)
- **Implementation**: [FDA-177_CICD_IMPLEMENTATION.md](FDA-177_CICD_IMPLEMENTATION.md)
- **Docker Guide**: [docs/DOCKER_GUIDE.md](docs/DOCKER_GUIDE.md)

## Common Commands

```bash
# Local testing
./scripts/ci_helper.sh ci        # Full CI pipeline
./scripts/ci_helper.sh format    # Format code
./scripts/ci_helper.sh test      # Run tests

# Release
git tag -a v5.37.0 -m "Release 5.37.0"
git push origin master --tags

# Rollback
# GitHub → Actions → Emergency Rollback → Run workflow
```

**Setup Time**: ~30 minutes | **Status**: Production Ready ✅
