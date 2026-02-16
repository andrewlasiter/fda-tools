# Test Implementation Checklist

**Document Version:** 2.0
**Date:** 2026-02-16
**Reference:** `docs/TESTING_SPEC.md` (v5.36.0 Test Specification)
**Total Test Cases:** 34 (17 SMART + 16 SIM + 6 INT + 3 PERF -- some INT/PERF overlap)

---

## Quick Wins Completed (v2.0)

**Date completed:** 2026-02-16
**Total Quick Win tests implemented:** 17 (original target) + 7 bonus = 24 test IDs, 70 test methods
**Files created:**
- `tests/test_change_detector.py` -- 12 test classes, 23 test methods
- `tests/test_section_analytics.py` -- 11 test classes, 47 test methods
- `tests/conftest.py` -- 12 shared fixtures
- `tests/mocks/mock_fda_client.py` -- MockFDAClient class (170 lines)
- `tests/fixtures/sample_fingerprints.json` -- 3 product code fingerprints
- `tests/fixtures/sample_api_responses.json` -- 10 API response scenarios
- `tests/fixtures/sample_section_data.json` -- 8 devices with section data

**Coverage achieved:** All 17 Quick Win test IDs implemented, plus bonus tests for
SMART-003, SMART-005, SMART-006, SMART-011, SIM-007, SIM-008, SIM-013, SIM-015, SIM-016.

**Next recommended tests:** Critical priority list -- SMART-007 (recall detection),
SMART-004 (multi-product fingerprints), SMART-008 (API error degradation), INT-001
(end-to-end detect+trigger).

---

## Test Implementation Status

### Critical Tests (Must Have for Release)

| Status | Test ID | Description | Est. Time |
|--------|---------|-------------|-----------|
| [x] | SMART-001 | Fingerprint creation on first run | 20 min |
| [x] | SMART-002 | Fingerprint update on subsequent run | 15 min |
| [x] | SMART-005 | New clearance detection | 20 min |
| [x] | SMART-006 | No changes detected (stable state) | 15 min |
| [ ] | SMART-007 | New recall detection | 15 min |
| [x] | SIM-001 | Similarity scoring accuracy (all 3 methods) | 20 min |
| [x] | SIM-002 | Identical text similarity = 1.0 | 10 min |
| [x] | SIM-003 | Empty string similarity = 0.0 | 10 min |
| [x] | SIM-006 | Basic pairwise matrix computation | 25 min |
| [x] | SIM-009 | Basic temporal trend detection | 20 min |
| [x] | SIM-014 | Basic cross-product comparison | 20 min |
| [ ] | INT-001 | Smart update end-to-end (detect + trigger) | 30 min |

**Subtotal: 10/12 critical tests implemented**

---

### High Priority Tests (Should Have)

| Status | Test ID | Description | Est. Time |
|--------|---------|-------------|-----------|
| [x] | SMART-003 | Fingerprint persistence across sessions | 15 min |
| [ ] | SMART-004 | Multiple product code fingerprints | 20 min |
| [ ] | SMART-008 | API error graceful degradation | 15 min |
| [x] | SMART-009 | Empty known K-numbers list | 10 min |
| [x] | SMART-010 | No fingerprints and no product codes | 10 min |
| [x] | SMART-011 | Pipeline trigger with dry-run | 15 min |
| [ ] | SMART-012 | Pipeline trigger execution (mocked) | 20 min |
| [x] | SMART-013 | Pipeline trigger with timeout | 15 min |
| [x] | SIM-004 | Invalid method raises ValueError | 10 min |
| [x] | SIM-007 | Pairwise matrix with sample size limit | 15 min |
| [x] | SIM-008 | Pairwise matrix with insufficient devices | 15 min |
| [x] | SIM-010 | Stable trend detection | 10 min |
| [x] | SIM-011 | Decreasing trend detection | 10 min |
| [x] | SIM-012 | Insufficient data for trend | 10 min |
| [ ] | INT-002 | update_manager.py smart mode integration | 20 min |
| [ ] | INT-003 | compare_sections.py similarity integration | 25 min |
| [ ] | INT-004 | compare_sections.py trends integration | 25 min |
| [ ] | INT-005 | compare_sections.py cross-product integration | 25 min |

