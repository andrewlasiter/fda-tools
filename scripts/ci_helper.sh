#!/bin/bash
# CI/CD Helper Script for FDA Tools
# This script provides common CI/CD operations for local testing and automation

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# Functions
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Check if running in CI
is_ci() {
    [[ -n "${CI}" ]] || [[ -n "${GITHUB_ACTIONS}" ]]
}

# Lint command
cmd_lint() {
    print_header "Running Linters"

    print_info "Running Ruff (linting)..."
    if ruff check plugins/fda-tools/ --output-format=concise; then
        print_success "Ruff linting passed"
    else
        print_error "Ruff linting failed"
        return 1
    fi

    print_info "Running Ruff (formatting check)..."
    if ruff format --check plugins/fda-tools/; then
        print_success "Ruff formatting check passed"
    else
        print_error "Ruff formatting check failed"
        print_info "Run 'ruff format plugins/fda-tools/' to fix"
        return 1
    fi

    print_info "Running Black (formatting check)..."
    if black --check plugins/fda-tools/lib plugins/fda-tools/scripts plugins/fda-tools/tests; then
        print_success "Black formatting check passed"
    else
        print_error "Black formatting check failed"
        print_info "Run 'black plugins/fda-tools/' to fix"
        return 1
    fi

    print_success "All linters passed"
}

# Format command
cmd_format() {
    print_header "Formatting Code"

    print_info "Running Ruff formatter..."
    ruff format plugins/fda-tools/

    print_info "Running Black formatter..."
    black plugins/fda-tools/lib plugins/fda-tools/scripts plugins/fda-tools/tests

    print_info "Running Ruff auto-fix..."
    ruff check --fix plugins/fda-tools/

    print_success "Code formatted"
}

# Type check command
cmd_typecheck() {
    print_header "Running Type Checks"

    print_info "Running mypy on lib/..."
    if mypy plugins/fda-tools/lib/ --config-file=pyproject.toml; then
        print_success "Type checking passed"
    else
        print_warning "Type checking found issues (non-blocking)"
    fi
}

# Security scan command
cmd_security() {
    print_header "Running Security Scans"

    print_info "Running Bandit..."
    if bandit -r plugins/fda-tools/lib plugins/fda-tools/scripts -ll -i; then
        print_success "Bandit security scan passed"
    else
        print_error "Bandit found security issues"
        return 1
    fi

    print_info "Running Safety..."
    if safety check || true; then
        print_success "Safety check completed"
    else
        print_warning "Safety found vulnerable dependencies"
    fi

    print_info "Running detect-secrets..."
    if detect-secrets scan --baseline .secrets.baseline; then
        print_success "No secrets detected"
    else
        print_error "Potential secrets detected"
        return 1
    fi

    print_success "Security scans completed"
}

# Test command
cmd_test() {
    print_header "Running Tests"

    local markers="${1:-not slow and not e2e and not api and not e2e_integration}"
    local coverage_min="${2:-80}"

    print_info "Running tests with markers: $markers"
    print_info "Minimum coverage: $coverage_min%"

    if pytest plugins/fda-tools/tests/ \
        -m "$markers" \
        --cov=plugins/fda-tools/lib \
        --cov=plugins/fda-tools/scripts \
        --cov-report=xml \
        --cov-report=term-missing:skip-covered \
        --cov-report=html \
        -v; then
        print_success "Tests passed"
    else
        print_error "Tests failed"
        return 1
    fi

    # Check coverage threshold
    if command -v coverage &> /dev/null; then
        local coverage=$(coverage report | grep TOTAL | awk '{print $4}' | sed 's/%//')
        print_info "Coverage: $coverage%"
        if (( $(echo "$coverage < $coverage_min" | bc -l) )); then
            print_error "Coverage ($coverage%) is below threshold ($coverage_min%)"
            return 1
        fi
    fi

    print_success "Test suite passed with sufficient coverage"
}

