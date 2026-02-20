# Gap Analyzer Refactoring Plan (FDA-116)

## Current State
- **File:** `lib/gap_analyzer.py` (794 lines)
- **Problem:** Violates Single Responsibility Principle
- **Responsibilities:** 4 distinct concerns in one module

## Split Strategy

### 1. Core Detection Modules

**predicate_gap_analyzer.py** (New)
- Class: `PredicateGapAnalyzer`
- Methods:
  - `detect_missing_device_data()` - Missing/incomplete device fields
  - `detect_weak_predicates()` - Recall history, age, SE differences
- Lines: ~140 from original

**testing_gap_detector.py** (New)
- Class: `TestingGapDetector`
- Methods:
  - `detect_testing_gaps()` - Missing test evidence
- Lines: ~60 from original

**standards_gap_detector.py** (New)
- Class: `StandardsGapDetector`
- Methods:
  - `detect_standards_gaps()` - Unapplied standards
- Lines: ~40 from original

**data_completeness_scorer.py** (New)
- Functions:
  - `calculate_gap_analysis_confidence()` - Scoring logic
  - `_interpret_confidence()` - Confidence interpretation
- Lines: ~110 from original

### 2. Main Orchestrator

**gap_analyzer.py** (Refactored)
- Class: `GapAnalyzer` (delegates to focused modules)
- Functions:
  - `analyze_all_gaps()` - Orchestrates all detectors
  - `generate_gap_analysis_report()` - Reporting
  - `write_gap_data_json()` - Output
  - `update_enrichment_metadata()` - Metadata
- Lines: ~200 (orchestration + reporting)
- **Backward Compatible:** Existing public API preserved

## Backward Compatibility

All existing imports work unchanged:
```python
from fda_tools.lib.gap_analyzer import GapAnalyzer, analyze_all_gaps
```

New modular imports also available:
```python
from fda_tools.lib.predicate_gap_analyzer import PredicateGapAnalyzer
from fda_tools.lib.testing_gap_detector import TestingGapDetector
```

## Implementation Steps

1. ✅ Create refactoring plan
2. Create 4 new focused modules
3. Update main gap_analyzer.py to delegate
4. Verify backward compatibility
5. Add deprecation notices for direct usage
6. Update callers to use focused modules
7. Commit with comprehensive tests

## Benefits

- **Testability:** Each module independently testable
- **Maintainability:** Clear boundaries, easier to modify
- **Extensibility:** Add new gap types without touching others
- **Reusability:** Focused modules can be used standalone
