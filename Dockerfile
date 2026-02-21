# FDA Tools Docker Container - Production Ready
# Multi-stage build optimized for size, security, and CI/CD integration
# Version: 5.36.0+docker
# Supports Python 3.11+ with all dependencies
# Build contexts: development, testing, production

# ============================================================================
# Build Arguments (customize via --build-arg)
# ============================================================================
ARG PYTHON_VERSION=3.11
ARG ENVIRONMENT=production
ARG ENABLE_OPTIONAL_DEPS=true

# ============================================================================
# Stage 1: Builder - Install dependencies and compile extensions
# ============================================================================
FROM python:${PYTHON_VERSION}-slim AS builder

# Set build-time labels
LABEL stage=builder
LABEL description="FDA Tools - Build stage"

# Build arguments
ARG ENABLE_OPTIONAL_DEPS
ARG ENVIRONMENT

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    libjpeg-dev \
    libpng-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libtiff-dev \
    libffi-dev \
    libssl-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv

# Activate virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install build tools
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Set working directory for build
WORKDIR /build

# Copy dependency specification files first (layer caching optimization)
COPY pyproject.toml setup.py ./
COPY plugins/fda_tools/__init__.py plugins/fda_tools/

# Install dependencies based on environment
RUN if [ "$ENABLE_OPTIONAL_DEPS" = "true" ]; then \
        echo "Installing with optional dependencies..." && \
        pip install --no-cache-dir -e ".[optional]"; \
    else \
        echo "Installing core dependencies only..." && \
        pip install --no-cache-dir -e .; \
    fi

# Install bridge server dependencies (always needed for health checks)
COPY plugins/fda_tools/bridge/requirements.txt /tmp/bridge-requirements.txt
RUN pip install --no-cache-dir -r /tmp/bridge-requirements.txt

# Install test dependencies if not production
RUN if [ "$ENVIRONMENT" != "production" ]; then \
        echo "Installing test dependencies..." && \
        pip install --no-cache-dir pytest pytest-cov pytest-timeout pytest-mock; \
    fi

# ============================================================================
# Stage 2: Runtime - Minimal production image
# ============================================================================
FROM python:${PYTHON_VERSION}-slim AS runtime

# Metadata labels (OpenContainers standard)
LABEL maintainer="FDA Tools Team <andrew@example.com>"
LABEL version="5.36.0"
LABEL description="AI-powered tools for FDA medical device regulatory work (510k submissions)"
LABEL org.opencontainers.image.source="https://github.com/your-org/fda-tools"
LABEL org.opencontainers.image.documentation="https://github.com/your-org/fda-tools/blob/main/docs/DOCKER_GUIDE.md"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.title="FDA Tools Plugin"
LABEL org.opencontainers.image.description="Containerized FDA regulatory tools for medical device submissions"
LABEL org.opencontainers.image.vendor="FDA Tools Project"

# Build arguments
ARG ENVIRONMENT=production

# Install runtime dependencies only (minimal footprint)
RUN apt-get update && apt-get install -y --no-install-recommends \
    # PDF processing runtime libraries
    libxml2 \
    libxslt1.1 \
    libjpeg62-turbo \
    libpng16-16 \
    libfreetype6 \
    liblcms2-2 \
    libtiff6 \
    # OCR support (optional but small)
    tesseract-ocr \
    tesseract-ocr-eng \
    # Network utilities for health checks
    curl \
    ca-certificates \
    # Process management
    tini \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && apt-get autoclean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Create non-root user for security (FDA 21 CFR Part 11 compliance)
RUN groupadd -g 1000 fdatools && \
    useradd -r -u 1000 -g fdatools -m -s /bin/bash fdatools && \
    mkdir -p /app /data /cache /logs /config && \
    chown -R fdatools:fdatools /app /data /cache /logs /config

# Set comprehensive environment variables
ENV PATH="/opt/venv/bin:$PATH" \
    # Python configuration
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH="/app:/app/plugins/fda-tools:${PYTHONPATH}" \
    PYTHONHASHSEED=random \
    # FDA Tools configuration paths
    FDA_DATA_DIR=/data \
    FDA_CACHE_DIR=/cache \
    FDA_LOG_DIR=/logs \
    FDA_CONFIG_FILE=/config/config.toml \
    # Performance tuning
    MALLOC_ARENA_MAX=2 \
    # Environment indicator
    FDA_ENVIRONMENT=${ENVIRONMENT} \
    # Disable pip version check in container
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Security: Don't load user site packages
    PYTHONNOUSERSITE=1

