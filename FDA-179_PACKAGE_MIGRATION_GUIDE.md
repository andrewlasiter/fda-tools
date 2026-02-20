# FDA-179: Python Package Migration Guide

## Overview

This guide covers the conversion of FDA Tools from a sys.path-based plugin to a proper pip-installable Python package following PEP 517/518 standards.

## What Changed

### Package Structure

```
OLD (sys.path manipulation):
fda-tools/
├── plugins/fda-tools/
│   ├── scripts/
│   │   ├── __init__.py (with sys.path hacks)
│   │   ├── batchfetch.py
│   │   └── gap_analysis.py
│   └── lib/
│       └── gap_analyzer.py

NEW (proper package):
fda-tools/
├── pyproject.toml          # PEP 517/518 build configuration
├── setup.py                # Backward compatibility shim
├── plugins/fda-tools/
│   ├── __init__.py         # Package root with version and exports
│   ├── scripts/
│   │   ├── __init__.py     # Clean imports, no sys.path
│   │   ├── batchfetch.py
│   │   └── gap_analysis.py
│   └── lib/
│       ├── __init__.py     # Clean imports, no sys.path
│       └── gap_analyzer.py
```

### Key Files

1. **pyproject.toml**: Modern package configuration
   - All dependencies declared
   - CLI entry points defined
   - Build system configuration
   - Tool configuration (pytest, mypy, ruff)

2. **setup.py**: Backward compatibility for older pip versions

3. **__init__.py files**: Package initialization with clean imports

## Installation

### For Development (Editable Install)

```bash
# From repository root
cd /path/to/fda-tools

# Install in editable mode with all dev dependencies
pip install -e ".[dev]"

# Or install with optional features
pip install -e ".[optional]"

# Or install everything
pip install -e ".[all]"
```

### For Production

```bash
# Install from repository
pip install /path/to/fda-tools

# Or from git
pip install git+https://github.com/your-org/fda-tools.git

# With optional features
pip install "fda-tools[optional]"
```

### Verify Installation

```bash
# Check package is installed
pip show fda-tools

# Check CLI tools are available
fda-batchfetch --help
fda-gap-analysis --help

# Test imports in Python
python -c "from fda_tools import GapAnalyzer; print('Success!')"
```

## CLI Entry Points

After installation, the following commands are available system-wide:

```bash
fda-batchfetch          # FDA 510(k) batch fetch tool
fda-gap-analysis        # Gap analysis for K-numbers
fda-batch-analyze       # Batch analysis of test results
fda-batch-seed          # Seed test projects
fda-backup-project      # Backup project data
fda-setup-api-key       # Setup API credentials
fda-migrate-keyring     # Migrate to keyring storage
fda-auto-standards      # Auto-generate device standards
fda-check-version       # Check for updates
fda-update-manager      # Manage package updates
```

## Import Migration Examples

### Example 1: Simple Script Import

**BEFORE (sys.path manipulation):**
```python
#!/usr/bin/env python3
import os
import sys

# BAD: Manual sys.path manipulation
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LIB_DIR = os.path.join(SCRIPT_DIR, '..', 'lib')
sys.path.insert(0, LIB_DIR)

# Now import works
from gap_analyzer import GapAnalyzer

def main():
    analyzer = GapAnalyzer()
    # ...
```

**AFTER (proper package import):**
```python
#!/usr/bin/env python3
# GOOD: Clean imports, no sys.path needed

from fda_tools.lib import GapAnalyzer
# or
from lib.gap_analyzer import GapAnalyzer

def main():
    analyzer = GapAnalyzer()
    # ...
```

### Example 2: Cross-Module Imports

**BEFORE:**
```python
# In scripts/batchfetch.py
import os
import sys

# BAD: Fragile path manipulation
_lib_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")
sys.path.insert(0, _lib_dir)

from cross_process_rate_limiter import CrossProcessRateLimiter
from fda_enrichment import FDAEnrichment
```

