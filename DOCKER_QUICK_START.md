# FDA Tools Docker - Quick Start Guide

Get up and running with FDA Tools in Docker in 5 minutes.

## Prerequisites

- Docker 20.10+ installed
- Docker Compose v2.0+ installed
- 4GB+ available RAM
- 10GB+ available disk space

## 1. Quick Setup

```bash
# Clone repository
git clone https://github.com/your-org/fda-tools.git
cd fda-tools

# Create environment file
cp .env.example .env
# Edit .env and add your API keys:
#   GEMINI_API_KEY=your-key-here
#   FDA_API_KEY=your-key-here
```

## 2. Build & Run

### Option A: Docker Compose (Recommended)

```bash
# Build and start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f fda-tools
```

### Option B: Docker CLI

```bash
# Build image
./scripts/docker_build.sh

# Run a command
./scripts/docker_run.sh -- -m scripts.batchfetch --product-codes DQY --years 2024
```

## 3. Common Commands

### Run BatchFetch with Enrichment

```bash
docker-compose run --rm fda-tools \
  -m scripts.batchfetch \
  --product-codes DQY,OVE,QKQ \
  --years 2023,2024 \
  --enrich \
  --full-auto
```

### Run Tests

```bash
# Quick test
./scripts/docker_test.sh

# With coverage
./scripts/docker_test.sh --coverage

# Specific test
docker-compose run --rm fda-tools \
  -m pytest /app/plugins/fda-tools/tests/test_config.py -v
```

### Interactive Shell

```bash
# Docker Compose
docker-compose run --rm fda-tools /bin/bash

# Docker CLI
./scripts/docker_run.sh --interactive
```

### View Logs

```bash
# All services
docker-compose logs -f

# FDA Tools only
docker-compose logs -f fda-tools

# Last 100 lines
docker-compose logs --tail=100 fda-tools
```

## 4. Access Data

```bash
# Data is stored in Docker volumes
docker volume ls | grep fda-tools

# Export data from container
docker cp fda-tools-main:/data ./local-data

# Or mount local directory
docker-compose run --rm \
  -v $(pwd)/my-data:/data \
  fda-tools \
  -m scripts.batchfetch --product-codes DQY
```

## 5. Stop & Cleanup

```bash
# Stop services
docker-compose down

# Stop and remove volumes (CAUTION: deletes data!)
docker-compose down -v

# Remove all images
docker rmi fda-tools:latest
```

## 6. Troubleshooting

### Container won't start

```bash
# Check logs
docker-compose logs fda-tools

# Run health check
docker-compose exec fda-tools python /app/health_check.py --verbose
```

### Permission errors

```bash
# Fix volume permissions
docker-compose run --rm --user root fda-tools \
  chown -R 1000:1000 /data /cache /logs
```

### Out of memory

```bash
# Increase memory limit in .env file
echo "FDA_MEMORY_LIMIT=8G" >> .env
docker-compose up -d
```

## 7. Monitoring (Optional)

```bash
# Start with monitoring
docker-compose --profile monitoring up -d

# Access dashboards
open http://localhost:9090  # Prometheus
open http://localhost:3000  # Grafana (admin/admin)
```

## 8. Production Deployment

```bash
# Build production image with security scan
./scripts/docker_build.sh --scan --push --registry registry.example.com

# Deploy with resource limits
export FDA_CPU_LIMIT=4.0
export FDA_MEMORY_LIMIT=8G
docker-compose up -d
```

## Environment Variables

### Required

```bash
GEMINI_API_KEY=your-gemini-api-key     # For AI features
FDA_API_KEY=your-openfda-api-key       # For FDA API access
```

### Optional

```bash
FDA_VERSION=5.36.0                      # Image version
LOG_LEVEL=INFO                          # Logging level
FDA_MEMORY_LIMIT=4G                     # Memory limit
FDA_CPU_LIMIT=2.0                       # CPU limit
```

## Next Steps

- Read full documentation: [DOCKER_README.md](DOCKER_README.md)
- Configure monitoring: [Monitoring Setup](#7-monitoring-optional)
- CI/CD integration: [DOCKER_README.md#cicd-integration](DOCKER_README.md#cicd-integration)

## Support

- Issues: https://github.com/your-org/fda-tools/issues
- Documentation: https://github.com/your-org/fda-tools/wiki
