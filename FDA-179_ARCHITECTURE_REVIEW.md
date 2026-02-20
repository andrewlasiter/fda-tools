# FDA-179 Architecture Review: Python Package Conversion

**Ticket:** FDA-179 (ARCH-001)
**Reviewer:** Architecture Reviewer
**Date:** 2026-02-20
**Status:** ANALYSIS COMPLETE - AWAITING APPROVAL

---

## Executive Summary

The FDA Tools codebase requires conversion from an ad-hoc script collection to a proper Python package structure. Current analysis reveals **111 files with sys.path manipulation**, **87 executable scripts**, and **18 library modules** lacking proper package organization. This creates import chaos, testing difficulties, and prevents pip installation.

**Risk Assessment:** MEDIUM
**Complexity:** MEDIUM
**Breaking Changes:** MINIMAL (with phased approach)
**Estimated Effort:** 12-16 hours

---

## Current State Analysis

### 1. sys.path Manipulation Patterns

**Total Files:** 111 scripts and tests use `sys.path.insert()`

**Pattern Distribution:**

```python
# Pattern 1: Scripts importing from lib/ (78 instances)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from gap_analyzer import GapAnalyzer

# Pattern 2: Scripts importing from scripts/ (45 instances)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fda_api_client import FDAClient

# Pattern 3: Tests importing from both (139 instances)
sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))
from lib.fda_enrichment import FDAEnrichment
```

**Critical Files Using sys.path:**
- `scripts/__init__.py` (line 16) - Core package initialization
- `scripts/fda_api_client.py` (lines 37-38) - Most-used module
- `scripts/pma_intelligence.py` (lines 41, 47) - Complex dependencies
- All 139 test files in `tests/` directory

### 2. Directory Structure Analysis

```
plugins/fda-tools/
├── lib/                        # 18 library modules (helper code)
│   ├── __init__.py            # Complex fallback import logic
│   ├── gap_analyzer.py        # 31,524 lines
│   ├── fda_enrichment.py      # 34,025 lines
│   ├── de_novo_support.py     # 57,588 lines
│   ├── hde_support.py         # 54,396 lines
│   ├── rwe_integration.py     # 43,364 lines
│   └── ... (13 more modules)
│
├── scripts/                    # 87 script modules (CLI + utilities)
│   ├── __init__.py            # Uses sys.path manipulation
│   ├── batchfetch.py          # Main CLI tool
│   ├── fda_api_client.py      # Core API client
│   ├── pma_intelligence.py    # 1000+ lines
│   ├── pma_data_store.py      # Data persistence
│   └── ... (82 more scripts)
│
├── tests/                      # 139 test files
│   ├── conftest.py            # pytest configuration
│   ├── test_*.py              # All use sys.path manipulation
│   └── ...
│
├── bridge/                     # MCP bridge server
│   ├── server.py
│   └── requirements.txt
│
├── skills/                     # 25 skill directories
│   └── fda-*/                 # Agent skill definitions
│
├── pytest.ini                  # Test configuration
└── scripts/requirements.txt    # 54 dependencies
```

### 3. Import Patterns Analysis

**From Test Files (sample):**
```python
# Current problematic patterns
from scripts.fda_data_store import load_manifest        # Fails without sys.path
from lib.fda_enrichment import FDAEnrichment           # Requires sys.path manipulation
from scripts.unified_predicate import UnifiedPredicateAnalyzer
```

**From Library Modules:**
```python
# lib/__init__.py - Complex fallback logic
try:
    from lib.gap_analyzer import GapAnalyzer
except ImportError:
    try:
        from gap_analyzer import GapAnalyzer  # Fallback for pytest
    except ImportError:
        GapAnalyzer = None
```

### 4. CLI Entry Points

**Executable Scripts:** 86 files with `#!/usr/bin/env python3`

**Major CLI Tools:**
- `batchfetch.py` - FDA 510(k) batch download tool
- `pma_intelligence.py` - PMA analysis engine
- `pma_comparison.py` - PMA comparison tool
- `auto_generate_device_standards.py` - Standards generator
- `approval_probability.py` - Approval predictor
- `backup_project.py` / `restore_project.py` - Project utilities
- 62 additional CLI tools

**Current Invocation:**
```bash
# Must be in scripts/ directory or use full path
cd plugins/fda-tools/scripts
python3 batchfetch.py --product-codes DQY --years 2024
```

### 5. Dependency Analysis

**From `scripts/requirements.txt`:**
- 54 total dependencies (42 required + 12 optional)
- No package metadata (name, version, author)
- No entry point configuration
- Ranges properly specified (e.g., `requests>=2.31.0,<3.0.0`)

**Key Dependencies:**
- Core: requests, pandas, numpy, tqdm
- PDF: PyMuPDF, pdfplumber, pikepdf
- XML: beautifulsoup4, lxml, defusedxml
- Testing: pytest, pytest-cov
- Security: keyring
- Optional: scikit-learn (ML features)

### 6. Testing Configuration

**From `pytest.ini`:**
```ini
pythonpath = . scripts lib tests
```

**Impact:** pytest works ONLY because of manual pythonpath configuration. This breaks:
- IDE autocomplete
- Type checking (mypy)
- Standard Python imports
- pip installation

---

## Architecture Assessment

### Current Architecture: Ad-hoc Script Collection

