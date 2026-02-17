#!/bin/bash
#
# Pre-commit hooks setup script for FDA Tools
#
# This script automates the setup of pre-commit hooks for the FDA Tools project.
# It handles virtual environment setup and hook installation.
#
# Usage:
#   bash scripts/setup-precommit.sh
#   ./scripts/setup-precommit.sh  (if executable)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "${BLUE}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Main setup
main() {
    print_header "FDA Tools Pre-commit Hook Setup"
    echo ""

    # Check Python version
    print_header "Checking Python version..."
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 not found. Please install Python 3.9 or higher."
        exit 1
    fi

    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    print_success "Found Python $PYTHON_VERSION"
    echo ""

    # Check for virtual environment
    print_header "Checking virtual environment..."
    if [ -z "$VIRTUAL_ENV" ]; then
        print_warning "No virtual environment detected."
        echo "Creating virtual environment..."

        if [ ! -d "venv" ]; then
            python3 -m venv venv
            print_success "Virtual environment created at ./venv"
        fi

        # Activate virtual environment
        if [ -f "venv/bin/activate" ]; then
            source venv/bin/activate
            print_success "Virtual environment activated"
        elif [ -f "venv/Scripts/activate" ]; then
            # Windows
            source venv/Scripts/activate
            print_success "Virtual environment activated (Windows)"
        fi
    else
        print_success "Using existing virtual environment: $VIRTUAL_ENV"
    fi
    echo ""

    # Upgrade pip
    print_header "Upgrading pip..."
    pip install --upgrade pip > /dev/null 2>&1
    print_success "pip upgraded"
    echo ""

    # Install pre-commit
    print_header "Installing pre-commit framework..."
    if pip install pre-commit > /dev/null 2>&1; then
        print_success "pre-commit installed"
    else
        print_error "Failed to install pre-commit"
        exit 1
    fi
    echo ""

    # Install development dependencies
    print_header "Installing development dependencies..."
    if pip install -e ".[dev]" > /dev/null 2>&1; then
        print_success "Development dependencies installed"
    else
        print_warning "Failed to install dev dependencies, continuing..."
    fi
    echo ""

    # Install git hooks
    print_header "Installing git pre-commit hooks..."
    if pre-commit install > /dev/null 2>&1; then
        print_success "Git hooks installed"
    else
        print_error "Failed to install git hooks"
        exit 1
    fi
    echo ""

    # Run hooks on all files (optional, can skip)
    read -p "Run pre-commit hooks on all files now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_header "Running pre-commit on all files..."
        if pre-commit run --all-files; then
            print_success "All files passed pre-commit checks"
        else
            print_warning "Some files need fixes. See details above."
            echo "You can fix issues and run again: pre-commit run --all-files"
        fi
    fi
    echo ""

    # Summary
    print_header "Setup Complete!"
    echo ""
    echo "Next steps:"
    echo "  1. Pre-commit hooks are now active"
    echo "  2. Hooks will run automatically before each commit"
    echo "  3. Run 'pre-commit run --all-files' to check all files anytime"
    echo "  4. Read docs/CONTRIBUTING.md for detailed information"
    echo ""
    echo "Quick commands:"
    echo "  pre-commit run              # Check staged files"
    echo "  pre-commit run --all-files  # Check all files"
    echo "  pre-commit run ruff --all-files  # Check Python only"
    echo "  git commit --no-verify      # Skip hooks (use sparingly!)"
    echo ""
    print_success "Enjoy clean code!"
}

# Run main function
main "$@"
