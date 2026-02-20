# FDA Tools - Linear Issues Template for QA Findings

Use this template to create Linear issues from the QA Testing Findings report.

---

## Issue FDA-QA-001: E2E Test Infrastructure Missing

**Title:** E2E Test Infrastructure Missing - Traditional 510(k) and OpenClaw Tests Cannot Execute

**Priority:** P0 - Critical  
**Labels:** testing, e2e, infrastructure, blocked  
**Estimate:** 21 points (5-8 hours)

**Description:**
Two comprehensive E2E test files (348 lines) cannot execute due to missing test utility modules. This blocks all end-to-end validation of the Traditional 510(k) workflow (most critical submission type) and OpenClaw bridge integration.

**Impact:**
- 0% E2E coverage for complete user journeys
- Cannot verify cross-module integration
- Cannot catch regressions in full workflows
- 71 test cases blocked

**Acceptance Criteria:**
- [ ] Create `tests/utils/` directory structure
- [ ] Implement `e2e_helpers.py` with 6 required helper functions
- [ ] Implement `regulatory_validators.py` with RegulatoryValidator class
- [ ] Create fixture: `fixtures/seed_data_traditional_510k.json`
- [ ] All 41 Traditional 510(k) tests execute successfully
- [ ] All 30 OpenClaw integration tests execute successfully
- [ ] Add E2E tests to CI/CD pipeline
- [ ] Document E2E test execution in README

**Files:**
- tests/test_e2e_traditional_510k.py
- tests/test_e2e_openclaw_integration.py

---

## Issue FDA-QA-002: Critical Test Failures in Production Modules

**Title:** Fix 47 Failing Tests in fda_enrichment.py and error_handling.py

**Priority:** P0 - Critical  
**Labels:** testing, bug, production-code  
**Estimate:** 13 points (3-5 hours)

**Description:**
Production modules have 47 failing tests indicating potential bugs. 21 failures in fda_enrichment.py (KeyError: 'KNUMBER') and 13 failures in error_handling.py (retry/circuit breaker logic).

**Root Causes:**
1. fda_enrichment.py: `enrich_single_device()` expects uppercase 'KNUMBER' but tests pass lowercase
2. error_handling.py: Retry decorator not propagating exceptions correctly
3. Circuit breaker threshold logic incorrect

**Acceptance Criteria:**
- [ ] Fix KeyError in fda_enrichment.py:703 with input validation
- [ ] Standardize API contract for device row keys (uppercase)
- [ ] Update test fixtures to match production contract
- [ ] Fix retry decorator exception propagation
- [ ] Fix circuit breaker threshold logic
- [ ] Fix timing-sensitive tests with proper mocking
- [ ] All 43 tests pass in both modules
- [ ] Add API contract documentation

**Files:**
- lib/fda_enrichment.py
- scripts/error_handling.py
- tests/test_fda_enrichment.py
- tests/test_error_handling.py

---

## Issue FDA-QA-003: Critical Utilities Lack Test Coverage

**Title:** Add Test Coverage for fda_http, subprocess_utils, and cross_process_rate_limiter

**Priority:** P1 - High  
**Labels:** testing, security, infrastructure  
**Estimate:** 34 points (8-13 hours)

**Description:**
Three critical security-sensitive infrastructure modules have ZERO test coverage:
- fda_http.py (175 lines): User-agent management, FDA API/website authentication
- subprocess_utils.py (280 lines): Command allowlisting, subprocess security
- cross_process_rate_limiter.py (350 lines): File-based rate limiting

**Security Risks:**
- User-agent handling could violate FDA ToS
- Command injection vulnerabilities if allowlist bypassed
- Race conditions in file locking could cause API rate limit violations

**Acceptance Criteria:**
- [ ] Create tests/test_fda_http.py with 15 tests
- [ ] Create tests/test_subprocess_utils.py with 18 tests
- [ ] Create tests/test_cross_process_rate_limiter.py with 20 tests
- [ ] Test coverage >80% for all three modules
- [ ] All security scenarios validated
- [ ] Concurrent operation tests passing

**Test Classes Required:**
- TestUserAgentSelection (6 tests)
- TestFDAToSCompliance (3 tests)
- TestCommandAllowlist (4 tests)
- TestSecurityHardening (4 tests)
- TestFileLocking (3 tests)
- TestRateLimitEnforcement (4 tests)
- TestConcurrency (3 tests)