# Switch to app directory
WORKDIR /app

# Copy application code with proper ownership
COPY --chown=fdatools:fdatools plugins/fda_tools/ /app/plugins/fda_tools/
COPY --chown=fdatools:fdatools pyproject.toml setup.py /app/

# Copy scripts and libraries
COPY --chown=fdatools:fdatools plugins/fda_tools/scripts/ /app/plugins/fda_tools/scripts/
COPY --chown=fdatools:fdatools plugins/fda_tools/lib/ /app/plugins/fda_tools/lib/
COPY --chown=fdatools:fdatools plugins/fda_tools/bridge/ /app/plugins/fda_tools/bridge/
COPY --chown=fdatools:fdatools plugins/fda_tools/commands/ /app/plugins/fda_tools/commands/
COPY --chown=fdatools:fdatools plugins/fda_tools/data/ /app/plugins/fda_tools/data/

# Copy configuration with fallback
COPY --chown=fdatools:fdatools plugins/fda_tools/config.toml /config/config.toml

# Create entrypoint script for flexible execution
COPY --chown=fdatools:fdatools <<'EOF' /app/entrypoint.sh
#!/bin/bash
set -e

# Entrypoint script for FDA Tools container
# Provides flexible command execution with environment setup

# Initialize directories if they don't exist
mkdir -p "${FDA_DATA_DIR}" "${FDA_CACHE_DIR}" "${FDA_LOG_DIR}"

# Function to run bridge server
run_bridge_server() {
    echo "Starting FDA Tools Bridge Server..."
    exec python -m uvicorn bridge.server:app \
        --host 0.0.0.0 \
        --port "${FDA_BRIDGE_PORT:-18790}" \
        --log-level "${LOG_LEVEL:-info}"
}

# Function to run health check
run_health_check() {
    exec python /app/plugins/fda_tools/scripts/health_check.py "$@"
}

# Function to run tests
run_tests() {
    echo "Running FDA Tools test suite..."
    cd /app/plugins/fda_tools
    exec pytest "$@"
}

# Command routing
case "$1" in
    bridge)
        shift
        run_bridge_server "$@"
        ;;
    health)
        shift
        run_health_check "$@"
        ;;
    test)
        shift
        run_tests "$@"
        ;;
    bash|sh|shell)
        exec /bin/bash
        ;;
    *)
        # Default: run Python with provided arguments
        exec python "$@"
        ;;
esac
EOF

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

# Switch to non-root user (security best practice)
USER fdatools

# Expose ports
# 8080: General HTTP interface (if implemented)
# 18790: Bridge server port
EXPOSE 8080 18790

# Health check configuration
# Uses skip-network flag to avoid external dependencies in container health
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python /app/plugins/fda_tools/scripts/health_check.py --skip-network || exit 1

# Volume mount points for persistence
VOLUME ["/data", "/cache", "/logs", "/config"]

# Use tini as init system to handle signals properly
ENTRYPOINT ["/usr/bin/tini", "--", "/app/entrypoint.sh"]

# Default command - show help
CMD ["--help"]

# ============================================================================
# Build and Usage Examples:
# ============================================================================
# Build for production:
#   docker build -t fda-tools:5.36.0 .
#   docker build -t fda-tools:latest --build-arg ENVIRONMENT=production .
#
# Build for development:
#   docker build -t fda-tools:dev --build-arg ENVIRONMENT=development .
#
# Build minimal (no optional deps):
#   docker build -t fda-tools:minimal --build-arg ENABLE_OPTIONAL_DEPS=false .
#
# Run batchfetch:
#   docker run --rm -v $(pwd)/data:/data fda-tools:5.36.0 \
#     -m scripts.batchfetch --product-codes DQY --years 2024 --enrich
#
# Run bridge server:
#   docker run -d -p 18790:18790 --name fda-bridge fda-tools:5.36.0 bridge
#
# Interactive shell:
#   docker run --rm -it -v $(pwd)/data:/data fda-tools:5.36.0 shell
#
# Run tests:
#   docker run --rm fda-tools:5.36.0 test -v
#
# Health check:
#   docker run --rm fda-tools:5.36.0 health --verbose
#
# Security scan (after build):
#   docker scan fda-tools:5.36.0
#   trivy image fda-tools:5.36.0
# ============================================================================
