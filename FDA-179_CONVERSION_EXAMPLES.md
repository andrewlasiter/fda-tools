# FDA-179: Import Conversion Examples

This document provides detailed before/after examples for converting sys.path-based imports to proper package imports.

## Table of Contents

1. [Basic Script Conversion](#basic-script-conversion)
2. [Library Module Imports](#library-module-imports)
3. [Cross-Module Dependencies](#cross-module-dependencies)
4. [Test File Conversion](#test-file-conversion)
5. [CLI Entry Points](#cli-entry-points)
6. [Circular Import Resolution](#circular-import-resolution)
7. [Optional Import Handling](#optional-import-handling)

---

## Basic Script Conversion

### Example 1: gap_analysis.py

**BEFORE (with sys.path manipulation):**

```python
#!/usr/bin/env python3
"""
gap_analysis.py — Identify missing K-numbers in 510k_output.csv
"""

import argparse
import csv
import os
import re
from collections import defaultdict

# --- sys.path hack ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PMN_FILES = [
    os.path.join(SCRIPT_DIR, "pmn96cur.txt"),
    os.path.join(SCRIPT_DIR, "pmnlstmn.txt"),
]
DEFAULT_BASELINE_CSV = os.path.join(SCRIPT_DIR, "..", "download", "510k", "510k_output.csv")

def parse_years(years_str):
    """Parse year argument into a set of year integers."""
    # ... implementation ...
    pass

def main():
    parser = argparse.ArgumentParser(description="Gap analysis for K-numbers")
    # ... parser setup ...
    args = parser.parse_args()
    # ... main logic ...

if __name__ == '__main__':
    main()
```

**AFTER (clean package import):**

```python
#!/usr/bin/env python3
"""gap_analysis.py — Identify missing K-numbers in 510k_output.csv

This module can be run as:
    python -m scripts.gap_analysis
    fda-gap-analysis  # After pip install
"""

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from typing import Set, List

# No sys.path manipulation needed!
# Use Path for cleaner path handling
SCRIPT_DIR = Path(__file__).parent
DEFAULT_PMN_FILES = [
    SCRIPT_DIR / "pmn96cur.txt",
    SCRIPT_DIR / "pmnlstmn.txt",
]
DEFAULT_BASELINE_CSV = SCRIPT_DIR.parent / "download" / "510k" / "510k_output.csv"

def parse_years(years_str: str) -> Set[int]:
    """Parse year argument into a set of year integers.

    Args:
        years_str: Year specification (e.g., "2024", "2020-2025", "2020,2024")

    Returns:
        Set of year integers
    """
    # ... implementation with type hints ...
    pass

def main() -> None:
    """Entry point for gap analysis CLI."""
    parser = argparse.ArgumentParser(description="Gap analysis for K-numbers")
    # ... parser setup ...
    args = parser.parse_args()
    # ... main logic ...

if __name__ == '__main__':
    main()
```

---

## Library Module Imports

### Example 2: batchfetch.py Importing from lib/

**BEFORE:**

```python
#!/usr/bin/env python3
import os
import sys
import requests
import pandas as pd

# BAD: Manual sys.path manipulation
try:
    _lib_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib")
    sys.path.insert(0, _lib_dir)
    from cross_process_rate_limiter import CrossProcessRateLimiter
    _CROSS_PROCESS_LIMITER_AVAILABLE = True
except ImportError:
    _CROSS_PROCESS_LIMITER_AVAILABLE = False

# BAD: Another sys.path hack for fda_http
try:
    from fda_http import create_session, FDA_WEBSITE_HEADERS
except ImportError:
    FDA_WEBSITE_HEADERS = {
        'User-Agent': 'Mozilla/5.0...',
    }
    def create_session(api_mode=False):
        session = requests.Session()
        session.headers.update(FDA_WEBSITE_HEADERS)
        return session

def main():
    if _CROSS_PROCESS_LIMITER_AVAILABLE:
        limiter = CrossProcessRateLimiter()
        # ...
```

**AFTER:**

```python
#!/usr/bin/env python3
"""FDA 510(k) Batch Fetch Tool

This module can be run as:
    python -m scripts.batchfetch
    fda-batchfetch  # After pip install
"""

from typing import Optional
import requests
import pandas as pd

# GOOD: Clean imports with graceful fallbacks
try:
    from fda_tools.lib.cross_process_rate_limiter import CrossProcessRateLimiter
    _CROSS_PROCESS_LIMITER_AVAILABLE = True
except ImportError:
    _CROSS_PROCESS_LIMITER_AVAILABLE = False

try:
    from fda_tools.lib.fda_http import create_session, FDA_WEBSITE_HEADERS
except ImportError:
    # Fallback implementation
    FDA_WEBSITE_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                     'AppleWebKit/537.36 (KHTML, like Gecko) '
                     'Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }

    def create_session(api_mode: bool = False) -> requests.Session:
        """Create HTTP session with proper headers."""
        session = requests.Session()
        session.headers.update(FDA_WEBSITE_HEADERS)
        return session

def main() -> None:
    """Entry point for batch fetch CLI."""
    if _CROSS_PROCESS_LIMITER_AVAILABLE:
        limiter = CrossProcessRateLimiter()
        # ...
```

---

## Cross-Module Dependencies

### Example 3: Module Importing from Same Package

**BEFORE (lib/gap_analyzer.py):**

```python
import os
import sys
from typing import Dict, List

# BAD: Import sibling module with sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from predicate_ranker import PredicateRanker
from expert_validator import ExpertValidator

class GapAnalyzer:
    def __init__(self):
        self.ranker = PredicateRanker()
        self.validator = ExpertValidator()
```

**AFTER (lib/gap_analyzer.py):**

```python
"""Gap analysis module for detecting missing device data."""

from typing import Dict, List, Optional

# GOOD: Relative imports within package
from .predicate_ranker import PredicateRanker
from .expert_validator import ExpertValidator

# OR absolute imports
from fda_tools.lib.predicate_ranker import PredicateRanker
from fda_tools.lib.expert_validator import ExpertValidator

class GapAnalyzer:
    """Analyzes gaps in device submissions."""

    def __init__(self) -> None:
        """Initialize analyzer with ranker and validator."""
        self.ranker = PredicateRanker()
        self.validator = ExpertValidator()
```

---

## Test File Conversion

### Example 4: Test Importing Production Code

**BEFORE (tests/test_gap_analyzer.py):**

```python
import os
import sys
import pytest

# BAD: Complex path manipulation
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
LIB_DIR = os.path.join(TEST_DIR, '..', 'lib')
SCRIPTS_DIR = os.path.join(TEST_DIR, '..', 'scripts')
sys.path.insert(0, LIB_DIR)
sys.path.insert(0, SCRIPTS_DIR)

from gap_analyzer import GapAnalyzer
from fda_data_store import get_projects_dir

def test_gap_detection():
    analyzer = GapAnalyzer()
    gaps = analyzer.detect_testing_gaps({})
    assert gaps is not None
```

**AFTER (tests/test_gap_analyzer.py):**

```python
"""Tests for gap_analyzer module."""

import pytest
from typing import Dict, Any

# GOOD: Direct imports, pytest handles PYTHONPATH
from fda_tools.lib.gap_analyzer import GapAnalyzer
from fda_tools.scripts.fda_data_store import get_projects_dir

# OR use relative imports (if tests/ is a package)
from lib.gap_analyzer import GapAnalyzer
from scripts.fda_data_store import get_projects_dir

def test_gap_detection() -> None:
    """Test gap detection with empty device data."""
    analyzer = GapAnalyzer()
    gaps = analyzer.detect_testing_gaps({})
    assert gaps is not None
    assert isinstance(gaps, dict)

def test_gap_analyzer_initialization() -> None:
    """Test GapAnalyzer can be instantiated."""
    analyzer = GapAnalyzer()
    assert analyzer is not None
    assert hasattr(analyzer, 'detect_testing_gaps')
```

---

## CLI Entry Points

### Example 5: Making Scripts Installable

**BEFORE (scripts/batchfetch.py):**

```python
#!/usr/bin/env python3
import argparse
import sys

def main():
    parser = argparse.ArgumentParser()
    # ... parser setup ...
    args = parser.parse_args()
    # ... main logic ...
    print("Batch fetch complete!")

# This only works when running script directly
if __name__ == '__main__':
    main()
```

**AFTER (scripts/batchfetch.py):**

```python
#!/usr/bin/env python3
"""FDA 510(k) Batch Fetch Tool

Can be invoked as:
    python -m scripts.batchfetch --help
    fda-batchfetch --help  # After pip install

The main() function is registered as a CLI entry point in pyproject.toml.
"""

import argparse
import sys
from typing import Optional

def main(argv: Optional[list[str]] = None) -> int:
    """Entry point for batch fetch CLI.

    Args:
        argv: Command line arguments (defaults to sys.argv)

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    parser = argparse.ArgumentParser(
        description="FDA 510(k) Batch Fetch Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    # ... parser setup ...
    args = parser.parse_args(argv)

    try:
        # ... main logic ...
        print("Batch fetch complete!")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
```

**pyproject.toml entry:**

```toml
[project.scripts]
fda-batchfetch = "scripts.batchfetch:main"
```

Now `fda-batchfetch` is available system-wide after `pip install`!

---

## Circular Import Resolution

### Example 6: Avoiding Circular Dependencies

**BEFORE (causes circular import):**

```python
# lib/gap_analyzer.py
from predicate_ranker import PredicateRanker

class GapAnalyzer:
    def analyze(self):
        ranker = PredicateRanker()
        return ranker.rank_gaps(self)

# lib/predicate_ranker.py
from gap_analyzer import GapAnalyzer  # CIRCULAR!

class PredicateRanker:
    def rank_gaps(self, analyzer: GapAnalyzer):
        gaps = analyzer.analyze()  # Circular dependency
```

**AFTER (proper solution):**

```python
# lib/gap_analyzer.py
"""Gap analysis module."""

from typing import TYPE_CHECKING

# Import only for type checking (not at runtime)
if TYPE_CHECKING:
    from .predicate_ranker import PredicateRanker

class GapAnalyzer:
    """Analyzes submission gaps."""

    def analyze(self, ranker: 'PredicateRanker') -> dict:
        """Analyze gaps using provided ranker.

        Args:
            ranker: PredicateRanker instance (injected dependency)

        Returns:
            Dictionary of ranked gaps
        """
        return ranker.rank_gaps(self)

# lib/predicate_ranker.py
"""Predicate ranking module."""

from typing import Any, Dict

class PredicateRanker:
    """Ranks predicates by quality score."""

    def rank_gaps(self, analyzer: Any) -> Dict[str, Any]:
        """Rank gaps from analyzer.

        Args:
            analyzer: GapAnalyzer instance

        Returns:
            Ranked gaps dictionary
        """
        # Access analyzer without circular import
        gap_data = analyzer.get_gap_data()
        return self._rank(gap_data)
```

**Alternative: Lazy import in function**

```python
# lib/gap_analyzer.py
class GapAnalyzer:
    def analyze(self):
        # Import only when needed (function-level import)
        from .predicate_ranker import PredicateRanker
        ranker = PredicateRanker()
        return ranker.rank_gaps(self)
```

---

## Optional Import Handling

### Example 7: Graceful Degradation for Optional Dependencies

**BEFORE:**

```python
# No handling of missing dependencies
import sklearn
from sklearn.ensemble import RandomForestClassifier

def predict_approval(data):
    model = RandomForestClassifier()
    return model.predict(data)
```

**AFTER:**

```python
"""Approval prediction with optional ML support."""

from typing import Any, Optional
import warnings

# Graceful handling of optional dependency
try:
    import sklearn
    from sklearn.ensemble import RandomForestClassifier
    _SKLEARN_AVAILABLE = True
except ImportError:
    _SKLEARN_AVAILABLE = False
    sklearn = None
    RandomForestClassifier = None

def predict_approval(data: Any) -> Optional[float]:
    """Predict approval probability.

    Falls back to rule-based scoring if scikit-learn not installed.

    Args:
        data: Device submission data

    Returns:
        Approval probability (0.0-1.0) or None if unavailable
    """
    if _SKLEARN_AVAILABLE:
        model = RandomForestClassifier()
        return model.predict(data)
    else:
        warnings.warn(
            "scikit-learn not installed. "
            "Install with: pip install 'fda-tools[optional]' "
            "Falling back to rule-based scoring.",
            category=ImportWarning,
        )
        return _rule_based_score(data)

def _rule_based_score(data: Any) -> float:
    """Simple rule-based approval score as fallback."""
    # ... implementation ...
    return 0.75  # Example
```

---

## Package __init__.py Patterns

### Example 8: lib/__init__.py

**AFTER (new file):**

```python
"""FDA Tools Library Package

Core functionality for FDA regulatory tools.

Public API:
    - GapAnalyzer: Detect missing device data
    - FDAEnrichment: Enrich device data from FDA APIs
    - PredicateRanker: Rank predicate quality
    - ExpertValidator: Validate submissions
"""

# Public API exports for convenience
try:
    from .gap_analyzer import (
        GapAnalyzer,
        detect_missing_device_data,
        detect_weak_predicates,
        detect_testing_gaps,
        analyze_all_gaps,
    )
    from .fda_enrichment import FDAEnrichment
    from .predicate_ranker import PredicateRanker, rank_predicates
    from .expert_validator import ExpertValidator
    from .combination_detector import CombinationProductDetector
    from .ecopy_exporter import eCopyExporter
    from .disclaimers import (
        get_csv_header_disclaimer,
        get_html_banner_disclaimer,
    )
    from .import_helpers import safe_import, safe_import_from
    from .logging_config import setup_logging, get_logger
    from .secure_config import SecureConfig

    __all__ = [
        # Gap Analysis
        'GapAnalyzer',
        'detect_missing_device_data',
        'detect_weak_predicates',
        'detect_testing_gaps',
        'analyze_all_gaps',
        # Enrichment
        'FDAEnrichment',
        # Ranking
        'PredicateRanker',
        'rank_predicates',
        # Validation
        'ExpertValidator',
        # Detection
        'CombinationProductDetector',
        # Export
        'eCopyExporter',
        # Disclaimers
        'get_csv_header_disclaimer',
        'get_html_banner_disclaimer',
        # Utilities
        'safe_import',
        'safe_import_from',
        'setup_logging',
        'get_logger',
        'SecureConfig',
    ]
except ImportError:
    # Graceful degradation if modules not available
    __all__ = []
```

Now users can do:
```python
from fda_tools.lib import GapAnalyzer, FDAEnrichment
# Instead of:
from fda_tools.lib.gap_analyzer import GapAnalyzer
from fda_tools.lib.fda_enrichment import FDAEnrichment
```

---

## Complete Migration Checklist

For each file being migrated:

```python
# 1. REMOVE sys.path manipulation
# Delete these lines:
import sys
import os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ...)

# 2. UPDATE imports to use package paths
# Change:
from gap_analyzer import GapAnalyzer
# To:
from fda_tools.lib.gap_analyzer import GapAnalyzer
# Or relative:
from .gap_analyzer import GapAnalyzer

# 3. ADD type hints
def process_data(data):  # BEFORE
def process_data(data: Dict[str, Any]) -> List[str]:  # AFTER

# 4. UPDATE docstrings to Google style
def func():
    """Does something."""  # BEFORE

def func() -> None:
    """Does something.

    Args:
        param1: Description

    Returns:
        Description

    Raises:
        ValueError: When invalid input
    """  # AFTER

# 5. USE pathlib.Path for file paths
import os
file_path = os.path.join(dir, "file.txt")  # BEFORE

from pathlib import Path
file_path = Path(dir) / "file.txt"  # AFTER

# 6. TEST the changes
pytest tests/test_module.py -v
```

---

## Summary of Import Patterns

| Context | Old Pattern | New Pattern |
|---------|------------|-------------|
| Script importing lib | `sys.path.insert(0, lib_dir)`<br>`from module import X` | `from fda_tools.lib.module import X` |
| Lib importing lib | `from module import X` | `from .module import X`<br>or `from fda_tools.lib.module import X` |
| Test importing code | `sys.path.insert(0, lib_dir)`<br>`from module import X` | `from fda_tools.lib.module import X` |
| Optional imports | `import module` (fails if missing) | `try: import module`<br>`except: module = None` |
| Circular imports | Direct import at top | `from typing import TYPE_CHECKING`<br>`if TYPE_CHECKING: import module` |
| CLI entry point | `if __name__ == '__main__': main()` | Entry point in pyproject.toml<br>`[project.scripts]` |

---

**Last Updated:** 2026-02-20
**Related:** FDA-179 (ARCH-001)
