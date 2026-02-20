# Test Specification: Smart Auto-Update System & Section Comparison Analytics

**Document Version:** 1.0
**Date:** 2026-02-16
**Status:** APPROVED
**Applicable Version:** v5.36.0
**Modules Under Test:**
- `scripts/change_detector.py` (654 lines)
- `scripts/section_analytics.py` (702 lines)
- `scripts/update_manager.py` (smart mode integration, +76 lines)
- `scripts/compare_sections.py` (analytics integration, +308 lines)

---

## 1. Overview

### 1.1 Purpose

This document defines the formal test specification for the two features delivered in v5.36.0:

1. **Smart Auto-Update System** -- Fingerprint-based FDA change detection that compares live API data against stored fingerprints to identify new clearances and recalls without full data re-fetches.

2. **Advanced Section Comparison Analytics** -- Text similarity scoring, pairwise similarity matrices, temporal trend analysis, and cross-product-code comparison for 510(k) submission sections.

### 1.2 Scope

This specification covers:
- Unit tests for individual functions
- Integration tests for module interactions
- Functional tests for end-to-end workflows
- Performance tests for computation-bound operations
- Edge case tests for boundary conditions and error handling

### 1.3 Test Environment

- **Python version:** 3.12+
- **Test framework:** pytest (existing `pytest.ini` in project root)
- **Mock framework:** unittest.mock (stdlib)
- **Test data:** Fixture-based (no network access required)
- **CI/CD:** All tests must run offline with mocked API calls

### 1.4 Conventions

- Test IDs use prefix `SMART-` for change detector tests and `SIM-` for section analytics tests
- Priority levels: Critical (must pass for release), High (should pass), Medium (quality improvement), Low (nice-to-have)
- Each test case specifies explicit pass/fail criteria

---

## 2. Test Categories

| Category | Description | Count |
|----------|-------------|-------|
| Unit | Individual function behavior | 18 |
| Integration | Cross-module interactions | 6 |
| Functional | End-to-end CLI workflows | 5 |
| Performance | Computation time and scale | 3 |
| Edge Case | Boundary conditions and errors | 2 (embedded in other categories) |
| **Total** | | **34** |

---

## 3. Smart Auto-Update System Test Cases

### 3.1 Fingerprint Management

---

### SMART-001: Fingerprint Creation on First Run

**Category:** Functional
**Priority:** Critical
**Module:** `change_detector.py` -- `_save_fingerprint()`, `detect_changes()`

**Prerequisites:**
- Project directory exists at `~/fda-510k-data/projects/{project_name}/`
- `data_manifest.json` exists with `product_codes: ["DQY"]` but no `fingerprints` key
- FDAClient mock configured to return 5 clearances and 2 recalls for product code DQY

**Test Steps:**
1. Create mock FDAClient returning sample clearance data (5 items) and recall data (total=2)
2. Call `detect_changes(project_name, client=mock_client)`
3. Read updated `data_manifest.json`

**Expected Results:**
- `data_manifest.json` now contains a `fingerprints` key
- `fingerprints.DQY` exists with all required fields
- `fingerprints.DQY.last_checked` is a valid ISO 8601 timestamp
- `fingerprints.DQY.clearance_count` equals the total from API meta (e.g., 147)
- `fingerprints.DQY.latest_k_number` matches the first result K-number
- `fingerprints.DQY.latest_decision_date` matches the first result date
- `fingerprints.DQY.recall_count` equals 2
- `fingerprints.DQY.known_k_numbers` is a sorted list of 5 K-numbers

**Pass Criteria:** All 8 expected results verified
**Fail Criteria:** Any field missing, null, or invalid format

---

### SMART-002: Fingerprint Update on Subsequent Run

**Category:** Unit
**Priority:** Critical
**Module:** `change_detector.py` -- `_save_fingerprint()`, `_load_fingerprint()`

**Prerequisites:**
- Project directory with existing fingerprint for DQY (clearance_count=5, known_k_numbers=["K241001", "K241002", "K241003", "K241004", "K241005"])
- FDAClient mock returning 7 clearances (5 existing + 2 new: K251001, K251002)

**Test Steps:**
1. Set up data_manifest.json with existing DQY fingerprint
2. Call `detect_changes(project_name, client=mock_client)`
3. Read updated fingerprint via `_load_fingerprint()`

**Expected Results:**
- `fingerprints.DQY.clearance_count` updated to new total
- `fingerprints.DQY.known_k_numbers` now contains all 7 K-numbers
- `fingerprints.DQY.last_checked` is more recent than the original
- Original K-numbers are preserved (not lost during update)

**Pass Criteria:** All 4 expected results verified
**Fail Criteria:** Any existing K-number lost, or count not updated

---

### SMART-003: Fingerprint Persistence Across Sessions

**Category:** Unit
**Priority:** High
**Module:** `change_detector.py` -- `_load_fingerprint()`, `_save_fingerprint()`

**Prerequisites:**
- Empty project directory with data_manifest.json containing `{}`

**Test Steps:**
1. Call `_save_fingerprint(project_dir, "DQY", sample_fingerprint)`
2. Create new Python process context (simulate session restart)
3. Call `_load_fingerprint(project_dir, "DQY")`

**Expected Results:**
- Loaded fingerprint matches saved fingerprint exactly (all fields)
- JSON file is valid and properly formatted
- Product code is stored uppercase regardless of input case

**Pass Criteria:** Round-trip serialization preserves all fields
**Fail Criteria:** Any field differs between save and load

---

### SMART-004: Multiple Product Code Fingerprints