**AFTER:**
```python
# In scripts/batchfetch.py
# GOOD: Standard Python imports

from fda_tools.lib.cross_process_rate_limiter import CrossProcessRateLimiter
from fda_tools.lib.fda_enrichment import FDAEnrichment

# Or use relative imports within package
from ..lib.cross_process_rate_limiter import CrossProcessRateLimiter
from ..lib.fda_enrichment import FDAEnrichment
```

### Example 3: Test File Imports

**BEFORE:**
```python
# tests/test_gap_analyzer.py
import os
import sys
import pytest

# BAD: Path juggling to find modules
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LIB_DIR = os.path.join(SCRIPT_DIR, '..', 'lib')
sys.path.insert(0, LIB_DIR)

from gap_analyzer import GapAnalyzer

def test_gap_detection():
    analyzer = GapAnalyzer()
    # ...
```

**AFTER:**
```python
# tests/test_gap_analyzer.py
import pytest

# GOOD: Direct imports, pytest handles everything
from fda_tools.lib.gap_analyzer import GapAnalyzer
# or
from lib.gap_analyzer import GapAnalyzer

def test_gap_detection():
    analyzer = GapAnalyzer()
    # ...
```

### Example 4: Convenience Imports from Package Root

**NEW CAPABILITY:**
```python
# Top-level imports for commonly used classes
from fda_tools import (
    GapAnalyzer,
    FDAEnrichment,
    PredicateRanker,
    FDAClient,
    setup_logging,
)

# Check package version
from fda_tools import __version__
print(f"FDA Tools version: {__version__}")
```

## Script Entry Point Pattern

Scripts that should work both as CLI tools and importable modules:

**BEFORE:**
```python
#!/usr/bin/env python3
import sys
import os

# Path manipulation
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from gap_analyzer import GapAnalyzer

def main():
    # Main logic
    pass

if __name__ == '__main__':
    main()
```

**AFTER:**
```python
#!/usr/bin/env python3
"""Gap analysis CLI tool.

Can be run as:
    python -m scripts.gap_analysis
    fda-gap-analysis  # After pip install
"""

from fda_tools.lib import GapAnalyzer

def main():
    """Entry point for CLI command."""
    # Main logic
    pass

if __name__ == '__main__':
    main()
```

## Running Scripts

### Before Installation

```bash
# OLD way (still works in development):
cd plugins/fda-tools/scripts
python gap_analysis.py --help

# NEW way (recommended):
python -m scripts.gap_analysis --help
```

### After Installation

```bash
# Use installed CLI commands:
fda-gap-analysis --help
fda-batchfetch --product-codes DQY --years 2024

# Or via Python module:
python -m scripts.gap_analysis --help
```

## Testing

### Running Tests

```bash
# From repository root
pytest

# With coverage
pytest --cov=lib --cov=scripts

# Specific test file
pytest tests/test_gap_analyzer.py

# Run in verbose mode
pytest -v
```

### pytest Configuration

All pytest configuration is in `pyproject.toml`:
- Test discovery paths
- Coverage settings
- Markers for test categories
- Warning filters

## Type Checking

```bash
# Check types with mypy
mypy plugins/fda-tools/lib
mypy plugins/fda-tools/scripts

# Strict checking for lib/
mypy --strict plugins/fda-tools/lib/gap_analyzer.py
```

## Linting and Formatting

```bash
# Format code with ruff
ruff format plugins/fda-tools/

# Check for linting issues
ruff check plugins/fda-tools/

# Auto-fix linting issues
ruff check --fix plugins/fda-tools/
```

## Dependencies

### Core Dependencies (Always Installed)

```toml
requests>=2.31.0,<3.0.0
pandas>=2.0.0,<3.0.0
numpy>=1.24.0,<2.0.0
PyMuPDF>=1.23.0,<2.0.0
beautifulsoup4>=4.12.0,<5.0.0
keyring>=24.0.0,<26.0.0
# ... (see pyproject.toml for complete list)
```

