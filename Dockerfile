# FDA Tools Docker Container
# Multi-stage build for optimized size and security
# Supports Python 3.11+ with all dependencies

# ============================================================================
# Stage 1: Builder - Install dependencies and compile extensions
# ============================================================================
FROM python:3.11-slim AS builder

# Set build-time labels
LABEL stage=builder
LABEL description="FDA Tools - Build stage"

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

# Copy only dependency files first (for layer caching)
COPY pyproject.toml setup.py /app/
COPY plugins/fda-tools/__init__.py /app/plugins/fda-tools/

# Set working directory
WORKDIR /app

# Install Python dependencies (core + optional features)
RUN pip install --no-cache-dir -e ".[optional]"

# ============================================================================
# Stage 2: Runtime - Minimal production image
# ============================================================================
FROM python:3.11-slim AS runtime

# Metadata labels
LABEL maintainer="FDA Tools Team <andrew@example.com>"
LABEL version="5.36.0"
LABEL description="AI-powered tools for FDA medical device regulatory work (510k submissions)"
LABEL org.opencontainers.image.source="https://github.com/your-org/fda-tools"
LABEL org.opencontainers.image.documentation="https://github.com/your-org/fda-tools/blob/main/DOCKER_README.md"
LABEL org.opencontainers.image.licenses="MIT"

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    # PDF processing libraries
    libxml2 \
    libxslt1.1 \
    libjpeg62-turbo \
    libpng16-16 \
    libfreetype6 \
    liblcms2-2 \
    libtiff6 \
    # OCR support (optional)
    tesseract-ocr \
    tesseract-ocr-eng \
    # Network utilities
    curl \
    ca-certificates \
    # Cleanup
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Create non-root user for security
RUN groupadd -g 1000 fdatools && \
    useradd -r -u 1000 -g fdatools -m -s /bin/bash fdatools && \
    mkdir -p /app /data /cache /logs && \
    chown -R fdatools:fdatools /app /data /cache /logs

# Set environment variables
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH="/app:${PYTHONPATH}" \
    # FDA Tools configuration
    FDA_DATA_DIR=/data \
    FDA_CACHE_DIR=/cache \
    FDA_LOG_DIR=/logs \
    FDA_CONFIG_FILE=/app/plugins/fda-tools/config.toml \
    # Security settings
    PYTHONHASHSEED=random \
    # Performance tuning
    MALLOC_ARENA_MAX=2

# Switch to app directory
WORKDIR /app

# Copy application code
COPY --chown=fdatools:fdatools . /app/

# Create health check script
COPY --chown=fdatools:fdatools plugins/fda-tools/scripts/health_check.py /app/health_check.py

# Switch to non-root user
USER fdatools

# Expose health check port (if using HTTP server)
EXPOSE 8080

# Health check configuration
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python /app/health_check.py || exit 1

# Volume mount points for persistence
VOLUME ["/data", "/cache", "/logs"]

# Default entrypoint - can be overridden
ENTRYPOINT ["python"]

# Default command - can be overridden
CMD ["--help"]

# ============================================================================
# Usage examples:
# ============================================================================
# Build:
#   docker build -t fda-tools:5.36.0 .
#
# Run batchfetch:
#   docker run --rm -v $(pwd)/data:/data fda-tools:5.36.0 \
#     -m scripts.batchfetch --product-codes DQY --years 2024 --enrich
#
# Interactive shell:
#   docker run --rm -it -v $(pwd)/data:/data fda-tools:5.36.0 /bin/bash
#
# Run tests:
#   docker run --rm fda-tools:5.36.0 -m pytest /app/plugins/fda-tools/tests
# ============================================================================
