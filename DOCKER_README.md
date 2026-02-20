# FDA Tools Docker Guide

Complete guide to deploying FDA Tools using Docker and Docker Compose.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Installation](#installation)
3. [Building the Image](#building-the-image)
4. [Running Containers](#running-containers)
5. [Environment Variables](#environment-variables)
6. [Volume Management](#volume-management)
7. [Docker Compose](#docker-compose)
8. [Common Tasks](#common-tasks)
9. [Security](#security)
10. [Troubleshooting](#troubleshooting)
11. [Production Deployment](#production-deployment)

## Quick Start

```bash
# 1. Clone repository
git clone https://github.com/your-org/fda-tools.git
cd fda-tools

# 2. Create environment file
cp .env.example .env
# Edit .env with your API keys

# 3. Build and start services
docker-compose up -d

# 4. Run a command
docker-compose run --rm fda-tools -m scripts.batchfetch --product-codes DQY --years 2024

# 5. View logs
docker-compose logs -f fda-tools
```

## Installation

### Prerequisites

- Docker Engine 20.10+ or Docker Desktop
- Docker Compose v2.0+ (included with Docker Desktop)
- 4GB+ available RAM
- 10GB+ available disk space

### Verify Installation

```bash
docker --version
# Docker version 24.0.0 or higher

docker-compose --version
# Docker Compose version v2.20.0 or higher
```

## Building the Image

### Basic Build

```bash
# Build from root directory
docker build -t fda-tools:5.36.0 .

# Build with BuildKit (faster, better caching)
DOCKER_BUILDKIT=1 docker build -t fda-tools:5.36.0 .
```

### Build Arguments

```bash
# Custom Python version (requires Dockerfile modification)
docker build --build-arg PYTHON_VERSION=3.12 -t fda-tools:5.36.0 .

# Enable inline cache for CI/CD
docker build --build-arg BUILDKIT_INLINE_CACHE=1 -t fda-tools:5.36.0 .
```

### Multi-Architecture Build

```bash
# Build for multiple platforms (requires buildx)
docker buildx create --use
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t fda-tools:5.36.0 \
  --push \
  .
```

## Running Containers

### Basic Run

```bash
# Run with automatic cleanup
docker run --rm fda-tools:5.36.0 --version

# Mount data directory
docker run --rm \
  -v $(pwd)/data:/data \
  fda-tools:5.36.0 \
  -m scripts.batchfetch --product-codes DQY --years 2024
```

### Interactive Shell

```bash
# Start interactive bash session
docker run --rm -it \
  -v $(pwd)/data:/data \
  fda-tools:5.36.0 \
  /bin/bash

# Inside container:
python -m scripts.batchfetch --help
```

### Running Tests

```bash
# Run full test suite
docker run --rm fda-tools:5.36.0 \
  -m pytest /app/plugins/fda-tools/tests -v

# Run specific test file
docker run --rm fda-tools:5.36.0 \
  -m pytest /app/plugins/fda-tools/tests/test_config.py

# Run with coverage
docker run --rm fda-tools:5.36.0 \
  -m pytest /app/plugins/fda-tools/tests --cov=lib --cov-report=html
```

## Environment Variables

### Core Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `FDA_DATA_DIR` | Data storage directory | `/data` | No |
| `FDA_CACHE_DIR` | Cache directory | `/cache` | No |
| `FDA_LOG_DIR` | Log directory | `/logs` | No |
| `FDA_CONFIG_FILE` | Configuration file path | `/app/plugins/fda-tools/config.toml` | No |

### API Keys

| Variable | Description | Required |
|----------|-------------|----------|
| `GEMINI_API_KEY` | Google Gemini API key | For AI features |
| `FDA_API_KEY` | FDA openFDA API key | Recommended |

### Database Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection URL | None |
| `POSTGRES_HOST` | PostgreSQL hostname | `postgres` |
| `POSTGRES_PORT` | PostgreSQL port | `5432` |
| `POSTGRES_DB` | Database name | `fda_tools` |
| `POSTGRES_USER` | Database user | `fdatools` |
| `POSTGRES_PASSWORD` | Database password | None |

### Redis Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `REDIS_URL` | Redis connection URL | `redis://redis:6379/0` |
| `REDIS_HOST` | Redis hostname | `redis` |
| `REDIS_PORT` | Redis port | `6379` |

### Logging Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | `INFO` |
| `LOG_FORMAT` | Log format (json, text) | `json` |

### Example .env File

```bash
# API Keys
GEMINI_API_KEY=your-gemini-api-key-here
FDA_API_KEY=your-fda-api-key-here

# Database (optional)
POSTGRES_PASSWORD=secure-password-here

# Application
FDA_VERSION=5.36.0
LOG_LEVEL=INFO

# Resource limits
FDA_CPU_LIMIT=2.0
FDA_MEMORY_LIMIT=4G
```

## Volume Management

### Named Volumes

```bash
# List volumes
docker volume ls | grep fda-tools

# Inspect volume
docker volume inspect fda-tools-data

# Backup volume
docker run --rm \
  -v fda-tools-data:/data \
  -v $(pwd)/backup:/backup \
  alpine tar czf /backup/fda-data-$(date +%Y%m%d).tar.gz /data
```

### Bind Mounts

```bash
# Mount local directory
docker run --rm \
  -v $(pwd)/local-data:/data \
  -v $(pwd)/local-cache:/cache \
  fda-tools:5.36.0 \
  -m scripts.batchfetch --product-codes DQY
```

### Volume Permissions

```bash
# Fix permissions (if needed)
sudo chown -R 1000:1000 ./local-data ./local-cache
```

## Docker Compose

### Starting Services

```bash
# Start all core services (fda-tools, postgres, redis)
docker-compose up -d

# Start with monitoring (Prometheus, Grafana)
docker-compose --profile monitoring up -d

# Start specific service
docker-compose up -d postgres
```

### Stopping Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (CAUTION: deletes data)
docker-compose down -v

# Stop specific service
docker-compose stop fda-tools
```

### Running Commands

```bash
# Run batchfetch
docker-compose run --rm fda-tools \
  -m scripts.batchfetch --product-codes DQY --years 2024 --enrich

# Run gap analysis
docker-compose run --rm fda-tools \
  -m scripts.gap_analysis --project-dir /projects/my-project

# Run tests
docker-compose run --rm fda-tools \
  -m pytest /app/plugins/fda-tools/tests -v

# Interactive shell
docker-compose run --rm fda-tools /bin/bash
```

### Viewing Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f fda-tools

# Last 100 lines
docker-compose logs --tail=100 fda-tools

# Follow new logs only
docker-compose logs -f --since 5m
```

### Scaling Services

```bash
# Scale to multiple instances (if stateless)
docker-compose up -d --scale fda-tools=3
```

## Common Tasks

### BatchFetch with Enrichment

```bash
docker-compose run --rm fda-tools \
  -m scripts.batchfetch \
  --product-codes DQY,OVE,QKQ \
  --years 2023,2024 \
  --enrich \
  --full-auto
```

### Running Predicate Search

```bash
docker-compose run --rm fda-tools \
  -m scripts.predicate_search \
  --device-type "cardiovascular catheter" \
  --max-results 50
```

### Database Migration

```bash
# Run database migrations
docker-compose run --rm fda-tools \
  -m scripts.db_migrate --upgrade

# Backup database
docker-compose exec postgres pg_dump -U fdatools fda_tools > backup.sql
```

### Update Container

```bash
# Pull latest image
docker-compose pull fda-tools

# Rebuild from source
docker-compose build --no-cache fda-tools

# Restart with new image
docker-compose up -d fda-tools
```

## Security

### Best Practices

1. **Never commit .env files** to version control
2. **Use Docker secrets** for production deployments
3. **Run as non-root user** (already configured)
4. **Scan for vulnerabilities** regularly
5. **Keep images updated** with security patches

### Security Scanning

```bash
# Install Trivy
# https://aquasecurity.github.io/trivy/

# Scan image for vulnerabilities
trivy image fda-tools:5.36.0

# Scan with severity filter
trivy image --severity HIGH,CRITICAL fda-tools:5.36.0

# Generate report
trivy image --format json --output report.json fda-tools:5.36.0
```

### Using Docker Secrets

```bash
# Create secret
echo "your-api-key" | docker secret create gemini_api_key -

# Use in docker-compose.yml
secrets:
  - gemini_api_key

environment:
  - GEMINI_API_KEY_FILE=/run/secrets/gemini_api_key
```

### Network Security

```bash
# Use custom network with isolation
docker network create --driver bridge fda-secure

# Run with isolated network
docker run --rm --network fda-secure fda-tools:5.36.0
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs fda-tools

# Check health status
docker inspect --format='{{.State.Health.Status}}' fda-tools-main

# Run health check manually
docker-compose exec fda-tools python /app/health_check.py --verbose
```

### Permission Errors

```bash
# Fix volume permissions
docker-compose run --rm --user root fda-tools \
  chown -R 1000:1000 /data /cache /logs
```

### Out of Memory

```bash
# Increase memory limit in docker-compose.yml
deploy:
  resources:
    limits:
      memory: 8G

# Or set in environment
export FDA_MEMORY_LIMIT=8G
docker-compose up -d
```

### Disk Space Issues

```bash
# Clean up unused images
docker image prune -a

# Clean up volumes
docker volume prune

# Clean up everything (CAUTION)
docker system prune -a --volumes
```

### Network Connectivity

```bash
# Test database connection
docker-compose exec fda-tools \
  python -c "import psycopg2; psycopg2.connect('postgresql://fdatools:changeme@postgres:5432/fda_tools')"

# Test Redis connection
docker-compose exec fda-tools \
  python -c "import redis; redis.from_url('redis://redis:6379/0').ping()"

# Check network
docker network inspect fda-tools-network
```

## Production Deployment

### Docker Swarm

```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.yml fda-tools

# List services
docker service ls

# Scale service
docker service scale fda-tools_fda-tools=3

# Update service
docker service update --image fda-tools:5.37.0 fda-tools_fda-tools
```

### Kubernetes

```bash
# Generate Kubernetes manifests (requires kompose)
kompose convert -f docker-compose.yml

# Apply to cluster
kubectl apply -f fda-tools-deployment.yaml
kubectl apply -f fda-tools-service.yaml

# Check status
kubectl get pods -l app=fda-tools
kubectl logs -f deployment/fda-tools
```

### CI/CD Integration

```yaml
# GitHub Actions example
- name: Build Docker image
  run: |
    docker build -t fda-tools:${{ github.sha }} .

- name: Run tests in container
  run: |
    docker run --rm fda-tools:${{ github.sha }} \
      -m pytest /app/plugins/fda-tools/tests

- name: Security scan
  run: |
    trivy image --severity HIGH,CRITICAL fda-tools:${{ github.sha }}

- name: Push to registry
  run: |
    docker tag fda-tools:${{ github.sha }} registry.example.com/fda-tools:latest
    docker push registry.example.com/fda-tools:latest
```

### Health Checks

```bash
# Manual health check
curl http://localhost:8080/health

# Using Docker health check
docker inspect --format='{{json .State.Health}}' fda-tools-main | jq
```

### Monitoring

```bash
# Start monitoring stack
docker-compose --profile monitoring up -d

# Access Prometheus
open http://localhost:9090

# Access Grafana
open http://localhost:3000
# Default credentials: admin/admin
```

### Backup Strategy

```bash
#!/bin/bash
# backup.sh - Automated backup script

DATE=$(date +%Y%m%d-%H%M%S)
BACKUP_DIR=/backups/fda-tools

# Backup volumes
docker run --rm \
  -v fda-tools-data:/data:ro \
  -v $BACKUP_DIR:/backup \
  alpine tar czf /backup/data-$DATE.tar.gz /data

# Backup database
docker-compose exec -T postgres pg_dump -U fdatools fda_tools | \
  gzip > $BACKUP_DIR/postgres-$DATE.sql.gz

# Retain last 7 days
find $BACKUP_DIR -type f -mtime +7 -delete
```

## Performance Optimization

### Resource Tuning

```yaml
# docker-compose.yml
deploy:
  resources:
    limits:
      cpus: '4.0'
      memory: 8G
    reservations:
      cpus: '2.0'
      memory: 4G
```

### Caching Strategy

```bash
# Use Redis for caching
export REDIS_URL=redis://redis:6379/0

# Configure cache TTL
export CACHE_TTL_SECONDS=3600
```

### Build Optimization

```dockerfile
# Use .dockerignore to exclude unnecessary files
# Enable BuildKit for parallel builds
# Use multi-stage builds to minimize image size
# Cache pip dependencies in separate layer
```

## Support

For issues and questions:

- GitHub Issues: https://github.com/your-org/fda-tools/issues
- Documentation: https://github.com/your-org/fda-tools/wiki
- Email: support@example.com

## License

MIT License - See LICENSE file for details
