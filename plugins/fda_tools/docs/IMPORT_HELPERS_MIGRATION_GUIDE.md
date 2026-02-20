# Import Helpers Migration Guide

## Overview

The `import_helpers` module (FDA-17 / GAP-015) provides standardized, safe import patterns to replace the anti-pattern `except (ImportError, Exception)`. This guide shows how to migrate existing code.

## When to Use Import Helpers

### ✅ Use import_helpers when:
- Importing optional dependencies (e.g., ML libraries, GUI frameworks)
- Importing modules with multiple possible locations (scripts.module vs module)
- You need to distinguish between missing packages and broken code
- You want automatic logging of import failures
- Implementing graceful degradation for missing features

### ❌ Don't use import_helpers when:
- Importing standard library modules (json, sys, os)
- Importing core dependencies that must be present
- Simple, one-time imports with no error handling needed

## Migration Patterns

### Pattern 1: Optional Module Import with Fallback

#### Before
```python
try:
    from optional_module import OptionalClass
    use_optional = True
except (ImportError, Exception):
    OptionalClass = None
    use_optional = False
```

#### After
```python
from lib.import_helpers import safe_import

result = safe_import('optional_module', 'OptionalClass', log_level=logging.DEBUG)
OptionalClass = result.module
use_optional = result.success
```

**Benefits**:
- Separates ImportError from other exceptions
- Automatic DEBUG logging of missing module
- Full traceback if module exists but has syntax errors

---

### Pattern 2: Try Multiple Import Paths

#### Before
```python
try:
    from scripts.my_module import MyClass
except ImportError:
    try:
        from my_module import MyClass
    except ImportError:
        MyClass = None
```

#### After
```python
from lib.import_helpers import safe_import

result = safe_import(
    'scripts.my_module',
    'MyClass',
    alternative_names=['my_module']
)
MyClass = result.module
```

**Benefits**:
- Eliminates nested try/except
- Cleaner code (6 lines → 3 lines)
- Consistent logging across alternatives

---

### Pattern 3: Import Multiple Names from Module

#### Before
```python
try:
    from data_module import func1, func2, func3
except ImportError:
    func1 = None
    func2 = None
    func3 = None
```

#### After
```python
from lib.import_helpers import safe_import_from

imports = safe_import_from('data_module', ['func1', 'func2', 'func3'])
func1 = imports['func1']
func2 = imports['func2']
func3 = imports['func3']
```

**Benefits**:
- Handles partial import failures (module exists but missing some names)
- Logs missing attributes separately
- Cleaner variable assignment

---

### Pattern 4: Optional Dependency with Feature Detection

#### Before
```python
try:
    import sklearn
    from sklearn.ensemble import RandomForestRegressor
    SKLEARN_AVAILABLE = True
except (ImportError, Exception):
    SKLEARN_AVAILABLE = False
```

#### After
```python
from lib.import_helpers import try_optional_import

sklearn = try_optional_import('sklearn', package_name='scikit-learn', min_version='1.0.0')
SKLEARN_AVAILABLE = sklearn.success

if sklearn.success:
    from sklearn.ensemble import RandomForestRegressor
```

**Benefits**:
- Version checking built-in
- Helpful pip install message in logs
- Clear feature flag

---

### Pattern 5: Runtime Error Separation

#### Before (ANTI-PATTERN)
```python
try:
    from analytics_module import AnalyticsEngine
    engine = AnalyticsEngine(config=my_config)
    result = engine.run()
except (ImportError, Exception):
    # PROBLEM: Catches both missing module AND runtime errors!
    result = {"note": "Analytics not available"}
```

#### After
```python
from lib.import_helpers import safe_import
import logging

logger = logging.getLogger(__name__)

result_import = safe_import('analytics_module', 'AnalyticsEngine', log_level=logging.DEBUG)
if result_import.success:
    try:
        engine = result_import.module(config=my_config)
        result = engine.run()
    except Exception as e:
        # Now we can properly log runtime errors
        logger.error(f"Analytics engine error: {e}", exc_info=True)
        result = {"note": f"Analytics error: {type(e).__name__}"}
else:
    result = {"note": "Analytics module not available"}
```

**Benefits**:
- **Critical**: Separates missing module from bugs
- Runtime errors logged with full traceback
- User sees specific error type in fallback message

---

### Pattern 6: Conditional Import (Environment-Specific)

#### Before
```python
import sys
if sys.platform == 'linux':
    try:
        from linux_module import LinuxFeature
    except ImportError:
        LinuxFeature = None
else:
    LinuxFeature = None
```

#### After
```python
from lib.import_helpers import conditional_import
import sys

result = conditional_import(
    lambda: sys.platform == 'linux',
    'linux_module',
    'LinuxFeature'
)
LinuxFeature = result.module
```

**Benefits**:
- Cleaner condition handling
- Logs reason import was skipped
- Consistent pattern

---

## Real-World Examples from Codebase

### Example 1: PMA Intelligence Optional Analytics

**File**: `scripts/pma_intelligence.py`

