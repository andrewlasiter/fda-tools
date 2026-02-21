#!/usr/bin/env bash
# FDA Tools - Docker Compose Deploy Script
# Manages deployment of the full FDA Tools stack
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$ROOT_DIR/docker-compose.yml"

usage() {
    cat <<EOF
Usage: $(basename "$0") COMMAND [OPTIONS]

Deploy FDA Tools stack with Docker Compose.

Commands:
  up        Start all services (postgres + bridge server)
  down      Stop all services
  restart   Restart all services
  logs      Show service logs
  status    Show service status
  health    Check bridge server health

Options:
  --bridge-only   Only start bridge server (no postgres)
  --db-only       Only start database services
  --follow        Follow log output (with logs command)
  -h, --help      Show this help message

Environment variables (set in .env file):
  DB_PASSWORD           PostgreSQL password (default: changeme)
  FDA_BRIDGE_API_KEY    Bridge server API key (required for /metrics)
  FDA_BRIDGE_PORT       Bridge server port (default: 18790)
  LOG_LEVEL             Log level: debug|info|warning|error (default: info)

Examples:
  $(basename "$0") up                # Start everything
  $(basename "$0") up --db-only      # Start only PostgreSQL
  $(basename "$0") down              # Stop everything
  $(basename "$0") logs --follow     # Stream logs
  $(basename "$0") health            # Check bridge health
EOF
}

COMMAND="${1:-help}"
shift || true

BRIDGE_ONLY="false"
DB_ONLY="false"
FOLLOW="false"

while [[ $# -gt 0 ]]; do
    case $1 in
        --bridge-only) BRIDGE_ONLY="true"; shift ;;
        --db-only) DB_ONLY="true"; shift ;;
        --follow) FOLLOW="true"; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $1"; usage; exit 1 ;;
    esac
done

cd "$ROOT_DIR"

# Build service list based on flags
SERVICES=()
if [[ "$BRIDGE_ONLY" == "true" ]]; then
    SERVICES=("bridge-server")
elif [[ "$DB_ONLY" == "true" ]]; then
    SERVICES=("postgres-blue" "pgbouncer")
fi

case "$COMMAND" in
    up)
        echo "Starting FDA Tools stack..."
        docker compose -f "$COMPOSE_FILE" up -d "${SERVICES[@]}"
        echo ""
        echo "Services started. Check status with: $(basename "$0") status"
        ;;
    down)
        echo "Stopping FDA Tools stack..."
        docker compose -f "$COMPOSE_FILE" down
        echo "Services stopped."
        ;;
    restart)
        echo "Restarting FDA Tools stack..."
        docker compose -f "$COMPOSE_FILE" restart "${SERVICES[@]}"
        echo "Services restarted."
        ;;
    logs)
        if [[ "$FOLLOW" == "true" ]]; then
            docker compose -f "$COMPOSE_FILE" logs -f "${SERVICES[@]}"
        else
            docker compose -f "$COMPOSE_FILE" logs --tail=100 "${SERVICES[@]}"
        fi
        ;;
    status)
        docker compose -f "$COMPOSE_FILE" ps
        ;;
    health)
        PORT="${FDA_BRIDGE_PORT:-18790}"
        echo "Checking bridge server health at http://localhost:${PORT}/health ..."
        curl -sf "http://localhost:${PORT}/health" | python3 -m json.tool || {
            echo "Health check failed - bridge server may not be running"
            exit 1
        }
        ;;
    help|-h|--help)
        usage
        ;;
    *)
        echo "Unknown command: $COMMAND"
        usage
        exit 1
        ;;
esac
