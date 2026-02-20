# FDA-179: Quick Reference Card

## Installation (One-Time Setup)

```bash
cd /path/to/fda-tools
pip install -e ".[all]"
```

## Import Cheat Sheet

### Before (OLD - Don't Use)

```python
import sys
import os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, '..', 'lib'))
from gap_analyzer import GapAnalyzer
```

### After (NEW - Use This)

```python
from fda_tools.lib.gap_analyzer import GapAnalyzer
# or
from lib.gap_analyzer import GapAnalyzer  # if pytest handles it
```

## Common Import Patterns

| What | New Import |
|------|-----------|
| **From lib/** | `from fda_tools.lib.gap_analyzer import GapAnalyzer` |
| **From scripts/** | `from fda_tools.scripts.fda_api_client import FDAClient` |
| **Within lib/** | `from .module import Class` (relative) |
| **Top-level** | `from fda_tools import GapAnalyzer` |

## CLI Commands (After Install)

```bash
fda-batchfetch --product-codes DQY --years 2024 --enrich
fda-gap-analysis --years 2020-2025
fda-setup-api-key
```

## Testing

```bash
# Run all tests
pytest

# Run specific test
pytest tests/test_gap_analyzer.py

# With coverage
pytest --cov=lib --cov=scripts
```

## Type Checking

```bash
mypy plugins/fda-tools/lib/
```

## Linting

```bash
ruff check --fix plugins/fda-tools/
```

## Verification

```bash
# Check package installed
pip show fda-tools

# Test import
python -c "from fda_tools import __version__; print(__version__)"

# Test CLI
fda-batchfetch --help
```

## Migration Steps (Per File)

1. Remove all `sys.path.insert()` lines
2. Change imports: `from module import X` → `from fda_tools.lib.module import X`
3. Add type hints: `def func(x: int) -> str:`
4. Test: `pytest tests/test_module.py`

## Common Issues

| Issue | Solution |
|-------|----------|
| `ImportError: No module named 'fda_tools'` | Run `pip install -e .` |
| `command not found: fda-batchfetch` | Run `pip install -e .` |
| Circular import | Use `TYPE_CHECKING` and forward references |

## Full Documentation

- [Installation Guide](./INSTALLATION.md)
- [Migration Guide](./FDA-179_PACKAGE_MIGRATION_GUIDE.md)
- [Conversion Examples](./FDA-179_CONVERSION_EXAMPLES.md)
- [Implementation Summary](./FDA-179_IMPLEMENTATION_SUMMARY.md)
