#!/bin/bash
# docker_build.sh - Build FDA Tools Docker image
#
# Usage:
#   ./scripts/docker_build.sh [OPTIONS]
#
# Options:
#   --version VERSION    Set image version (default: from pyproject.toml)
#   --tag TAG            Additional tag for image
#   --no-cache           Build without cache
#   --push               Push to registry after build
#   --registry URL       Registry URL (default: docker.io)
#   --platform PLATFORM  Target platform (default: linux/amd64)
#   --scan               Run security scan after build
#   --help               Show this help message

set -e

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Default values
VERSION=$(grep '^version = ' "${PROJECT_ROOT}/pyproject.toml" | cut -d'"' -f2)
IMAGE_NAME="fda-tools"
REGISTRY=""
ADDITIONAL_TAGS=()
NO_CACHE=""
PUSH=false
PLATFORM="linux/amd64"
SCAN=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Show help
show_help() {
    head -n 16 "$0" | tail -n +2 | sed 's/^# //' | sed 's/^#//'
    exit 0
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --version)
            VERSION="$2"
            shift 2
            ;;
        --tag)
            ADDITIONAL_TAGS+=("$2")
            shift 2
            ;;
        --no-cache)
            NO_CACHE="--no-cache"
            shift
            ;;
        --push)
            PUSH=true
            shift
            ;;
        --registry)
            REGISTRY="$2"
            shift 2
            ;;
        --platform)
            PLATFORM="$2"
            shift 2
            ;;
        --scan)
            SCAN=true
            shift
            ;;
        --help|-h)
            show_help
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            ;;
    esac
done

# Validation
if [[ -z "$VERSION" ]]; then
    log_error "Version not specified and could not be detected from pyproject.toml"
    exit 1
fi

# Build full image name
if [[ -n "$REGISTRY" ]]; then
    FULL_IMAGE_NAME="${REGISTRY}/${IMAGE_NAME}"
else
    FULL_IMAGE_NAME="${IMAGE_NAME}"
fi

# Print build configuration
log_info "Build Configuration:"
echo "  Project Root: ${PROJECT_ROOT}"
echo "  Image Name: ${FULL_IMAGE_NAME}"
echo "  Version: ${VERSION}"
echo "  Platform: ${PLATFORM}"
echo "  No Cache: ${NO_CACHE:-false}"
echo "  Push: ${PUSH}"
echo "  Scan: ${SCAN}"

if [[ ${#ADDITIONAL_TAGS[@]} -gt 0 ]]; then
    echo "  Additional Tags: ${ADDITIONAL_TAGS[*]}"
fi

# Check prerequisites
log_info "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    log_error "Docker is not installed"
    exit 1
fi

if [[ "$PUSH" == true ]] && [[ -z "$REGISTRY" ]]; then
    log_warning "Push enabled but no registry specified, using Docker Hub"
fi

if [[ "$SCAN" == true ]] && ! command -v trivy &> /dev/null; then
    log_warning "Trivy not found, security scan will be skipped"
    SCAN=false
fi

# Change to project root
cd "${PROJECT_ROOT}"

# Build image
log_info "Building Docker image..."

BUILD_CMD="docker build"
BUILD_CMD="${BUILD_CMD} ${NO_CACHE}"
BUILD_CMD="${BUILD_CMD} --platform ${PLATFORM}"
BUILD_CMD="${BUILD_CMD} --build-arg BUILDKIT_INLINE_CACHE=1"
BUILD_CMD="${BUILD_CMD} -t ${FULL_IMAGE_NAME}:${VERSION}"
BUILD_CMD="${BUILD_CMD} -t ${FULL_IMAGE_NAME}:latest"

# Add additional tags
for tag in "${ADDITIONAL_TAGS[@]}"; do
    BUILD_CMD="${BUILD_CMD} -t ${FULL_IMAGE_NAME}:${tag}"
done

BUILD_CMD="${BUILD_CMD} -f Dockerfile ."

log_info "Executing: ${BUILD_CMD}"

if ${BUILD_CMD}; then
    log_success "Image built successfully: ${FULL_IMAGE_NAME}:${VERSION}"
else
    log_error "Build failed"
    exit 1
fi

# Get image size
IMAGE_SIZE=$(docker images "${FULL_IMAGE_NAME}:${VERSION}" --format "{{.Size}}")
log_info "Image size: ${IMAGE_SIZE}"

# Check size warning (500MB threshold)
SIZE_MB=$(docker images "${FULL_IMAGE_NAME}:${VERSION}" --format "{{.Size}}" | sed 's/MB//' | sed 's/GB/*1024/' | bc 2>/dev/null || echo "0")
if (( $(echo "$SIZE_MB > 500" | bc -l 2>/dev/null || echo 0) )); then
    log_warning "Image size exceeds 500MB target: ${IMAGE_SIZE}"
fi

# Run security scan
if [[ "$SCAN" == true ]]; then
    log_info "Running security scan with Trivy..."

    if trivy image --severity HIGH,CRITICAL "${FULL_IMAGE_NAME}:${VERSION}"; then
        log_success "Security scan passed"
    else
        log_error "Security vulnerabilities found"
        exit 1
    fi
fi

# Test image
log_info "Testing image..."

if docker run --rm "${FULL_IMAGE_NAME}:${VERSION}" --version &> /dev/null; then
    log_success "Image test passed"
else
    log_warning "Image test failed (this might be expected if --version is not implemented)"
fi

# Run health check
log_info "Running health check..."

if docker run --rm "${FULL_IMAGE_NAME}:${VERSION}" /app/health_check.py --skip-network; then
    log_success "Health check passed"
else
    log_error "Health check failed"
    exit 1
fi

# Push to registry
if [[ "$PUSH" == true ]]; then
    log_info "Pushing image to registry..."

    # Push version tag
    if docker push "${FULL_IMAGE_NAME}:${VERSION}"; then
        log_success "Pushed ${FULL_IMAGE_NAME}:${VERSION}"
    else
        log_error "Failed to push ${FULL_IMAGE_NAME}:${VERSION}"
        exit 1
    fi

    # Push latest tag
    if docker push "${FULL_IMAGE_NAME}:latest"; then
        log_success "Pushed ${FULL_IMAGE_NAME}:latest"
    else
        log_error "Failed to push ${FULL_IMAGE_NAME}:latest"
        exit 1
    fi

    # Push additional tags
    for tag in "${ADDITIONAL_TAGS[@]}"; do
        if docker push "${FULL_IMAGE_NAME}:${tag}"; then
            log_success "Pushed ${FULL_IMAGE_NAME}:${tag}"
        else
            log_error "Failed to push ${FULL_IMAGE_NAME}:${tag}"
            exit 1
        fi
    done
fi

# Summary
log_success "Build completed successfully!"
echo ""
echo "Image Details:"
echo "  Name: ${FULL_IMAGE_NAME}"
echo "  Version: ${VERSION}"
echo "  Size: ${IMAGE_SIZE}"
echo "  Platform: ${PLATFORM}"
echo ""
echo "Available tags:"
echo "  - ${FULL_IMAGE_NAME}:${VERSION}"
echo "  - ${FULL_IMAGE_NAME}:latest"
for tag in "${ADDITIONAL_TAGS[@]}"; do
    echo "  - ${FULL_IMAGE_NAME}:${tag}"
done
echo ""
echo "Run with:"
echo "  docker run --rm ${FULL_IMAGE_NAME}:${VERSION} --help"
echo ""
echo "Or use docker-compose:"
echo "  docker-compose up -d"
