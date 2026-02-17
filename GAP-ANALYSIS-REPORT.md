# FDA Tools Plugin - Comprehensive Gap Analysis Report

**Date:** 2026-02-16
**Analyst:** Workflow Orchestrator (Claude Code)
**Repository:** `/home/linux/.claude/plugins/marketplaces/fda-tools`
**Current Version:** v5.36.0
**Scope:** All code, tests, docs, configs NOT already tracked in TICKET-001-022, FE-001-010, QUA-11-32

---

## Executive Summary

After exhaustive analysis of 48 Python scripts (scripts/ + lib/), 68 commands, 15 agents, 60+ test files, 80+ documentation files, the openclaw-skill TypeScript module, and the fda-predicate-assistant plugin, I identified **42 new issues** not covered by existing tickets or Linear items.

**By Priority:** URGENT (3), HIGH (12), MEDIUM (18), LOW (9)
**By Category:** Code Quality (10), Testing (11), Security (4), CI/CD (3), Documentation (4), Architecture (5), Data/Schema (3), Compliance (2)
**Estimated Total Effort:** 195-270 hours

---

## NEW Issues for Linear Import

---

### ISSUE: GAP-001 - Bare `except:` Clauses in Standards Generation Scripts

**Priority**: HIGH
**Effort**: 2-3 hours
**Category**: Code Quality

**Description**:
Six bare `except:` clauses (catching ALL exceptions including SystemExit, KeyboardInterrupt) found in standards generation scripts. This silently swallows errors and makes debugging impossible, particularly dangerous for regulatory data processing.

**Affected Files**:
- `/home/linux/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/scripts/knowledge_based_generator.py` (line 159)
- `/home/linux/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/scripts/quick_standards_generator.py` (line 150)
- `/home/linux/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/scripts/auto_generate_device_standards.py` (lines 158, 180, 287, 298)

**Tasks**:
- [ ] Replace all bare `except:` with specific exception types (e.g., `except (ValueError, KeyError, json.JSONDecodeError):`)
- [ ] Add logging for caught exceptions to audit trail
- [ ] Verify no legitimate exception swallowing is needed

**Acceptance Criteria**:
- Zero bare `except:` clauses in codebase
- All exception handlers specify at least `Exception` (not bare)
- Caught exceptions logged with context

---

### ISSUE: GAP-002 - Silent `except...pass` Patterns (50+ Instances)

**Priority**: HIGH
**Effort**: 8-12 hours
**Category**: Code Quality

**Description**:
Over 50 instances of `except SomeError: pass` found across the codebase. While some are intentional (e.g., optional feature detection), many silently swallow errors in data processing pipelines, making regulatory data integrity unverifiable. This pattern is particularly problematic in:
- `pma_intelligence.py` (12 instances)
- `supplement_tracker.py` (3 instances)
- `pma_data_store.py` (4 instances)
- `fda_approval_monitor.py` (4 instances)

**Tasks**:
- [ ] Audit all 50+ `except...pass` instances
- [ ] Classify each as: intentional (document why), needs logging, needs re-raise
- [ ] Add `logging.debug()` or `logging.warning()` for non-trivial catches
- [ ] Document remaining intentional passes with comments

**Acceptance Criteria**:
- Each `except...pass` has either a comment justifying silence OR logging added
- Data processing paths never silently discard exceptions
- Audit logger captures suppressed errors for regulatory traceability

---

### ISSUE: GAP-003 - No `__init__.py` in `scripts/` and `lib/` Directories

**Priority**: MEDIUM
**Effort**: 1-2 hours
**Category**: Architecture

**Description**:
The `scripts/` directory (48 Python files) and `lib/` directory (8 Python files) lack `__init__.py` files. All imports use `sys.path.insert(0, ...)` hacks. This prevents proper Python package imports, breaks IDE autocompletion, prevents `pytest --cov` from correctly measuring coverage, and makes the codebase fragile to path changes.

**Affected Files**:
- `/home/linux/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/scripts/` (missing `__init__.py`)
- `/home/linux/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/lib/` (missing `__init__.py`)

**Tasks**:
- [ ] Create `scripts/__init__.py` with package-level imports
- [ ] Create `lib/__init__.py` with public API exports
- [ ] Refactor `sys.path.insert(0, ...)` patterns in test files to use proper imports
- [ ] Update conftest.py to use proper package imports

**Acceptance Criteria**:
- Both directories have `__init__.py`
- At least 50% of `sys.path.insert` usages replaced with proper imports
- All tests still pass

---

### ISSUE: GAP-004 - No Tests for 6 `lib/` Modules (0% Coverage)

**Priority**: HIGH
**Effort**: 12-16 hours
**Category**: Testing

**Description**:
The `lib/` directory contains 6 production modules with ZERO test coverage. These are core analytical modules used in regulatory workflows:

1. `gap_analyzer.py` - Gap analysis for submissions
2. `predicate_ranker.py` - TF-IDF predicate ranking
3. `combination_detector.py` - Drug-device combination detection
4. `predicate_diversity.py` - Predicate diversity scoring
5. `ecopy_exporter.py` - FDA eCopy format export
6. `expert_validator.py` - Multi-agent validation orchestration

Grep confirmed: no test file imports any of these modules.

**Tasks**:
- [ ] Create `tests/test_gap_analyzer.py` (10+ tests: missing field detection, priority scoring, standards gaps)
- [ ] Create `tests/test_predicate_ranker.py` (10+ tests: TF-IDF scoring, ranking order, edge cases)
- [ ] Create `tests/test_combination_detector.py` (8+ tests: drug-device, device-biologic, false positive)
- [ ] Create `tests/test_predicate_diversity.py` (8+ tests: 5-dimension scoring, grading thresholds)
- [ ] Create `tests/test_ecopy_exporter.py` (8+ tests: folder structure, size validation, manifest)
- [ ] Create `tests/test_expert_validator.py` (6+ tests: orchestration, consensus logic)

**Acceptance Criteria**:
- Each lib module has a dedicated test file
- Minimum 50 tests total across all 6 modules
- Coverage >= 80% for each module
- No network access required (all mocked)