# Build command
cmd_build() {
    print_header "Building Distribution"

    print_info "Cleaning old builds..."
    rm -rf build/ dist/ *.egg-info

    print_info "Building package..."
    if python3 -m build; then
        print_success "Build completed"
    else
        print_error "Build failed"
        return 1
    fi

    print_info "Checking distribution..."
    if twine check dist/*; then
        print_success "Distribution check passed"
    else
        print_error "Distribution check failed"
        return 1
    fi

    print_success "Package built successfully"
    ls -lh dist/
}

# Pre-commit command
cmd_precommit() {
    print_header "Running Pre-commit Hooks"

    if ! command -v pre-commit &> /dev/null; then
        print_error "pre-commit not installed. Install with: pip install pre-commit"
        return 1
    fi

    print_info "Running all pre-commit hooks..."
    if pre-commit run --all-files; then
        print_success "All pre-commit hooks passed"
    else
        print_error "Some pre-commit hooks failed"
        return 1
    fi
}

# CI command (run all checks)
cmd_ci() {
    print_header "Running Full CI Pipeline"

    local failed=0

    cmd_lint || failed=1
    cmd_typecheck || true  # Non-blocking
    cmd_security || failed=1
    cmd_test || failed=1
    cmd_build || failed=1

    if [ $failed -eq 0 ]; then
        print_success "CI pipeline passed"
        return 0
    else
        print_error "CI pipeline failed"
        return 1
    fi
}

# Version bump command
cmd_bump() {
    local bump_type="${1:-patch}"

    print_header "Bumping Version"

    if [ ! -f "scripts/bump_version.py" ]; then
        print_error "bump_version.py not found"
        return 1
    fi

    python3 scripts/bump_version.py "$bump_type"
}

# Changelog command
cmd_changelog() {
    print_header "Generating Changelog"

    if [ ! -f "scripts/generate_changelog.py" ]; then
        print_error "generate_changelog.py not found"
        return 1
    fi

    python3 scripts/generate_changelog.py "$@"
}

# Release command
cmd_release() {
    local version="$1"

    if [ -z "$version" ]; then
        print_error "Version required. Usage: $0 release <version>"
        return 1
    fi

    print_header "Preparing Release $version"

    # Run full CI
    if ! cmd_ci; then
        print_error "CI checks failed. Fix issues before releasing."
        return 1
    fi

    # Bump version
    print_info "Setting version to $version..."
    python3 scripts/bump_version.py "$version"

    # Generate changelog
    print_info "Generating changelog..."
    python3 scripts/generate_changelog.py --version "$version" --output CHANGELOG_LATEST.md

    print_success "Release preparation complete"
    print_info "Next steps:"
    echo "  1. Review CHANGELOG_LATEST.md"
    echo "  2. git add pyproject.toml CHANGELOG_LATEST.md"
    echo "  3. git commit -m 'chore: release v$version'"
    echo "  4. git tag -a v$version -F CHANGELOG_LATEST.md"
    echo "  5. git push origin master --tags"
}

# Help command
cmd_help() {
    cat <<EOF
FDA Tools CI/CD Helper Script

Usage: $0 <command> [options]

Commands:
  lint              Run linting checks (Ruff, Black)
  format            Auto-format code with Ruff and Black
  typecheck         Run type checking with mypy
  security          Run security scans (Bandit, Safety, detect-secrets)
  test [markers]    Run test suite with optional pytest markers
  build             Build distribution packages
  precommit         Run all pre-commit hooks
  ci                Run full CI pipeline (lint, security, test, build)
  bump <type>       Bump version (major|minor|patch)
  changelog [opts]  Generate changelog from git commits
  release <version> Prepare a release (CI + version + changelog)
  help              Show this help message

Examples:
  $0 lint                          # Run linters
  $0 format                        # Format code
  $0 test                          # Run fast tests
  $0 test "not slow"               # Run all non-slow tests
  $0 security                      # Run security scans
  $0 ci                            # Run full CI pipeline
  $0 bump minor                    # Bump minor version
  $0 changelog --output RELEASE.md # Generate changelog
  $0 release 5.37.0                # Prepare release 5.37.0

Environment Variables:
  CI                Set to 'true' for CI mode
  GITHUB_ACTIONS    Set to 'true' for GitHub Actions

EOF
}

# Main command dispatcher
main() {
    local command="${1:-help}"
    shift || true

    case "$command" in
        lint)
            cmd_lint "$@"
            ;;
        format)
            cmd_format "$@"
            ;;
        typecheck)
            cmd_typecheck "$@"
            ;;
        security)
            cmd_security "$@"
            ;;
        test)
            cmd_test "$@"
            ;;
        build)
            cmd_build "$@"
            ;;
        precommit)
            cmd_precommit "$@"
            ;;
        ci)
            cmd_ci "$@"
            ;;
        bump)
            cmd_bump "$@"
            ;;
        changelog)
            cmd_changelog "$@"
            ;;
        release)
            cmd_release "$@"
            ;;
        help|--help|-h)
            cmd_help
            ;;
        *)
            print_error "Unknown command: $command"
            echo ""
            cmd_help
            exit 1
            ;;
    esac
}

# Run main
main "$@"