**Subtotal: 12/18 high priority tests implemented**

---

### Medium Priority Tests (Quality Improvement)

| Status | Test ID | Description | Est. Time |
|--------|---------|-------------|-----------|
| [x] | SMART-014 | Pipeline trigger with empty K-numbers | 10 min |
| [x] | SMART-015 | _run_subprocess OSError handling | 10 min |
| [ ] | SMART-016 | CLI with --json output | 15 min |
| [ ] | SMART-017 | CLI with --trigger flag | 15 min |
| [x] | SIM-005 | Case insensitivity in tokenization | 10 min |
| [x] | SIM-013 | Temporal trends with missing decision dates | 15 min |
| [x] | SIM-015 | Cross-product with unknown product code | 10 min |
| [x] | SIM-016 | Product code case insensitivity | 10 min |
| [ ] | INT-006 | Auto-build cache error handling | 20 min |
| [ ] | PERF-001 | Pairwise similarity computation time | 20 min |

**Subtotal: 6/10 medium priority tests implemented**

---

### Low Priority Tests (Nice-to-Have)

| Status | Test ID | Description | Est. Time |
|--------|---------|-------------|-----------|
| [ ] | PERF-002 | Temporal trend analysis scaling | 15 min |
| [ ] | PERF-003 | Cross-product comparison with large cache | 15 min |

**Subtotal: 0/2 low priority tests implemented**

---

## Summary by Module

| Module | Critical | High | Medium | Low | Total | Implemented |
|--------|----------|------|--------|-----|-------|-------------|
| change_detector.py | 4/5 | 5/8 | 2/4 | 0/0 | 11/17 | 65% |
| section_analytics.py | 4/4 | 5/5 | 4/4 | 0/2 | 13/15 | 87% |
| Integration (cross-module) | 0/1 | 0/4 | 0/1 | 0/0 | 0/6 | 0% |
| Performance | 0/0 | 0/0 | 0/1 | 0/2 | 0/3 | 0% |
| **Total** | **10/12** | **12/18** | **6/10** | **0/2** | **28/42** | **67%** |

Note: Some tests span categories (e.g., INT-001 is both Integration and Critical). The count of 42 above includes overlap. Unique test case count is 34. Of the 34 unique test IDs, 24 are now implemented.

---

## Quick Wins (< 30 min each)

The following tests can be implemented with minimal setup, using simple assertions and existing fixtures. These are ideal starting points for building test coverage.

### Tier 1: Trivial (< 10 min each) -- ALL IMPLEMENTED

1. **SIM-002:** [x] Identical text similarity -- `assert compute_similarity("foo", "foo") == 1.0`
2. **SIM-003:** [x] Empty string similarity -- `assert compute_similarity("", "text") == 0.0`
3. **SIM-004:** [x] Invalid method -- `with pytest.raises(ValueError): compute_similarity("a", "b", "invalid")`
4. **SIM-005:** [x] Tokenization case -- `assert _tokenize("ISO TEST") == ["iso", "test"]`
5. **SIM-012:** [x] Single data point trend -- `assert result["direction"] == "insufficient_data"`
6. **SMART-014:** [x] Empty K-numbers -- `assert result["status"] == "skipped"`

### Tier 2: Simple (10-20 min each) -- ALL IMPLEMENTED

7. **SIM-001:** [x] Similarity accuracy -- 3 method calls with `assert score_AB > score_AC`
8. **SIM-010:** [x] Stable trend -- Set up 5 points near 85.0, verify direction = "stable"
9. **SIM-011:** [x] Decreasing trend -- Set up 5 decreasing points, verify direction
10. **SMART-009:** [x] Empty known list -- Set up empty fingerprint, verify all results are new
11. **SMART-010:** [x] No fingerprints -- Set up empty manifest, verify status = "no_fingerprints"
12. **SMART-013:** [x] Timeout handling -- Mock subprocess.TimeoutExpired, verify result
13. **SMART-015:** [x] OSError handling -- Mock OSError, verify graceful result

### Tier 3: Moderate (20-30 min each) -- ALL IMPLEMENTED

14. **SMART-001:** [x] Fingerprint creation -- Requires tmp directory, mock client, manifest setup
15. **SMART-005:** [x] New clearance detection -- Requires fingerprint + mock client setup
16. **SIM-006:** [x] Pairwise matrix -- Requires 4-device fixture, verify pair count and stats
17. **SIM-014:** [x] Cross-product comparison -- Requires multi-code cache fixture

