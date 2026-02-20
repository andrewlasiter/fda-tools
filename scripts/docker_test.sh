#!/bin/bash
# docker_test.sh - Run FDA Tools tests in Docker container
#
# Usage:
#   ./scripts/docker_test.sh [OPTIONS]
#
# Options:
#   --version VERSION    Image version (default: latest)
#   --test-path PATH     Test path to run (default: all tests)
#   --coverage           Run with coverage report
#   --markers MARKERS    Pytest markers to select (e.g., "not slow")
#   --verbose            Verbose output
#   --parallel           Run tests in parallel
#   --keep-container     Keep container after tests (for debugging)
#   --help               Show this help message
#
# Examples:
#   # Run all tests
#   ./scripts/docker_test.sh
#
#   # Run specific test file
#   ./scripts/docker_test.sh --test-path tests/test_config.py
#
#   # Run with coverage
#   ./scripts/docker_test.sh --coverage
#
#   # Run only fast tests
#   ./scripts/docker_test.sh --markers "not slow"

set -e

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Default values
VERSION="latest"
IMAGE_NAME="fda-tools"
TEST_PATH="/app/plugins/fda-tools/tests"
COVERAGE=false
MARKERS=""
VERBOSE=false
PARALLEL=false
KEEP_CONTAINER=false
PYTEST_ARGS=()

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
    head -n 24 "$0" | tail -n +2 | sed 's/^# //' | sed 's/^#//'
    exit 0
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --version)
            VERSION="$2"
            shift 2
            ;;
        --test-path)
            TEST_PATH="$2"
            shift 2
            ;;
        --coverage)
            COVERAGE=true
            shift
            ;;
        --markers|-m)
            MARKERS="$2"
            shift 2
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --parallel)
            PARALLEL=true
            shift
            ;;
        --keep-container)
            KEEP_CONTAINER=true
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

# Build pytest arguments
PYTEST_CMD="pytest ${TEST_PATH}"

if [[ "$VERBOSE" == true ]]; then
    PYTEST_CMD="${PYTEST_CMD} -v"
fi

if [[ -n "$MARKERS" ]]; then
    PYTEST_CMD="${PYTEST_CMD} -m '${MARKERS}'"
fi

if [[ "$COVERAGE" == true ]]; then
    PYTEST_CMD="${PYTEST_CMD} --cov=lib --cov=scripts --cov-report=term-missing --cov-report=html:/data/htmlcov"
fi

if [[ "$PARALLEL" == true ]]; then
    PYTEST_CMD="${PYTEST_CMD} -n auto"
fi

# Add standard pytest options
PYTEST_CMD="${PYTEST_CMD} --tb=short --strict-markers"

# Print configuration
log_info "Test Configuration:"
echo "  Image: ${IMAGE_NAME}:${VERSION}"
echo "  Test Path: ${TEST_PATH}"
echo "  Coverage: ${COVERAGE}"
echo "  Markers: ${MARKERS:-none}"
echo "  Verbose: ${VERBOSE}"
echo "  Parallel: ${PARALLEL}"
echo "  Keep Container: ${KEEP_CONTAINER}"
echo ""

# Check if image exists
if ! docker images "${IMAGE_NAME}:${VERSION}" --format "{{.Repository}}:{{.Tag}}" | grep -q "${IMAGE_NAME}:${VERSION}"; then
    log_warning "Image ${IMAGE_NAME}:${VERSION} not found locally"
    log_info "Building image..."
    "${SCRIPT_DIR}/docker_build.sh" --version "${VERSION}"
fi

# Create output directory for coverage reports
OUTPUT_DIR="${PROJECT_ROOT}/test-output"
mkdir -p "${OUTPUT_DIR}"

# Build docker run command
DOCKER_CMD="docker run"

if [[ "$KEEP_CONTAINER" == false ]]; then
    DOCKER_CMD="${DOCKER_CMD} --rm"
fi

# Add volumes
DOCKER_CMD="${DOCKER_CMD} -v ${OUTPUT_DIR}:/data"

# Add environment variables for testing
DOCKER_CMD="${DOCKER_CMD} -e PYTHONDONTWRITEBYTECODE=1"
DOCKER_CMD="${DOCKER_CMD} -e PYTEST_CURRENT_TEST="

# Add image
DOCKER_CMD="${DOCKER_CMD} ${IMAGE_NAME}:${VERSION}"

# Add pytest command
DOCKER_CMD="${DOCKER_CMD} -m ${PYTEST_CMD}"

# Run tests
log_info "Running tests..."
echo ""

START_TIME=$(date +%s)

if ${DOCKER_CMD}; then
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))

    echo ""
    log_success "All tests passed! (${DURATION}s)"

    if [[ "$COVERAGE" == true ]]; then
        log_info "Coverage report saved to: ${OUTPUT_DIR}/htmlcov/index.html"
    fi

    exit 0
else
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))

    echo ""
    log_error "Tests failed! (${DURATION}s)"

    if [[ "$KEEP_CONTAINER" == true ]]; then
        log_info "Container kept for debugging"
    fi

    exit 1
fi