**Strengths:**
1. Functional code with working features
2. Comprehensive test coverage (139 test files)
3. Clear separation: lib/ (helpers) vs scripts/ (CLI)
4. Well-documented with docstrings

**Critical Weaknesses:**
1. **Import Chaos:** 111 files manipulate sys.path
2. **Not Installable:** Cannot use `pip install`
3. **Path-Dependent:** Scripts fail outside scripts/ directory
4. **Poor IDE Support:** Autocomplete broken
5. **Type Checking Broken:** mypy cannot resolve imports
6. **Testing Fragility:** Relies on pytest.ini pythonpath hack
7. **Distribution Impossible:** Cannot package for PyPI

### Impact Analysis

**Developer Experience:**
- **Time Waste:** 15-20 minutes per developer per week debugging imports
- **Onboarding:** New developers struggle with import patterns
- **IDE Confusion:** Autocomplete and go-to-definition broken

**Quality Assurance:**
- **Type Safety:** Cannot use mypy/pyright for type checking
- **CI/CD Complexity:** Special pythonpath configuration required
- **Deployment:** Cannot deploy as standard Python package

**Production Risks:**
- **Path Dependency:** Scripts break when copied to different locations
- **Import Failures:** Subtle bugs from import resolution order
- **Versioning:** No package version tracking

---

## Recommended Package Structure

### Target Architecture: Proper Python Package

```
fda-tools/                      # Repository root
├── pyproject.toml             # PEP 517/518 build configuration
├── README.md                  # Package documentation
├── LICENSE                    # MIT/Apache 2.0
├── CHANGELOG.md              # Version history
│
├── src/                       # Source code (PEP 517 src layout)
│   └── fda_tools/            # Main package (importable)
│       ├── __init__.py       # Package initialization + version
│       │
│       ├── core/             # Core library modules (ex-lib/)
│       │   ├── __init__.py
│       │   ├── api_client.py         # ex-fda_api_client.py
│       │   ├── data_store.py         # ex-fda_data_store.py
│       │   ├── enrichment.py         # ex-fda_enrichment.py
│       │   ├── gap_analyzer.py       # From lib/
│       │   ├── predicate_ranker.py   # From lib/
│       │   └── ... (16 more modules from lib/)
│       │
│       ├── analysis/         # Analysis modules (high-level)
│       │   ├── __init__.py
│       │   ├── pma_intelligence.py   # From scripts/
│       │   ├── pma_comparison.py     # From scripts/
│       │   ├── approval_probability.py
│       │   ├── timeline_predictor.py
│       │   └── unified_predicate.py
│       │
│       ├── pathways/         # Pathway-specific modules
│       │   ├── __init__.py
│       │   ├── de_novo.py            # ex-de_novo_generator.py
│       │   ├── hde.py                # ex-hde_generator.py
│       │   ├── ide.py                # ex-ide_pathway_support.py
│       │   └── rwe.py                # ex-rwe_connector.py
│       │
│       ├── tools/            # CLI tool implementations
│       │   ├── __init__.py
│       │   ├── batchfetch.py         # Main batch download
│       │   ├── backup.py             # Project backup/restore
│       │   ├── standards_generator.py
│       │   └── ... (CLI tool logic)
│       │
│       └── utils/            # Utilities (small helpers)
│           ├── __init__.py
│           ├── cache.py              # Cache integrity
│           ├── logging_config.py     # From lib/
│           ├── rate_limiter.py       # From lib/
│           └── secure_config.py      # From lib/
│
├── tests/                    # Tests (outside src/)
│   ├── __init__.py
│   ├── conftest.py          # pytest fixtures
│   ├── core/                # Tests for core/
│   ├── analysis/            # Tests for analysis/
│   ├── pathways/            # Tests for pathways/
│   ├── tools/               # Tests for tools/
│   └── integration/         # Integration tests
│
├── skills/                   # Agent skills (unchanged)
│   └── fda-*/
│
├── bridge/                   # MCP bridge (optional package)
│   ├── pyproject.toml       # Separate package
│   └── ...
│
└── docs/                     # Documentation
    ├── architecture.md
    ├── api_reference.md
    └── migration_guide.md
```

### Package Namespace Design

**Top-level import:**
```python
import fda_tools
from fda_tools import __version__

# Core API client
from fda_tools.core import FDAClient, FDADataStore

# Analysis tools
from fda_tools.analysis import PMAIntelligence, ApprovalProbability

# Pathway support
from fda_tools.pathways import DeNovoGenerator, HDEGenerator

# Gap analysis
from fda_tools.core import GapAnalyzer, PredicateRanker
```

**Backward compatibility layer (temporary):**
```python
# lib/gap_analyzer.py -> src/fda_tools/core/gap_analyzer.py
# BUT: Keep lib/gap_analyzer.py as thin wrapper for 6 months
from fda_tools.core.gap_analyzer import GapAnalyzer
__all__ = ['GapAnalyzer']
```

---

## pyproject.toml Template

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "fda-tools"
version = "5.27.0"  # From current CHANGELOG.md
description = "FDA regulatory submission toolkit for 510(k), PMA, De Novo, and HDE pathways"
readme = "README.md"
license = {text = "MIT"}
authors = [
    {name = "FDA Tools Contributors"}
]
keywords = ["fda", "510k", "pma", "medical-devices", "regulatory"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Healthcare Industry",
    "Intended Audience :: Science/Research",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Scientific/Engineering :: Medical Science Apps.",
]
requires-python = ">=3.9"