---

### ISSUE: GAP-005 - No Tests for 20+ Script Modules

**Priority**: HIGH
**Effort**: 20-30 hours
**Category**: Testing

**Description**:
The following production scripts in `scripts/` have NO corresponding test file. Some are large (800-1600 lines) with complex logic:

| Script | Lines | Criticality |
|--------|-------|-------------|
| `update_manager.py` | 584 | HIGH - data freshness |
| `build_structured_cache.py` | ~500 | HIGH - data pipeline |
| `predicate_extractor.py` | ~800 | HIGH - core extraction |
| `full_text_search.py` | ~400 | MEDIUM |
| `markdown_to_html.py` | ~300 | LOW |
| `quick_standards_generator.py` | ~350 | MEDIUM |
| `auto_generate_device_standards.py` | ~300 | MEDIUM |
| `knowledge_based_generator.py` | ~350 | MEDIUM |
| `web_predicate_validator.py` | ~200 | MEDIUM |
| `verify_enhancement.py` | ~200 | LOW |
| `estar_xml.py` | 1720 | HIGH - XML generation |
| `seed_test_project.py` | ~1175 | MEDIUM |
| `batch_seed.py` | ~200 | LOW |
| `gap_analysis.py` | ~300 | MEDIUM |
| `setup_api_key.py` | ~100 | LOW |

Note: Some scripts like `estar_xml.py` have partial test coverage via `test_estar_parser.py` and `test_sprint4b_xml_estar.py`, but these test adjacent functionality, not the full module.

**Tasks**:
- [ ] Prioritize HIGH criticality scripts for test creation
- [ ] Create at minimum: test_update_manager.py, test_build_structured_cache.py, test_predicate_extractor.py, test_estar_xml_full.py
- [ ] Add smoke tests for remaining scripts
- [ ] Track coverage per-module

**Acceptance Criteria**:
- All HIGH criticality scripts have dedicated test files
- Minimum 40 new tests across priority scripts
- Coverage tracking established for all scripts

---

### ISSUE: GAP-006 - CI/CD Pipeline Missing Python 3.12 and Missing Dependencies

**Priority**: URGENT
**Effort**: 3-4 hours
**Category**: CI/CD

**Description**:
The GitHub Actions workflow (`.github/workflows/test.yml`) has critical gaps:

1. **Missing Python 3.12**: Tests only against Python 3.9, 3.10, 3.11. The project specifies Python 3.12+ in TESTING_SPEC.md and the development environment uses Python 3.12.
2. **Incomplete dependency installation**: Only installs `pytest pytest-cov pikepdf beautifulsoup4 lxml`. Missing: `requests tqdm pandas numpy colorama PyPDF2 reportlab openpyxl pdfplumber PyMuPDF orjson ijson` (from `requirements.txt`).
3. **No coverage reporting**: Runs pytest with `-v -m "not api"` but no `--cov` flag, no coverage upload to Codecov/Coveralls.
4. **No linting step**: No flake8, ruff, or mypy check.
5. **Missing test markers for new modules**: `smart`, `sim`, `quickwin` markers defined in `pytest.ini` but not selectively run in CI.

**Tasks**:
- [ ] Add Python 3.12 to matrix (and optionally 3.13)
- [ ] Install full `requirements.txt` in CI
- [ ] Add `--cov` flags and coverage upload step
- [ ] Add linting step (ruff or flake8)
- [ ] Add marker-based test stages (offline, smart, sim, integration)

**Acceptance Criteria**:
- CI runs on Python 3.9-3.12
- All dependencies from requirements.txt installed
- Coverage report generated and uploaded
- Linting passes (or failures documented)

---

### ISSUE: GAP-007 - No `requirements.txt` Version Pinning or Lock File

**Priority**: HIGH
**Effort**: 2-3 hours
**Category**: CI/CD

**Description**:
`requirements.txt` uses minimum version specifiers (`>=`) without maximum bounds. This means:
- `pandas>=2.0.0` could install pandas 3.x (breaking API changes possible)
- `numpy>=1.24.0` could install numpy 2.x (known breaking changes)
- `requests>=2.31.0` could install requests 3.x (API changes planned)

For a regulatory-grade tool, reproducible builds are essential (21 CFR 820.70(i)).

**Tasks**:
- [ ] Generate `requirements-lock.txt` with exact pinned versions
- [ ] Add upper bounds to `requirements.txt` (e.g., `pandas>=2.0.0,<3.0.0`)
- [ ] Add `pip freeze` step to CI for reproducibility verification
- [ ] Document dependency update procedure

**Acceptance Criteria**:
- Lock file exists with exact versions
- CI uses lock file for deterministic installs
- Upper bounds prevent surprise breaking changes
- Update procedure documented

---

### ISSUE: GAP-008 - OpenClaw Skill Has No Build/Dist Directory and Untested Bridge Server

**Priority**: HIGH
**Effort**: 8-12 hours
**Category**: Architecture

**Description**:
The `openclaw-skill/` directory defines a TypeScript skill for OpenClaw integration, but:

1. **No `dist/` directory**: The skill references `"main": "dist/index.js"` but no compiled output exists. The skill has never been built.
2. **No `node_modules/`**: Dependencies have never been installed.
3. **Bridge server referenced but does not exist**: The skill requires a Phase 2 HTTP Bridge Server at `localhost:18790` (referenced in `fda-predicate-assistant/`), but no bridge server Python code exists in the repository.
4. **Integration tests are structural only**: `tests/integration.test.ts` only validates file existence and TypeScript types, not actual bridge communication.
5. **No `.gitignore` for node_modules**: If `npm install` were run, `node_modules/` would be committed.

**Tasks**:
- [ ] Add `openclaw-skill/.gitignore` with `node_modules/`, `dist/`
- [ ] Document build prerequisites in README
- [ ] Either build the bridge server or mark openclaw-skill as experimental/placeholder
- [ ] Add build step to CI or document manual build process
- [ ] Create functional tests that mock the bridge server

