#!/bin/bash
# docker_run.sh - Run FDA Tools Docker container
#
# Usage:
#   ./scripts/docker_run.sh [OPTIONS] -- [COMMAND_ARGS]
#
# Options:
#   --version VERSION    Image version (default: latest)
#   --data-dir DIR       Host data directory (default: ./data)
#   --cache-dir DIR      Host cache directory (default: ./cache)
#   --log-dir DIR        Host log directory (default: ./logs)
#   --env-file FILE      Environment file (default: .env)
#   --interactive        Run interactive shell
#   --detach             Run in detached mode
#   --name NAME          Container name
#   --network NETWORK    Docker network
#   --help               Show this help message
#
# Examples:
#   # Run batchfetch
#   ./scripts/docker_run.sh -- -m scripts.batchfetch --product-codes DQY --years 2024
#
#   # Interactive shell
#   ./scripts/docker_run.sh --interactive
#
#   # Run tests
#   ./scripts/docker_run.sh -- -m pytest /app/plugins/fda-tools/tests

set -e

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Default values
VERSION="latest"
IMAGE_NAME="fda-tools"
DATA_DIR="${PROJECT_ROOT}/data"
CACHE_DIR="${PROJECT_ROOT}/cache"
LOG_DIR="${PROJECT_ROOT}/logs"
ENV_FILE="${PROJECT_ROOT}/.env"
INTERACTIVE=false
DETACH=false
CONTAINER_NAME=""
NETWORK=""
COMMAND_ARGS=()

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
    head -n 22 "$0" | tail -n +2 | sed 's/^# //' | sed 's/^#//'
    exit 0
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --version)
            VERSION="$2"
            shift 2
            ;;
        --data-dir)
            DATA_DIR="$2"
            shift 2
            ;;
        --cache-dir)
            CACHE_DIR="$2"
            shift 2
            ;;
        --log-dir)
            LOG_DIR="$2"
            shift 2
            ;;
        --env-file)
            ENV_FILE="$2"
            shift 2
            ;;
        --interactive)
            INTERACTIVE=true
            shift
            ;;
        --detach)
            DETACH=true
            shift
            ;;
        --name)
            CONTAINER_NAME="$2"
            shift 2
            ;;
        --network)
            NETWORK="$2"
            shift 2
            ;;
        --help|-h)
            show_help
            ;;
        --)
            shift
            COMMAND_ARGS=("$@")
            break
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            ;;
    esac
done

# Create directories if they don't exist
mkdir -p "${DATA_DIR}" "${CACHE_DIR}" "${LOG_DIR}"

# Check if image exists
if ! docker images "${IMAGE_NAME}:${VERSION}" --format "{{.Repository}}:{{.Tag}}" | grep -q "${IMAGE_NAME}:${VERSION}"; then
    log_warning "Image ${IMAGE_NAME}:${VERSION} not found locally"
    log_info "Building image..."
    "${SCRIPT_DIR}/docker_build.sh" --version "${VERSION}"
fi

# Build docker run command
DOCKER_CMD="docker run"

# Add cleanup flag (unless detached)
if [[ "$DETACH" == false ]]; then
    DOCKER_CMD="${DOCKER_CMD} --rm"
fi

# Add interactive flags
if [[ "$INTERACTIVE" == true ]]; then
    DOCKER_CMD="${DOCKER_CMD} -it"
fi

# Add detach flag
if [[ "$DETACH" == true ]]; then
    DOCKER_CMD="${DOCKER_CMD} -d"
fi

# Add container name
if [[ -n "$CONTAINER_NAME" ]]; then
    DOCKER_CMD="${DOCKER_CMD} --name ${CONTAINER_NAME}"
fi

# Add network
if [[ -n "$NETWORK" ]]; then
    DOCKER_CMD="${DOCKER_CMD} --network ${NETWORK}"
fi

# Add environment file
if [[ -f "$ENV_FILE" ]]; then
    DOCKER_CMD="${DOCKER_CMD} --env-file ${ENV_FILE}"
else
    log_warning "Environment file not found: ${ENV_FILE}"
fi

# Add volume mounts
DOCKER_CMD="${DOCKER_CMD} -v ${DATA_DIR}:/data"
DOCKER_CMD="${DOCKER_CMD} -v ${CACHE_DIR}:/cache"
DOCKER_CMD="${DOCKER_CMD} -v ${LOG_DIR}:/logs"

# Add image
DOCKER_CMD="${DOCKER_CMD} ${IMAGE_NAME}:${VERSION}"

# Add command or shell
if [[ "$INTERACTIVE" == true ]]; then
    DOCKER_CMD="${DOCKER_CMD} /bin/bash"
elif [[ ${#COMMAND_ARGS[@]} -gt 0 ]]; then
    DOCKER_CMD="${DOCKER_CMD} ${COMMAND_ARGS[*]}"
else
    DOCKER_CMD="${DOCKER_CMD} --help"
fi

# Print configuration
log_info "Run Configuration:"
echo "  Image: ${IMAGE_NAME}:${VERSION}"
echo "  Data Directory: ${DATA_DIR}"
echo "  Cache Directory: ${CACHE_DIR}"
echo "  Log Directory: ${LOG_DIR}"
echo "  Environment File: ${ENV_FILE}"
echo "  Interactive: ${INTERACTIVE}"
echo "  Detached: ${DETACH}"
if [[ -n "$CONTAINER_NAME" ]]; then
    echo "  Container Name: ${CONTAINER_NAME}"
fi
if [[ -n "$NETWORK" ]]; then
    echo "  Network: ${NETWORK}"
fi

# Run container
log_info "Running container..."
echo ""

if ${DOCKER_CMD}; then
    log_success "Container completed successfully"
    exit 0
else
    log_error "Container failed"
    exit 1
fi
