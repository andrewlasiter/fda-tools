#!/bin/bash
# FDA Tools Health Check Script (FDA-91)
#
# Verifies connectivity and configuration of all FDA Tools components:
#   1. Skills directory and agent registry
#   2. Python dependencies
#   3. ClinicalTrials.gov API connectivity
#   4. openFDA API connectivity
#   5. Bridge server status
#   6. Data directory and disk space
#
# Usage:
#   bash health_check.sh
#   bash health_check.sh --verbose
#
# Exit codes:
#   0 = All checks passed
#   1 = One or more checks failed

set -euo pipefail

# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------

PLUGIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SKILLS_DIR="${PLUGIN_ROOT}/skills"
SCRIPTS_DIR="${PLUGIN_ROOT}/scripts"
BRIDGE_DIR="${PLUGIN_ROOT}/bridge"
DATA_DIR="${HOME}/fda-510k-data"
BRIDGE_PORT="${FDA_BRIDGE_PORT:-18790}"

VERBOSE=false
if [[ "${1:-}" == "--verbose" || "${1:-}" == "-v" ]]; then
    VERBOSE=true
fi

PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

pass_check() {
    echo "  [PASS] $1"
    PASS_COUNT=$((PASS_COUNT + 1))
}

fail_check() {
    echo "  [FAIL] $1"
    FAIL_COUNT=$((FAIL_COUNT + 1))
}

warn_check() {
    echo "  [WARN] $1"
    WARN_COUNT=$((WARN_COUNT + 1))
}

info() {
    if $VERBOSE; then
        echo "        $1"
    fi
}

# -------------------------------------------------------------------
# Header
# -------------------------------------------------------------------

echo "============================================="
echo "  FDA Tools Health Check"
echo "  $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "============================================="
echo ""

# -------------------------------------------------------------------
# 1. Skills Directory and Agent Registry
# -------------------------------------------------------------------

echo "[1/6] Agent Registry"