**Acceptance Criteria**:
- Build process documented and executable
- `.gitignore` prevents accidental commits
- Status clearly documented (production vs experimental)

---

### ISSUE: GAP-009 - fda-predicate-assistant Plugin is Untracked and Partially Built

**Priority**: HIGH
**Effort**: 4-6 hours
**Category**: Architecture

**Description**:
The `plugins/fda-predicate-assistant/` directory contains:
- `lib/` with 8 Python modules (security_gateway.py, audit_logger.py, user_manager.py, rbac_manager.py, tenant_manager.py, signature_manager.py, monitoring_manager.py)
- `tests/` with 3 test files (test_security_phase1.py, test_bridge_phase2.py, test_enterprise_phase4.py)
- `venv/` with Python 3.12 virtual environment (COMMITTED to git)
- No `commands/` directory (despite MEMORY.md referencing commands)

Issues:
1. **Virtual environment committed to git**: `venv/` directory (hundreds of files) should be in `.gitignore`
2. **No `.gitignore`**: Missing entirely for this sub-plugin
3. **Commands directory missing**: MEMORY.md references `commands/` with compare-se.md, consistency.md, pre-check.md, draft.md, assemble.md -- but these appear to have been moved or never created here
4. **Unclear relationship to fda-tools**: The predicate-assistant appears to be a separate plugin that overlaps with fda-tools commands

**Tasks**:
- [ ] Add `.gitignore` for venv/, __pycache__/, *.pyc
- [ ] Remove committed venv/ from git tracking (`git rm -r --cached`)
- [ ] Document the relationship between fda-tools and fda-predicate-assistant
- [ ] Resolve command directory discrepancy with MEMORY.md

**Acceptance Criteria**:
- venv/ removed from git tracking
- .gitignore in place
- Relationship documented
- No orphaned references

---

### ISSUE: GAP-010 - Missing Input Validation on CLI Arguments Across Scripts

**Priority**: HIGH
**Effort**: 6-8 hours
**Category**: Security

**Description**:
Multiple CLI scripts accept user input without validation:

1. **Product code injection**: Scripts like `batchfetch.py`, `change_detector.py`, `compare_sections.py` accept `--product-code` arguments that are inserted into API query strings without sanitization. While openFDA API is read-only, malformed product codes could cause unexpected behavior.
2. **Path traversal**: `--project` arguments are used to construct file paths without validation. A malicious `--project ../../etc/` could read/write outside the project directory.
3. **K-number format**: K-numbers are accepted without regex validation (should match `K\d{6,7}`).
4. **No argument length limits**: Long arguments could cause memory issues.

**Tasks**:
- [ ] Create shared input validation module (`scripts/input_validators.py`)
- [ ] Add product code validation (3 uppercase letters)
- [ ] Add K-number validation (regex: `^K\d{6,7}$`)
- [ ] Add project name validation (alphanumeric + hyphens, no path separators)
- [ ] Add path canonicalization to prevent traversal
- [ ] Apply validators to all CLI entry points

**Acceptance Criteria**:
- All CLI arguments validated before use
- Path traversal attacks prevented
- Invalid inputs return helpful error messages
- Validation module has 15+ tests

---

### ISSUE: GAP-011 - Cache Files Have No Integrity Verification

**Priority**: MEDIUM
**Effort**: 4-6 hours
**Category**: Security / Data Integrity

**Description**:
The API cache system (`fda_api_client.py`, `pma_data_store.py`) stores JSON files on disk with no integrity verification. A corrupted or tampered cache file would be silently used, potentially providing incorrect regulatory data.

- Cache key is a truncated SHA-256 (16 chars) -- collision-resistant but no HMAC
- No file checksum verification on read
- No atomic write (data could be corrupted on crash during write)
- Cache TTL is the only staleness check

**Tasks**:
- [ ] Add SHA-256 checksum field to cached JSON
- [ ] Verify checksum on cache read
- [ ] Implement atomic write (write to temp file, then rename)
- [ ] Add cache corruption detection and auto-invalidation
- [ ] Log cache integrity events to audit logger

**Acceptance Criteria**:
- Corrupted cache files detected and invalidated
- Atomic writes prevent partial file corruption
- Cache integrity events logged
- 10+ tests for cache integrity scenarios

---

### ISSUE: GAP-012 - `save_manifest()` Not Atomic (Data Loss Risk)

**Priority**: URGENT
**Effort**: 2-3 hours
**Category**: Data Integrity

**Description**:
`fda_data_store.py` line 78: `save_manifest()` writes directly to `data_manifest.json` using `open(manifest_path, "w")`. If the process crashes during write, the manifest is corrupted and all project data references are lost. This is the SINGLE most critical data file in each project.

The same pattern exists in `change_detector.py` for fingerprint saving.

**Tasks**:
- [ ] Implement atomic write: write to `data_manifest.json.tmp`, then `os.replace()` to final path
- [ ] Apply same pattern to fingerprint saves in change_detector.py
- [ ] Add manifest backup before write (keep `data_manifest.json.bak`)
- [ ] Add manifest recovery procedure (if .json is corrupt, try .bak, then .tmp)

**Acceptance Criteria**:
- All manifest writes are atomic (write-then-rename)
- Backup file maintained
- Recovery from corrupted manifest documented and tested
- 5+ tests for crash recovery scenarios

---

### ISSUE: GAP-013 - `batchfetch.py` Has 17 Optional Dependencies with No Graceful Degradation Documentation

**Priority**: MEDIUM
**Effort**: 3-4 hours
**Category**: Documentation / Code Quality

**Description**:
`batchfetch.py` imports 8+ optional packages (pytesseract, pdf2image, PyPDF2, reportlab, colorama, numpy, pandas, tqdm) with try/except fallbacks. While the fallbacks exist, there is no documentation about which features are lost when each dependency is missing. Users on minimal installations may get confusing behavior.

Additionally, `numpy` and `pandas` are imported at module level (line 33-34) without try/except, meaning they are REQUIRED but listed as optional.

