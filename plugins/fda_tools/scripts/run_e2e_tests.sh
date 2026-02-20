#!/bin/bash
#
# End-to-End Test Execution Script
# ==================================
#
# Runs E2E test suite with various options and configurations.
#
# Usage:
#   ./scripts/run_e2e_tests.sh [OPTIONS]
#
# Options:
#   --fast          Run only fast tests (<5s each)
#   --510k          Run 510(k) workflow tests only
#   --security      Run security and auth tests only
#   --integration   Run integration tests (may require real APIs)
#   --edge-cases    Run edge case tests only
#   --coverage      Generate coverage report
#   --parallel      Run tests in parallel (requires pytest-xdist)
#   --verbose       Verbose output
#   --help          Show this help message
#
# Examples:
#   ./scripts/run_e2e_tests.sh --fast
#   ./scripts/run_e2e_tests.sh --510k --coverage
#   ./scripts/run_e2e_tests.sh --parallel --verbose
#
# Version: 1.0.0
# Date: 2026-02-20
# Issue: FDA-186

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default options
RUN_FAST=false
RUN_510K=false
RUN_SECURITY=false
RUN_INTEGRATION=false
RUN_EDGE_CASES=false
GENERATE_COVERAGE=false
RUN_PARALLEL=false
VERBOSE=false
SHOW_HELP=false

# Plugin root directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PLUGIN_ROOT="$(dirname "$SCRIPT_DIR")"
E2E_TESTS_DIR="$PLUGIN_ROOT/tests/e2e"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --fast)
            RUN_FAST=true
            shift
            ;;
        --510k)
            RUN_510K=true
            shift
            ;;
        --security)
            RUN_SECURITY=true
            shift
            ;;
        --integration)
            RUN_INTEGRATION=true
            shift
            ;;
        --edge-cases)
            RUN_EDGE_CASES=true
            shift
            ;;
        --coverage)
            GENERATE_COVERAGE=true
            shift
            ;;
        --parallel)
            RUN_PARALLEL=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --help|-h)
            SHOW_HELP=true
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            SHOW_HELP=true
            shift
            ;;
    esac
done

# Show help if requested
if [ "$SHOW_HELP" = true ]; then
    head -n 30 "$0" | tail -n +3 | sed 's/^# //'
    exit 0
fi

# Print header
echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}FDA Tools E2E Test Suite${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}Error: pytest is not installed${NC}"
    echo "Install with: pip install pytest pytest-cov pytest-xdist"
    exit 1
fi

# Change to plugin root directory
cd "$PLUGIN_ROOT"
echo -e "${YELLOW}Working directory: $(pwd)${NC}"
echo ""

# Build pytest command
PYTEST_CMD="pytest"
PYTEST_ARGS=()

# Add test directory
PYTEST_ARGS+=("$E2E_TESTS_DIR")

# Add markers based on options
MARKERS=()

if [ "$RUN_FAST" = true ]; then
    MARKERS+=("e2e_fast")
fi

if [ "$RUN_510K" = true ]; then
    MARKERS+=("e2e_510k")
fi

if [ "$RUN_SECURITY" = true ]; then
    MARKERS+=("e2e_security")
fi

if [ "$RUN_INTEGRATION" = true ]; then
    MARKERS+=("e2e_integration")
fi

if [ "$RUN_EDGE_CASES" = true ]; then
    MARKERS+=("e2e_edge_cases")
fi

# Build marker expression
if [ ${#MARKERS[@]} -gt 0 ]; then
    MARKER_EXPR=$(IFS=" or "; echo "${MARKERS[*]}")
    PYTEST_ARGS+=("-m" "$MARKER_EXPR")
    echo -e "${YELLOW}Running tests with markers: ${MARKER_EXPR}${NC}"
else
    echo -e "${YELLOW}Running all E2E tests${NC}"
    PYTEST_ARGS+=("-m" "e2e")
fi

# Add verbose flag
if [ "$VERBOSE" = true ]; then
    PYTEST_ARGS+=("-v")
fi

# Add coverage flags
if [ "$GENERATE_COVERAGE" = true ]; then
    PYTEST_ARGS+=("--cov=lib" "--cov=scripts" "--cov=skills")
    PYTEST_ARGS+=("--cov-report=term-missing")
    PYTEST_ARGS+=("--cov-report=html:coverage_html")
    PYTEST_ARGS+=("--cov-report=xml:coverage.xml")
    echo -e "${YELLOW}Coverage reporting enabled${NC}"
fi

# Add parallel execution
if [ "$RUN_PARALLEL" = true ]; then
    if ! pytest --co -q --collect-only 2>&1 | grep -q "xdist"; then
        echo -e "${YELLOW}Warning: pytest-xdist not installed, parallel execution disabled${NC}"
        echo "Install with: pip install pytest-xdist"
    else
        PYTEST_ARGS+=("-n" "auto")
        echo -e "${YELLOW}Parallel execution enabled${NC}"
    fi
fi

# Add standard flags
PYTEST_ARGS+=("--tb=short")
PYTEST_ARGS+=("--strict-markers")

echo ""

# Execute tests
echo -e "${BLUE}Executing: $PYTEST_CMD ${PYTEST_ARGS[*]}${NC}"
echo ""

set +e
$PYTEST_CMD "${PYTEST_ARGS[@]}"
TEST_EXIT_CODE=$?
set -e

echo ""

# Print summary
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}================================${NC}"
    echo -e "${GREEN}All E2E Tests Passed!${NC}"
    echo -e "${GREEN}================================${NC}"
    
    if [ "$GENERATE_COVERAGE" = true ]; then
        echo ""
        echo -e "${YELLOW}Coverage reports generated:${NC}"
        echo "  - Terminal: (above)"
        echo "  - HTML: coverage_html/index.html"
        echo "  - XML: coverage.xml"
    fi
else
    echo -e "${RED}================================${NC}"
    echo -e "${RED}E2E Tests Failed${NC}"
    echo -e "${RED}================================${NC}"
    echo ""
    echo -e "${YELLOW}Troubleshooting tips:${NC}"
    echo "  1. Run with --verbose for detailed output"
    echo "  2. Check test logs for specific failures"
    echo "  3. Verify all dependencies installed"
    echo "  4. Ensure mock data files exist"
    echo "  5. Review test documentation in tests/e2e/README.md"
fi

echo ""
exit $TEST_EXIT_CODE
