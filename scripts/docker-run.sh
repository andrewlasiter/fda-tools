#!/usr/bin/env bash
# FDA Tools Docker Run Script
# Convenient wrapper for running FDA Tools commands in Docker
# Version: 5.36.0+docker

set -euo pipefail

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Defaults
IMAGE="${FDA_IMAGE:-fda-tools:5.36.0}"
COMPOSE_FILE="docker-compose.yml"
DATA_DIR="${FDA_PROJECTS_DIR:-$(pwd)/projects}"

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

show_usage() {
    cat << EOF
Usage: $0 COMMAND [OPTIONS]

Run FDA Tools commands in Docker container.

COMMANDS:
    shell               Interactive bash shell
    health              Run health check
    test [ARGS]         Run test suite
    batchfetch [ARGS]   Run batchfetch script
    bridge              Start bridge server
    python [ARGS]       Run Python interpreter
    exec [CMD]          Execute arbitrary command

    compose [CMD]       Docker compose wrapper
    up                  Start services
    down                Stop services
    logs [SERVICE]      View logs
    ps                  List containers

OPTIONS:
    -i, --image IMAGE       Docker image to use [default: fda-tools:5.36.0]
    -d, --data-dir DIR      Host data directory [default: ./projects]
    -e, --env FILE          Environment file [default: .env]
    -v, --verbose           Verbose output
    -h, --help              Show this help

EXAMPLES:
    # Interactive shell
    $0 shell

    # Run health check
    $0 health --verbose

    # Run tests
    $0 test -v -k test_batchfetch

    # Run batchfetch
    $0 batchfetch --product-codes DQY --years 2024 --enrich

    # Start services
    $0 up

    # View logs
    $0 logs fda-tools

    # Execute Python
    $0 python -c "import lib.config; print('OK')"

ENVIRONMENT VARIABLES:
    FDA_IMAGE           Docker image name
    FDA_PROJECTS_DIR    Host projects directory
    COMPOSE_FILE        Docker compose file

EOF
}

run_shell() {
    print_info "Starting interactive shell..."
    docker run --rm -it \
        -v "${DATA_DIR}:/projects" \
        -e PYTHONUNBUFFERED=1 \
        "${IMAGE}" shell
}

run_health_check() {
    print_info "Running health check..."
    docker run --rm \
        "${IMAGE}" health "$@"
}

run_tests() {
    print_info "Running tests..."
    docker run --rm \
        -e PYTHONUNBUFFERED=1 \
        "${IMAGE}" test "$@"
}

run_batchfetch() {
    print_info "Running batchfetch..."
    docker run --rm \
        -v "${DATA_DIR}:/projects" \
        -v "$(pwd)/data:/data" \
        -e PYTHONUNBUFFERED=1 \
        "${IMAGE}" \
        -m scripts.batchfetch "$@"
}

run_bridge() {
    print_info "Starting bridge server..."
    docker run --rm -it \
        -p 18790:18790 \
        -v "${DATA_DIR}:/projects:ro" \
        -e PYTHONUNBUFFERED=1 \
        "${IMAGE}" bridge "$@"
}

run_python() {
    docker run --rm -it \
        -v "${DATA_DIR}:/projects" \
        -e PYTHONUNBUFFERED=1 \
        "${IMAGE}" python "$@"
}

run_exec() {
    docker run --rm -it \
        -v "${DATA_DIR}:/projects" \
        -e PYTHONUNBUFFERED=1 \
        "${IMAGE}" "$@"
}

compose_up() {
    print_info "Starting services..."
    docker compose up -d "$@"
    print_success "Services started"
    docker compose ps
}

compose_down() {
    print_info "Stopping services..."
    docker compose down "$@"
    print_success "Services stopped"
}

compose_logs() {
    docker compose logs -f "$@"
}

compose_ps() {
    docker compose ps
}

compose_exec() {
    docker compose "$@"
}

# Parse arguments
COMMAND="${1:-help}"
shift || true

case "${COMMAND}" in
    shell)
        run_shell "$@"
        ;;
    health)
        run_health_check "$@"
        ;;
    test)
        run_tests "$@"
        ;;
    batchfetch)
        run_batchfetch "$@"
        ;;
    bridge)
        run_bridge "$@"
        ;;
    python)
        run_python "$@"
        ;;
    exec)
        run_exec "$@"
        ;;
    compose)
        compose_exec "$@"
        ;;
    up)
        compose_up "$@"
        ;;
    down)
        compose_down "$@"
        ;;
    logs)
        compose_logs "$@"
        ;;
    ps)
        compose_ps
        ;;
    help|--help|-h)
        show_usage
        ;;
    *)
        print_error "Unknown command: ${COMMAND}"
        echo ""
        show_usage
        exit 1
        ;;
esac