**Before** (6 identical blocks):
```python
try:
    from supplement_tracker import SupplementTracker
    tracker = SupplementTracker(store=self.store)
    supp_report = tracker.generate_supplement_report(pma_key, refresh=refresh)

    if supp_report and not supp_report.get("error"):
        summary["supplement_lifecycle"] = {
            "total_supplements": supp_report.get("total_supplements", 0),
            # ... more fields
        }
except (ImportError, Exception):
    summary["supplement_lifecycle"] = {
        "note": "Supplement tracker module not available."
    }
```

**After**:
```python
result = safe_import('supplement_tracker', 'SupplementTracker', log_level=logging.DEBUG)
if result.success:
    try:
        tracker = result.module(store=self.store)
        supp_report = tracker.generate_supplement_report(pma_key, refresh=refresh)

        if supp_report and not supp_report.get("error"):
            summary["supplement_lifecycle"] = {
                "total_supplements": supp_report.get("total_supplements", 0),
                # ... more fields
            }
    except Exception as e:
        logger.error(f"Error running supplement tracker: {e}", exc_info=True)
        summary["supplement_lifecycle"] = {
            "note": f"Supplement tracker error: {type(e).__name__}"
        }
else:
    summary["supplement_lifecycle"] = {
        "note": "Supplement tracker module not available."
    }
```

**Impact**: Now bugs in supplement_tracker are logged instead of silently swallowed!

---

### Example 2: Predicate Extractor GUI Import

**File**: `scripts/predicate_extractor.py`

**Before**:
```python
try:
    import tkinter as tk
    from tkinter import filedialog, messagebox
    root = tk.Tk()
    root.withdraw()
    directory = filedialog.askdirectory()
    if not directory:
        print("No directory selected. Exiting.")
        sys.exit(1)
except (ImportError, Exception) as e:
    print(f"Error: GUI not available ({e}). Use --directory to specify PDF path.")
    sys.exit(1)
```

**After**:
```python
tk_imports = safe_import_from('tkinter', ['Tk', 'filedialog', 'messagebox'])

if tk_imports['Tk'] is None:
    print("Error: GUI not available (tkinter not installed). Use --directory to specify PDF path.")
    sys.exit(1)

try:
    Tk = tk_imports['Tk']
    filedialog = tk_imports['filedialog']

    root = Tk()
    root.withdraw()
    directory = filedialog.askdirectory()
    if not directory:
        print("No directory selected. Exiting.")
        sys.exit(1)
except Exception as e:
    logger.error(f"Error using tkinter GUI: {e}", exc_info=True)
    print(f"Error: GUI failed ({type(e).__name__}). Use --directory to specify PDF path.")
    sys.exit(1)
```

**Impact**: Missing tkinter vs GUI runtime errors now handled separately!

---

### Example 3: Scripts Package Exports

**File**: `scripts/__init__.py`

**Before** (repeated 5 times):
```python
try:
    from scripts.fda_api_client import FDAClient
except ImportError:
    try:
        from fda_api_client import FDAClient
    except ImportError:
        FDAClient = None
```

**After**:
```python
result = safe_import(
    'scripts.fda_api_client',
    'FDAClient',
    alternative_names=['fda_api_client']
)
FDAClient = result.module
```

**Impact**: 50% code reduction, consistent logging, cleaner exports!

---

## API Reference

### safe_import()

```python
def safe_import(
    module_name: str,
    class_or_function_name: Optional[str] = None,
    *,
    fallback: Optional[Any] = None,
    required: bool = False,
    log_level: int = logging.DEBUG,
    alternative_names: Optional[List[str]] = None,
) -> ImportResult
```

**Parameters**:
- `module_name`: Name of module to import
- `class_or_function_name`: Optional specific attribute to extract
- `fallback`: Value to return if import fails
- `required`: If True, log at WARNING level (default: DEBUG)
- `log_level`: Logging level for failures
- `alternative_names`: List of alternative module names to try

**Returns**: `ImportResult` with success status, module, and error details

---

### try_optional_import()

```python
def try_optional_import(
    module_name: str,
    *,
    package_name: Optional[str] = None,
    min_version: Optional[str] = None,
    log_level: int = logging.DEBUG
) -> ImportResult
```

**Parameters**:
- `module_name`: Module to import
- `package_name`: Package name for pip install message
- `min_version`: Minimum required version
- `log_level`: Logging level

**Returns**: `ImportResult` with success status and module

---

### safe_import_from()

```python
def safe_import_from(
    module_name: str,
    names: List[str],
    *,
    required: bool = False,
    log_level: int = logging.DEBUG
) -> dict
```

**Parameters**:
- `module_name`: Module to import from
- `names`: List of names to import
- `required`: Whether to log failures as warnings
- `log_level`: Logging level

**Returns**: Dict mapping name -> imported object (or None if failed)

---

### conditional_import()

```python
def conditional_import(
    condition: Callable[[], bool],
    module_name: str,
    class_or_function_name: Optional[str] = None,
    **kwargs
) -> ImportResult
```