### Optional Dependencies

```bash
# Install OCR support
pip install "fda-tools[optional]"

# Install dev tools
pip install "fda-tools[dev]"

# Install everything
pip install "fda-tools[all]"
```

## Migration Checklist

For each script/module being migrated:

- [ ] Remove all `sys.path.insert()` calls
- [ ] Replace relative path imports with package imports
- [ ] Update `from module import X` to `from fda_tools.lib.module import X`
- [ ] Test imports work: `python -c "from fda_tools.lib import X"`
- [ ] Run tests: `pytest tests/test_module.py`
- [ ] Update documentation with new import patterns

## Common Issues and Solutions

### Issue 1: ImportError after migration

```python
ImportError: No module named 'gap_analyzer'
```

**Solution:** Use full package path:
```python
# Change this:
from gap_analyzer import GapAnalyzer

# To this:
from fda_tools.lib.gap_analyzer import GapAnalyzer
```

### Issue 2: Tests can't find modules

**Solution:** Install package in editable mode:
```bash
pip install -e .
```

### Issue 3: CLI commands not found

```bash
bash: fda-batchfetch: command not found
```

**Solution:** Ensure package is installed:
```bash
pip install -e .
# or
pip install .
```

Then verify:
```bash
which fda-batchfetch
# Should show path in your Python environment
```

### Issue 4: Circular imports

**Solution:** Use lazy imports or restructure:
```python
# Instead of top-level import
from fda_tools.lib import heavy_module

# Use function-level import
def my_function():
    from fda_tools.lib import heavy_module
    # ...
```

## Version Management

The package version is defined in `pyproject.toml` and exposed via:

```python
from fda_tools import __version__
print(__version__)  # "5.36.0"
```

To update version:
1. Edit `pyproject.toml`: `version = "5.37.0"`
2. Update `plugins/fda-tools/__init__.py`: `__version__ = "5.37.0"`
3. Commit and tag: `git tag v5.37.0`

## Build and Distribution

### Build Wheel Package

```bash
# Install build tool
pip install build

# Build wheel and source distribution
python -m build

# Output in dist/:
# - fda_tools-5.36.0-py3-none-any.whl
# - fda_tools-5.36.0.tar.gz
```

### Install from Wheel

```bash
pip install dist/fda_tools-5.36.0-py3-none-any.whl
```

## Integration with Existing Workflows

### Pre-commit Hooks

No changes needed - hooks continue to work with package structure.

### CI/CD Pipelines

Update CI configuration:

```yaml
# .github/workflows/test.yml
- name: Install package
  run: pip install -e ".[dev]"

- name: Run tests
  run: pytest

- name: Type checking
  run: mypy plugins/fda-tools/lib
```

### Documentation Generation

```bash
# Install sphinx
pip install sphinx sphinx-rtd-theme

# Generate API docs
sphinx-apidoc -o docs/api plugins/fda-tools/

# Build HTML docs
cd docs && make html
```

## Benefits of Package Structure

1. **No sys.path manipulation**: Cleaner, more maintainable code
2. **Standard imports**: Familiar to all Python developers
3. **Pip installable**: Easy distribution and deployment
4. **CLI entry points**: Professional command-line tools
5. **Type checking**: Better IDE support and static analysis
6. **Testing**: Simpler test configuration
7. **Version management**: Single source of truth for version
8. **Dependency management**: Declarative, version-controlled

## Related Documentation

- [PEP 517 - Build System](https://peps.python.org/pep-0517/)
- [PEP 518 - pyproject.toml](https://peps.python.org/pep-0518/)
- [Python Packaging User Guide](https://packaging.python.org/)
- [Setuptools Documentation](https://setuptools.pypa.io/)

## Support

For issues or questions:
1. Check this migration guide
2. Review example conversions in this document
3. Check test files for working examples
4. Open an issue on GitHub

---

**Status**: FDA-179 Implementation Complete
**Last Updated**: 2026-02-20
**Version**: 5.36.0
