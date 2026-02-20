# FDA Tools Installation Guide

## Quick Start

```bash
# Clone repository
cd /path/to/fda-tools

# Install in editable mode with all features
pip install -e ".[all]"

# Verify installation
fda-batchfetch --help
python -c "from fda_tools import __version__; print(__version__)"
```

## Installation Options

### 1. Development Installation (Recommended for Contributors)

Install in editable mode so changes to code are immediately reflected:

```bash
# Install with dev dependencies (pytest, mypy, ruff, etc.)
pip install -e ".[dev]"

# Or install with all features
pip install -e ".[all]"
```

**Benefits:**
- Changes to code take effect immediately without reinstalling
- Full development tooling (tests, linters, type checkers)
- CLI commands available system-wide

### 2. Production Installation

Install as a regular package:

```bash
# Basic installation
pip install /path/to/fda-tools

# With optional features
pip install "/path/to/fda-tools[optional]"
```

### 3. From Git Repository

```bash
# Install latest from git
pip install git+https://github.com/your-org/fda-tools.git

# Install specific branch
pip install git+https://github.com/your-org/fda-tools.git@feature-branch

# Install specific tag
pip install git+https://github.com/your-org/fda-tools.git@v5.36.0

# With extras
pip install "git+https://github.com/your-org/fda-tools.git#egg=fda-tools[all]"
```

## Dependency Groups

### Core Dependencies (Always Installed)

Required for basic functionality:

```
requests>=2.31.0,<3.0.0           # HTTP requests
pandas>=2.0.0,<3.0.0              # Data processing
numpy>=1.24.0,<2.0.0              # Numerical computing
PyMuPDF>=1.23.0,<2.0.0            # PDF processing
beautifulsoup4>=4.12.0,<5.0.0     # HTML/XML parsing
lxml>=4.9.0,<6.0.0                # XML processing
defusedxml>=0.7.1,<1.0.0          # Secure XML parsing
keyring>=24.0.0,<26.0.0           # Secure credential storage
tenacity>=8.0.0,<10.0.0           # Retry logic
tqdm>=4.66.0,<5.0.0               # Progress bars
```

### Optional Dependencies

Enable additional features:

```bash
# Install all optional features
pip install "fda-tools[optional]"
```

Includes:
- `colorama` - Colored terminal output
- `pytesseract` + `pdf2image` - OCR support for scanned PDFs
- `PyPDF2` - PDF validation
- `reportlab` - PDF generation
- `openpyxl` - Excel export functionality
- `scikit-learn` - ML-based approval predictions

### Development Dependencies

Tools for development and testing:

```bash
# Install dev dependencies
pip install "fda-tools[dev]"
```

Includes:
- `pytest` + plugins - Testing framework
- `ruff` - Fast linter and formatter
- `mypy` - Static type checker
- `black` - Code formatter (backup)
- `pre-commit` - Git hooks
- `interrogate` - Docstring coverage

### Testing Only

Minimal dependencies for CI/CD:

```bash
pip install "fda-tools[test]"
```

### All Features

Everything in one command:

```bash
pip install "fda-tools[all]"
# Equivalent to: fda-tools[optional,dev]
```

## System Requirements

### Python Version

- **Required:** Python 3.9 or higher
- **Recommended:** Python 3.11 or 3.12
- **Tested:** 3.9, 3.10, 3.11, 3.12

Check your Python version:
```bash
python3 --version
```

### Optional System Dependencies

#### Tesseract OCR (for scanned PDF support)

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
```

**macOS:**
```bash
brew install tesseract
```

**Windows:**
Download installer from: https://github.com/UB-Mannheim/tesseract/wiki

#### Poppler (for pdf2image)

**Ubuntu/Debian:**
```bash
sudo apt-get install poppler-utils
```

**macOS:**
```bash
brew install poppler
```

**Windows:**
Download from: http://blog.alivate.com.au/poppler-windows/

## Virtual Environments

### Using venv (Recommended)

```bash
# Create virtual environment
python3 -m venv venv

# Activate (Linux/macOS)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Install FDA Tools
pip install -e ".[all]"

# Deactivate when done
deactivate
```

### Using conda

```bash
# Create conda environment
conda create -n fda-tools python=3.11

# Activate
conda activate fda-tools

# Install FDA Tools
pip install -e ".[all]"

# Deactivate
conda deactivate
```

### Using virtualenvwrapper

```bash
# Create environment
mkvirtualenv fda-tools

# Install
pip install -e ".[all]"

# Switch to environment later
workon fda-tools
```

## Verification

### Check Package Installation

```bash
# Show package info
pip show fda-tools

# List installed dependencies
pip list | grep fda-tools

# Check installed version
python -c "from fda_tools import __version__; print(__version__)"
```

### Verify CLI Commands

All CLI commands should be available after installation:

```bash
# Check command exists
which fda-batchfetch

# Test help output
fda-batchfetch --help
fda-gap-analysis --help
fda-batch-analyze --help
fda-setup-api-key --help