**Category:** Unit
**Priority:** High
**Module:** `change_detector.py` -- `_save_fingerprint()`, `detect_changes()`

**Prerequisites:**
- Project with `product_codes: ["DQY", "OVE", "GEI"]`
- FDAClient mock returning different data for each product code

**Test Steps:**
1. Call `detect_changes()` for project with 3 product codes
2. Verify all 3 fingerprints are saved independently

**Expected Results:**
- `fingerprints` dict contains keys for "DQY", "OVE", "GEI"
- Each fingerprint has independent clearance_count and known_k_numbers
- Rate limiting observed between product code checks (0.5s delay)

**Pass Criteria:** All 3 fingerprints present and independent
**Fail Criteria:** Any fingerprint missing or cross-contaminated

---

### 3.2 Change Detection

---

### SMART-005: New Clearance Detection

**Category:** Functional
**Priority:** Critical
**Module:** `change_detector.py` -- `detect_changes()`, `find_new_clearances()`

**Prerequisites:**
- Existing fingerprint with `known_k_numbers: ["K241001", "K241002", "K241003"]`
- FDAClient mock returning 5 clearances (3 known + 2 new: K251001, K251002)

**Test Steps:**
1. Call `detect_changes(project_name, client=mock_client)`
2. Examine `changes` list in result

**Expected Results:**
- `result["status"]` is "completed"
- `result["total_new_clearances"]` equals 2
- `result["changes"]` contains one entry with `change_type: "new_clearances"`
- Change entry `count` equals 2
- Change entry `new_items` contains K251001 and K251002 with device_name, applicant, decision_date
- Existing K-numbers not reported as new

**Pass Criteria:** Exactly 2 new clearances detected with correct K-numbers
**Fail Criteria:** Existing clearances reported as new, or new clearances missed

---

### SMART-006: No Changes Detected (Stable State)

**Category:** Functional
**Priority:** Critical
**Module:** `change_detector.py` -- `detect_changes()`

**Prerequisites:**
- Existing fingerprint with `known_k_numbers: ["K241001", "K241002"]`, `clearance_count: 2`, `recall_count: 1`
- FDAClient mock returning exactly the same 2 clearances and 1 recall

**Test Steps:**
1. Call `detect_changes(project_name, client=mock_client)`
2. Examine result

**Expected Results:**
- `result["status"]` is "completed"
- `result["total_new_clearances"]` equals 0
- `result["total_new_recalls"]` equals 0
- `result["changes"]` is an empty list
- Fingerprint `last_checked` is updated to current time

**Pass Criteria:** No false positives -- zero changes reported when data is stable
**Fail Criteria:** Any change incorrectly reported

---

### SMART-007: New Recall Detection

**Category:** Functional
**Priority:** Critical
**Module:** `change_detector.py` -- `detect_changes()`

**Prerequisites:**
- Existing fingerprint with `recall_count: 2`
- FDAClient mock returning recall total of 4

**Test Steps:**
1. Call `detect_changes(project_name, client=mock_client)`
2. Examine changes for recall entry

**Expected Results:**
- `result["total_new_recalls"]` equals 2
- Changes list contains entry with `change_type: "new_recalls"`
- Recall change `count` equals 2
- Recall change `details.previous_count` equals 2 and `details.current_count` equals 4

**Pass Criteria:** Recall delta correctly computed
**Fail Criteria:** Incorrect recall count or missing recall change entry

---

### SMART-008: API Error Graceful Degradation

**Category:** Unit
**Priority:** High
**Module:** `change_detector.py` -- `detect_changes()`, `find_new_clearances()`

**Prerequisites:**
- FDAClient mock configured to return `{"error": "API unavailable", "degraded": True}`

**Test Steps:**
1. Call `detect_changes(project_name, client=mock_client)`
2. Verify no crash and graceful result

**Expected Results:**
- Function does not raise an exception
- `result["status"]` is "completed" (individual product code errors are skipped)
- `result["changes"]` is empty (no false positives from error states)
- Existing fingerprint is NOT modified (no data loss on error)

**Pass Criteria:** Graceful degradation with no data corruption
**Fail Criteria:** Exception raised or fingerprint modified on error

---

### SMART-009: Empty Known K-Numbers List

**Category:** Edge Case (Unit)
**Priority:** High
**Module:** `change_detector.py` -- `detect_changes()`

**Prerequisites:**
- Existing fingerprint with `known_k_numbers: []`, `clearance_count: 0`
- FDAClient mock returning 3 clearances

**Test Steps:**
1. Call `detect_changes(project_name, client=mock_client)`

**Expected Results:**
- All 3 clearances reported as new (since known set is empty)
- `result["total_new_clearances"]` equals 3
- Fingerprint updated with all 3 K-numbers

**Pass Criteria:** All API results treated as new when starting from empty
**Fail Criteria:** Any clearance missed or division-by-zero error

---

### SMART-010: No Fingerprints and No Product Codes

**Category:** Edge Case (Unit)
**Priority:** High
**Module:** `change_detector.py` -- `detect_changes()`

**Prerequisites:**
- Project with `data_manifest.json` containing `{}` (no product_codes, no fingerprints)

**Test Steps:**
1. Call `detect_changes(project_name, client=mock_client)`

**Expected Results:**
- `result["status"]` is "no_fingerprints"
- `result["message"]` contains guidance to run batchfetch first
- `result["total_new_clearances"]` equals 0
- `result["total_new_recalls"]` equals 0

**Pass Criteria:** Correct status with helpful message
**Fail Criteria:** Crash or confusing error message

---