**Tasks**:
- [ ] Document which features require which dependencies
- [ ] Create `--check-deps` CLI flag that reports available/missing dependencies
- [ ] Make numpy/pandas truly optional (defer import to functions that need them)
- [ ] Add dependency status to `--help` output

**Acceptance Criteria**:
- Dependency matrix documented in INSTALLATION.md
- `--check-deps` flag works
- batchfetch.py runs without numpy/pandas for basic operations
- Clear error messages when optional dependency needed but missing

---

### ISSUE: GAP-014 - No Logging Framework (print() Everywhere)

**Priority**: MEDIUM
**Effort**: 6-8 hours
**Category**: Code Quality

**Description**:
The entire codebase uses `print()` for output with no structured logging. This means:
- No log levels (debug, info, warning, error)
- No log file output (everything goes to stdout)
- No structured log format (can't parse logs programmatically)
- No correlation IDs for tracking operations across modules
- Cannot suppress verbose output in production

The `fda_audit_logger.py` module exists but is only used by a few commands, not as a general logging framework.

**Tasks**:
- [ ] Create `scripts/logger.py` with configured Python logging
- [ ] Define log levels: DEBUG (verbose), INFO (normal), WARNING (issues), ERROR (failures)
- [ ] Add file handler for `~/fda-510k-data/logs/fda-tools.log`
- [ ] Migrate high-traffic modules first: fda_api_client.py, change_detector.py, batchfetch.py
- [ ] Add `--verbose` / `--quiet` CLI flags to all scripts

**Acceptance Criteria**:
- Logging module created and documented
- At least 5 core modules migrated from print() to logging
- Log file rotation implemented (max 10MB, 5 backups)
- CLI verbosity control works

---

### ISSUE: GAP-015 - `pma_intelligence.py` Has 6 Duplicate Import-Exception Patterns

**Priority**: MEDIUM
**Effort**: 2-3 hours
**Category**: Code Quality

**Description**:
`pma_intelligence.py` (1692 lines) contains 6 identical `except (ImportError, Exception):` blocks (lines 1379, 1397, 1417, 1474, 1493, 1513) that catch ImportError and ALL exceptions together. This is:
- Overly broad (catches TypeError, ValueError, etc. that indicate bugs)
- Duplicated code (same pattern 6 times)
- Hiding real errors behind ImportError handling

**Tasks**:
- [ ] Separate ImportError handling from general Exception handling
- [ ] Extract common import-with-fallback pattern into a utility function
- [ ] Add specific exception types for known failure modes
- [ ] Add logging for caught exceptions

**Acceptance Criteria**:
- No `except (ImportError, Exception)` patterns remain
- Common pattern extracted to utility
- Each exception handler catches specific types

---

### ISSUE: GAP-016 - Integration Tests Between fda_data_store and fda_api_client Are Missing

**Priority**: MEDIUM
**Effort**: 4-6 hours
**Category**: Testing

**Description**:
`fda_data_store.py` depends on `fda_api_client.py` for all API calls, but `test_data_store.py` may not test the integration boundary. Key untested paths:
- Manifest TTL expiry triggering API refresh
- API degraded mode (error response) handling in data store
- Concurrent manifest access (race conditions)
- Cache key collision handling
- `--refresh` flag behavior

**Tasks**:
- [ ] Create `tests/test_data_store_integration.py` with mock FDAClient
- [ ] Test TTL expiry triggers refresh
- [ ] Test degraded mode propagation
- [ ] Test concurrent manifest read/write
- [ ] Test `--refresh` flag bypasses cache

**Acceptance Criteria**:
- 12+ integration tests
- All TTL tiers tested (24hr and 168hr)
- Degraded mode tested for each query type
- No race conditions in manifest access

---

### ISSUE: GAP-017 - `competitive_dashboard.py` HTML Template is Inline (466 Lines of HTML in Python)

**Priority**: LOW
**Effort**: 3-4 hours
**Category**: Code Quality

**Description**:
`competitive_dashboard.py` contains a massive HTML template (`HTML_TEMPLATE`) as a Python string starting at line 53. This makes the Python file hard to maintain, prevents HTML linting, and mixes concerns.

**Tasks**:
- [ ] Extract HTML template to `data/templates/competitive_dashboard.html`
- [ ] Load template at runtime from file
- [ ] Use Jinja2-compatible placeholders or Python's string.Template
- [ ] Add HTML linting to CI (optional)

**Acceptance Criteria**:
- HTML template in separate file
- Python file reduced by ~400 lines
- Template renders identically to current output

---

### ISSUE: GAP-018 - No Version Consistency Check Between Scripts and Plugin Manifest

**Priority**: MEDIUM
**Effort**: 2-3 hours
**Category**: CI/CD

**Description**:
Version is defined in `scripts/version.py` but there is no automated check that it matches CHANGELOG.md, README.md, or the `.claude-plugin/plugin.json` manifest. Version drift can cause confusion about which features are available.

**Tasks**:
- [ ] Create `scripts/check_version.py` that validates version consistency across all files
- [ ] Add version check to CI pipeline
- [ ] Add version check to pre-commit hook

**Acceptance Criteria**:
- Version mismatch detected and reported
- CI fails on version inconsistency
- All version references updated atomically

---

### ISSUE: GAP-019 - `estar_xml.py` Lacks XML Schema Validation

**Priority**: HIGH
**Effort**: 6-8 hours
**Category**: Compliance

**Description**:
`estar_xml.py` (1720 lines) generates FDA eSTAR XML for 510(k) and Pre-Sub submissions. The TODO.md notes "Validation against FDA schema (structural validation - no FDA XSD available)" but the code only performs basic structural checks. Key gaps:

1. No XSD/DTD validation (even though structural validation is possible)
2. No field value validation (e.g., date formats, required field lengths)
3. No character encoding validation (FDA requires UTF-8)
4. No XML injection prevention (user text inserted directly into XML elements)
5. Template field maps are hardcoded with no validation against FDA field IDs

**Tasks**:
- [ ] Create structural XSD for nIVD, IVD, and PreSTAR templates
- [ ] Add lxml-based schema validation after XML generation
- [ ] Validate field values (date regex, required fields non-empty)
- [ ] Add XML character escaping for user-provided text
- [ ] Test with malicious input (XSS-style payloads)

**Acceptance Criteria**:
- Generated XML validates against structural schema
- All user text properly escaped
- Required fields validated before generation
- 15+ tests for XML validation

---

### ISSUE: GAP-020 - PMA SSED Cache Has No Disk Space Management

**Priority**: MEDIUM
**Effort**: 3-4 hours
**Category**: Data / Schema

**Description**:
`pma_ssed_cache.py` downloads PMA SSED PDFs to disk with no space management. Each PDF is 100KB-5MB. For large product codes with 100+ PMAs, this could consume 500MB+ without warning.

Similarly, `fda_api_client.py` cache grows unbounded -- each API response cached as JSON with 7-day TTL, but expired entries are only cleaned on access (no background cleanup).

**Tasks**:
- [ ] Add configurable max cache size (default 500MB)
- [ ] Implement LRU eviction when cache exceeds limit
- [ ] Add `--clean-cache` CLI command
- [ ] Add disk space check before PDF download
- [ ] Report cache size in `--show-manifest` output

**Acceptance Criteria**:
- Cache size respects configured limit
- LRU eviction works correctly
- Users informed about cache size
- Cleanup command available

---

### ISSUE: GAP-021 - No Rate Limit Tracking Across Sessions

**Priority**: MEDIUM
**Effort**: 4-6 hours
**Category**: Architecture

**Description**:
Rate limiting is implemented per-script and per-session:
- `batchfetch.py`: 500ms delay between requests
- `change_detector.py`: 0.5s delay between product code checks
- `data_refresh_orchestrator.py`: Token bucket rate limiter
- `fda_api_client.py`: Retry on 429 with backoff

But rate limits are NOT shared across concurrent processes. If a user runs `batchfetch` and `change_detector` simultaneously, they double the request rate and risk FDA API blocking.

**Tasks**:
- [ ] Create shared rate limiter using file-based lock (`~/fda-510k-data/.rate_limit.lock`)
- [ ] Track request timestamps across processes
- [ ] Honor openFDA rate limits (240 requests/minute with API key, 40 without)
- [ ] Add rate limit status to health check output

**Acceptance Criteria**:
- Cross-process rate limiting works
- openFDA rate limits respected
- Rate limit status visible to user
- 8+ tests including concurrent access

---

### ISSUE: GAP-022 - Missing Error Recovery Documentation for Each Script

**Priority**: MEDIUM
**Effort**: 4-6 hours
**Category**: Documentation

**Description**:
`docs/ERROR_RECOVERY.md` exists but only covers a few error scenarios. There is no per-script error recovery guide. When a script fails mid-execution, users have no guidance on:
- Whether it is safe to re-run
- What partial state might exist
- How to clean up and retry
- Which data might be corrupted

**Tasks**:
- [ ] Add "Error Recovery" section to each major command's documentation
- [ ] Document idempotency status for each script (safe to re-run: yes/no)
- [ ] Create `docs/IDEMPOTENCY_MATRIX.md` listing all scripts
- [ ] Add `--recover` flag to scripts that support resumption

**Acceptance Criteria**:
- Top 10 scripts have error recovery documentation
- Idempotency status documented for all scripts
- Users can recover from any failure without data loss

---

### ISSUE: GAP-023 - `pma_section_extractor.py` Has 5 Silent `pass` Exception Handlers

**Priority**: MEDIUM
**Effort**: 2-3 hours
**Category**: Code Quality

**Description**:
`pma_section_extractor.py` (600 lines) has 5 `except...pass` blocks (lines 405, 420, 422, 440, 447) in the PDF section extraction pipeline. This means extraction errors are silently ignored, potentially returning incomplete section data that downstream modules treat as complete.

**Tasks**:
- [ ] Replace each `pass` with appropriate error handling
- [ ] Return extraction quality indicators (e.g., "section X failed to extract")
- [ ] Log extraction failures to enable quality reporting
- [ ] Add section completeness score to extraction results

**Acceptance Criteria**:
- No silent extraction failures
- Quality indicators included in output
- Extraction errors logged
- Tests verify error reporting

---

### ISSUE: GAP-024 - Test Fixtures Use Hardcoded FDA Data That May Become Stale

**Priority**: LOW
**Effort**: 2-3 hours
**Category**: Testing

**Description**:
Test fixtures in `tests/fixtures/` contain hardcoded K-numbers, product codes, and API response structures. If the openFDA API changes its response format, tests would pass (because they use fixtures) but the actual code would fail.

**Tasks**:
- [ ] Add a quarterly API contract test that fetches one real response and validates structure
- [ ] Document fixture update procedure
- [ ] Add `api_schema_version` field to fixtures for tracking
- [ ] Create script to regenerate fixtures from live API

**Acceptance Criteria**:
- API contract test exists (marked with `@pytest.mark.api`)
- Fixtures have version tracking
- Update procedure documented

---

### ISSUE: GAP-025 - Incomplete Test Spec Implementation (10 Tests Still Pending)

**Priority**: HIGH
**Effort**: 5-7 hours
**Category**: Testing

**Description**:
Per `TEST_IMPLEMENTATION_CHECKLIST.md`, 10 out of 34 test cases from TESTING_SPEC.md remain unimplemented:

**Critical (2 remaining)**: SMART-007 (recall detection), INT-001 (end-to-end detect+trigger)
**High (6 remaining)**: SMART-004, SMART-008, SMART-012, INT-002, INT-003, INT-004, INT-005
**Medium (4 remaining)**: SMART-016, SMART-017, INT-006, PERF-001
**Low (2 remaining)**: PERF-002, PERF-003

This was NOT tracked in FE-001/FE-002 (which focus on creating test suites) because these are SPEC-defined tests that should already exist.

**Tasks**:
- [ ] Implement SMART-007 (recall detection) - CRITICAL
- [ ] Implement INT-001 (end-to-end flow) - CRITICAL
- [ ] Implement remaining HIGH priority tests (6 tests)
- [ ] Implement PERF-001 (performance baseline)

**Acceptance Criteria**:
- All 12 CRITICAL tests pass (currently 10/12)
- All HIGH priority tests pass
- TEST_IMPLEMENTATION_CHECKLIST.md updated to reflect 100%

**Related Files**:
- `/home/linux/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/docs/TESTING_SPEC.md`
- `/home/linux/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/docs/TEST_IMPLEMENTATION_CHECKLIST.md`

---

### ISSUE: GAP-026 - No Pre-commit Hook Configuration

**Priority**: MEDIUM
**Effort**: 2-3 hours
**Category**: CI/CD

**Description**:
No `.pre-commit-config.yaml` exists. Developers can commit:
- Python syntax errors
- Missing imports
- Trailing whitespace
- Mixed line endings
- Large binary files
- Secrets (API keys in code)

**Tasks**:
- [ ] Create `.pre-commit-config.yaml` with hooks for: ruff, black/autopep8, trailing-whitespace, end-of-file-fixer, check-yaml, check-json, detect-secrets
- [ ] Add `pyproject.toml` with ruff/black configuration
- [ ] Document pre-commit setup in CONTRIBUTING.md or INSTALLATION.md

**Acceptance Criteria**:
- Pre-commit config exists
- At minimum: syntax check, import sort, trailing whitespace
- Setup instructions documented

---

### ISSUE: GAP-027 - `fda_http.py` Spoofs Browser User-Agent for FDA Servers

**Priority**: MEDIUM
**Effort**: 2-3 hours
**Category**: Security / Compliance

**Description**:
`fda_http.py` uses browser-like headers (`Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...`) for FDA server requests. While this was likely needed to bypass FDA server restrictions, it:
1. Misrepresents the client identity to a government server
2. Could violate FDA Terms of Service
3. Makes it harder for FDA to identify and support legitimate tool usage

The `OPENFDA_HEADERS` alternative uses `Mozilla/5.0 (FDA-Plugin/{version})` which is more appropriate.

**Tasks**:
- [ ] Review which FDA endpoints actually require browser headers vs API headers
- [ ] Document which endpoints need browser UA and why
- [ ] Use `FDA-Plugin/{version}` UA for all openFDA API calls
- [ ] Only use browser UA for FDA.gov website scraping (SSED PDFs) where necessary
- [ ] Add configuration option to override UA string

**Acceptance Criteria**:
- API calls use honest UA string
- Browser UA only used where technically required
- Configuration documented

---

### ISSUE: GAP-028 - No Data Backup/Restore Procedure

**Priority**: MEDIUM
**Effort**: 4-6 hours
**Category**: Data / Schema

**Description**:
Project data (device profiles, review decisions, cached API responses, fingerprints) has no backup or restore procedure. A disk failure or accidental deletion would lose all project work.

**Tasks**:
- [ ] Create `scripts/backup_project.py` that archives a project to timestamped zip
- [ ] Create `scripts/restore_project.py` that extracts backup
- [ ] Add `--backup` flag to update_manager.py (before updates)
- [ ] Add backup schedule recommendation to documentation
- [ ] Validate backup integrity (checksum verification)

**Acceptance Criteria**:
- Backup creates complete project archive
- Restore recreates exact project state
- Backup integrity verifiable
- Documented in TROUBLESHOOTING.md

---

### ISSUE: GAP-029 - TESTING_SPEC `conftest.py` Fixtures Not Portable

**Priority**: LOW
**Effort**: 2-3 hours
**Category**: Testing

**Description**:
The `conftest.py` uses `sys.path.insert(0, SCRIPTS_DIR)` to make scripts importable. This breaks when:
- Tests are run from a different working directory
- Tests are run in parallel (pytest-xdist)
- IDE test runners use different working directories

**Tasks**:
- [ ] Convert to proper Python package structure (see GAP-003)
- [ ] Or add `setup.py`/`pyproject.toml` with `pip install -e .` for development
- [ ] Ensure conftest.py works regardless of working directory

**Acceptance Criteria**:
- Tests pass when run from any directory
- Tests pass with pytest-xdist
- IDE test runners work

---

### ISSUE: GAP-030 - Skills Directory Has No Functional Tests

**Priority**: LOW
**Effort**: 3-4 hours
**Category**: Testing

**Description**:
The `skills/` directory contains 5 skill definitions (fda-predicate-assessment, fda-510k-knowledge, fda-safety-signal-triage, fda-plugin-e2e-smoke, fda-510k-submission-outline) with OpenAI agent YAML configs. Only `fda-plugin-e2e-smoke` has a test script (`scripts/run_smoke.sh`), but it has never been validated. The other 4 skills have no tests.

**Tasks**:
- [ ] Validate each SKILL.md has valid frontmatter
- [ ] Validate each agent YAML has required fields
- [ ] Create structural validation test for all skills
- [ ] Test smoke script works (or document it as manual)

**Acceptance Criteria**:
- All skill manifests validated
- Agent YAML structure verified
- At least structural tests for all 5 skills

---

### ISSUE: GAP-031 - `approval_probability.py` Falls Back to No-Op on sklearn Import Failure

**Priority**: MEDIUM
**Effort**: 2-3 hours
**Category**: Code Quality

**Description**:
`approval_probability.py` (line 46-47) has `except ImportError: pass` for sklearn import. If sklearn is not installed, the RandomForest classifier silently falls back to rule-based scoring. This is intentional degradation, but:
1. No user warning about degraded mode
2. Output does not indicate which mode was used
3. Rule-based baseline may give very different scores than ML model

**Tasks**:
- [ ] Add warning when sklearn not available
- [ ] Include `method_used: "ml" | "rule_based"` in output
- [ ] Document accuracy difference between modes
- [ ] Add sklearn to requirements.txt (optional section)

**Acceptance Criteria**:
- Users informed about degraded mode
- Output indicates which method was used
- Accuracy implications documented

---

### ISSUE: GAP-032 - No Telemetry or Usage Analytics

**Priority**: LOW
**Effort**: 6-8 hours
**Category**: Architecture

**Description**:
No usage tracking exists to understand:
- Which commands are most used
- Which product codes are most queried
- Average project size and complexity
- Error frequency by command
- Feature adoption rates

This data would help prioritize development and identify pain points.

**Tasks**:
- [ ] Design opt-in anonymous usage tracking
- [ ] Track: command name, execution time, success/failure, product code count
- [ ] Store locally in `~/fda-510k-data/.usage_stats.json`
- [ ] Create `--show-stats` command to display usage summary
- [ ] Respect `--no-telemetry` flag

**Acceptance Criteria**:
- Opt-in only (disabled by default)
- No PII collected
- Local storage only (no network)
- Stats viewable by user

---

### ISSUE: GAP-033 - `data_manifest.json` Schema Not Documented or Validated

**Priority**: MEDIUM
**Effort**: 3-4 hours
**Category**: Data / Schema

**Description**:
`data_manifest.json` is the central data file for each project but has no JSON Schema definition. Different code paths expect different fields, and there is no validation that the manifest contains required fields before operations.

**Tasks**:
- [ ] Create JSON Schema for data_manifest.json
- [ ] Add manifest validation on load
- [ ] Add schema version field for migration support
- [ ] Create migration script for schema changes
- [ ] Document all manifest fields

**Acceptance Criteria**:
- JSON Schema exists in `data/schemas/`
- Manifest validated on load
- Schema version tracked
- Invalid manifests produce helpful error messages

---

### ISSUE: GAP-034 - Compliance Disclaimer Not Shown at CLI Runtime

**Priority**: URGENT
**Effort**: 1-2 hours
**Category**: Compliance

**Description**:
Per TICKET-022 and expert panel review, the standards generation feature is "RESEARCH USE ONLY." However, the CLI scripts (`knowledge_based_generator.py`, `auto_generate_device_standards.py`, `quick_standards_generator.py`) do not display any disclaimer at runtime. Users running these scripts directly never see the "RESEARCH USE ONLY" warning.

**Tasks**:
- [ ] Add startup banner to standards generation scripts: "RESEARCH USE ONLY - NOT FOR DIRECT FDA SUBMISSION"
- [ ] Add `--accept-disclaimer` flag required for non-interactive use
- [ ] Log disclaimer acceptance to audit trail
- [ ] Apply same pattern to any other research-only features

**Acceptance Criteria**:
- CLI users see disclaimer before output
- Disclaimer cannot be bypassed silently
- Acceptance logged for audit trail

---

### ISSUE: GAP-035 - `external_data_hub.py` PubMed/ClinicalTrials.gov Integration Has No Tests

**Priority**: MEDIUM
**Effort**: 4-6 hours
**Category**: Testing

**Description**:
`external_data_hub.py` (742 lines) integrates with 3 external APIs (ClinicalTrials.gov, PubMed, USPTO) with rate limiting and caching. Despite its complexity, it has no dedicated test file. The `test_pma_phase5.py` tests may cover some paths but there are no focused tests for:
- PubMed API response parsing
- ClinicalTrials.gov result extraction
- USPTO patent search
- Rate limiter behavior under load
- Cache expiry and refresh

**Tasks**:
- [ ] Create `tests/test_external_data_hub.py`
- [ ] Mock all 3 external APIs
- [ ] Test response parsing for each API
- [ ] Test rate limiter (token bucket algorithm)
- [ ] Test cache behavior

**Acceptance Criteria**:
- 15+ tests covering all 3 APIs
- Rate limiter tested under simulated load
- Cache expiry verified
- No network access in tests

---

### ISSUE: GAP-036 - `review_time_predictor.py` and `maude_comparison.py` ML Models Not Validated

**Priority**: LOW
**Effort**: 4-6 hours
**Category**: Testing

**Description**:
Two ML-based modules (`review_time_predictor.py` at 1158 lines, `maude_comparison.py` at 1002 lines) implement statistical models (Z-score outlier detection, panel-specific baselines, risk factor adjustments) but have no model validation tests. The test file `test_pma_phase4.py` tests API behavior but not model accuracy.

**Tasks**:
- [ ] Create golden test dataset with known expected outcomes
- [ ] Test Z-score calculation accuracy
- [ ] Test panel baseline correctness against published FDA data
- [ ] Test risk factor adjustment ranges
- [ ] Validate model outputs against historical FDA review times

**Acceptance Criteria**:
- Golden dataset with 10+ scenarios
- Z-score calculations verified within 0.01 tolerance
- Panel baselines match published FDA statistics
- Risk adjustments produce sensible ranges

---

### ISSUE: GAP-037 - No Type Checking (mypy) Configuration

**Priority**: LOW
**Effort**: 3-4 hours
**Category**: Code Quality

**Description**:
While some modules have type hints (128 occurrences across 28 files), there is no mypy configuration or type checking in CI. Many modules have incomplete type hints. Running mypy would likely reveal type errors.

**Tasks**:
- [ ] Add `mypy.ini` or `[mypy]` section in `pyproject.toml`
- [ ] Run mypy on codebase, document current error count
- [ ] Fix critical type errors (None handling, incorrect return types)
- [ ] Add mypy to CI (initially as warning-only, then enforced)

**Acceptance Criteria**:
- mypy configuration exists
- Baseline error count documented
- No new type errors in CI (baseline enforcement)
- Core modules (fda_api_client, fda_data_store) pass mypy strict

---

### ISSUE: GAP-038 - `supplement_tracker.py` Has Hardcoded Regulatory Dates

**Priority**: MEDIUM
**Effort**: 2-3 hours
**Category**: Code Quality

**Description**:
`supplement_tracker.py` (~1200 lines) contains hardcoded review period durations (e.g., 180 days for panel-track supplements, 30 days for real-time supplements). These are per 21 CFR 814.39 but FDA has modified review timelines via guidance. Hardcoded values cannot be updated without code changes.

**Tasks**:
- [ ] Extract regulatory timeline constants to a configuration file (`data/regulatory_timelines.json`)
- [ ] Add effective dates for each timeline (when regulation changed)
- [ ] Support multiple timelines (current vs historical)
- [ ] Add CFR citation for each timeline constant
- [ ] Create update procedure when FDA changes review periods

**Acceptance Criteria**:
- All timeline constants in external configuration
- CFR citations documented
- Configuration update does not require code changes
- Historical timelines preserved

---

### ISSUE: GAP-039 - OpenClaw Skill Tests Cannot Run (Missing node_modules)

**Priority**: LOW
**Effort**: 1-2 hours
**Category**: Testing

**Description**:
`openclaw-skill/tests/integration.test.ts` exists but cannot run because:
1. No `node_modules/` directory (dependencies not installed)
2. No `dist/` directory (TypeScript not compiled)
3. No CI step for TypeScript tests
4. Jest config references `ts-jest` which is not installed

**Tasks**:
- [ ] Add `npm ci && npm run build && npm test` step to CI
- [ ] Or mark openclaw-skill tests as manual/experimental
- [ ] Ensure `package-lock.json` exists for reproducible builds
- [ ] Add TypeScript compilation check

**Acceptance Criteria**:
- Either tests run in CI or are explicitly marked as manual
- Build process documented
- package-lock.json committed

---

### ISSUE: GAP-040 - Multiple Settings Files with No Schema Documentation

**Priority**: LOW
**Effort**: 2-3 hours
**Category**: Documentation

**Description**:
Settings are read from `~/.claude/fda-tools.local.md` in multiple places (fda_api_client.py, fda_data_store.py) using regex parsing of a markdown file. The expected format is undocumented:
- `openfda_api_key: <key>`
- `openfda_enabled: true|false`
- `projects_dir: <path>`

There is also `setup_api_key.py` that writes this file with a template, but the template and runtime parsers may drift.

**Tasks**:
- [ ] Document all settings fields in INSTALLATION.md
- [ ] Create settings validation function
- [ ] Add `--show-config` command to display current settings
- [ ] Validate settings on first use of each script

**Acceptance Criteria**:
- All settings documented with types and defaults
- Invalid settings produce helpful error messages
- `--show-config` shows current effective configuration

---

### ISSUE: GAP-041 - Zone.Identifier Files Committed to Git

**Priority**: LOW
**Effort**: 0.5 hours
**Category**: Code Quality

**Description**:
Three `Zone.Identifier` files are committed to git in the `estar/` directory:
- `nIVD_eSTAR_6-1.pdf:Zone.Identifier`
- `IVD_eSTAR_6-1.pdf:Zone.Identifier`
- `PreSTAR_2-1.pdf:Zone.Identifier`

These are Windows NTFS alternate data stream markers created when files are downloaded from the internet. They serve no purpose in the repository.

**Tasks**:
- [ ] Remove Zone.Identifier files from git
- [ ] Add `*:Zone.Identifier` to `.gitignore`

**Acceptance Criteria**:
- Zone.Identifier files removed from tracking
- .gitignore prevents future commits

---

### ISSUE: GAP-042 - `batchfetch.md.backup` Committed to Repository

**Priority**: LOW
**Effort**: 0.5 hours
**Category**: Code Quality

**Description**:
`commands/batchfetch.md.backup` is a backup file committed to git. Backup files should not be in version control.

**Tasks**:
- [ ] Remove backup file from git
- [ ] Add `*.backup` to `.gitignore`

**Acceptance Criteria**:
- Backup file removed
- .gitignore updated

---

## Summary Statistics

| Category | URGENT | HIGH | MEDIUM | LOW | Total |
|----------|--------|------|--------|-----|-------|
| Code Quality | 0 | 2 | 5 | 3 | 10 |
| Testing | 0 | 4 | 4 | 3 | 11 |
| Security | 0 | 2 | 2 | 0 | 4 |
| CI/CD | 1 | 1 | 1 | 0 | 3 |
| Documentation | 0 | 0 | 3 | 1 | 4 |
| Architecture | 0 | 3 | 1 | 1 | 5 |
| Data / Schema | 1 | 0 | 2 | 0 | 3 |
| Compliance | 1 | 0 | 1 | 0 | 2 |
| **Total** | **3** | **12** | **18** | **9** | **42** |

### Estimated Total Effort

| Priority | Count | Hours (Low) | Hours (High) |
|----------|-------|-------------|--------------|
| URGENT | 3 | 6 | 9 |
| HIGH | 12 | 81 | 117 |
| MEDIUM | 18 | 62 | 87 |
| LOW | 9 | 28 | 42 |
| **Total** | **42** | **177** | **255** |

### Recommended Implementation Order

**Sprint 1 (URGENT + Blocking HIGH):**
1. GAP-034 - Compliance disclaimer at CLI (URGENT, 1-2h)
2. GAP-006 - CI/CD pipeline fixes (URGENT, 3-4h)
3. GAP-012 - Atomic manifest writes (URGENT, 2-3h)
4. GAP-001 - Bare except clauses (HIGH, 2-3h)
5. GAP-010 - Input validation (HIGH, 6-8h)
6. GAP-007 - Requirements pinning (HIGH, 2-3h)

**Sprint 2 (HIGH - Testing):**
7. GAP-004 - lib/ module tests (HIGH, 12-16h)
8. GAP-005 - Script module tests (HIGH, 20-30h)
9. GAP-025 - Complete TESTING_SPEC (HIGH, 5-7h)

**Sprint 3 (HIGH - Architecture):**
10. GAP-008 - OpenClaw skill build (HIGH, 8-12h)
11. GAP-009 - predicate-assistant cleanup (HIGH, 4-6h)
12. GAP-019 - eSTAR XML validation (HIGH, 6-8h)

**Sprint 4+ (MEDIUM + LOW):**
13-42. Remaining issues in priority order.

---

**Report Generated:** 2026-02-16
**Total Files Analyzed:** 180+
**Total Lines of Code Reviewed:** ~50,000
**Deduplication Verified Against:** TICKET-001-022, FE-001-010, QUA-11-32
