#!/usr/bin/env bash
# FDA Tools - Docker Run Script
# Runs FDA Tools container with common configurations
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

IMAGE_NAME="${FDA_IMAGE_NAME:-fda-tools}"
VERSION="${FDA_VERSION:-latest}"
DATA_DIR="${FDA_DATA_DIR:-$HOME/fda-data}"
PORT="${FDA_BRIDGE_PORT:-18790}"

usage() {
    cat <<EOF
Usage: $(basename "$0") COMMAND [OPTIONS]

Run FDA Tools Docker container.

Commands:
  bridge    Start the bridge server (foreground)
  test      Run the test suite
  shell     Open an interactive shell
  run CMD   Run an arbitrary python command

Options:
  -v, --version VERSION     Image version (default: latest)
  -d, --data-dir DIR        Host data directory to mount (default: ~/fda-data)
  -p, --port PORT           Bridge server port (default: 18790)
  --api-key KEY             FDA Bridge API key (or set FDA_BRIDGE_API_KEY env var)
  -h, --help                Show this help message

Examples:
  $(basename "$0") bridge                           # Start bridge server
  $(basename "$0") bridge --port 9090               # Bridge on custom port
  $(basename "$0") test -v                          # Run tests verbosely
  $(basename "$0") shell                            # Interactive shell
  $(basename "$0") run -m fda_tools.scripts.batchfetch --help
EOF
}

# Parse global options before command
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--version) VERSION="$2"; shift 2 ;;
        -d|--data-dir) DATA_DIR="$2"; shift 2 ;;
        -p|--port) PORT="$2"; shift 2 ;;
        --api-key) FDA_BRIDGE_API_KEY="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        bridge|test|shell|run) COMMAND="$1"; shift; break ;;
        *) echo "Unknown option or command: $1"; usage; exit 1 ;;
    esac
done

COMMAND="${COMMAND:-shell}"
ARGS=("$@")

# Ensure data directory exists
mkdir -p "$DATA_DIR"/{data,cache,logs}

# Build docker run args
DOCKER_ARGS=(
    "--rm"
    "--volume" "${DATA_DIR}/data:/data"
    "--volume" "${DATA_DIR}/cache:/cache"
    "--volume" "${DATA_DIR}/logs:/logs"
    "--env" "FDA_DATA_DIR=/data"
    "--env" "FDA_CACHE_DIR=/cache"
    "--env" "FDA_LOG_DIR=/logs"
)

if [[ "$COMMAND" == "bridge" ]]; then
    DOCKER_ARGS+=("--detach" "--name" "fda-bridge")
    DOCKER_ARGS+=("--publish" "${PORT}:18790")
    DOCKER_ARGS+=("--env" "FDA_BRIDGE_API_KEY=${FDA_BRIDGE_API_KEY:-}")
    echo "Starting bridge server on port $PORT..."
elif [[ "$COMMAND" == "shell" ]]; then
    DOCKER_ARGS+=("--interactive" "--tty")
fi

docker run "${DOCKER_ARGS[@]}" "${IMAGE_NAME}:${VERSION}" "$COMMAND" "${ARGS[@]}"

if [[ "$COMMAND" == "bridge" ]]; then
    echo "Bridge server running at http://localhost:${PORT}"
    echo "Health: http://localhost:${PORT}/health"
    echo "Stop: docker stop fda-bridge"
fi
