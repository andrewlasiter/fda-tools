# FDA Tools - Docker Quick Reference

**Version:** 5.36.0+docker
**Status:** Production Ready
**Documentation:** See `/docs/DOCKER_GUIDE.md` for comprehensive guide

---

## Quick Start (30 seconds)

```bash
# 1. Setup environment
cp .env.example .env
# Edit .env with your API keys (optional for basic usage)

# 2. Build image
./scripts/docker-build.sh

# 3. Test it works
./scripts/docker-run.sh health --verbose

# 4. Start using it
./scripts/docker-run.sh shell
```

---

## Common Commands

### Build & Test
```bash
# Build image
./scripts/docker-build.sh

# Build with security scan
./scripts/docker-build.sh --scan --test

# Build for development
./scripts/docker-build.sh --environment development
```

### Run Commands
```bash
# Interactive shell
./scripts/docker-run.sh shell

# Run health check
./scripts/docker-run.sh health --verbose

# Run tests
./scripts/docker-run.sh test -v

# Run batchfetch
./scripts/docker-run.sh batchfetch --product-codes DQY --years 2024 --enrich
```

### Service Management
```bash
# Start core services
./scripts/docker-run.sh up

# Start with database and cache
docker compose --profile database --profile cache up -d

# View logs
./scripts/docker-run.sh logs fda-tools

# Stop services
./scripts/docker-run.sh down
```

---

## Architecture Overview

```
FDA Tools Container
├── Base: python:3.11-slim
├── Size: ~380MB (optimized)
├── User: fdatools (non-root)
├── Health: Comprehensive checks
└── Security: Hardened configuration

Optional Services
├── PostgreSQL (--profile database)
├── Redis (--profile cache)
└── Monitoring (--profile monitoring)
```

---

## Environment Configuration

### Minimal (No API Keys)
```bash
# Just copy the example
cp .env.example .env

# Start using it
./scripts/docker-run.sh shell
```

### Production (With API Keys)
```bash
# Copy and edit
cp .env.example .env
nano .env

# Set at minimum:
OPENFDA_API_KEY=your_key_here
FDA_BRIDGE_API_KEY=$(openssl rand -hex 32)
ENVIRONMENT=production
```

---

## Directory Structure

```
fda-tools/
├── Dockerfile                    # Multi-stage production build
├── docker-compose.yml            # Service orchestration
├── .dockerignore                 # Build optimization
├── .env.example                  # Environment template
├── DOCKER_README.md              # This file
├── docs/
│   └── DOCKER_GUIDE.md          # Comprehensive documentation
└── scripts/
    ├── docker-build.sh          # Build automation
    └── docker-run.sh            # Run automation
```

---

## Success Criteria

| Feature | Status |
|---------|--------|
| Image size < 500MB | ✅ ~380MB |
| Health checks | ✅ Implemented |
| Non-root user | ✅ UID 1000 |
| Security hardened | ✅ Complete |
| Documentation | ✅ 5,000+ words |
| CI/CD ready | ✅ Examples included |

---

## Security Notes

### ✅ What's Secure
- Non-root user execution
- Minimal base image (slim)
- No hardcoded secrets
- Capabilities dropped
- Security scanning ready

### ⚠️ What You Must Do
- Set strong passwords in .env
- Use secret management in production (not .env files)
- Enable TLS/SSL for external access
- Regular security scans (`docker scan` or `trivy`)
- Keep base images updated

---

## Troubleshooting

### Build fails
```bash
# Check Docker is running
docker info

# Clean and rebuild
docker compose down -v
./scripts/docker-build.sh --no-cache
```

### Container won't start
```bash
# Check logs
docker compose logs fda-tools

# Verify health
docker inspect --format='{{.State.Health}}' fda-tools-main
```

### Permission errors
```bash
# Fix volume permissions
docker compose exec -u root fda-tools chown -R fdatools:fdatools /data
```

---

## Next Steps

1. **Read full documentation:** `/docs/DOCKER_GUIDE.md`
2. **Configure environment:** Edit `.env` with your settings
3. **Run tests:** `./scripts/docker-run.sh test -v`
4. **Deploy to staging:** Follow production deployment guide
5. **Set up CI/CD:** See GitHub Actions / GitLab CI examples

---

## Support

- **Documentation:** `/docs/DOCKER_GUIDE.md`
- **Implementation Details:** `FDA-176_DOCKER_IMPLEMENTATION.md`
- **Issues:** Create GitHub issue with logs

---

## Resources

- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Container Security Guide](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)
- [FDA Tools Main README](README.md)

---

**Last Updated:** 2026-02-20
**Version:** 5.36.0+docker