### 3.3 Pipeline Triggering

---

### SMART-011: Pipeline Trigger with Dry-Run

**Category:** Functional
**Priority:** High
**Module:** `change_detector.py` -- `trigger_pipeline()`

**Prerequisites:**
- List of 3 new K-numbers
- `dry_run=True`

**Test Steps:**
1. Call `trigger_pipeline(project, ["K251001", "K251002", "K251003"], "DQY", dry_run=True)`

**Expected Results:**
- `result["status"]` is "dry_run"
- `result["k_numbers_processed"]` equals 3
- `result["k_numbers"]` contains the 3 K-numbers
- No subprocess was actually invoked (no batchfetch, no build_structured_cache)
- Steps list contains preview entry

**Pass Criteria:** Dry run reports correct data without executing anything
**Fail Criteria:** Subprocess actually invoked, or incorrect K-number count

---

### SMART-012: Pipeline Trigger Execution (Mocked)

**Category:** Integration
**Priority:** High
**Module:** `change_detector.py` -- `trigger_pipeline()`, `_run_subprocess()`

**Prerequisites:**
- Mock `subprocess.run` to return successful result (returncode=0)
- `scripts/batchfetch.py` and `scripts/build_structured_cache.py` exist (or paths mocked)

**Test Steps:**
1. Call `trigger_pipeline(project, ["K251001"], "DQY", dry_run=False)`
2. Verify subprocess calls

**Expected Results:**
- `result["status"]` is "completed"
- Two subprocess calls made (batchfetch, build_structured_cache)
- Batchfetch called with correct product code and year range arguments
- Build cache called with correct cache directory
- Steps list contains 2 entries with "success" status

**Pass Criteria:** Both pipeline steps executed with correct arguments
**Fail Criteria:** Missing step, incorrect arguments, or wrong status

---

### SMART-013: Pipeline Trigger with Timeout

**Category:** Unit
**Priority:** High
**Module:** `change_detector.py` -- `_run_subprocess()`

**Prerequisites:**
- Mock `subprocess.run` to raise `subprocess.TimeoutExpired`

**Test Steps:**
1. Call `_run_subprocess(["cmd"], "test_step", timeout_seconds=60, cwd="/tmp")`

**Expected Results:**
- Result `status` is "timeout"
- Result `output` contains diagnostic message with 3 possible causes
- Result `step` is "test_step"
- No exception propagated to caller

**Pass Criteria:** Timeout handled gracefully with user-friendly message
**Fail Criteria:** Exception propagated or unhelpful error message

---

### SMART-014: Pipeline Trigger with Empty K-Numbers

**Category:** Edge Case (Unit)
**Priority:** Medium
**Module:** `change_detector.py` -- `trigger_pipeline()`

**Prerequisites:**
- Empty list of K-numbers

**Test Steps:**
1. Call `trigger_pipeline(project, [], "DQY", dry_run=False)`

**Expected Results:**
- `result["status"]` is "skipped"
- `result["k_numbers_processed"]` equals 0
- `result["message"]` indicates no K-numbers to process
- No subprocess invoked

**Pass Criteria:** Graceful skip with informative message
**Fail Criteria:** Subprocess invoked with empty input

---

### SMART-015: `_run_subprocess` OSError Handling

**Category:** Unit
**Priority:** Medium
**Module:** `change_detector.py` -- `_run_subprocess()`

**Prerequisites:**
- Mock `subprocess.run` to raise `OSError("No such file")`

**Test Steps:**
1. Call `_run_subprocess(["nonexistent"], "test_step", timeout_seconds=60, cwd="/tmp")`

**Expected Results:**
- Result `status` is "error"
- Result `output` contains the OSError message
- No exception propagated

**Pass Criteria:** OSError handled gracefully
**Fail Criteria:** Unhandled exception

---

### 3.4 CLI Interface

---

### SMART-016: CLI with --json Output

**Category:** Functional
**Priority:** Medium
**Module:** `change_detector.py` -- `main()`

**Prerequisites:**
- Mock sys.argv with `["change_detector.py", "--project", "test_proj", "--json"]`
- Mock detect_changes to return sample result

**Test Steps:**
1. Call `main()` with mocked sys.argv and detect_changes
2. Capture stdout

**Expected Results:**
- Output is valid JSON
- JSON contains "project", "status", "changes" keys
- No non-JSON text in output

**Pass Criteria:** Valid JSON output with all expected keys
**Fail Criteria:** Invalid JSON or missing keys

---

### SMART-017: CLI with --trigger Flag

**Category:** Integration
**Priority:** Medium
**Module:** `change_detector.py` -- `main()`

**Prerequisites:**
- Mock sys.argv with `["change_detector.py", "--project", "test_proj", "--trigger"]`
- Mock detect_changes to return result with new clearances
- Mock trigger_pipeline

**Test Steps:**
1. Call `main()` with mocked argv and functions
2. Verify trigger_pipeline was called

**Expected Results:**
- `trigger_pipeline` called for each product code with new clearances
- Correct K-numbers passed to trigger_pipeline
- dry_run parameter matches CLI flag (False when --trigger without --dry-run)

**Pass Criteria:** Pipeline triggered for correct product codes and K-numbers
**Fail Criteria:** Pipeline not triggered or called with wrong data

---

## 4. Section Comparison Analytics Test Cases

### 4.1 Text Similarity

---

### SIM-001: Similarity Scoring Accuracy (All 3 Methods)

**Category:** Unit
**Priority:** Critical
**Module:** `section_analytics.py` -- `compute_similarity()`

