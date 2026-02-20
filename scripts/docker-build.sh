#!/usr/bin/env bash
# FDA Tools Docker Build Script
# Provides convenient build commands with validation and reporting
# Version: 5.36.0+docker

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Default values
ENVIRONMENT="${ENVIRONMENT:-production}"
PYTHON_VERSION="${PYTHON_VERSION:-3.11}"
ENABLE_OPTIONAL="${ENABLE_OPTIONAL_DEPS:-true}"
NO_CACHE="${NO_CACHE:-false}"
PUSH="${PUSH:-false}"
TAG="${TAG:-5.36.0}"

# Functions
print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}FDA Tools Docker Build${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    print_info "Checking prerequisites..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    # Check Docker version
    DOCKER_VERSION=$(docker --version | grep -oP '\d+\.\d+\.\d+' | head -1)
    print_info "Docker version: ${DOCKER_VERSION}"

    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running. Please start Docker."
        exit 1
    fi

    # Check disk space (need at least 5GB)
    AVAILABLE_SPACE=$(df -BG "${PROJECT_ROOT}" | awk 'NR==2 {print $4}' | sed 's/G//')
    if [ "${AVAILABLE_SPACE}" -lt 5 ]; then
        print_warning "Low disk space: ${AVAILABLE_SPACE}GB available. Recommend at least 5GB."
    fi

    print_success "Prerequisites check passed"
}

show_build_info() {
    echo ""
    print_info "Build Configuration:"
    echo "  Environment:      ${ENVIRONMENT}"
    echo "  Python Version:   ${PYTHON_VERSION}"
    echo "  Optional Deps:    ${ENABLE_OPTIONAL}"
    echo "  Tag:              fda-tools:${TAG}"
    echo "  No Cache:         ${NO_CACHE}"
    echo "  Push:             ${PUSH}"
    echo ""
}

build_image() {
    print_info "Building Docker image..."

    BUILD_ARGS=(
        --build-arg "ENVIRONMENT=${ENVIRONMENT}"
        --build-arg "PYTHON_VERSION=${PYTHON_VERSION}"
        --build-arg "ENABLE_OPTIONAL_DEPS=${ENABLE_OPTIONAL}"
        --tag "fda-tools:${TAG}"
        --tag "fda-tools:latest"
    )

    if [ "${NO_CACHE}" = "true" ]; then
        BUILD_ARGS+=(--no-cache)
    fi

    # Build
    if docker build "${BUILD_ARGS[@]}" "${PROJECT_ROOT}"; then
        print_success "Image built successfully: fda-tools:${TAG}"
        return 0
    else
        print_error "Image build failed"
        return 1
    fi
}

scan_image() {
    print_info "Scanning image for vulnerabilities..."

    if command -v trivy &> /dev/null; then
        trivy image "fda-tools:${TAG}" || print_warning "Trivy scan found issues"
    elif command -v docker &> /dev/null && docker scan --help &> /dev/null; then
        docker scan "fda-tools:${TAG}" || print_warning "Docker scan found issues"
    else
        print_warning "No security scanner found (install trivy or enable docker scan)"
    fi
}

test_image() {
    print_info "Testing image..."

    # Test health check
    if docker run --rm "fda-tools:${TAG}" health --verbose; then
        print_success "Health check passed"
    else
        print_error "Health check failed"
        return 1
    fi

    # Test import
    if docker run --rm "fda-tools:${TAG}" -c "import sys; sys.path.insert(0, '/app'); from lib import config; print('Import test: OK')"; then
        print_success "Import test passed"
    else
        print_error "Import test failed"
        return 1
    fi
}

show_image_info() {
    print_info "Image Information:"

    # Size
    SIZE=$(docker images "fda-tools:${TAG}" --format "{{.Size}}")
    echo "  Size: ${SIZE}"

    # Created
    CREATED=$(docker images "fda-tools:${TAG}" --format "{{.CreatedAt}}")
    echo "  Created: ${CREATED}"

    # Layers
    LAYERS=$(docker history "fda-tools:${TAG}" | wc -l)
    echo "  Layers: ${LAYERS}"

    # Check size threshold
    SIZE_MB=$(docker images "fda-tools:${TAG}" --format "{{.Size}}" | sed 's/MB//' | sed 's/GB/*1024/')
    if [ "${SIZE_MB%%.*}" -gt 500 ] 2>/dev/null; then
        print_warning "Image size is larger than 500MB. Consider optimizing."
    fi
}