---

## Issue FDA-QA-004: 54 Production Scripts Untested (Tier 1 - Critical Infrastructure)

**Title:** Add Test Coverage for Tier 1 Critical Infrastructure Scripts (13 modules)

**Priority:** P1 - High  
**Labels:** testing, infrastructure, phased-approach  
**Estimate:** 34 points (13-21 hours for Tier 1 only)

**Description:**
65% of scripts directory (54 modules) lacks test coverage. This issue focuses on Tier 1 critical infrastructure (13 modules) including:
- approval_probability.py
- backup_project.py / restore_project.py
- data_refresh_orchestrator.py
- fda_data_store.py
- execution_coordinator.py
- linear_integrator.py
- pma_data_store.py
- update_manager.py
- version.py
- validate_skills.py
- verify_citations.py
- verify_enhancement.py
- web_predicate_validator.py

**Acceptance Criteria:**
- [ ] Create test file for each Tier 1 module
- [ ] Minimum 70% code coverage for each module
- [ ] All critical paths tested
- [ ] Error handling validated
- [ ] Integration points tested
- [ ] Follow-up issues created for Tiers 2-4

**Note:** This is Phase 1 of FDA-QA-004. Additional issues will be created for Tiers 2-4.

---

## Issue FDA-QA-005: Integration Test Coverage Gaps

**Title:** Add Integration Tests for Multi-Module Workflows

**Priority:** P1 - High  
**Labels:** testing, integration, workflows  
**Estimate:** 55 points (21-34 hours)

**Description:**
Integration test coverage for cross-module workflows is incomplete. While unit tests are strong (5,361 tests), workflows lack runtime integration validation.

**Missing Integration Scenarios:**
1. Complete Submission Workflow (import → export)
2. Multi-Agent Orchestration
3. Data Refresh Pipeline
4. PMA Intelligence Pipeline
5. External System Integration
6. Cache Integrity Across Modules

**Acceptance Criteria:**
- [ ] Create tests/test_integration_submission_workflow.py (25 tests)
- [ ] Create tests/test_integration_multi_agent.py (18 tests)
- [ ] Create tests/test_integration_data_refresh.py (20 tests)
- [ ] Create tests/test_integration_pma_pipeline.py (22 tests)
- [ ] Create tests/test_integration_cache_coherence.py (15 tests)
- [ ] All 100 integration tests passing
- [ ] Data handoff between stages validated
- [ ] Error propagation tested across modules

---

## Issue FDA-QA-006: Mock vs Real API Test Balance

**Title:** Implement Quarterly API Contract Validation and Real API Tests

**Priority:** P2 - Medium  
**Labels:** testing, api, contract-testing  
**Estimate:** 13 points (3-5 hours)

**Description:**
Test suite is mock-heavy (316 mock instances) with only 9 real API tests. Need to implement quarterly API contract validation and hybrid test strategy.

**Current Risks:**
- FDA API changes not detected until production
- Mock responses drift from real API schema
- Rate limiting behavior not validated

**Acceptance Criteria:**
- [ ] Create tests/test_api_contract_validation.py (12 tests)
- [ ] Create tests/test_fixture_staleness.py (8 tests)
- [ ] Implement @pytest.mark.api_contract marker usage
- [ ] Document hybrid test strategy (mocks vs real API)
- [ ] Schedule quarterly API contract test runs
- [ ] Add fixture freshness metadata

---

## Issue FDA-QA-007: Edge Case and Error Scenario Coverage

**Title:** Add Comprehensive Edge Case and Error Scenario Tests

**Priority:** P2 - Medium  
**Labels:** testing, edge-cases, error-handling  
**Estimate:** 55 points (21-34 hours)

**Description:**
Edge case and error scenario coverage is inconsistent. Need systematic testing of boundary conditions, malformed input, and degraded mode operation.

**Edge Case Categories:**
1. Input Validation (empty, malformed, unicode, long text)
2. API Errors (429, 503, 504, partial responses)
3. File System (permissions, disk full, concurrent access)
4. Data Integrity (corrupted JSON, schema mismatches)
5. Concurrency (race conditions, deadlocks)