**Prerequisites:**
- Three test texts:
  - Text A: "The device is a cardiovascular catheter for percutaneous transluminal coronary angioplasty"
  - Text B: "This cardiovascular catheter device is indicated for percutaneous coronary interventions"
  - Text C: "An orthopedic spinal implant system consisting of pedicle screws and rods"

**Test Steps:**
1. Compute similarity(A, B) for all 3 methods
2. Compute similarity(A, C) for all 3 methods
3. Compute similarity(B, C) for all 3 methods

**Expected Results:**
- For all methods: similarity(A, B) > similarity(A, C)
- For all methods: similarity(A, B) > similarity(B, C)
- All scores between 0.0 and 1.0 (inclusive)
- Sequence method: A-B score > 0.4 (structural overlap)
- Jaccard method: A-B score > 0.3 (vocabulary overlap)
- Cosine method: A-B score > 0.5 (content similarity)

**Pass Criteria:** Similar devices score higher than dissimilar across all methods
**Fail Criteria:** Dissimilar devices score higher, or scores outside [0, 1] range

---

### SIM-002: Identical Text Similarity

**Category:** Unit
**Priority:** Critical
**Module:** `section_analytics.py` -- `compute_similarity()`

**Prerequisites:**
- Same text for both inputs: "ISO 10993-1 biocompatibility testing was performed"

**Test Steps:**
1. Compute similarity(text, text) for all 3 methods

**Expected Results:**
- Sequence method returns 1.0
- Jaccard method returns 1.0
- Cosine method returns 1.0 (or very close, e.g., > 0.9999)

**Pass Criteria:** All methods return 1.0 for identical texts
**Fail Criteria:** Any method returns < 0.99 for identical input

---

### SIM-003: Empty String Similarity

**Category:** Edge Case (Unit)
**Priority:** Critical
**Module:** `section_analytics.py` -- `compute_similarity()`

**Prerequisites:**
- Empty string inputs (various combinations)

**Test Steps:**
1. Compute similarity("", "some text") for all 3 methods
2. Compute similarity("some text", "") for all 3 methods
3. Compute similarity("", "") for all 3 methods

**Expected Results:**
- All return 0.0
- No division-by-zero errors
- No exceptions raised

**Pass Criteria:** All empty-input cases return 0.0 without error
**Fail Criteria:** Exception raised or non-zero score for empty input

---

### SIM-004: Invalid Method Raises ValueError

**Category:** Unit
**Priority:** High
**Module:** `section_analytics.py` -- `compute_similarity()`

**Prerequisites:** None

**Test Steps:**
1. Call `compute_similarity("a", "b", method="invalid_method")`

**Expected Results:**
- `ValueError` raised
- Error message contains the invalid method name
- Error message lists valid methods (sequence, jaccard, cosine)

**Pass Criteria:** ValueError with informative message
**Fail Criteria:** No error raised, or unhelpful error message

---

### SIM-005: Case Insensitivity in Tokenization

**Category:** Unit
**Priority:** Medium
**Module:** `section_analytics.py` -- `_tokenize()`

**Prerequisites:**
- Text with mixed case: "ISO Biocompatibility TESTING Device"

**Test Steps:**
1. Call `_tokenize("ISO Biocompatibility TESTING Device")`

**Expected Results:**
- All tokens lowercase: `["iso", "biocompatibility", "testing", "device"]`
- No punctuation in tokens
- No empty tokens

**Pass Criteria:** Tokens are lowercase with no punctuation
**Fail Criteria:** Mixed case tokens or punctuation included

---

### 4.2 Pairwise Similarity Matrix

---

### SIM-006: Basic Pairwise Matrix Computation

**Category:** Unit
**Priority:** Critical
**Module:** `section_analytics.py` -- `pairwise_similarity_matrix()`

**Prerequisites:**
- Section data for 4 devices with "clinical_testing" sections:
  - K241001: "Clinical testing per ISO 10993-5 cytotoxicity was performed..."
  - K241002: "Clinical evaluation included ISO 10993-5 cytotoxicity testing..."
  - K241003: "Performance testing showed device meets specifications..."
  - K241004: "Clinical testing per ISO 10993-5 and ISO 10993-10 was conducted..."

**Test Steps:**
1. Call `pairwise_similarity_matrix(section_data, "clinical_testing", method="cosine")`