push_image() {
    if [ "${PUSH}" = "true" ]; then
        print_info "Pushing image to registry..."

        if [ -n "${REGISTRY:-}" ]; then
            docker tag "fda-tools:${TAG}" "${REGISTRY}/fda-tools:${TAG}"
            docker push "${REGISTRY}/fda-tools:${TAG}"
            print_success "Image pushed to ${REGISTRY}"
        else
            print_warning "REGISTRY not set. Skipping push."
        fi
    fi
}

cleanup_old_images() {
    print_info "Cleaning up old images..."

    # Remove dangling images
    DANGLING=$(docker images -f "dangling=true" -q | wc -l)
    if [ "${DANGLING}" -gt 0 ]; then
        docker image prune -f
        print_success "Removed ${DANGLING} dangling images"
    else
        print_info "No dangling images to clean"
    fi
}

show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Build FDA Tools Docker image with validation and testing.

OPTIONS:
    -e, --environment ENV       Set environment (development|testing|staging|production) [default: production]
    -p, --python VERSION        Set Python version [default: 3.11]
    -o, --optional BOOL         Enable optional dependencies (true|false) [default: true]
    -t, --tag TAG               Set image tag [default: 5.36.0]
    -n, --no-cache              Build without cache
    -s, --scan                  Run security scan after build
    -T, --test                  Run tests after build
    -P, --push                  Push to registry (requires REGISTRY env var)
    -c, --clean                 Clean up old images
    -h, --help                  Show this help message

EXAMPLES:
    # Standard production build
    $0

    # Development build with testing
    $0 --environment development --test

    # Build without cache and scan
    $0 --no-cache --scan

    # Build minimal image
    $0 --optional false --tag minimal

    # Build and push
    $0 --push

ENVIRONMENT VARIABLES:
    ENVIRONMENT              Build environment
    PYTHON_VERSION           Python version
    ENABLE_OPTIONAL_DEPS     Enable optional dependencies
    NO_CACHE                 Build without cache
    PUSH                     Push to registry
    TAG                      Image tag
    REGISTRY                 Docker registry URL

EOF
}

# Parse command line arguments
RUN_SCAN=false
RUN_TEST=false
RUN_CLEAN=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -p|--python)
            PYTHON_VERSION="$2"
            shift 2
            ;;
        -o|--optional)
            ENABLE_OPTIONAL="$2"
            shift 2
            ;;
        -t|--tag)
            TAG="$2"
            shift 2
            ;;
        -n|--no-cache)
            NO_CACHE=true
            shift
            ;;
        -s|--scan)
            RUN_SCAN=true
            shift
            ;;
        -T|--test)
            RUN_TEST=true
            shift
            ;;
        -P|--push)
            PUSH=true
            shift
            ;;
        -c|--clean)
            RUN_CLEAN=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Main execution
main() {
    print_header
    check_prerequisites
    show_build_info

    # Change to project root
    cd "${PROJECT_ROOT}"

    # Build
    if ! build_image; then
        exit 1
    fi

    # Show info
    show_image_info

    # Optional: Security scan
    if [ "${RUN_SCAN}" = "true" ]; then
        scan_image
    fi

    # Optional: Run tests
    if [ "${RUN_TEST}" = "true" ]; then
        if ! test_image; then
            exit 1
        fi
    fi

    # Optional: Push
    push_image

    # Optional: Clean
    if [ "${RUN_CLEAN}" = "true" ]; then
        cleanup_old_images
    fi

    echo ""
    print_success "Build complete!"
    echo ""
    print_info "Next steps:"
    echo "  - Run container: docker run --rm -it fda-tools:${TAG} shell"
    echo "  - Start services: docker compose up -d"
    echo "  - Run tests: docker run --rm fda-tools:${TAG} test -v"
    echo "  - Security scan: docker scan fda-tools:${TAG}"
    echo ""
}

# Run main
main