**Parameters**:
- `condition`: Callable that returns True if import should be attempted
- `module_name`: Module to import
- `class_or_function_name`: Optional specific attribute
- `**kwargs`: Additional arguments passed to safe_import

**Returns**: `ImportResult` (success=False if condition not met)

---

### ImportResult

```python
@dataclass
class ImportResult:
    success: bool
    module: Optional[Any] = None
    error: Optional[Exception] = None
    error_type: Optional[str] = None  # 'import', 'attribute', 'syntax', 'other'
    fallback_used: bool = False
```

**Usage**:
```python
result = safe_import('my_module')
if result.success:
    # Use result.module
else:
    # Check result.error_type and result.error
```

---

## Error Type Classification

The import helpers classify errors into 4 types:

### 1. 'import' - ImportError
- **Cause**: Module not installed or not in path
- **Log Level**: DEBUG (optional) or WARNING (required)
- **Action**: Install package or add to PYTHONPATH

### 2. 'attribute' - AttributeError
- **Cause**: Module exists but missing requested class/function
- **Log Level**: WARNING
- **Action**: Check module version or function name

### 3. 'syntax' - SyntaxError
- **Cause**: Broken code in module
- **Log Level**: ERROR (with full traceback)
- **Action**: Fix syntax error in module

### 4. 'other' - Other exceptions
- **Cause**: Runtime errors during import (TypeError, ValueError, etc.)
- **Log Level**: ERROR (with full traceback)
- **Action**: Debug the error in module initialization

---

## Logging Guidelines

### Optional Dependencies
```python
result = safe_import('optional_lib', log_level=logging.DEBUG)
# Logs at DEBUG: "Module optional_lib not available..."
```

### Required Dependencies
```python
result = safe_import('required_lib', required=True)
# Logs at WARNING: "Module required_lib not available..."
```

### Conditional Features
```python
ml_result = safe_import('sklearn', log_level=logging.INFO)
if ml_result.success:
    logger.info("Machine learning features enabled")
else:
    logger.info("Running without ML features (sklearn not available)")
```

---

## Testing Imports

### Unit Tests
```python
from lib.import_helpers import safe_import

def test_optional_feature():
    result = safe_import('optional_module', 'OptionalClass')
    if result.success:
        obj = result.module()
        assert obj.method() == expected_value
    else:
        # Test fallback behavior
        assert fallback_behavior_works()
```

### Integration Tests
```python
def test_with_mock_import_failure():
    with patch('importlib.import_module', side_effect=ImportError):
        result = safe_import('my_module')
        assert result.success is False
        assert result.error_type == 'import'
```

---

## Common Mistakes to Avoid

### ❌ Don't catch broad exceptions after safe_import
```python
# BAD: Still catching everything
result = safe_import('my_module')
try:
    obj = result.module()
    result = obj.process()
except Exception:  # ❌ Too broad!
    pass
```

### ✅ Do catch specific exceptions
```python
# GOOD: Specific error handling
result = safe_import('my_module')
if result.success:
    try:
        obj = result.module()
        result = obj.process()
    except ValueError as e:  # ✅ Specific
        logger.error(f"Invalid input: {e}")
    except Exception as e:    # ✅ Log the rest
        logger.error(f"Unexpected error: {e}", exc_info=True)
```

---

### ❌ Don't ignore the error_type
```python
# BAD: Not using error classification
result = safe_import('my_module')
if not result.success:
    print("Import failed")  # ❌ No details!
```

### ✅ Do use error_type for diagnostics
```python
# GOOD: Use error classification
result = safe_import('my_module')
if not result.success:
    if result.error_type == 'import':
        print(f"Module not installed: pip install {module_name}")
    elif result.error_type == 'syntax':
        print(f"Module has syntax errors, check logs")
        logger.error(f"Syntax error: {result.error}")
```

---

## Checklist for Migration

- [ ] Add import at top of file: `from lib.import_helpers import safe_import`
- [ ] Add logging import if not present: `import logging`
- [ ] Create logger instance: `logger = logging.getLogger(__name__)`
- [ ] Replace `except (ImportError, Exception)` with `safe_import`
- [ ] Separate import failures from runtime errors
- [ ] Use appropriate log level (DEBUG for optional, WARNING for required)
- [ ] Include error type in fallback messages
- [ ] Add error logging for runtime failures
- [ ] Test both success and failure paths
- [ ] Update any relevant documentation

---

## Getting Help

- **Documentation**: See this guide and `lib/import_helpers.py` docstrings
- **Examples**: Check `scripts/pma_intelligence.py` for real-world usage
- **Tests**: See `tests/test_import_helpers.py` for comprehensive examples
- **Issues**: FDA-17 / GAP-015 for original refactoring

---

## References

- **Implementation**: `/plugins/fda-tools/lib/import_helpers.py`
- **Tests**: `/plugins/fda-tools/tests/test_import_helpers.py`
- **Documentation**: `FDA-17-GAP-015-COMPLETE.md`
- **Examples**: `scripts/pma_intelligence.py`, `scripts/__init__.py`