**Expected Results:**
- `result["devices_compared"]` equals 4
- `result["pairs_computed"]` equals 6 (4 choose 2)
- `result["statistics"]["mean"]` is between 0.0 and 1.0
- `result["statistics"]["stdev"]` is >= 0.0
- `result["most_similar_pair"]` has `score` > result["least_similar_pair"]["score"]`
- All scores in `result["scores"]` are between 0.0 and 1.0
- Each score tuple has format (k_number_1, k_number_2, score)

**Pass Criteria:** Correct pair count, valid statistics, ordered extremes
**Fail Criteria:** Wrong pair count, scores outside [0,1], or statistics error

---

### SIM-007: Pairwise Matrix with Sample Size Limit

**Category:** Unit
**Priority:** High
**Module:** `section_analytics.py` -- `pairwise_similarity_matrix()`

**Prerequisites:**
- Section data for 10 devices with "clinical_testing" sections

**Test Steps:**
1. Call `pairwise_similarity_matrix(section_data, "clinical_testing", sample_size=5)`

**Expected Results:**
- `result["devices_compared"]` equals 5 (limited by sample_size)
- `result["pairs_computed"]` equals 10 (5 choose 2)
- Devices selected are the most recent 5 (by K-number sort order)

**Pass Criteria:** Sample size correctly limits computation
**Fail Criteria:** More than 5 devices compared, or random selection

---

### SIM-008: Pairwise Matrix with Insufficient Devices

**Category:** Edge Case (Unit)
**Priority:** High
**Module:** `section_analytics.py` -- `pairwise_similarity_matrix()`

**Prerequisites:**
- Section data with only 1 device having the specified section type
- Section data with 0 devices having the specified section type

**Test Steps:**
1. Call with 1 device: `pairwise_similarity_matrix(section_data, "clinical_testing")`
2. Call with 0 devices: `pairwise_similarity_matrix({}, "clinical_testing")`

**Expected Results:**
- Both return result with `pairs_computed: 0`
- Statistics all equal 0.0
- `most_similar_pair` and `least_similar_pair` are None
- `scores` is empty list
- No exceptions raised

**Pass Criteria:** Graceful handling of insufficient data
**Fail Criteria:** Exception raised or invalid statistics

---

### 4.3 Temporal Trend Analysis

---

### SIM-009: Basic Temporal Trend Detection

**Category:** Unit
**Priority:** Critical
**Module:** `section_analytics.py` -- `analyze_temporal_trends()`

**Prerequisites:**
- Section data for 20 devices spanning 2020-2025
- Clinical testing section coverage increasing over time (e.g., 50% in 2020 -> 90% in 2025)
- Average word count increasing (e.g., 200 words in 2020 -> 500 in 2025)

**Test Steps:**
1. Call `analyze_temporal_trends(section_data, ["clinical_testing"])`

**Expected Results:**
- `result["total_devices"]` equals 20
- `result["year_range"]["start"]` equals 2020
- `result["year_range"]["end"]` equals 2025
- `result["trends"]["clinical_testing"]["coverage_trend"]["direction"]` is "increasing"
- `result["trends"]["clinical_testing"]["coverage_trend"]["slope"]` is positive
- `result["trends"]["clinical_testing"]["length_trend"]["direction"]` is "increasing"
- `by_year` contains entries for each year with device_count, coverage_pct, avg_word_count

**Pass Criteria:** Correct trend direction and valid year-by-year breakdown
**Fail Criteria:** Wrong trend direction or missing yearly data

---

### SIM-010: Stable Trend Detection

**Category:** Unit
**Priority:** High
**Module:** `section_analytics.py` -- `_detect_trend_direction()`

**Prerequisites:**
- Year-value pairs with near-constant values: [(2020, 85.0), (2021, 84.5), (2022, 85.2), (2023, 84.8), (2024, 85.1)]

**Test Steps:**
1. Call `_detect_trend_direction(year_values)`

**Expected Results:**
- `direction` is "stable"
- `slope` is near 0 (absolute value < 0.5)
- `r_squared` is low (variation not explained by linear trend)

**Pass Criteria:** Correctly identified as stable with near-zero slope
**Fail Criteria:** Incorrectly classified as increasing or decreasing

---

### SIM-011: Decreasing Trend Detection

**Category:** Unit
**Priority:** High
**Module:** `section_analytics.py` -- `_detect_trend_direction()`

**Prerequisites:**
- Year-value pairs with decreasing values: [(2020, 500), (2021, 450), (2022, 380), (2023, 310), (2024, 250)]

**Test Steps:**
1. Call `_detect_trend_direction(year_values)`

**Expected Results:**
- `direction` is "decreasing"
- `slope` is negative
- `r_squared` > 0.8 (strong linear relationship)

**Pass Criteria:** Correctly identified as decreasing with negative slope
**Fail Criteria:** Wrong direction classification

---

### SIM-012: Insufficient Data for Trend

**Category:** Edge Case (Unit)
**Priority:** High
**Module:** `section_analytics.py` -- `_detect_trend_direction()`

**Prerequisites:**
- Single data point: [(2024, 85.0)]

**Test Steps:**
1. Call `_detect_trend_direction([(2024, 85.0)])`

**Expected Results:**
- `direction` is "insufficient_data"
- `slope` is 0.0
- `r_squared` is 0.0

**Pass Criteria:** Correctly handles single data point without error
**Fail Criteria:** Exception or incorrect direction

---

### SIM-013: Temporal Trends with Missing Decision Dates

**Category:** Edge Case (Unit)
**Priority:** Medium
**Module:** `section_analytics.py` -- `analyze_temporal_trends()`

**Prerequisites:**
- Section data where 30% of devices have empty `decision_date` fields

**Test Steps:**
1. Call `analyze_temporal_trends(section_data, ["clinical_testing"])`

**Expected Results:**
- Devices with missing dates are excluded from year grouping
- `total_devices` includes all devices (including undated)
- `year_range` only reflects devices with valid dates
- No exceptions from invalid date parsing

**Pass Criteria:** Missing dates handled gracefully
**Fail Criteria:** Exception on empty/invalid date or incorrect count

---

### 4.4 Cross-Product Comparison

---

### SIM-014: Basic Cross-Product Comparison

**Category:** Unit
**Priority:** Critical
**Module:** `section_analytics.py` -- `cross_product_compare()`

**Prerequisites:**
- Structured cache with 10 DQY devices and 8 OVE devices
- Both have clinical_testing and biocompatibility sections
- DQY devices have higher clinical coverage, OVE have longer sections

**Test Steps:**
1. Call `cross_product_compare(["DQY", "OVE"], ["clinical_testing", "biocompatibility"], cache)`

**Expected Results:**
- `result["product_codes"]` equals ["DQY", "OVE"]
- `result["comparison"]["clinical_testing"]["DQY"]["device_count"]` equals 10
- `result["comparison"]["clinical_testing"]["OVE"]["device_count"]` equals 8
- `result["comparison"]["clinical_testing"]["DQY"]["coverage_pct"]` is between 0 and 100
- `result["summary"]["highest_coverage"]` maps each section to the product code with highest coverage
- `result["summary"]["longest_sections"]` maps each section to the product code with longest average word count
- Top standards are returned as (standard_name, count) tuples

**Pass Criteria:** Correct device counts, valid percentages, summary populated
**Fail Criteria:** Wrong device counts or missing summary fields

---

### SIM-015: Cross-Product with Unknown Product Code

**Category:** Edge Case (Unit)
**Priority:** Medium
**Module:** `section_analytics.py` -- `cross_product_compare()`

**Prerequisites:**
- Structured cache with DQY devices only
- Query includes "DQY" and "XYZ" (XYZ has no devices in cache)

**Test Steps:**
1. Call `cross_product_compare(["DQY", "XYZ"], ["clinical_testing"], cache)`

**Expected Results:**
- `result["comparison"]["clinical_testing"]["XYZ"]["device_count"]` equals 0
- `result["comparison"]["clinical_testing"]["XYZ"]["coverage_pct"]` equals 0.0
- DQY comparison data is still valid and present
- No exception raised

**Pass Criteria:** Missing product code handled with zero counts
**Fail Criteria:** Exception raised or DQY data corrupted

---

### SIM-016: Product Code Case Insensitivity

**Category:** Unit
**Priority:** Medium
**Module:** `section_analytics.py` -- `cross_product_compare()`

**Prerequisites:**
- Structured cache with DQY devices (product_code stored as "DQY")
- Query uses lowercase: "dqy"

**Test Steps:**
1. Call `cross_product_compare(["dqy"], ["clinical_testing"], cache)`

**Expected Results:**
- DQY devices found regardless of input case
- `result["product_codes"]` contains "DQY" (uppercase normalized)
- Device counts match actual DQY devices

**Pass Criteria:** Case-insensitive matching
**Fail Criteria:** Zero devices found due to case mismatch

---

## 5. Integration Test Cases

---

### INT-001: Smart Update End-to-End (Detect + Trigger)

**Category:** Integration
**Priority:** Critical
**Module:** `change_detector.py` -- `detect_changes()` + `trigger_pipeline()`

**Prerequisites:**
- Project with existing fingerprint (3 known K-numbers)
- FDAClient mock returning 5 clearances (3 known + 2 new)
- Subprocess mock for batchfetch and build_structured_cache

**Test Steps:**
1. Call `detect_changes()` to find new clearances
2. Extract new K-numbers from result
3. Call `trigger_pipeline()` with new K-numbers

**Expected Results:**
- detect_changes finds 2 new clearances
- trigger_pipeline receives correct 2 K-numbers
- Pipeline steps execute in order (batchfetch first, then build_cache)
- Fingerprint updated after detection

**Pass Criteria:** Full detection-to-pipeline flow completes correctly
**Fail Criteria:** Wrong K-numbers passed to pipeline or steps out of order

---

### INT-002: update_manager.py Smart Mode Integration

**Category:** Integration
**Priority:** High
**Module:** `update_manager.py` -- smart mode calling `change_detector.detect_changes()`

**Prerequisites:**
- update_manager.py with `--smart` flag
- Mock change_detector.detect_changes

**Test Steps:**
1. Invoke update_manager with `--smart --project test_proj`
2. Verify change_detector.detect_changes was called

**Expected Results:**
- change_detector module imported successfully
- detect_changes called with correct project name
- Results displayed in update_manager format

**Pass Criteria:** Smart mode correctly delegates to change_detector
**Fail Criteria:** Import error or wrong function called

---

### INT-003: compare_sections.py Similarity Integration

**Category:** Integration
**Priority:** High
**Module:** `compare_sections.py` + `section_analytics.py`

**Prerequisites:**
- Structured cache with 5 devices having clinical_testing sections
- CLI invocation: `--product-code DQY --sections clinical --similarity`

**Test Steps:**
1. Invoke compare_sections with `--similarity` flag
2. Verify section_analytics.pairwise_similarity_matrix was called
3. Check output report contains Section 5 (Similarity Analysis)

**Expected Results:**
- section_analytics module imported by compare_sections
- pairwise_similarity_matrix called with correct section_type and method
- Report includes similarity statistics (mean, median, stdev)
- Most and least similar pairs identified

**Pass Criteria:** Similarity analysis integrated into report output
**Fail Criteria:** Import error or missing report section

---

### INT-004: compare_sections.py Trends Integration

**Category:** Integration
**Priority:** High
**Module:** `compare_sections.py` + `section_analytics.py`

**Prerequisites:**
- Structured cache with devices spanning 2020-2025
- CLI invocation: `--product-code DQY --sections clinical --trends`

**Test Steps:**
1. Invoke compare_sections with `--trends` flag
2. Verify section_analytics.analyze_temporal_trends was called
3. Check output report contains Section 6 (Temporal Trends)

**Expected Results:**
- analyze_temporal_trends called with correct section types
- Report includes trend direction (increasing/stable/decreasing)
- Year-by-year breakdown in report
- Trend slope and R-squared values present

**Pass Criteria:** Temporal trends integrated into report output
**Fail Criteria:** Missing trend section or wrong trend data

---

### INT-005: compare_sections.py Cross-Product Integration

**Category:** Integration
**Priority:** High
**Module:** `compare_sections.py` + `section_analytics.py`

**Prerequisites:**
- Structured cache with DQY and OVE devices
- CLI invocation: `--product-codes DQY,OVE --sections clinical,biocompatibility`

**Test Steps:**
1. Invoke compare_sections with `--product-codes` flag
2. Verify section_analytics.cross_product_compare was called
3. Check report includes cross-product comparison section

**Expected Results:**
- cross_product_compare called with both product codes and both section types
- Report includes per-product-code coverage and word count comparison
- Summary shows highest coverage and longest sections per product code

**Pass Criteria:** Cross-product comparison section in report with both codes
**Fail Criteria:** Only one product code analyzed or missing comparison

---

### INT-006: Auto-Build Cache Error Handling

**Category:** Integration
**Priority:** Medium
**Module:** `compare_sections.py` -- auto-build cache path

**Prerequisites:**
- No structured cache exists at expected path
- `build_structured_cache.py` exists but mock it to fail

**Test Steps:**
1. Invoke compare_sections when no cache exists
2. Verify auto-build attempt and error handling

**Expected Results:**
- Error message includes actionable guidance:
  - Check if structured cache path exists
  - Run build_structured_cache.py manually
  - Verify file permissions
- No unhandled exception
- Clear exit with non-zero status

**Pass Criteria:** User-friendly error with actionable suggestions
**Fail Criteria:** Cryptic error or unhandled exception

---

## 6. Performance Test Cases

---

### PERF-001: Pairwise Similarity Computation Time

**Category:** Performance
**Priority:** Medium
**Module:** `section_analytics.py` -- `pairwise_similarity_matrix()`

**Prerequisites:**
- Section data for 30 devices with ~500 word sections

**Test Steps:**
1. Time `pairwise_similarity_matrix()` with 30 devices using each method
2. Compute pairs: 30 * 29 / 2 = 435 pairs

**Expected Results:**
- Sequence method: < 10 seconds for 435 pairs
- Jaccard method: < 5 seconds for 435 pairs
- Cosine method: < 5 seconds for 435 pairs
- Memory usage does not exceed 100MB

**Pass Criteria:** All methods complete within time limits
**Fail Criteria:** Any method exceeds 2x time limit

---

### PERF-002: Temporal Trend Analysis Scaling

**Category:** Performance
**Priority:** Low
**Module:** `section_analytics.py` -- `analyze_temporal_trends()`

**Prerequisites:**
- Section data for 200 devices spanning 10 years
- 5 section types analyzed

**Test Steps:**
1. Time `analyze_temporal_trends()` with 200 devices and 5 section types

**Expected Results:**
- Completes in < 5 seconds
- Linear scaling with device count (no quadratic behavior)

**Pass Criteria:** Completes within time limit
**Fail Criteria:** Exceeds 10 seconds

---

### PERF-003: Cross-Product Comparison with Large Cache

**Category:** Performance
**Priority:** Low
**Module:** `section_analytics.py` -- `cross_product_compare()`

**Prerequisites:**
- Structured cache with 500 devices across 5 product codes
- 3 section types analyzed

**Test Steps:**
1. Time `cross_product_compare()` with 5 product codes and 3 section types

**Expected Results:**
- Completes in < 10 seconds
- Memory usage does not exceed 200MB

**Pass Criteria:** Completes within time limit
**Fail Criteria:** Exceeds 20 seconds

---

## 7. Test Data Fixtures

### 7.1 Sample Fingerprint Fixture

```python
SAMPLE_FINGERPRINT = {
    "last_checked": "2026-02-15T10:00:00+00:00",
    "clearance_count": 147,
    "latest_k_number": "K251234",
    "latest_decision_date": "20260115",
    "recall_count": 3,
    "known_k_numbers": ["K241001", "K241002", "K241003", "K241004", "K241005"],
}
```

### 7.2 Sample API Clearance Response

```python
SAMPLE_CLEARANCE_RESPONSE = {
    "meta": {"results": {"total": 149}},
    "results": [
        {
            "k_number": "K261001",
            "device_name": "Percutaneous Transluminal Coronary Catheter",
            "applicant": "MedTech Corp",
            "decision_date": "20260201",
            "decision_code": "SESE",
            "clearance_type": "Traditional",
            "product_code": "DQY",
        },
        {
            "k_number": "K261002",
            "device_name": "Coronary Catheter System",
            "applicant": "CardioDevices Inc",
            "decision_date": "20260115",
            "decision_code": "SESE",
            "clearance_type": "Traditional",
            "product_code": "DQY",
        },
        # ... existing K-numbers from fingerprint would also appear here
    ],
}
```

### 7.3 Sample Section Data Fixture

```python
SAMPLE_SECTION_DATA = {
    "K241001": {
        "decision_date": "20240315",
        "sections": {
            "clinical_testing": {
                "text": "Clinical testing per ISO 10993-5 cytotoxicity was performed on the device...",
                "word_count": 250,
                "standards": ["ISO 10993-5", "ISO 10993-10"],
            },
            "biocompatibility": {
                "text": "Biocompatibility was evaluated per ISO 10993-1 risk assessment framework...",
                "word_count": 180,
                "standards": ["ISO 10993-1"],
            },
        },
        "metadata": {"product_code": "DQY"},
    },
    "K241002": {
        "decision_date": "20240601",
        "sections": {
            "clinical_testing": {
                "text": "Clinical evaluation included ISO 10993-5 cytotoxicity and ISO 10993-10...",
                "word_count": 300,
                "standards": ["ISO 10993-5", "ISO 10993-10", "ISO 10993-11"],
            },
        },
        "metadata": {"product_code": "DQY"},
    },
    # Add more devices as needed for test scenarios
}
```

### 7.4 Sample Structured Cache Fixture

```python
SAMPLE_STRUCTURED_CACHE = {
    "K241001": {
        "metadata": {"product_code": "DQY"},
        "sections": {
            "clinical_testing": {
                "text": "Clinical testing was performed...",
                "word_count": 250,
                "standards": ["ISO 10993-5"],
            },
        },
    },
    "K241010": {
        "metadata": {"product_code": "OVE"},
        "sections": {
            "clinical_testing": {
                "text": "Mechanical testing of the spinal implant...",
                "word_count": 400,
                "standards": ["ASTM F1717", "ASTM F2077"],
            },
        },
    },
}
```

---

## 8. Test Execution Procedure

### 8.1 Running All Tests

```bash
# From project root
cd /home/linux/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools

# Run all new feature tests
python3 -m pytest tests/test_change_detector.py tests/test_section_analytics.py -v

# Run with coverage
python3 -m pytest tests/test_change_detector.py tests/test_section_analytics.py --cov=scripts/change_detector --cov=scripts/section_analytics --cov-report=term-missing
```

### 8.2 Running by Priority

```bash
# Critical tests only (must pass for release)
python3 -m pytest tests/ -k "SMART_001 or SMART_002 or SMART_005 or SMART_006 or SMART_007 or SIM_001 or SIM_002 or SIM_003 or SIM_006 or SIM_009 or SIM_014 or INT_001" -v

# High priority
python3 -m pytest tests/ -k "high" -v

# All including performance
python3 -m pytest tests/ -v --timeout=60
```

### 8.3 Test Reports

```bash
# Generate HTML report
python3 -m pytest tests/test_change_detector.py tests/test_section_analytics.py --html=reports/test_report.html

# Generate JUnit XML for CI
python3 -m pytest tests/test_change_detector.py tests/test_section_analytics.py --junitxml=reports/junit.xml
```

---

## 9. Traceability Matrix

| Test ID | Module | Function | Requirement |
|---------|--------|----------|-------------|
| SMART-001 | change_detector | _save_fingerprint, detect_changes | Fingerprint creation on first run |
| SMART-002 | change_detector | _save_fingerprint, _load_fingerprint | Fingerprint update persistence |
| SMART-003 | change_detector | _load_fingerprint, _save_fingerprint | Cross-session persistence |
| SMART-004 | change_detector | detect_changes | Multi-product-code support |
| SMART-005 | change_detector | detect_changes, find_new_clearances | New clearance detection |
| SMART-006 | change_detector | detect_changes | Stable state (no false positives) |
| SMART-007 | change_detector | detect_changes | Recall monitoring |
| SMART-008 | change_detector | detect_changes | API error graceful degradation |
| SMART-009 | change_detector | detect_changes | Empty known list edge case |
| SMART-010 | change_detector | detect_changes | No fingerprints edge case |
| SMART-011 | change_detector | trigger_pipeline | Dry-run mode |
| SMART-012 | change_detector | trigger_pipeline, _run_subprocess | Pipeline execution |
| SMART-013 | change_detector | _run_subprocess | Timeout handling |
| SMART-014 | change_detector | trigger_pipeline | Empty K-numbers |
| SMART-015 | change_detector | _run_subprocess | OSError handling |
| SMART-016 | change_detector | main | JSON CLI output |
| SMART-017 | change_detector | main | Pipeline trigger from CLI |
| SIM-001 | section_analytics | compute_similarity | Multi-method accuracy |
| SIM-002 | section_analytics | compute_similarity | Identical text = 1.0 |
| SIM-003 | section_analytics | compute_similarity | Empty string = 0.0 |
| SIM-004 | section_analytics | compute_similarity | Invalid method error |
| SIM-005 | section_analytics | _tokenize | Case insensitivity |
| SIM-006 | section_analytics | pairwise_similarity_matrix | Basic matrix computation |
| SIM-007 | section_analytics | pairwise_similarity_matrix | Sample size limiting |
| SIM-008 | section_analytics | pairwise_similarity_matrix | Insufficient devices |
| SIM-009 | section_analytics | analyze_temporal_trends | Increasing trend detection |
| SIM-010 | section_analytics | _detect_trend_direction | Stable trend detection |
| SIM-011 | section_analytics | _detect_trend_direction | Decreasing trend detection |
| SIM-012 | section_analytics | _detect_trend_direction | Single data point |
| SIM-013 | section_analytics | analyze_temporal_trends | Missing decision dates |
| SIM-014 | section_analytics | cross_product_compare | Multi-code comparison |
| SIM-015 | section_analytics | cross_product_compare | Unknown product code |
| SIM-016 | section_analytics | cross_product_compare | Case insensitivity |
| INT-001 | change_detector | detect + trigger | End-to-end flow |
| INT-002 | update_manager | smart mode | Module integration |
| INT-003 | compare_sections + analytics | similarity | Report integration |
| INT-004 | compare_sections + analytics | trends | Report integration |
| INT-005 | compare_sections + analytics | cross-product | Report integration |
| INT-006 | compare_sections | auto-build cache | Error handling |
| PERF-001 | section_analytics | pairwise_similarity_matrix | Computation time |
| PERF-002 | section_analytics | analyze_temporal_trends | Scaling behavior |
| PERF-003 | section_analytics | cross_product_compare | Large cache handling |

---

## 10. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-16 | Workflow Orchestrator | Initial specification (34 test cases) |
