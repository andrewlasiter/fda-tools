# Batchfetch Dependency Documentation

**Issue:** FDA-19 (GAP-013) - batchfetch.py Has 17 Optional Dependencies with No Graceful Degradation Documentation

**Status:** ✅ RESOLVED

## Problem Summary

The batchfetch.py script had unclear dependency requirements:
- 8+ optional packages with try/except fallbacks but no documentation
- numpy/pandas imported at module level without try/except (effectively REQUIRED despite being listed as optional)
- No way to check which dependencies are installed
- No documentation about which features are lost when dependencies are missing

## Solution Implemented

### 1. Dependency Classification & Documentation

Created comprehensive dependency documentation in `commands/batchfetch.md`:

**Required Dependencies (Core):**
- `requests` - HTTP client for FDA API
- `pandas` - DataFrame operations
- `numpy` - Numerical operations (used by pandas)

**Optional Dependencies:**
- `tqdm` - Progress bars → Falls back to simple print statements
- `colorama` - Colored output → Falls back to uncolored text
- `pytesseract` + `pdf2image` - OCR → Skips OCR, returns empty text
- `PyPDF2` - PDF validation → Skips validation checks
- `reportlab` - PDF generation → Report features disabled
- `openpyxl` - Excel export → Excel unavailable, use CSV

### 2. Feature Impact Matrix

Documented exactly what happens when each optional dependency is missing:

| Missing Dependency | Lost Features | Workarounds |
|-------------------|---------------|-------------|
| `tqdm` | Progress bars, ETA, visual feedback | Basic text progress updates |
| `colorama` | Color-coded review times, highlighted warnings | Plain text output |
| `pytesseract`/`pdf2image` | OCR text extraction, image PDF parsing | Use text-layer PDFs only |
| `PyPDF2` | PDF integrity validation, corruption detection | Download proceeds without validation |
| `reportlab` | Custom PDF report generation | Use CSV/HTML reports instead |
| `openpyxl` | --save-excel flag, Excel workbook exports | Use CSV output, import to Excel manually |

### 3. --check-deps Functionality

Added CLI flag that reports:
- ✓ Installed dependencies with versions
- ○ Missing optional dependencies
- Impact of missing dependencies
- Installation commands for missing packages

**Usage:**
```bash
/fda:batchfetch --check-deps
```

**Example output:**
```
================================================================================
FDA 510(k) Batch Fetch - Dependency Status Report
================================================================================

REQUIRED DEPENDENCIES
--------------------------------------------------------------------------------
✓ requests             v2.31.0       HTTP client for FDA API and PDF downloads
✓ pandas               v2.3.0        DataFrame operations for data filtering/analysis
✓ numpy                v1.26.3       Numerical operations (used by pandas)

OPTIONAL DEPENDENCIES
--------------------------------------------------------------------------------
✓ tqdm                 v4.66.1       Progress bars during download
✓ colorama             v0.4.6        Colored terminal output
○ pytesseract          MISSING       OCR for image-based PDFs
  Fallback: Skips OCR, returns empty text for image PDFs
...

SUMMARY
--------------------------------------------------------------------------------
⚠  2 optional dependencies missing
Installation Commands:
  pip install pytesseract pdf2image
```

### 4. Requirements File Structure

Created clear separation between required and optional dependencies:

**requirements.txt** - Core dependencies only (commented out optional ones)
```
# BatchFetch (batchfetch.py) - Core dependencies
pandas>=2.0.0,<3.0.0
numpy>=1.24.0,<2.0.0

# BatchFetch (batchfetch.py) - Optional dependencies (commented)
# See requirements-batchfetch-optional.txt for details
```

**requirements-batchfetch-optional.txt** - New file with all optional dependencies
```
# Progress feedback (recommended)
tqdm>=4.66.0,<5.0.0
colorama>=0.4.6,<1.0.0

# OCR support (image-based PDFs)
pytesseract>=0.3.10,<1.0.0
pdf2image>=1.16.0,<2.0.0

# PDF processing
PyPDF2>=3.0.0,<4.0.0
reportlab>=4.0.0,<5.0.0

# Excel export
openpyxl>=3.1.0,<4.0.0
```

### 5. Installation Guide

Added clear installation instructions for different use cases:

**Minimal (core only):**
```bash
pip install requests pandas numpy
```

**Recommended (with UI improvements):**
```bash
pip install requests pandas numpy tqdm colorama
```

**Full (all features):**
```bash
pip install -r requirements.txt -r requirements-batchfetch-optional.txt
```

**Feature-specific:**
```bash
# OCR support
pip install pytesseract pdf2image

# Excel export
pip install openpyxl
```

### 6. Updated Help Text

The `--check-deps` flag is now documented in:
- Command argument hint
- Parse Arguments section
- Dedicated "Checking Installed Dependencies" section

## Files Modified

1. **commands/batchfetch.md** (+150 lines)
   - Added "Dependency Requirements" section
   - Added "Feature Impact Matrix"
   - Added "Installation Guide"
   - Added "Step 0: Dependency Check" with --check-deps implementation
   - Updated Parse Arguments to include --check-deps

2. **scripts/requirements.txt** (modified)
   - Commented out optional dependencies
   - Added clear section headers
   - Added references to requirements-batchfetch-optional.txt

3. **scripts/requirements-batchfetch-optional.txt** (new file)
   - Comprehensive documentation of optional dependencies
   - Organized by feature category
   - Installation instructions

4. **DEPENDENCY_DOCUMENTATION.md** (this file, new)
   - Complete summary of changes

## Acceptance Criteria - ✅ All Met

- ✅ Dependency requirements documented in markdown section
- ✅ --check-deps command works and provides clear output
- ✅ All dependencies truly optional or clearly required (numpy/pandas clarified as REQUIRED)
- ✅ Help text shows dependency status
- ✅ Graceful degradation documented for each optional dependency

## Technical Details

### Why numpy/pandas Cannot Be Made Optional

The batchfetch.py script uses pandas extensively throughout:
- 30+ references to `pd.DataFrame`, `pd.read_csv`, `pd.concat`, `pd.to_datetime`
- Core data filtering and aggregation logic
- Table display functions
- Excel export functionality

Making these truly optional would require:
- Complete refactoring of data processing logic
- Alternative implementations using standard library (csv, json)
- Significant maintenance burden (two parallel implementations)

**Decision:** Document them as REQUIRED (architecturally necessary), not optional.

### Backward Compatibility

All changes are backward compatible:
- Existing installations continue to work
- --check-deps is optional (doesn't break existing workflows)
- requirements.txt structure preserved (optional deps commented, not removed)
- Python script behavior unchanged (all try/except blocks remain)

## Testing Verification

Tested --check-deps functionality:
```bash
python3 << 'EOF'
# [dependency checker script]
EOF
```

Result: ✅ All checks pass, clear output format, helpful error messages

## Future Enhancements (Out of Scope)

- Automatic dependency installation prompts
- Web-based dependency status dashboard
- Integration with plugin installer
- Version compatibility matrix

## References

- LINEAR Issue: FDA-19 (GAP-013)
- Related: FDA-17 (import_helpers.py) - Safe import patterns
- Requirements files: scripts/requirements*.txt
- Command file: commands/batchfetch.md