**Acceptance Criteria:**
- [ ] Create tests/test_edge_cases_input_validation.py (30 tests)
- [ ] Create tests/test_edge_cases_api_errors.py (25 tests)
- [ ] Create tests/test_edge_cases_file_system.py (20 tests)
- [ ] Create tests/test_edge_cases_data_integrity.py (22 tests)
- [ ] Document edge case testing standards
- [ ] All 97 edge case tests passing

---

## Issue FDA-QA-008: Regression Test Quality

**Title:** Implement Regression Test Tracking Infrastructure

**Priority:** P2 - Medium  
**Labels:** testing, regression, infrastructure  
**Estimate:** 8 points (2-3 hours)

**Description:**
Test suite lacks systematic regression test tracking. Need marker infrastructure and policy for linking tests to fixed bugs.

**Acceptance Criteria:**
- [ ] Add @pytest.mark.regression marker to pytest.ini
- [ ] Add @pytest.mark.fixes(issue_id) custom marker
- [ ] Document regression test policy in CONTRIBUTING.md
- [ ] Create regression coverage report script
- [ ] Add regression test requirement to bug fix checklist
- [ ] Mark existing bug-fix tests with regression marker

---

## Issue FDA-QA-009: Test Data Management

**Title:** Build Comprehensive Fixture Library for All Device Types

**Priority:** P2 - Medium  
**Labels:** testing, fixtures, test-data  
**Estimate:** 21 points (5-8 hours)

**Description:**
Test suite relies on only 4 JSON fixture files. Need comprehensive fixture library covering PMA, De Novo, HDE/IDE, combination products, SaMD, and error scenarios.

**Acceptance Criteria:**
- [ ] Create fixtures/pma/ directory with 3 fixture files
- [ ] Create fixtures/de_novo/ directory with 2 fixture files
- [ ] Create fixtures/pathways/ directory with 2 fixture files
- [ ] Create fixtures/device_types/ directory with 3 fixture files
- [ ] Create fixtures/error_scenarios/ directory with 3 fixture files
- [ ] Add fixture metadata (generation_date, schema_version)
- [ ] Document fixture update process
- [ ] Create fixture validation tests

---

## Issue FDA-QA-010: Performance and Load Testing

**Title:** Implement Performance Benchmarks and Load Testing Suite

**Priority:** P2 - Medium  
**Labels:** testing, performance, load-testing  
**Estimate:** 34 points (8-13 hours)

**Description:**
Zero performance or load tests exist. Need validation of system behavior under stress, with large datasets, and concurrent operations.

**Test Categories:**
1. Large Dataset Handling (1,000+ devices, 10,000+ cache entries)
2. Concurrent Operations (multiple processes, parallel execution)
3. Memory Usage (profiling, leak detection)
4. Response Time Benchmarks (API, cache, section similarity)

**Acceptance Criteria:**
- [ ] Create tests/test_performance_benchmarks.py (15 tests)
- [ ] Create tests/test_load_stress.py (12 tests)
- [ ] Add @pytest.mark.performance marker
- [ ] Add @pytest.mark.load marker
- [ ] Document performance baselines
- [ ] Add performance tests to CI/CD (separate job)
- [ ] All 27 performance/load tests passing

---

## Issue Tracking Summary

**Total Issues:** 10  
**Total Points:** 343 points (89-144 hours)

**Priority Breakdown:**
- P0 (Critical): 2 issues, 34 points
- P1 (High): 3 issues, 178 points  
- P2 (Medium): 5 issues, 131 points

**Recommended Sprint Allocation:**

Sprint 1 (P0):
- FDA-QA-001 (21 pts)
- FDA-QA-002 (13 pts)

Sprint 2 (P1 - Part 1):
- FDA-QA-003 (34 pts)
- FDA-QA-004 Tier 1 (34 pts)

Sprint 3 (P1 - Part 2):
- FDA-QA-005 (55 pts)

Sprint 4 (P2 - Selected):
- FDA-QA-006 (13 pts)
- FDA-QA-008 (8 pts)
- FDA-QA-009 (21 pts)

Backlog (P2 - Future):
- FDA-QA-007 (55 pts)
- FDA-QA-010 (34 pts)
- FDA-QA-004 Tiers 2-4 (55 pts remaining)