if [ -d "$SKILLS_DIR" ]; then
    AGENT_COUNT=$(find "$SKILLS_DIR" -mindepth 1 -maxdepth 1 -type d ! -name ".*" | wc -l)
    pass_check "Skills directory exists: ${SKILLS_DIR}"
    info "Agent directories found: ${AGENT_COUNT}"

    if [ "$AGENT_COUNT" -ge 10 ]; then
        pass_check "Agent count: ${AGENT_COUNT} (expected >= 10)"
    else
        warn_check "Agent count: ${AGENT_COUNT} (expected >= 10, may be incomplete)"
    fi

    # Check for SKILL.md in each agent directory
    SKILL_MD_COUNT=0
    MISSING_SKILL_MD=""
    for agent_dir in "$SKILLS_DIR"/*/; do
        if [ -f "${agent_dir}SKILL.md" ]; then
            SKILL_MD_COUNT=$((SKILL_MD_COUNT + 1))
        else
            dirname=$(basename "$agent_dir")
            MISSING_SKILL_MD="${MISSING_SKILL_MD} ${dirname}"
        fi
    done

    if [ -z "$MISSING_SKILL_MD" ]; then
        pass_check "All agents have SKILL.md (${SKILL_MD_COUNT}/${AGENT_COUNT})"
    else
        warn_check "Missing SKILL.md in:${MISSING_SKILL_MD}"
    fi

    # Check for agent.yaml files
    YAML_COUNT=$(find "$SKILLS_DIR" -name "agent.yaml" | wc -l)
    info "agent.yaml files found: ${YAML_COUNT}"
else
    fail_check "Skills directory not found: ${SKILLS_DIR}"
fi

echo ""

# -------------------------------------------------------------------
# 2. Python Dependencies
# -------------------------------------------------------------------

echo "[2/6] Python Dependencies"

if command -v python3 &>/dev/null; then
    PY_VERSION=$(python3 --version 2>&1)
    pass_check "Python3 available: ${PY_VERSION}"
else
    fail_check "python3 not found in PATH"
fi

# Check critical imports
DEPS=("requests" "json" "urllib.request")
for dep in "${DEPS[@]}"; do
    if python3 -c "import ${dep}" 2>/dev/null; then
        pass_check "Module available: ${dep}"
    else
        fail_check "Module missing: ${dep}"
    fi
done

# Check tenacity (retry logic - FDA-89)
if python3 -c "import tenacity" 2>/dev/null; then
    TENACITY_VER=$(python3 -c "import tenacity; print(tenacity.__version__)" 2>/dev/null || echo "unknown")
    pass_check "tenacity available: v${TENACITY_VER} (retry logic enabled)"
else
    warn_check "tenacity not installed (retry logic disabled, install with: pip install tenacity>=8.0.0)"
fi

# Check optional bridge dependencies
if python3 -c "import fastapi, uvicorn" 2>/dev/null; then
    pass_check "Bridge server dependencies available (fastapi, uvicorn)"
else
    warn_check "Bridge server dependencies missing (fastapi, uvicorn)"
fi

echo ""

# -------------------------------------------------------------------
# 3. ClinicalTrials.gov API Connectivity
# -------------------------------------------------------------------

echo "[3/6] ClinicalTrials.gov API"

if command -v curl &>/dev/null; then
    CT_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
        --connect-timeout 10 --max-time 15 \
        "https://clinicaltrials.gov/api/v2/studies?pageSize=1&format=json" 2>/dev/null || echo "000")

    if [ "$CT_RESPONSE" = "200" ]; then
        pass_check "ClinicalTrials.gov API: HTTP ${CT_RESPONSE}"
    elif [ "$CT_RESPONSE" = "429" ]; then
        warn_check "ClinicalTrials.gov API: HTTP ${CT_RESPONSE} (rate limited -- retry logic will handle this)"
    elif [ "$CT_RESPONSE" = "000" ]; then
        fail_check "ClinicalTrials.gov API: Connection failed (timeout or DNS error)"
    else
        fail_check "ClinicalTrials.gov API: HTTP ${CT_RESPONSE}"
    fi

    # Measure response time
    if $VERBOSE; then
        CT_TIME=$(curl -s -o /dev/null -w "%{time_total}" \
            --connect-timeout 10 --max-time 15 \
            "https://clinicaltrials.gov/api/v2/studies?pageSize=1&format=json" 2>/dev/null || echo "timeout")
        info "Response time: ${CT_TIME}s"
    fi
else
    warn_check "curl not available -- cannot test API connectivity"
fi

echo ""

# -------------------------------------------------------------------
# 4. openFDA API Connectivity
# -------------------------------------------------------------------

echo "[4/6] openFDA API"

if command -v curl &>/dev/null; then
    FDA_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
        --connect-timeout 10 --max-time 15 \
        "https://api.fda.gov/device/510k.json?limit=1" 2>/dev/null || echo "000")

    if [ "$FDA_RESPONSE" = "200" ]; then
        pass_check "openFDA API: HTTP ${FDA_RESPONSE}"
    elif [ "$FDA_RESPONSE" = "429" ]; then
        warn_check "openFDA API: HTTP ${FDA_RESPONSE} (rate limited)"
    elif [ "$FDA_RESPONSE" = "000" ]; then
        fail_check "openFDA API: Connection failed (timeout or DNS error)"
    else
        fail_check "openFDA API: HTTP ${FDA_RESPONSE}"
    fi

    # Check API key
    if [ -n "${FDA_API_KEY:-}" ]; then
        pass_check "FDA API key configured (higher rate limits)"
    else
        warn_check "FDA API key not set (using anonymous rate limits: 240 req/min)"
        info "Get a free key at: https://open.fda.gov/apis/authentication/"
    fi
else
    warn_check "curl not available -- cannot test API connectivity"
fi

echo ""

# -------------------------------------------------------------------
# 5. Bridge Server Status
# -------------------------------------------------------------------

echo "[5/6] Bridge Server"

if command -v curl &>/dev/null; then
    BRIDGE_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
        --connect-timeout 3 --max-time 5 \
        "http://127.0.0.1:${BRIDGE_PORT}/health" 2>/dev/null || echo "000")

    if [ "$BRIDGE_RESPONSE" = "200" ]; then
        pass_check "Bridge server: HTTP ${BRIDGE_RESPONSE} on port ${BRIDGE_PORT}"
        if $VERBOSE; then
            HEALTH_JSON=$(curl -s --connect-timeout 3 --max-time 5 \
                "http://127.0.0.1:${BRIDGE_PORT}/health" 2>/dev/null || echo "{}")
            info "Health response: ${HEALTH_JSON}"
        fi
    elif [ "$BRIDGE_RESPONSE" = "000" ]; then
        warn_check "Bridge server: Not running on port ${BRIDGE_PORT} (optional component)"
        info "Start with: python3 ${BRIDGE_DIR}/server.py"
    else
        warn_check "Bridge server: HTTP ${BRIDGE_RESPONSE} on port ${BRIDGE_PORT}"
    fi
else
    warn_check "curl not available -- cannot test bridge server"
fi

echo ""

# -------------------------------------------------------------------
# 6. Data Directory and Disk Space
# -------------------------------------------------------------------

echo "[6/6] Data Directory"

if [ -d "$DATA_DIR" ]; then
    pass_check "Data directory exists: ${DATA_DIR}"

    # Check subdirectories
    for subdir in "projects" "downloads" "extraction"; do
        if [ -d "${DATA_DIR}/${subdir}" ]; then
            COUNT=$(find "${DATA_DIR}/${subdir}" -maxdepth 1 -mindepth 1 | wc -l)
            info "${subdir}/: ${COUNT} items"
        fi
    done

    # Check disk space
    AVAIL_KB=$(df -k "$DATA_DIR" | tail -1 | awk '{print $4}')
    AVAIL_MB=$((AVAIL_KB / 1024))
    AVAIL_GB=$((AVAIL_MB / 1024))

    if [ "$AVAIL_MB" -ge 2048 ]; then
        pass_check "Disk space: ${AVAIL_GB} GB available (>= 2 GB required)"
    elif [ "$AVAIL_MB" -ge 512 ]; then
        warn_check "Disk space: ${AVAIL_MB} MB available (low -- 2 GB recommended)"
    else
        fail_check "Disk space: ${AVAIL_MB} MB available (critically low)"
    fi

    # Check directory permissions
    if [ -w "$DATA_DIR" ]; then
        pass_check "Data directory is writable"
    else
        fail_check "Data directory is NOT writable: ${DATA_DIR}"
    fi
else
    warn_check "Data directory not found: ${DATA_DIR}"
    info "Create with: mkdir -p ${DATA_DIR}/projects"
fi

echo ""

# -------------------------------------------------------------------
# Summary
# -------------------------------------------------------------------

echo "============================================="
TOTAL=$((PASS_COUNT + FAIL_COUNT + WARN_COUNT))
echo "  Results: ${PASS_COUNT} passed, ${FAIL_COUNT} failed, ${WARN_COUNT} warnings (${TOTAL} total)"

if [ "$FAIL_COUNT" -eq 0 ] && [ "$WARN_COUNT" -eq 0 ]; then
    echo "  Status: ALL CHECKS PASSED"
elif [ "$FAIL_COUNT" -eq 0 ]; then
    echo "  Status: PASSED WITH WARNINGS"
else
    echo "  Status: FAILURES DETECTED"
fi

echo "============================================="

# Exit with error if any checks failed
if [ "$FAIL_COUNT" -gt 0 ]; then
    exit 1
fi

exit 0
