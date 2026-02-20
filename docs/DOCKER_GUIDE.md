# FDA Tools Docker Deployment Guide

Comprehensive guide for deploying FDA Tools using Docker and Docker Compose.

**Version:** 5.36.0+docker
**Status:** Production Ready
**Target Environments:** Development, Testing, Staging, Production

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Quick Start](#quick-start)
4. [Configuration](#configuration)
5. [Build and Run](#build-and-run)
6. [Service Profiles](#service-profiles)
7. [Common Operations](#common-operations)
8. [Production Deployment](#production-deployment)
9. [Security Best Practices](#security-best-practices)
10. [Troubleshooting](#troubleshooting)
11. [CI/CD Integration](#cicd-integration)

---

## Overview

The FDA Tools Docker implementation provides:

- **Multi-stage builds** for optimized image size (< 500MB)
- **Production-ready** with security hardening
- **Environment-specific** configurations (dev, test, staging, prod)
- **Optional services** via Docker Compose profiles
- **Health checks** for container orchestration
- **Non-root user** execution for security
- **Volume management** for data persistence

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     FDA Tools Container                      │
├─────────────────────────────────────────────────────────────┤
│  Python 3.11 (slim base)                                    │
│  ├─ Core Dependencies (requests, pandas, PyMuPDF, etc.)     │
│  ├─ Optional Dependencies (OCR, ML, Excel)                  │
│  ├─ Bridge Server (FastAPI, Uvicorn)                        │
│  └─ Health Check System                                      │
├─────────────────────────────────────────────────────────────┤
│  Volumes: /data, /cache, /logs, /config                     │
│  Ports: 8080 (HTTP), 18790 (Bridge)                         │
│  User: fdatools (UID 1000, non-root)                        │
└─────────────────────────────────────────────────────────────┘

Optional Services (via profiles):
├─ PostgreSQL 15 (--profile database)
├─ Redis 7 (--profile cache)
└─ Monitoring (--profile monitoring)
   ├─ Prometheus
   └─ Grafana
```

---

## Prerequisites

### Required

- **Docker:** ≥ 20.10.0
- **Docker Compose:** ≥ 1.29.0 (or Docker Compose V2)
- **Host OS:** Linux, macOS, Windows (with WSL2)
- **Memory:** Minimum 2GB available RAM
- **Disk Space:** Minimum 5GB available

### Recommended

- **Docker Desktop:** Latest version (includes Docker Compose V2)
- **Memory:** 4GB+ available RAM
- **CPU:** 2+ cores
- **Disk Space:** 10GB+ available for data and cache

### Verification

```bash
# Check Docker version
docker --version
# Expected: Docker version 20.10.0 or higher

# Check Docker Compose version
docker compose version
# Expected: Docker Compose version v2.x.x or higher

# Check available resources
docker info | grep -E "CPUs|Total Memory"
```

---

## Quick Start

### 1. Clone and Configure

```bash
# Navigate to FDA Tools directory
cd /path/to/fda-tools

# Copy environment template
cp .env.example .env

# Edit configuration (see Configuration section)
nano .env
```

### 2. Build Images

```bash
# Build FDA Tools image
docker compose build

# Or build with specific arguments
docker compose build --build-arg ENVIRONMENT=production
```

### 3. Start Services

```bash
# Start core service only
docker compose up -d fda-tools

# Start with bridge server
docker compose up -d fda-tools fda-bridge

# Start all services (database + cache)
docker compose --profile database --profile cache up -d
```

### 4. Verify Deployment

```bash
# Check service status
docker compose ps

# Check health
docker compose exec fda-tools python /app/plugins/fda-tools/scripts/health_check.py --verbose

# View logs
docker compose logs -f fda-tools
```

---

## Configuration

### Environment Variables

Configuration is managed via `.env` file (never commit to version control).

#### Core Settings

```bash
# Environment type
ENVIRONMENT=production  # development, testing, staging, production

# Version
FDA_VERSION=5.36.0
PYTHON_VERSION=3.11

# Features
ENABLE_OPTIONAL_DEPS=true
```

#### API Keys (Required for Production)

```bash
# OpenFDA API (optional - increases rate limits)
OPENFDA_API_KEY=your_openfda_key

# AI Services (optional)
GEMINI_API_KEY=your_gemini_key
ANTHROPIC_API_KEY=your_anthropic_key
OPENAI_API_KEY=your_openai_key

# Bridge Server (generate with: openssl rand -hex 32)
FDA_BRIDGE_API_KEY=your_generated_key
```

#### Service Ports

```bash
FDA_PORT=8080
FDA_BRIDGE_PORT=18790
POSTGRES_EXTERNAL_PORT=5432
REDIS_EXTERNAL_PORT=6379
```

#### Resource Limits

```bash
# CPU (cores)
FDA_CPU_LIMIT=2.0
FDA_CPU_RESERVATION=0.5

# Memory
FDA_MEMORY_LIMIT=4G
FDA_MEMORY_RESERVATION=1G
```

See `.env.example` for complete configuration reference.

---

## Build and Run

### Building Images

#### Standard Build

```bash
# Build with defaults (production, optional deps enabled)
docker compose build
```

#### Custom Build Arguments

```bash
# Development build with test dependencies
docker compose build --build-arg ENVIRONMENT=development

# Minimal build without optional dependencies
docker compose build --build-arg ENABLE_OPTIONAL_DEPS=false

# Specific Python version
docker compose build --build-arg PYTHON_VERSION=3.12
```

#### Direct Dockerfile Build

```bash
# Build without docker-compose
docker build -t fda-tools:5.36.0 .

# Build with arguments
docker build \
  --build-arg ENVIRONMENT=production \
  --build-arg PYTHON_VERSION=3.11 \
  -t fda-tools:5.36.0 .
```

### Running Containers

#### Interactive Shell

```bash
# Get shell in container
docker compose run --rm fda-tools shell

# Or using Docker directly
docker run --rm -it fda-tools:5.36.0 shell
```

#### Execute Commands

```bash
# Run batchfetch
docker compose run --rm fda-tools \
  -m scripts.batchfetch --product-codes DQY --years 2024 --enrich

# Run tests
docker compose run --rm fda-tools test -v

# Health check
docker compose run --rm fda-tools health --verbose
```

#### Long-running Services

```bash
# Start bridge server
docker compose up -d fda-bridge

# Check logs
docker compose logs -f fda-bridge

# Stop service
docker compose stop fda-bridge
```

---

## Service Profiles

Docker Compose uses profiles to enable optional services.

### Available Profiles

- **database**: PostgreSQL database
- **cache**: Redis cache
- **monitoring**: Prometheus + Grafana

### Usage

```bash
# Start with database
docker compose --profile database up -d

# Start with database and cache
docker compose --profile database --profile cache up -d

# Start everything including monitoring
docker compose --profile database --profile cache --profile monitoring up -d

# Stop profile-specific services
docker compose --profile monitoring down
```

### Service Dependencies

```
fda-tools (core)
├─ Optional: postgres (--profile database)
├─ Optional: redis (--profile cache)
└─ No dependencies (runs standalone)

fda-bridge
├─ Uses: fda-tools volumes
└─ No dependencies

monitoring
├─ prometheus
└─ grafana
    └─ Depends on: prometheus
```

---

## Common Operations

### Data Management

#### Backup Data

```bash
# Backup all volumes
docker run --rm -v fda-tools-data:/data -v $(pwd)/backup:/backup \
  alpine tar czf /backup/fda-data-$(date +%Y%m%d).tar.gz /data

# Backup database (if using PostgreSQL)
docker compose exec postgres pg_dump -U fdatools fda_tools > backup_$(date +%Y%m%d).sql
```

#### Restore Data

```bash
# Restore from backup
docker run --rm -v fda-tools-data:/data -v $(pwd)/backup:/backup \
  alpine tar xzf /backup/fda-data-20260220.tar.gz -C /

# Restore database
docker compose exec -T postgres psql -U fdatools fda_tools < backup_20260220.sql
```

#### Clean Up

```bash
# Stop and remove containers (keep volumes)
docker compose down

# Remove volumes (CAUTION: deletes all data)
docker compose down -v

# Prune unused Docker resources
docker system prune -a --volumes
```

### Logs and Monitoring

#### View Logs

```bash
# Real-time logs
docker compose logs -f fda-tools

# Last 100 lines
docker compose logs --tail=100 fda-tools

# Since timestamp
docker compose logs --since 2026-02-20T10:00:00 fda-tools
```

#### Health Checks

```bash
# Manual health check
docker compose exec fda-tools python /app/plugins/fda-tools/scripts/health_check.py --verbose

# Docker health status
docker inspect --format='{{.State.Health.Status}}' fda-tools-main
```

#### Resource Usage

```bash
# Container stats
docker stats fda-tools-main

# Detailed resource usage
docker compose top fda-tools
```

### Debugging

#### Exec into Container

```bash
# Shell access
docker compose exec fda-tools /bin/bash

# Run as root (for debugging only)
docker compose exec -u root fda-tools /bin/bash
```

#### Inspect Configuration

```bash
# View environment variables
docker compose exec fda-tools env | grep FDA_

# View config file
docker compose exec fda-tools cat /config/config.toml

# Check Python packages
docker compose exec fda-tools pip list
```

---

## Production Deployment

### Pre-Deployment Checklist

- [ ] Set `ENVIRONMENT=production` in `.env`
- [ ] Generate strong passwords for all services
- [ ] Configure API keys via secure secret management
- [ ] Set appropriate resource limits
- [ ] Enable TLS/SSL for external connections
- [ ] Configure monitoring and alerting
- [ ] Set up backup strategy
- [ ] Review security settings
- [ ] Test disaster recovery procedures
- [ ] Document runbooks

### Security Hardening

#### 1. Secrets Management

**DO NOT** store secrets in `.env` file in production. Use:

- **Docker Secrets** (Swarm mode)
- **Kubernetes Secrets**
- **HashiCorp Vault**
- **AWS Secrets Manager**
- **Azure Key Vault**

Example with Docker Secrets:

```bash
# Create secrets
echo "your_api_key" | docker secret create openfda_api_key -

# Update docker-compose.yml
services:
  fda-tools:
    secrets:
      - openfda_api_key
    environment:
      - OPENFDA_API_KEY_FILE=/run/secrets/openfda_api_key

secrets:
  openfda_api_key:
    external: true
```

#### 2. Network Security

```bash
# Use internal network (no external ports)
networks:
  fda-network:
    driver: bridge
    internal: true  # Isolate from external networks
```

#### 3. Read-Only Filesystem

```yaml
services:
  fda-bridge:
    read_only: true
    tmpfs:
      - /tmp
      - /var/tmp
```

#### 4. Security Scanning

```bash
# Scan image for vulnerabilities
docker scan fda-tools:5.36.0

# Or use Trivy
trivy image fda-tools:5.36.0
```

### High Availability

#### Docker Swarm

```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.yml fda-tools

# Scale services
docker service scale fda-tools_fda-bridge=3
```

#### Kubernetes

See `k8s/` directory for Kubernetes manifests (if implemented).

### Monitoring

Enable monitoring profile:

```bash
# Start with monitoring
docker compose --profile monitoring up -d
```

Access dashboards:
- **Prometheus:** http://localhost:9090
- **Grafana:** http://localhost:3000 (admin/admin)

Configure alerts in `monitoring/prometheus.yml`.

---

## Security Best Practices

### Image Security

1. **Use minimal base images** (python:3.11-slim)
2. **Multi-stage builds** to reduce attack surface
3. **Non-root user** (UID 1000)
4. **Security scanning** in CI/CD pipeline
5. **Regular updates** of base images and dependencies

### Runtime Security

1. **No privileged mode**
2. **Drop unnecessary capabilities**
3. **Read-only root filesystem** where possible
4. **Resource limits** to prevent DoS
5. **Network isolation**

### Secrets Management

1. **Never hardcode secrets**
2. **Use environment variables or secret managers**
3. **Rotate credentials regularly**
4. **Audit secret access**
5. **Encrypt secrets at rest**

### Compliance

- **FDA 21 CFR Part 11** compliance ready
- **HIPAA** considerations for PHI data
- **Audit logging** enabled by default
- **Access control** via API keys

---

## Troubleshooting

### Common Issues

#### Container Won't Start

```bash
# Check logs
docker compose logs fda-tools

# Check health
docker inspect --format='{{.State.Health}}' fda-tools-main

# Verify configuration
docker compose config
```

#### Permission Errors

```bash
# Fix volume permissions
docker compose exec -u root fda-tools chown -R fdatools:fdatools /data /cache /logs
```

#### Out of Memory

```bash
# Increase memory limit in .env
FDA_MEMORY_LIMIT=8G

# Recreate container
docker compose up -d --force-recreate fda-tools
```

#### Network Issues

```bash
# Check network
docker network inspect fda-tools-network

# Recreate network
docker compose down
docker network prune
docker compose up -d
```

### Debug Mode

```bash
# Enable verbose logging
docker compose run --rm -e LOG_LEVEL=DEBUG fda-tools health --verbose

# Check Python environment
docker compose run --rm fda-tools python -c "import sys; print(sys.path)"
```

### Getting Help

- **Documentation:** `/docs` directory
- **Issues:** GitHub Issues
- **Logs:** Always include container logs when reporting issues

---

## CI/CD Integration

### GitHub Actions

```yaml
name: Docker Build and Test

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build Docker image
        run: docker compose build

      - name: Run tests
        run: docker compose run --rm fda-tools test -v

      - name: Security scan
        run: docker scan fda-tools:5.36.0
```

### GitLab CI

```yaml
stages:
  - build
  - test
  - scan

build:
  stage: build
  script:
    - docker compose build

test:
  stage: test
  script:
    - docker compose run --rm fda-tools test -v

scan:
  stage: scan
  script:
    - trivy image fda-tools:5.36.0
```

### Jenkins

```groovy
pipeline {
    agent any
    stages {
        stage('Build') {
            steps {
                sh 'docker compose build'
            }
        }
        stage('Test') {
            steps {
                sh 'docker compose run --rm fda-tools test -v'
            }
        }
        stage('Scan') {
            steps {
                sh 'docker scan fda-tools:5.36.0'
            }
        }
    }
}
```

---

## Advanced Topics

### Custom Entrypoint

Create custom entrypoint script:

```bash
#!/bin/bash
# custom-entrypoint.sh
echo "Running custom initialization..."
exec "$@"
```

Mount in docker-compose.yml:

```yaml
volumes:
  - ./custom-entrypoint.sh:/custom-entrypoint.sh
entrypoint: ["/custom-entrypoint.sh"]
```

### Multi-Architecture Builds

```bash
# Build for multiple platforms
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t fda-tools:5.36.0 \
  --push .
```

### Development Workflow

```bash
# Mount source code for live development
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# docker-compose.dev.yml
services:
  fda-tools:
    volumes:
      - ./plugins/fda-tools:/app/plugins/fda-tools
    environment:
      - RELOAD=true
```

---

## References

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Docker Security Best Practices](https://docs.docker.com/engine/security/)
- [FDA 21 CFR Part 11](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/part-11-electronic-records-electronic-signatures-scope-and-application)

---

**Document Version:** 1.0.0
**Last Updated:** 2026-02-20
**Maintainer:** FDA Tools DevOps Team