### Bonus Tests Implemented Beyond Quick Wins

- **SMART-002:** [x] Fingerprint update with new data (Tier 3 moderate)
- **SMART-003:** [x] Fingerprint persistence across sessions
- **SMART-006:** [x] No changes detected (stable state / no false positives)
- **SMART-011:** [x] Pipeline dry-run mode
- **SIM-007:** [x] Pairwise matrix sample size limit
- **SIM-008:** [x] Pairwise matrix with insufficient devices (0 and 1 device)
- **SIM-013:** [x] Temporal trends with missing decision dates
- **SIM-015:** [x] Cross-product with unknown product code
- **SIM-016:** [x] Product code case insensitivity

---

## Implementation Notes

### Deviations from Original Spec

1. **SIM-006 / SIM-008 combined:** The pairwise matrix tests (SIM-006, SIM-007, SIM-008)
   were combined into a single test class `TestSIM006PairwiseMatrixComputation` since they
   share fixture setup. SIM-007 and SIM-008 are implemented as additional test methods
   within this class.

2. **SIM-014 / SIM-015 / SIM-016 combined:** The cross-product comparison tests were
   combined into `TestSIM014CrossProductComparison` with SIM-015 (unknown product code)
   and SIM-016 (case insensitivity) as additional test methods.

3. **SIM-009 expanded:** The temporal trends test class includes coverage validation,
   year range checking, insufficient years detection, multi-year synthetic data, and
   missing decision date handling (SIM-013).

4. **SMART-005 / SMART-006 added:** These critical tests (new clearance detection and
   stable state validation) were added beyond the original 17 Quick Wins since they share
   fixture infrastructure with SMART-001/002.

5. **find_new_clearances standalone tests:** Additional unit tests were added for the
   `find_new_clearances()` function directly, testing identification logic, empty known
   list, and API error handling independently of the `detect_changes()` workflow.

### Test Infrastructure Created

- **conftest.py:** 12 shared fixtures covering project directories, fingerprints,
  API responses, section data, and pre-configured mock clients.
- **MockFDAClient:** Full mock class (170 lines) with configurable per-product-code
  responses, error simulation, and call logging for assertion.
- **Fixture data files:** 3 JSON files with realistic FDA data covering 8 devices,
  3 product codes, 10 API response scenarios, and 3 fingerprint configurations.

### Test Method Count Summary

| File | Classes | Methods |
|------|---------|---------|
| test_section_analytics.py | 11 | 47 |
| test_change_detector.py | 12 | 23 |
| **Total** | **23** | **70** |

---

## Implementation Recommendations

### 1. Framework and Structure

The project already has `pytest.ini` and a `tests/` directory with 50+ test files. Follow existing patterns:

```python
# tests/test_change_detector.py
"""Tests for Smart Auto-Update Change Detector (v5.36.0)."""
import json
import os
import pytest
import tempfile
from unittest.mock import MagicMock, patch

# Import production code
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
from change_detector import (
    _load_fingerprint,
    _save_fingerprint,
    detect_changes,
    find_new_clearances,
    trigger_pipeline,
    _run_subprocess,
)

# tests/test_section_analytics.py
"""Tests for Section Comparison Analytics (v5.36.0)."""
from section_analytics import (
    compute_similarity,
    _tokenize,
    _jaccard_similarity,
    _cosine_similarity_stdlib,
    pairwise_similarity_matrix,
    analyze_temporal_trends,
    _detect_trend_direction,
    cross_product_compare,
)
```

### 2. Mock FDAClient Pattern

```python
def _create_mock_client(clearances=None, recalls=None):
    """Create a mock FDAClient for offline testing."""
    client = MagicMock()
    client.get_clearances.return_value = clearances or {
        "meta": {"results": {"total": 5}},
        "results": [
            {"k_number": f"K24100{i}", "device_name": f"Device {i}",
             "applicant": "TestCo", "decision_date": f"2024010{i}",
             "product_code": "DQY"}
            for i in range(1, 6)
        ],
    }
    client.get_recalls.return_value = recalls or {
        "meta": {"results": {"total": 2}},
        "results": [],
    }
    return client
```