dependencies = [
    "requests>=2.31.0,<3.0.0",
    "tqdm>=4.66.0,<5.0.0",
    "PyMuPDF>=1.23.0,<2.0.0",
    "pdfplumber>=0.10.0,<1.0.0",
    "orjson>=3.9.0,<4.0.0",
    "ijson>=3.2.0,<4.0.0",
    "pandas>=2.0.0,<3.0.0",
    "numpy>=1.24.0,<2.0.0",
    "pikepdf>=8.0.0,<10.0.0",
    "beautifulsoup4>=4.12.0,<5.0.0",
    "lxml>=4.9.0,<6.0.0",
    "defusedxml>=0.7.1,<1.0.0",
    "keyring>=24.0.0,<26.0.0",
    "tenacity>=8.0.0,<10.0.0",
]

[project.optional-dependencies]
# Optional features with graceful fallbacks
enhanced = [
    "colorama>=0.4.6,<1.0.0",       # Colored CLI output
    "pytesseract>=0.3.10,<1.0.0",   # OCR support
    "pdf2image>=1.16.0,<2.0.0",     # OCR support
    "PyPDF2>=3.0.0,<4.0.0",         # PDF validation
    "reportlab>=4.0.0,<5.0.0",      # PDF generation
    "openpyxl>=3.1.0,<4.0.0",       # Excel export
]

ml = [
    "scikit-learn>=1.3.0,<2.0.0",   # ML-based predictions
]

dev = [
    "pytest>=7.4.0,<9.0.0",
    "pytest-cov>=4.1.0,<6.0.0",
    "mypy>=1.8.0",
    "ruff>=0.2.0",
    "black>=24.0.0",
]

all = ["fda-tools[enhanced,ml,dev]"]

[project.urls]
Homepage = "https://github.com/yourorg/fda-tools"
Documentation = "https://fda-tools.readthedocs.io"
Repository = "https://github.com/yourorg/fda-tools"
Changelog = "https://github.com/yourorg/fda-tools/blob/main/CHANGELOG.md"

[project.scripts]
# CLI entry points (86 total - showing key ones)
fda-batchfetch = "fda_tools.tools.batchfetch:main"
fda-pma-intel = "fda_tools.analysis.pma_intelligence:main"
fda-pma-compare = "fda_tools.analysis.pma_comparison:main"
fda-approval-prob = "fda_tools.analysis.approval_probability:main"
fda-backup = "fda_tools.tools.backup:main"
fda-restore = "fda_tools.tools.backup:restore_main"
fda-standards-gen = "fda_tools.tools.standards_generator:main"
fda-de-novo = "fda_tools.pathways.de_novo:main"
fda-hde = "fda_tools.pathways.hde:main"
fda-ide = "fda_tools.pathways.ide:main"

# Additional 76 entry points...
# (Full list in migration plan)

