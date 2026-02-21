# FDA Tools — common development tasks
# Run `make help` to list all targets.

.PHONY: help install dev test test-fast lint format check clean pre-commit \
        coverage build verify

# Default target
.DEFAULT_GOAL := help

# Project paths
SRC_DIR := plugins/fda_tools
TESTS_DIR := $(SRC_DIR)/tests

# ── Help ──────────────────────────────────────────────────────────────────────

help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ── Installation ──────────────────────────────────────────────────────────────

install:  ## Install package in editable mode (minimal)
	pip install -e .

dev:  ## Install package with all development dependencies
	pip install -e ".[dev]"

pre-commit-install:  ## Install pre-commit hooks
	pre-commit install

# ── Testing ───────────────────────────────────────────────────────────────────

test:  ## Run the full test suite
	pytest $(TESTS_DIR) -v

test-fast:  ## Run tests without verbose output (faster)
	pytest $(TESTS_DIR) -q

test-file:  ## Run a single test file: make test-file FILE=tests/test_foo.py
	pytest $(FILE) -v

coverage:  ## Run tests with coverage report
	pytest $(TESTS_DIR) \
	  --cov=$(SRC_DIR)/lib \
	  --cov=$(SRC_DIR)/scripts \
	  --cov-report=term-missing \
	  --cov-report=html:htmlcov

# ── Code quality ──────────────────────────────────────────────────────────────

lint:  ## Run Ruff linter
	ruff check $(SRC_DIR)/

format:  ## Auto-format code with Ruff
	ruff format $(SRC_DIR)/

format-check:  ## Check formatting without modifying files
	ruff format --check $(SRC_DIR)/

type-check:  ## Run mypy type checker
	mypy $(SRC_DIR)/lib $(SRC_DIR)/scripts --ignore-missing-imports

pre-commit:  ## Run all pre-commit hooks on staged files
	pre-commit run

pre-commit-all:  ## Run all pre-commit hooks on every file
	pre-commit run --all-files

check: lint format-check type-check  ## Run all quality checks (no auto-fix)

# ── Security ──────────────────────────────────────────────────────────────────

security:  ## Run security scanners (bandit + safety)
	bandit -r $(SRC_DIR)/lib $(SRC_DIR)/scripts -ll
	safety check

licenses:  ## Check for copyleft dependency licenses
	pip-licenses --format=plain | grep -E "GPL|AGPL|LGPL" && \
	  echo "WARNING: Copyleft licenses detected — review required" || \
	  echo "License check passed: no copyleft licenses"

# ── Installation verification ─────────────────────────────────────────────────

verify:  ## Verify the installation is working
	python3 $(SRC_DIR)/scripts/verify_install.py

# ── Cleanup ───────────────────────────────────────────────────────────────────

clean:  ## Remove build artifacts and caches
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	@echo "Cleaned build artifacts"