# Run version check
fda-check-version
```

### Test Imports

```bash
# Test core imports
python -c "from fda_tools.lib import GapAnalyzer; print('✓ GapAnalyzer')"
python -c "from fda_tools.lib import FDAEnrichment; print('✓ FDAEnrichment')"
python -c "from fda_tools.lib import PredicateRanker; print('✓ PredicateRanker')"

# Test script imports
python -c "from fda_tools.scripts import FDAClient; print('✓ FDAClient')"

# Test convenience imports
python -c "from fda_tools import GapAnalyzer, FDAClient; print('✓ Top-level imports')"
```

### Run Test Suite

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=lib --cov=scripts --cov-report=term-missing

# Run specific test file
pytest tests/test_gap_analyzer.py

# Run fast tests only (skip slow API tests)
pytest -m "not slow"
```

## Upgrading

### Upgrade from Previous Version

```bash
# If installed in editable mode
cd /path/to/fda-tools
git pull
pip install -e ".[all]" --upgrade

# If installed from wheel
pip install --upgrade fda-tools
```

### Reinstall

```bash
# Uninstall
pip uninstall fda-tools

# Reinstall
pip install -e ".[all]"
```

## Troubleshooting

### Issue: Command not found

```bash
fda-batchfetch: command not found
```

**Solution:**
```bash
# Ensure package is installed
pip show fda-tools

# If not installed:
pip install -e .

# Check if command is in PATH
which fda-batchfetch

# If not in PATH, reinstall
pip uninstall fda-tools
pip install -e .
```

### Issue: Import errors

```python
ImportError: No module named 'fda_tools'
```

**Solution:**
```bash
# Verify installation
pip list | grep fda-tools

# If not installed:
pip install -e .

# Verify Python is using correct environment
which python
python -c "import sys; print(sys.prefix)"
```

### Issue: Missing dependencies

```python
ModuleNotFoundError: No module named 'pandas'
```

**Solution:**
```bash
# Core dependencies should auto-install
# If missing, reinstall:
pip install -e ".[all]" --force-reinstall

# Or install specific dependency
pip install pandas>=2.0.0
```

### Issue: Tesseract not found

```python
TesseractNotFoundError: tesseract is not installed
```

**Solution:**
```bash
# Install system dependency (Ubuntu)
sudo apt-get install tesseract-ocr

# Verify installation
which tesseract
tesseract --version

# Set path in Python if needed
export TESSDATA_PREFIX=/usr/share/tesseract-ocr/
```

### Issue: Old sys.path imports still used

```python
# Old code still has:
sys.path.insert(0, lib_path)
```

**Solution:**
See [FDA-179_PACKAGE_MIGRATION_GUIDE.md](./FDA-179_PACKAGE_MIGRATION_GUIDE.md) for migration instructions.

### Issue: Permission denied during install

```bash
ERROR: Could not install packages due to an OSError: [Errno 13] Permission denied
```

**Solution:**
```bash
# Don't use sudo! Use virtual environment instead
python3 -m venv venv
source venv/bin/activate
pip install -e ".[all]"

# Or use --user flag (not recommended)
pip install --user -e ".[all]"
```

## Development Setup

Complete setup for development:

```bash
# 1. Clone repository
git clone https://github.com/your-org/fda-tools.git
cd fda-tools

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# 3. Install in editable mode with all dependencies
pip install -e ".[all]"

# 4. Install pre-commit hooks
pre-commit install

# 5. Verify installation
pytest
mypy plugins/fda-tools/lib
ruff check plugins/fda-tools

# 6. Set up API keys (optional)
fda-setup-api-key

# 7. Run sample command
fda-batchfetch --help
```

## IDE Configuration

### VS Code

Create `.vscode/settings.json`:

```json
{
    "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": [
        "tests"
    ],
    "python.linting.enabled": true,
    "python.linting.mypyEnabled": true,
    "python.formatting.provider": "black",
    "editor.formatOnSave": true,
    "[python]": {
        "editor.defaultFormatter": "charliermarsh.ruff"
    }
}
```

### PyCharm

1. Open project
2. Settings → Project → Python Interpreter
3. Add interpreter → Virtual Environment → Existing
4. Select `venv/bin/python`
5. Settings → Tools → Python Integrated Tools
6. Set Default test runner to pytest

## Uninstallation

```bash
# Uninstall package
pip uninstall fda-tools

# Remove virtual environment
deactivate
rm -rf venv/

# Remove build artifacts
rm -rf build/ dist/ *.egg-info
```

## Next Steps

After installation:

1. Read [FDA-179_PACKAGE_MIGRATION_GUIDE.md](./FDA-179_PACKAGE_MIGRATION_GUIDE.md) for import patterns
2. Review [README.md](./README.md) for usage examples
3. Check [QUICKSTART-BRIDGE.md](./QUICKSTART-BRIDGE.md) for bridge setup
4. Set up API keys with `fda-setup-api-key`
5. Run your first batch fetch: `fda-batchfetch --help`

## Support

For installation issues:
- Check this guide's Troubleshooting section
- Review closed issues on GitHub
- Open a new issue with details:
  - Python version (`python --version`)
  - OS and version
  - Full error message
  - Installation command used

---

**Last Updated:** 2026-02-20
**Package Version:** 5.36.0