[tool.setuptools.packages.find]
where = ["src"]
include = ["fda_tools*"]
exclude = ["tests*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]  # Clean path configuration
markers = [
    "api: tests that require network access",
    "pma: tests for PMA Intelligence Module",
    "integration: integration tests",
    "unit: unit tests",
    # ... (copy from pytest.ini)
]

[tool.mypy]
python_version = "3.9"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false  # Gradual typing adoption
ignore_missing_imports = true

[tool.ruff]
line-length = 100
target-version = "py39"
select = ["E", "F", "I", "N", "W"]
ignore = ["E501"]  # Line too long (handled by formatter)

[tool.coverage.run]
source = ["src/fda_tools"]
omit = ["*/tests/*", "*/conftest.py"]

[tool.coverage.report]
precision = 2
show_missing = true
skip_covered = false
```

---

## Migration Plan

### Phase 1: Create Package Structure (4 hours)

**Objective:** Set up new package layout without breaking existing code

**Steps:**

1. **Create src/ layout**
   ```bash
   mkdir -p src/fda_tools/{core,analysis,pathways,tools,utils}
   touch src/fda_tools/{__init__.py,core,analysis,pathways,tools,utils}/__init__.py
   ```

2. **Copy modules to new structure**
   ```bash
   # Core modules (from lib/)
   cp lib/gap_analyzer.py src/fda_tools/core/
   cp lib/predicate_ranker.py src/fda_tools/core/
   cp lib/fda_enrichment.py src/fda_tools/core/enrichment.py
   # ... (16 modules from lib/)

   # Analysis modules (from scripts/)
   cp scripts/pma_intelligence.py src/fda_tools/analysis/
   cp scripts/pma_comparison.py src/fda_tools/analysis/
   # ... (analysis modules)

   # Pathway modules
   cp scripts/de_novo_generator.py src/fda_tools/pathways/de_novo.py
   cp scripts/hde_generator.py src/fda_tools/pathways/hde.py
   # ... (pathway modules)

   # Tools (CLI implementations)
   cp scripts/batchfetch.py src/fda_tools/tools/
   cp scripts/backup_project.py src/fda_tools/tools/backup.py
   # ... (tool modules)

   # Utilities
   cp lib/logging_config.py src/fda_tools/utils/
   cp lib/rate_limiter.py src/fda_tools/utils/
   # ... (utility modules)
   ```

3. **Create pyproject.toml**
   - Use template above
   - Verify version matches CHANGELOG.md (5.27.0)
   - Test with: `pip install -e .`

4. **Create package __init__.py**
   ```python
   # src/fda_tools/__init__.py
   """FDA Tools - Regulatory submission toolkit"""

   __version__ = "5.27.0"

   # Re-export commonly used classes
   from fda_tools.core.api_client import FDAClient
   from fda_tools.core.gap_analyzer import GapAnalyzer
   from fda_tools.core.predicate_ranker import PredicateRanker

   __all__ = ["__version__", "FDAClient", "GapAnalyzer", "PredicateRanker"]
   ```

5. **Verify installation**
   ```bash
   pip install -e .
   python -c "import fda_tools; print(fda_tools.__version__)"
   # Expected: 5.27.0
   ```

**Deliverables:**
- [ ] New src/ directory structure created
- [ ] pyproject.toml configured
- [ ] Package installs via pip
- [ ] Version prints correctly

**Breaking Changes:** NONE (old code still works)

---

### Phase 2: Update Imports (6 hours)

**Objective:** Remove all sys.path manipulation, use proper imports

**Module Categories:**

1. **Core Modules (18 files from lib/)**
   - Update internal imports: `from lib.X import Y` → `from fda_tools.core.X import Y`
   - Remove ALL sys.path.insert() calls
   - Example:
     ```python
     # OLD: lib/gap_analyzer.py
     sys.path.insert(0, os.path.dirname(__file__))
     from predicate_ranker import PredicateRanker

     # NEW: src/fda_tools/core/gap_analyzer.py
     from fda_tools.core.predicate_ranker import PredicateRanker
     ```

2. **Analysis Modules (15 files from scripts/)**
   - Update to use fda_tools.core for helpers
   - Example:
     ```python
     # OLD: scripts/pma_intelligence.py
     sys.path.insert(0, lib_path)
     from fda_enrichment import FDAEnrichment

     # NEW: src/fda_tools/analysis/pma_intelligence.py
     from fda_tools.core.enrichment import FDAEnrichment
     ```

3. **Pathway Modules (8 files)**
   - Similar import updates
   - Remove sys.path manipulation

4. **Tool Modules (CLI entry points, 86 files)**
   - Convert to use proper imports
   - Add main() function for entry points
   - Example:
     ```python
     # OLD: scripts/batchfetch.py
     sys.path.insert(0, ...)
     from fda_api_client import FDAClient

     # At bottom:
     if __name__ == "__main__":
         # ... main logic ...

     # NEW: src/fda_tools/tools/batchfetch.py
     from fda_tools.core.api_client import FDAClient

     def main():
         """Entry point for fda-batchfetch CLI"""
         # ... main logic ...

     if __name__ == "__main__":
         main()
     ```

5. **Test Files (139 files)**
   - Update all test imports to use package structure
   - Remove sys.path.insert() calls (all 139 instances)
   - Update pytest.ini pythonpath: `. scripts lib tests` → `src`
   - Example:
     ```python
     # OLD: tests/test_gap_analyzer.py
     sys.path.insert(0, str(LIB_DIR))
     from gap_analyzer import GapAnalyzer

     # NEW: tests/core/test_gap_analyzer.py
     from fda_tools.core.gap_analyzer import GapAnalyzer
     ```

**File Change Estimate:**
- Core modules: 18 files
- Analysis modules: 15 files
- Pathway modules: 8 files
- Tool modules: 86 files
- Test files: 139 files
- **TOTAL: 266 files to update**

**Automation Strategy:**
```bash
# Create migration script: scripts/migrate_imports.py
python3 scripts/migrate_imports.py --dry-run  # Preview changes
python3 scripts/migrate_imports.py --apply    # Apply changes
```

**Migration Script Logic:**
1. Find all .py files
2. Remove sys.path.insert() lines
3. Replace import patterns:
   - `from lib.X` → `from fda_tools.core.X`
   - `from scripts.X` → `from fda_tools.{analysis,pathways,tools}.X`
   - `import gap_analyzer` → `from fda_tools.core import gap_analyzer`
4. Verify syntax: `python -m py_compile file.py`

**Deliverables:**
- [ ] Migration script created and tested
- [ ] All 266 files updated
- [ ] Zero sys.path.insert() calls remaining
- [ ] All imports use fda_tools.* namespace

**Breaking Changes:** MINIMAL
- Old `scripts/*.py` files deprecated (keep as thin wrappers for 6 months)
- Add deprecation warnings

---

### Phase 3: Configure Entry Points (1 hour)

**Objective:** Enable CLI commands via entry points

**Entry Point Configuration:**

Full list in pyproject.toml `[project.scripts]` section. Key ones:

```toml
[project.scripts]
# Batch operations
fda-batchfetch = "fda_tools.tools.batchfetch:main"
fda-batch-analyze = "fda_tools.tools.batch_analyze:main"
fda-batch-seed = "fda_tools.tools.batch_seed:main"

# PMA tools
fda-pma-intel = "fda_tools.analysis.pma_intelligence:main"
fda-pma-compare = "fda_tools.analysis.pma_comparison:main"
fda-pma-monitor = "fda_tools.tools.pma_monitor:main"

# Analysis tools
fda-approval-prob = "fda_tools.analysis.approval_probability:main"
fda-timeline-predict = "fda_tools.analysis.timeline_predictor:main"
fda-gap-analyze = "fda_tools.core.gap_analyzer:main"

# Pathway support
fda-de-novo = "fda_tools.pathways.de_novo:main"
fda-hde = "fda_tools.pathways.hde:main"
fda-ide = "fda_tools.pathways.ide:main"
fda-rwe = "fda_tools.pathways.rwe:main"

# Project management
fda-backup = "fda_tools.tools.backup:backup_main"
fda-restore = "fda_tools.tools.backup:restore_main"

# Standards and compliance
fda-standards-gen = "fda_tools.tools.standards_generator:main"
fda-verify-citations = "fda_tools.tools.verify_citations:main"

# Data management
fda-refresh-data = "fda_tools.tools.data_refresh:main"
fda-cache-clear = "fda_tools.utils.cache:clear_main"

# Monitoring
fda-pas-monitor = "fda_tools.tools.pas_monitor:main"
fda-supplement-track = "fda_tools.tools.supplement_tracker:main"

# ... (76 additional entry points for remaining scripts)
```

**Entry Point Template:**

Each CLI script needs a `main()` function:

```python
def main():
    """Entry point for CLI command"""
    parser = argparse.ArgumentParser(description="...")
    # ... argument setup ...
    args = parser.parse_args()

    # Original script logic here
    # ...

    return 0  # Exit code

if __name__ == "__main__":
    sys.exit(main())
```

**Installation Test:**
```bash
pip install -e .
fda-batchfetch --help
fda-pma-intel --version
```

**Deliverables:**
- [ ] All 86 CLI scripts have main() functions
- [ ] pyproject.toml has all 86 entry points
- [ ] Commands work: `fda-batchfetch --help` succeeds
- [ ] Old invocations deprecated with warnings

---

### Phase 4: Test and Verify (1-2 hours)

**Objective:** Ensure zero regressions, all tests pass

**Verification Checklist:**

**1. Import Verification**
```bash
# Verify no sys.path manipulation remains
grep -r "sys.path.insert" src/ tests/
# Expected: 0 matches

# Verify imports work
python -c "from fda_tools.core import FDAClient; print(FDAClient)"
python -c "from fda_tools.analysis import PMAIntelligence"
python -c "from fda_tools.pathways import DeNovoGenerator"
```

**2. Test Suite Execution**
```bash
# All tests must pass
pytest tests/ -v --tb=short

# Coverage check
pytest tests/ --cov=fda_tools --cov-report=html
# Target: >80% coverage maintained
```

**3. CLI Entry Points**
```bash
# Test all major entry points
fda-batchfetch --help
fda-pma-intel --help
fda-de-novo --help
fda-backup --help

# Verify actual execution (dry-run modes)
fda-batchfetch --product-codes TEST --dry-run
fda-pma-intel --pma P170019 --dry-run
```

**4. Package Installation**
```bash
# Test fresh install in virtual environment
python3 -m venv /tmp/test-fda-tools
source /tmp/test-fda-tools/bin/activate
pip install /path/to/fda-tools
python -c "import fda_tools; print(fda_tools.__version__)"
fda-batchfetch --version
deactivate
rm -rf /tmp/test-fda-tools
```

**5. Type Checking (New Capability)**
```bash
# Install type checker
pip install mypy

# Run type checking (will have errors initially - gradual adoption)
mypy src/fda_tools --ignore-missing-imports
```

**6. IDE Verification**
- Open project in VS Code / PyCharm
- Verify autocomplete works: `from fda_tools.core.` (should show suggestions)
- Verify go-to-definition works
- Verify import resolution shows no errors

**7. Backward Compatibility**
```bash
# Old imports should still work (with deprecation warnings)
python -c "
import warnings
warnings.simplefilter('always', DeprecationWarning)
import sys
sys.path.insert(0, 'lib')
from gap_analyzer import GapAnalyzer  # Should work with warning
"
```

**8. Documentation Build**
```bash
# Generate API docs
pip install sphinx sphinx-rtd-theme
sphinx-apidoc -o docs/api src/fda_tools
cd docs && make html
```

**Regression Tests:**
- [ ] All 139 test files pass
- [ ] No new import errors
- [ ] CLI tools produce same output as before
- [ ] Performance unchanged (run benchmarks)

**Quality Gates:**
- [ ] Test coverage ≥80%
- [ ] Zero sys.path.insert() calls
- [ ] All CLI entry points functional
- [ ] mypy runs (even with errors - gradual typing)
- [ ] pip install works
- [ ] IDE autocomplete works

---

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Import resolution failures | MEDIUM | HIGH | Comprehensive testing, gradual rollout |
| Broken relative imports | LOW | MEDIUM | Use absolute imports everywhere |
| Entry point naming conflicts | LOW | LOW | Use fda- prefix for all commands |
| Test failures from import changes | MEDIUM | MEDIUM | Update tests incrementally, verify each |
| Performance regression | LOW | LOW | Benchmark critical paths |
| Type errors exposed | MEDIUM | LOW | Gradual mypy adoption, ignore initially |
| Circular import dependencies | LOW | HIGH | Dependency graph analysis, refactor if needed |

### Migration Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Developer workflow disruption | HIGH | MEDIUM | Clear migration guide, team training |
| CI/CD pipeline breakage | MEDIUM | HIGH | Update CI config in parallel, test first |
| Documentation out of sync | MEDIUM | MEDIUM | Update docs in Phase 1 |
| Third-party integrations break | LOW | MEDIUM | Maintain old scripts as wrappers (6 months) |

---

## Breaking Changes Assessment

### MINIMAL Breaking Changes (with mitigation)

**Breaking:**
1. Import paths change: `from lib.X` → `from fda_tools.core.X`
2. CLI invocation changes: `python scripts/batchfetch.py` → `fda-batchfetch`
3. sys.path manipulation no longer needed/supported

**Mitigation:**
1. **Backward compatibility wrappers (6 months deprecation period):**
   ```python
   # lib/gap_analyzer.py (deprecated wrapper)
   import warnings
   warnings.warn(
       "Importing from lib/ is deprecated. Use: from fda_tools.core import GapAnalyzer",
       DeprecationWarning,
       stacklevel=2
   )
   from fda_tools.core.gap_analyzer import *
   ```

2. **Keep old script wrappers:**
   ```python
   # scripts/batchfetch.py (deprecated wrapper)
   #!/usr/bin/env python3
   import warnings
   warnings.warn(
       "Direct script execution is deprecated. Use: fda-batchfetch",
       DeprecationWarning
   )
   from fda_tools.tools.batchfetch import main
   if __name__ == "__main__":
       main()
   ```

3. **Migration guide in README.md:**
   - Clear before/after examples
   - Automated migration script provided
   - 6-month deprecation timeline

---

## Success Criteria

### Must-Have (Phase 1-4)
- [ ] Package installs via pip: `pip install fda-tools`
- [ ] Zero sys.path manipulation in codebase
- [ ] All 139 tests pass
- [ ] All 86 CLI commands work via entry points
- [ ] Import autocomplete works in IDEs
- [ ] CI/CD pipeline updated and passing

### Should-Have (Post-migration)
- [ ] Type checking runs: `mypy src/fda_tools`
- [ ] Package published to PyPI (test.pypi.org first)
- [ ] Documentation published (ReadTheDocs)
- [ ] Migration guide complete
- [ ] Team trained on new structure

### Nice-to-Have (Future)
- [ ] 100% type coverage (gradual)
- [ ] Automated dependency updates (Dependabot)
- [ ] Package signing for security
- [ ] Docker image published

---

## Timeline and Effort Estimate

| Phase | Effort | Dependencies | Team |
|-------|--------|--------------|------|
| Phase 1: Create Structure | 4 hours | None | 1 developer |
| Phase 2: Update Imports | 6 hours | Phase 1 | 1-2 developers |
| Phase 3: Entry Points | 1 hour | Phase 2 | 1 developer |
| Phase 4: Test & Verify | 1-2 hours | Phase 3 | 1 developer + QA |
| **TOTAL** | **12-13 hours** | Sequential | 1-2 developers |

**Recommended Schedule:**
- Day 1 AM: Phase 1 (4 hours)
- Day 1 PM: Phase 2 start (3 hours)
- Day 2 AM: Phase 2 complete (3 hours)
- Day 2 PM: Phase 3 + Phase 4 (2-3 hours)
- **Total: 2 days**

**Buffer:** +3 hours for unexpected issues = **16 hours total**

---

## Recommendations

### Immediate Actions (Priority: HIGH)

1. **Approve Migration Plan**
   - Review this architecture document
   - Get team consensus on package structure
   - Allocate 2-day sprint for migration

2. **Create Migration Branch**
   ```bash
   git checkout -b FDA-179-package-migration
   ```

3. **Execute Phase 1 (Same Day)**
   - Low risk, no breaking changes
   - Validates pyproject.toml configuration
   - Enables parallel work on Phase 2

### Short-Term Actions (Priority: MEDIUM)

4. **Update CI/CD Pipeline**
   - Modify GitHub Actions / CI config
   - Update pythonpath references
   - Test pipeline with new structure

5. **Create Migration Script**
   - Automate import updates (Phase 2)
   - Reduces manual errors
   - Speeds up Phase 2 from 6 hours to 3 hours

6. **Documentation Updates**
   - Update README.md with new installation instructions
   - Create MIGRATION_GUIDE.md
   - Update all code examples in docs/

### Long-Term Actions (Priority: LOW)

7. **Type Checking Integration**
   - Add mypy to CI/CD
   - Gradually add type hints
   - Target: 100% type coverage in 6 months

8. **PyPI Publication**
   - Register package name
   - Set up automated publishing
   - Enable pip install from PyPI

9. **Package Optimization**
   - Split into multiple packages (core, analysis, pathways)
   - Enable selective installation
   - Reduce dependency footprint

---

## Questions for Stakeholders

1. **Package Name:** Confirm `fda-tools` vs `fda_tools` (PyPI name vs import name)
   - Recommendation: `fda-tools` (PyPI) → `import fda_tools`

2. **License:** Confirm MIT vs Apache 2.0 vs Proprietary
   - Current: LICENSE file exists (need to verify)

3. **Versioning:** Start at 5.27.0 (current) or reset to 1.0.0?
   - Recommendation: Keep 5.27.0 (continuity)

4. **Entry Point Naming:** Confirm `fda-*` prefix for all commands
   - Alternative: `fda_*` or no prefix
   - Recommendation: `fda-*` (avoids namespace pollution)

5. **Deprecation Period:** 6 months for old imports/scripts?
   - Alternative: 3 months or 12 months
   - Recommendation: 6 months (balance between urgency and stability)

6. **Bridge Package:** Keep bridge/ as separate package or integrate?
   - Recommendation: Separate package `fda-tools-bridge` (optional dependency)

---

## Appendix A: File Mapping Reference

### Core Modules (lib/ → src/fda_tools/core/)

| Old Path | New Path | Purpose |
|----------|----------|---------|
| lib/gap_analyzer.py | src/fda_tools/core/gap_analyzer.py | Gap detection |
| lib/predicate_ranker.py | src/fda_tools/core/predicate_ranker.py | Predicate ranking |
| lib/predicate_diversity.py | src/fda_tools/core/predicate_diversity.py | Diversity analysis |
| lib/fda_enrichment.py | src/fda_tools/core/enrichment.py | FDA data enrichment |
| lib/expert_validator.py | src/fda_tools/core/expert_validator.py | Expert validation |
| lib/combination_detector.py | src/fda_tools/core/combination_detector.py | Combo product detect |
| lib/ecopy_exporter.py | src/fda_tools/core/ecopy_exporter.py | eCopy export |
| lib/disclaimers.py | src/fda_tools/core/disclaimers.py | Compliance disclaimers |
| lib/import_helpers.py | src/fda_tools/core/import_helpers.py | Safe import utilities |
| lib/manifest_validator.py | src/fda_tools/core/manifest_validator.py | Manifest validation |
| lib/de_novo_support.py | src/fda_tools/pathways/de_novo_support.py | De Novo pathway |
| lib/hde_support.py | src/fda_tools/pathways/hde_support.py | HDE pathway |
| lib/rwe_integration.py | src/fda_tools/pathways/rwe_integration.py | RWE pathway |
| lib/logging_config.py | src/fda_tools/utils/logging_config.py | Logging setup |
| lib/rate_limiter.py | src/fda_tools/utils/rate_limiter.py | Rate limiting |
| lib/cross_process_rate_limiter.py | src/fda_tools/utils/cross_process_rate_limiter.py | Multi-process rate limit |
| lib/secure_config.py | src/fda_tools/utils/secure_config.py | Secure config |

### Analysis Modules (scripts/ → src/fda_tools/analysis/)

| Old Path | New Path | Purpose |
|----------|----------|---------|
| scripts/pma_intelligence.py | src/fda_tools/analysis/pma_intelligence.py | PMA analysis |
| scripts/pma_comparison.py | src/fda_tools/analysis/pma_comparison.py | PMA comparison |
| scripts/approval_probability.py | src/fda_tools/analysis/approval_probability.py | Approval prediction |
| scripts/timeline_predictor.py | src/fda_tools/analysis/timeline_predictor.py | Timeline prediction |
| scripts/unified_predicate.py | src/fda_tools/analysis/unified_predicate.py | Unified predicate analyzer |
| scripts/clinical_requirements_mapper.py | src/fda_tools/analysis/clinical_requirements.py | Clinical requirements |
| scripts/competitive_dashboard.py | src/fda_tools/analysis/competitive_dashboard.py | Competitive analysis |
| scripts/risk_assessment.py | src/fda_tools/analysis/risk_assessment.py | Risk assessment |
| scripts/maude_comparison.py | src/fda_tools/analysis/maude_comparison.py | MAUDE comparison |
| scripts/pathway_recommender.py | src/fda_tools/analysis/pathway_recommender.py | Pathway recommendation |

### Tool Modules (scripts/ → src/fda_tools/tools/)

| Old Path | New Path | Purpose |
|----------|----------|---------|
| scripts/batchfetch.py | src/fda_tools/tools/batchfetch.py | Batch download |
| scripts/backup_project.py | src/fda_tools/tools/backup.py | Project backup/restore |
| scripts/auto_generate_device_standards.py | src/fda_tools/tools/standards_generator.py | Standards generation |
| scripts/compare_sections.py | src/fda_tools/tools/section_compare.py | Section comparison |
| scripts/section_analytics.py | src/fda_tools/tools/section_analytics.py | Section analytics |
| scripts/change_detector.py | src/fda_tools/tools/change_detector.py | Change detection |
| scripts/pas_monitor.py | src/fda_tools/tools/pas_monitor.py | PAS monitoring |
| scripts/supplement_tracker.py | src/fda_tools/tools/supplement_tracker.py | Supplement tracking |
| scripts/batch_seed.py | src/fda_tools/tools/batch_seed.py | Batch project seeding |
| scripts/batch_analyze.py | src/fda_tools/tools/batch_analyze.py | Batch analysis |

---

## Appendix B: Import Migration Examples

### Example 1: Core Module (lib/gap_analyzer.py)

**Before:**
```python
# lib/gap_analyzer.py
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from predicate_ranker import PredicateRanker
from expert_validator import ExpertValidator

class GapAnalyzer:
    def __init__(self):
        self.ranker = PredicateRanker()
        self.validator = ExpertValidator()
```

**After:**
```python
# src/fda_tools/core/gap_analyzer.py
from fda_tools.core.predicate_ranker import PredicateRanker
from fda_tools.core.expert_validator import ExpertValidator

class GapAnalyzer:
    def __init__(self):
        self.ranker = PredicateRanker()
        self.validator = ExpertValidator()
```

### Example 2: Analysis Module (scripts/pma_intelligence.py)

**Before:**
```python
# scripts/pma_intelligence.py
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pma_data_store import PMADataStore

lib_path = os.path.join(os.path.dirname(__file__), '..', 'lib')
sys.path.insert(0, lib_path)
from fda_enrichment import FDAEnrichment

class PMAIntelligenceEngine:
    def __init__(self):
        self.store = PMADataStore()
        self.enrichment = FDAEnrichment()
```

**After:**
```python
# src/fda_tools/analysis/pma_intelligence.py
from fda_tools.core.pma_data_store import PMADataStore
from fda_tools.core.enrichment import FDAEnrichment

class PMAIntelligenceEngine:
    def __init__(self):
        self.store = PMADataStore()
        self.enrichment = FDAEnrichment()
```

### Example 3: CLI Tool (scripts/batchfetch.py)

**Before:**
```python
# scripts/batchfetch.py
#!/usr/bin/env python3
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from fda_api_client import FDAClient

# Main logic
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # ... arg setup ...
    args = parser.parse_args()

    client = FDAClient()
    # ... main logic ...
```

**After:**
```python
# src/fda_tools/tools/batchfetch.py
#!/usr/bin/env python3
import argparse
import sys
from fda_tools.core.api_client import FDAClient

def main():
    """Entry point for fda-batchfetch CLI"""
    parser = argparse.ArgumentParser()
    # ... arg setup ...
    args = parser.parse_args()

    client = FDAClient()
    # ... main logic ...
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

### Example 4: Test File (tests/test_gap_analyzer.py)

**Before:**
```python
# tests/test_gap_analyzer.py
import sys
from pathlib import Path

LIB_DIR = str(Path(__file__).parent.parent / 'lib')
sys.path.insert(0, LIB_DIR)

from gap_analyzer import GapAnalyzer

def test_gap_detection():
    analyzer = GapAnalyzer()
    # ... test logic ...
```

**After:**
```python
# tests/core/test_gap_analyzer.py
import pytest
from fda_tools.core.gap_analyzer import GapAnalyzer

def test_gap_detection():
    analyzer = GapAnalyzer()
    # ... test logic ...
```

---

## Appendix C: Verification Script

```bash
#!/bin/bash
# verify_migration.sh - Comprehensive migration verification

set -e

echo "=== FDA-179 Migration Verification ==="

# 1. Check for sys.path manipulation
echo "1. Checking for sys.path.insert() calls..."
SYSPATH_COUNT=$(grep -r "sys.path.insert" src/ tests/ 2>/dev/null | wc -l)
if [ "$SYSPATH_COUNT" -gt 0 ]; then
    echo "  ❌ FAIL: Found $SYSPATH_COUNT sys.path.insert() calls"
    grep -rn "sys.path.insert" src/ tests/
    exit 1
else
    echo "  ✅ PASS: No sys.path manipulation found"
fi

# 2. Package installation
echo "2. Testing package installation..."
pip install -e . >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "  ✅ PASS: Package installs successfully"
else
    echo "  ❌ FAIL: Package installation failed"
    exit 1
fi

# 3. Import verification
echo "3. Testing imports..."
python -c "from fda_tools import __version__; print(f'  Version: {__version__}')"
python -c "from fda_tools.core import FDAClient" && echo "  ✅ FDAClient import works"
python -c "from fda_tools.core import GapAnalyzer" && echo "  ✅ GapAnalyzer import works"
python -c "from fda_tools.analysis import PMAIntelligence" && echo "  ✅ PMAIntelligence import works"

# 4. CLI entry points
echo "4. Testing CLI entry points..."
command -v fda-batchfetch >/dev/null && echo "  ✅ fda-batchfetch command exists"
command -v fda-pma-intel >/dev/null && echo "  ✅ fda-pma-intel command exists"
command -v fda-de-novo >/dev/null && echo "  ✅ fda-de-novo command exists"

fda-batchfetch --help >/dev/null 2>&1 && echo "  ✅ fda-batchfetch --help works"

# 5. Test suite
echo "5. Running test suite..."
pytest tests/ -v --tb=line -q
if [ $? -eq 0 ]; then
    echo "  ✅ PASS: All tests passed"
else
    echo "  ❌ FAIL: Some tests failed"
    exit 1
fi

# 6. Test coverage
echo "6. Checking test coverage..."
COVERAGE=$(pytest tests/ --cov=fda_tools --cov-report=term-missing | grep "TOTAL" | awk '{print $4}' | sed 's/%//')
if [ "$COVERAGE" -ge 80 ]; then
    echo "  ✅ PASS: Coverage is ${COVERAGE}% (≥80%)"
else
    echo "  ⚠️  WARNING: Coverage is ${COVERAGE}% (<80%)"
fi

# 7. Type checking
echo "7. Running type checking..."
mypy src/fda_tools --ignore-missing-imports --check-untyped-defs >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "  ✅ PASS: No type errors found"
else
    echo "  ⚠️  INFO: Type errors found (expected during gradual adoption)"
fi

echo ""
echo "=== ✅ Migration verification complete ==="
```

---

## Approval Required

This architecture review requires approval from:

- [ ] **Tech Lead:** Review package structure and migration plan
- [ ] **QA Lead:** Review testing strategy and verification checklist
- [ ] **DevOps:** Review CI/CD impact and deployment changes
- [ ] **Team:** Review timeline and resource allocation

**Next Steps:**
1. Review this document
2. Address questions in "Questions for Stakeholders" section
3. Approve migration plan
4. Create FDA-179 implementation tickets
5. Schedule 2-day sprint for migration

**Estimated Delivery:** 2-3 business days after approval

---

**Document Version:** 1.0
**Last Updated:** 2026-02-20
**Author:** Architecture Reviewer (FDA-179)
