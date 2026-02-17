#!/bin/bash
# ============================================================
# FDA Bridge Server - Startup Script
#
# Starts the FastAPI bridge server on port 18790 with:
# - Security config validation
# - Virtual environment activation
# - Dependency checking
# - Graceful shutdown handling
#
# Usage:
#   ./start_bridge.sh              # Start with default settings
#   ./start_bridge.sh --no-reload  # Start without auto-reload
#   ./start_bridge.sh --port 8080  # Start on custom port
#
# Author: FDA Tools Development Team
# Date: 2026-02-16
# Version: 1.0.0
# ============================================================

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$PLUGIN_DIR/venv"
SECURITY_CONFIG="$HOME/.claude/fda-tools.security.toml"
DEFAULT_PORT=18790
DEFAULT_HOST="127.0.0.1"

# Parse arguments
RELOAD="--reload"
PORT="$DEFAULT_PORT"
HOST="$DEFAULT_HOST"
LOG_LEVEL="info"

while [[ $# -gt 0 ]]; do
    case $1 in
        --no-reload)
            RELOAD=""
            shift
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --host)
            HOST="$2"
            shift 2
            ;;
        --debug)
            LOG_LEVEL="debug"
            shift
            ;;
        --help)
            echo "FDA Bridge Server Startup Script"
            echo ""
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --no-reload    Disable auto-reload on file changes"
            echo "  --port PORT    Set server port (default: $DEFAULT_PORT)"
            echo "  --host HOST    Set server host (default: $DEFAULT_HOST)"
            echo "  --debug        Enable debug logging"
            echo "  --help         Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "============================================"
echo "  FDA Bridge Server v1.0.0"
echo "============================================"
echo ""

# Step 1: Check security config
echo "[1/5] Checking security configuration..."
if [ -f "$SECURITY_CONFIG" ]; then
    PERMS=$(stat -c "%a" "$SECURITY_CONFIG" 2>/dev/null || stat -f "%A" "$SECURITY_CONFIG" 2>/dev/null)
    if [ "$PERMS" = "444" ]; then
        echo "  Security config: OK ($SECURITY_CONFIG, mode 444)"
    else
        echo "  WARNING: Security config is not immutable (mode $PERMS, expected 444)"
        echo "  Run: chmod 444 $SECURITY_CONFIG"
        echo "  Server will start in permissive mode."
    fi
else
    echo "  WARNING: Security config not found: $SECURITY_CONFIG"
    echo "  Server will start in permissive mode (no security enforcement)."
    echo "  To enable security, create the config file."
fi

# Step 2: Activate virtual environment
echo "[2/5] Activating virtual environment..."
if [ -d "$VENV_DIR" ]; then
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
    echo "  Virtual environment: $VENV_DIR"
else
    echo "  WARNING: Virtual environment not found at $VENV_DIR"
    echo "  Using system Python. Some packages may be missing."
fi

# Step 3: Check dependencies
echo "[3/5] Checking dependencies..."
MISSING_DEPS=""

python3 -c "import fastapi" 2>/dev/null || MISSING_DEPS="$MISSING_DEPS fastapi"
python3 -c "import uvicorn" 2>/dev/null || MISSING_DEPS="$MISSING_DEPS uvicorn"
python3 -c "import pydantic" 2>/dev/null || MISSING_DEPS="$MISSING_DEPS pydantic"
python3 -c "import toml" 2>/dev/null || MISSING_DEPS="$MISSING_DEPS toml"
python3 -c "import requests" 2>/dev/null || MISSING_DEPS="$MISSING_DEPS requests"

if [ -n "$MISSING_DEPS" ]; then
    echo "  Missing packages:$MISSING_DEPS"
    echo "  Installing missing packages..."
    pip install $MISSING_DEPS 2>/dev/null || pip3 install $MISSING_DEPS
    echo "  Dependencies installed."
else
    echo "  All dependencies available."
fi

# Step 4: Create required directories
echo "[4/5] Setting up directories..."
mkdir -p "$HOME/.claude/sessions"
mkdir -p "$HOME/fda-510k-data"
mkdir -p "/tmp/fda-bridge"
echo "  Sessions: $HOME/.claude/sessions"
echo "  Data: $HOME/fda-510k-data"
echo "  Temp: /tmp/fda-bridge"

# Step 5: Start server
echo "[5/5] Starting server..."
echo ""
echo "  Host: $HOST"
echo "  Port: $PORT"
echo "  Reload: $([ -n "$RELOAD" ] && echo 'enabled' || echo 'disabled')"
echo "  Log level: $LOG_LEVEL"
echo ""
echo "  API docs: http://$HOST:$PORT/docs"
echo "  Health:   http://$HOST:$PORT/health"
echo ""
echo "  Press Ctrl+C to stop."
echo "============================================"
echo ""

cd "$SCRIPT_DIR"

# Trap SIGINT for graceful shutdown
trap 'echo ""; echo "Shutting down FDA Bridge Server..."; exit 0' INT TERM

python3 -m uvicorn server:app \
    --host "$HOST" \
    --port "$PORT" \
    --log-level "$LOG_LEVEL" \
    $RELOAD