### 3. Fixture Data Files

Created in `tests/fixtures/`:

```
tests/fixtures/
    __init__.py
    sample_fingerprints.json       # SMART-001 through SMART-010
    sample_api_responses.json      # SMART-005, SMART-006, and 8 more scenarios
    sample_section_data.json       # SIM-006 through SIM-016 (8 devices, 2 product codes)
```

### 4. Temporary Directory Pattern

For tests that modify data_manifest.json:

```python
@pytest.fixture
def project_dir(tmp_path):
    """Create a temporary project directory with manifest."""
    manifest = {"product_codes": ["DQY"], "queries": []}
    manifest_path = tmp_path / "data_manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    return str(tmp_path)
```

### 5. Target Coverage

| Module | Target | Achieved (Quick Wins) | Notes |
|--------|--------|----------------------|-------|
| change_detector.py | 90% | ~65% | Missing: CLI, multi-code, recall detection |
| section_analytics.py | 90% | ~87% | Missing: performance tests only |
| Integration paths | 80% | 0% | Phase 4-5 work |

### 6. Phased Implementation Plan

| Phase | Tests | Priority | Est. Time | Cumulative | Status |
|-------|-------|----------|-----------|------------|--------|
| Phase 1 | Quick wins (Tier 1: 6 tests) | Critical/High | 1 hour | 6 tests | DONE |
| Phase 2 | Quick wins (Tier 2: 7 tests) | Critical/High | 2 hours | 13 tests | DONE |
| Phase 3 | Quick wins (Tier 3: 4 tests) | Critical | 2 hours | 17 tests | DONE |
| Phase 4 | Remaining critical (5 tests) | Critical | 2 hours | 22 tests | PENDING |
| Phase 5 | High priority (6 tests) | High | 3 hours | 28 tests | PENDING |
| Phase 6 | Medium + low (6 tests) | Medium/Low | 2.5 hours | 34 tests | PENDING |

**Total estimated effort: 12.5 hours (Phases 1-3 complete: ~3.5 hours)**

---

## Risk Coverage Analysis

### Highest Risk Areas (Covered by Critical Tests)

| Risk | Coverage | Tests | Status |
|------|----------|-------|--------|
| False positive changes (existing data reported as new) | SMART-006 | 1 test | IMPLEMENTED |
| False negative changes (new data not detected) | SMART-005, SMART-007 | 2 tests | 1/2 IMPLEMENTED |
| Fingerprint data loss on error | SMART-001, SMART-002, SMART-008 | 3 tests | 2/3 IMPLEMENTED |
| Similarity scoring accuracy | SIM-001, SIM-002, SIM-003 | 3 tests | ALL IMPLEMENTED |
| Trend direction misclassification | SIM-009, SIM-010, SIM-011 | 3 tests | ALL IMPLEMENTED |
| Cross-module integration failure | INT-001 | 1 test | PENDING |

### Medium Risk Areas (Covered by High Priority Tests)

| Risk | Coverage | Tests | Status |
|------|----------|-------|--------|
| Pipeline trigger failures | SMART-011, SMART-012, SMART-013 | 3 tests | 2/3 IMPLEMENTED |
| Multi-product-code handling | SMART-004, SIM-014, SIM-016 | 3 tests | 2/3 IMPLEMENTED |
| Edge cases (empty data, missing fields) | SMART-009, SMART-010, SIM-008, SIM-012 | 4 tests | ALL IMPLEMENTED |
| Module integration (similarity/trends/cross-product) | INT-002 through INT-005 | 4 tests | PENDING |

### Low Risk Areas (Covered by Medium/Low Priority Tests)

| Risk | Coverage | Tests | Status |
|------|----------|-------|--------|
| CLI output format | SMART-016, SMART-017 | 2 tests | PENDING |
| Performance degradation | PERF-001, PERF-002, PERF-003 | 3 tests | PENDING |
| Auto-build cache errors | INT-006 | 1 test | PENDING |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-16 | Workflow Orchestrator | Initial checklist (34 test cases, 3 tiers of quick wins) |
| 2.0 | 2026-02-16 | Workflow Orchestrator | Quick Wins implementation complete (24 unique test IDs, 60 test methods) |
