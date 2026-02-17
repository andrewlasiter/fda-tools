# FDA Tools Plugin - Master Issue Tracking Index

**Last Updated:** 2026-02-17
**Document Version:** 1.0
**Repository:** `/home/linux/.claude/plugins/marketplaces/fda-tools`
**Current Project Version:** v5.36.0

---

## Executive Summary

This document consolidates all issue tracking information for the FDA Tools Plugin project into a single source of truth. It serves as the central reference for:

- Current issue inventory across all tracking sources
- Priority-based status summaries
- Effort estimation and progress tracking
- Cross-referenced documentation and traceability
- Automated update procedures

**Total Issues Tracked:** 71+ active issues across all sources
- URGENT Priority: 3 issues
- HIGH Priority: 12 issues
- MEDIUM Priority: 18 issues
- LOW Priority: 9 issues

**Estimated Total Effort:** 195-270 hours remaining development work

---

## 1. Issue Inventory Summary

### 1.1 Source Distribution

| Source | Count | Status | Reference |
|--------|-------|--------|-----------|
| **TODO.md** | 13 | 6 COMPLETE, 7 NOT STARTED | [Link](#21-todo-tracked-issues) |
| **GAP-ANALYSIS-REPORT.md** | 42 | New (not in tickets) | [Link](#22-gap-analysis-issues) |
| **TICKET Files** | 16 | Mixed states | [Link](#23-ticket-tracked-issues) |
| **FUTURE ENHANCEMENTS (FE-001-010)** | 10 | Not started | [Link](#24-future-enhancements) |
| **Test Spec (TESTING_SPEC.md)** | Embedded in TICKET-016 | 10 pending | [Link](#25-testing-specification) |
| **Quality (QUA-11-32)** | Referenced in TICKET-022 | Compliance only | [Link](#26-quality-issues) |
| **TOTAL** | **71+** | Mixed | - |

### 1.2 Priority Distribution

```
URGENT (3)     ████                 [Must fix before feature release]
HIGH (12)      ████████████        [Complete within 1 month]
MEDIUM (18)    ██████████████████  [Complete within 3 months]
LOW (9)        █████████           [Nice-to-have enhancements]
```

### 1.3 Category Breakdown

| Category | URGENT | HIGH | MEDIUM | LOW | Total | Effort (hrs) |
|----------|--------|------|--------|-----|-------|--------------|
| Code Quality | 0 | 2 | 5 | 3 | 10 | 15-25 |
| Testing | 0 | 4 | 4 | 3 | 11 | 50-85 |
| Security | 0 | 2 | 2 | 0 | 4 | 12-16 |
| CI/CD | 1 | 1 | 1 | 0 | 3 | 6-10 |
| Documentation | 0 | 0 | 3 | 1 | 4 | 10-15 |
| Architecture | 0 | 3 | 1 | 1 | 5 | 15-25 |
| Data / Schema | 1 | 0 | 2 | 0 | 3 | 9-13 |
| Compliance | 1 | 0 | 1 | 0 | 2 | 2-4 |
| **TOTAL** | **3** | **12** | **18** | **9** | **42+** | **195-270** |

---

## 2. Issue Tracking by Source

### 2.1 TODO-Tracked Issues

**Reference:** `/home/linux/.claude/plugins/marketplaces/fda-tools/TODO.md`
**Last Updated:** 2026-02-16

#### Completed (6)

| ID | Title | Status | Version |
|----|----|--------|---------|
| TICKET-001 | Pre-Sub eSTAR/PreSTAR XML Generation | COMPLETE | v5.25.0-v5.27.0 |
| TICKET-002 | PMA SSED URL Research & Validation | COMPLETE | 2026-02-16 |
| TICKET-003 | PMA Intelligence Module (Phases 0-5) | COMPLETE | v5.29.0-v5.35.0 |
| TICKET-004 | Pre-Sub Multi-Pathway Package Generator | COMPLETE | v5.28.0 |
| TICKET-016 | Auto-Update Data Manager & Section Comparison | COMPLETE | v5.26.0, v5.36.0 |
| SMART-AUTO-UPDATE | Smart change detection + Section Analytics | COMPLETE | v5.36.0 |

#### Active (7)

| ID | Title | Priority | Effort | Status |
|----|-------|----------|--------|--------|
| TICKET-005 | IDE Pathway Support | MEDIUM | 100-140h | NOT STARTED |
| TICKET-006 | PMA Annual Report Generator | MEDIUM | 40-60h | UNBLOCKED (TICKET-003 COMPLETE) |
| TICKET-007 | PMA Supplement Support | MEDIUM | 80-120h | UNBLOCKED (TICKET-003 COMPLETE) |
| TICKET-008 | Post-Approval Study Monitoring | MEDIUM | 60-80h | UNBLOCKED (TICKET-003 COMPLETE) |
| TICKET-009 | De Novo Classification Request | LOW | 80-100h | NOT STARTED |
| TICKET-010 | Humanitarian Device Exemption (HDE) | LOW | 60-80h | NOT STARTED |
| TICKET-011 | Breakthrough Device Designation | LOW | 40-50h | NOT STARTED |

#### Low Priority (Optional)

| ID | Title | Priority | Effort | Status |
|----|-------|----------|--------|--------|
| TICKET-012 | 510(k) Third Party Review Integration | LOW | 30-40h | NOT STARTED |
| TICKET-013 | Real World Evidence (RWE) Integration | LOW | 60-80h | NOT STARTED |
| FE-001 | Mock-Based Tests for change_detector.py | HIGH | 4-6h | NOT STARTED |
| FE-002 | Mock-Based Tests for section_analytics.py | HIGH | 4-6h | NOT STARTED |
| FE-003 through FE-010 | Various enhancements | MEDIUM-LOW | 30-45h | NOT STARTED |

---

### 2.2 Gap Analysis Issues

**Reference:** `/home/linux/.claude/plugins/marketplaces/fda-tools/docs/planning/GAP-ANALYSIS-REPORT.md`
**Date:** 2026-02-16
**Total New Issues:** 42

#### Urgent Issues (3)

| ID | Title | Category | Effort | Impact |
|----|-------|----------|--------|--------|
| GAP-006 | CI/CD Pipeline Missing Python 3.12 | CI/CD | 3-4h | Can't test on prod Python |
| GAP-012 | `save_manifest()` Not Atomic | Data Integrity | 2-3h | **CRITICAL** - Data loss risk |
| GAP-034 | Compliance Disclaimer Not at CLI | Compliance | 1-2h | Regulatory exposure |

#### High Priority Issues (12)

| ID | Title | Category | Effort |
|----|-------|----------|--------|
| GAP-001 | Bare `except:` Clauses | Code Quality | 2-3h |
| GAP-002 | Silent `except...pass` Patterns (50+) | Code Quality | 8-12h |
| GAP-004 | No Tests for 6 `lib/` Modules | Testing | 12-16h |
| GAP-005 | No Tests for 20+ Script Modules | Testing | 20-30h |
| GAP-007 | No `requirements.txt` Version Pinning | CI/CD | 2-3h |
| GAP-008 | OpenClaw Skill Build Missing | Architecture | 8-12h |
| GAP-009 | fda-predicate-assistant Plugin Untracked | Architecture | 4-6h |
| GAP-010 | Missing Input Validation on CLI | Security | 6-8h |
| GAP-019 | `estar_xml.py` Lacks XML Schema Validation | Compliance | 6-8h |
| GAP-025 | Incomplete Test Spec Implementation (10 tests) | Testing | 5-7h |

#### Medium Priority Issues (18)

| ID | Title | Category | Effort |
|----|-------|----------|--------|
| GAP-003 | No `__init__.py` in scripts/lib | Architecture | 1-2h |
| GAP-011 | Cache Files No Integrity Verification | Security | 4-6h |
| GAP-013 | `batchfetch.py` Optional Dependencies | Documentation | 3-4h |
| GAP-014 | No Logging Framework | Code Quality | 6-8h |
| GAP-015 | Duplicate Import-Exception Patterns | Code Quality | 2-3h |
| GAP-016 | Missing Integration Tests (data_store) | Testing | 4-6h |
| GAP-018 | No Version Consistency Check | CI/CD | 2-3h |
| GAP-020 | PMA SSED Cache No Space Management | Data Schema | 3-4h |
| GAP-021 | No Rate Limit Tracking Across Sessions | Architecture | 4-6h |
| GAP-022 | Missing Error Recovery Documentation | Documentation | 4-6h |
| GAP-023 | Silent Exception Handlers in Extractor | Code Quality | 2-3h |
| GAP-026 | No Pre-commit Hook Config | CI/CD | 2-3h |
| GAP-027 | Browser User-Agent Spoofing | Security/Compliance | 2-3h |
| GAP-028 | No Data Backup/Restore Procedure | Data Schema | 4-6h |
| GAP-031 | ML Fallback Mode Not User-Visible | Code Quality | 2-3h |
| GAP-033 | `data_manifest.json` Schema Not Documented | Data Schema | 3-4h |
| GAP-038 | Hardcoded Regulatory Dates | Code Quality | 2-3h |
| GAP-040 | Settings Files Not Documented | Documentation | 2-3h |

#### Low Priority Issues (9)

| ID | Title | Category | Effort |
|----|-------|----------|--------|
| GAP-017 | Inline HTML Template in Python | Code Quality | 3-4h |
| GAP-024 | Test Fixtures May Become Stale | Testing | 2-3h |
| GAP-029 | conftest.py Fixtures Not Portable | Testing | 2-3h |
| GAP-030 | Skills Directory No Functional Tests | Testing | 3-4h |
| GAP-032 | No Telemetry/Usage Analytics | Architecture | 6-8h |
| GAP-035 | `external_data_hub.py` Has No Tests | Testing | 4-6h |
| GAP-036 | ML Models Not Validated | Testing | 4-6h |
| GAP-037 | No Type Checking (mypy) Config | Code Quality | 3-4h |
| GAP-039 | OpenClaw Tests Cannot Run | Testing | 1-2h |
| GAP-041 | Zone.Identifier Files Committed | Code Quality | 0.5h |
| GAP-042 | batchfetch.md.backup Committed | Code Quality | 0.5h |

---

### 2.3 TICKET-Tracked Issues

**Directory:** `/home/linux/.claude/plugins/marketplaces/fda-tools/docs/`

#### Closed Tickets (Completed Features)

| Ticket | Title | Version | Test Results |
|--------|-------|---------|--------------|
| TICKET-001 | Pre-Sub eSTAR/PreSTAR XML Generation | v5.25.0-v5.27.0 | 15/15 passing |
| TICKET-002 | PMA SSED URL Research & Validation | 2026-02-16 | Conditional GO |
| TICKET-003 Phase 0 | PMA Data Store | v5.29.0 | 95/95 passing |
| TICKET-003 Phase 1 | PMA Comparison & Intelligence | v5.30.0 | 108/108 passing |
| TICKET-003 Phase 1.5 | 510(k)/PMA Integration | v5.31.0 | 57/57 passing |
| TICKET-003 Phase 2 | Clinical Requirements & Timeline | v5.32.0 | 64/64 passing |
| TICKET-003 Phase 3 | Post-Approval Monitoring | v5.33.0 | 54/54 passing |
| TICKET-003 Phase 4 | ML Analytics & Dashboards | v5.34.0 | 82/82 passing |
| TICKET-003 Phase 5 | Real-time Data Pipelines | v5.35.0 | 86/86 passing |
| TICKET-004 | Pre-Sub Multi-Pathway | v5.28.0 | 20/20 passing |
| TICKET-016 Feature 1 | Auto-Update Data Manager | v5.26.0, v5.36.0 | 14/14 passing |
| TICKET-016 Feature 2 | Section Comparison Tool | v5.26.0, v5.36.0 | 4/4 passing |

#### Active Verification Tickets

| Ticket | Focus | Status |
|--------|-------|--------|
| TICKET-017 Phase 1 | PMA Intelligence Verification | COMPLETE |
| TICKET-017 Phase 3 | Advanced Analytics Verification | COMPLETE |
| TICKET-019 | IDE Pathway Verification | Pre-start |
| TICKET-020 | De Novo Verification Spec | Pre-start |
| TICKET-021 | HDE Support Verification | Pre-start |
| TICKET-022 | Compliance & Testing Summary | COMPLETE (Conditional Approval) |

---

### 2.4 Future Enhancements (FE-001 through FE-010)

**Reference:** TODO.md lines 1100-1222
**Category:** Post-v5.36.0 Enhancements

#### High Priority (3)

| ID | Title | Effort | Rationale |
|----|-------|--------|-----------|
| FE-001 | Mock-Based Test Suite for change_detector.py | 4-6h | CI/CD blocker - no pytest coverage |
| FE-002 | Mock-Based Test Suite for section_analytics.py | 4-6h | Regulatory intelligence accuracy |
| FE-003 | Cross-Module `_run_subprocess()` Reuse | 2-3h | Code maintainability |

#### Medium Priority (4)

| ID | Title | Effort | Rationale |
|----|-------|--------|-----------|
| FE-004 | Fingerprint Diff Reporting | 4-6h | Change detection enhancement |
| FE-005 | Similarity Score Caching | 3-4h | Performance optimization |
| FE-006 | Progress Callbacks for Long Computations | 2-3h | User experience improvement |
| FE-007 | Enhanced Trend Visualization | 3-5h | Usability improvement |

#### Low Priority (3)

| ID | Title | Effort | Rationale |
|----|-------|--------|-----------|
| FE-008 | SQLite Fingerprint Storage Migration | 4-6h | Scalability (100+ product codes) |
| FE-009 | Similarity Method Auto-Selection | 2-3h | UX simplification |
| FE-010 | Batch Smart Detection Across Projects | 3-4h | Multi-project support |

---

### 2.5 Testing Specification

**Reference:** `/home/linux/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/docs/TESTING_SPEC.md`
**Implemented By:** TODO.md (lines 224-262) and test files

#### Pending Tests (10 of 34)

**Critical (2):**
- [ ] SMART-007: Recall detection in smart update
- [ ] INT-001: End-to-end detect + trigger workflow

**High (6):**
- [ ] SMART-004, SMART-008, SMART-012
- [ ] INT-002, INT-003, INT-004, INT-005

**Medium (2):**
- [ ] SMART-016, SMART-017
- [ ] INT-006

**Performance (2):**
- [ ] PERF-001: Performance baseline
- [ ] PERF-002, PERF-003: Scalability tests

**Status:** See `/home/linux/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/docs/TEST_IMPLEMENTATION_CHECKLIST.md`

---

### 2.6 Quality Issues (QUA-11-32)

**Reference:** TICKET-022 Compliance Review
**Classification:** Compliance and Research Approval Issues

#### Phase 1 & 2 Delivery Status

| Item | Status | Notes |
|------|--------|-------|
| Data Integrity Layer | COMPLETE | 6 Phase 1 functions, 12 enrichment columns |
| Intelligence Layer | COMPLETE | 11 Phase 2 functions, 29 total enrichment columns |
| Production Code | 100% | `lib/fda_enrichment.py`, `lib/disclaimers.py` |
| Automated Tests | 22/22 PASSING | `tests/test_fda_enrichment.py` |
| Verification Materials | READY | 3 templates (CFR, Guidance, Manual Audit) |

#### Required Actions Before Production

| RA # | Action | Status | Effort |
|------|--------|--------|--------|
| RA-1 | Remove misleading claims | COMPLETE | 0 |
| RA-2 | Manual audit on 5 devices | TEMPLATE READY | 8-10h |
| RA-3 | True integration tests | COMPLETE | 0 |
| RA-4 | CFR/guidance verification | TEMPLATE READY | 2-3h |
| RA-5 | Assertion-based testing | COMPLETE | 0 |
| RA-6 | Prominent disclaimers | COMPLETE | 0 |

**Current Status:** CONDITIONAL APPROVAL (Research Use Only)

---

## 3. Issue Tracking Automation

### 3.1 How to Update This Index

This document is maintained manually but can be semi-automated. To keep it current:

#### Monthly Update Procedure

1. **Update TODO.md completion counts:**
   ```bash
   grep -c "^\- \[x\]" TODO.md  # Completed items
   grep -c "^\- \[ \]" TODO.md  # Active items
   ```

2. **Check for new gap analysis issues:**
   ```bash
   diff <(grep "^### ISSUE:" docs/planning/GAP-ANALYSIS-REPORT.md | cut -d' ' -f2) \
        <(echo "GAP-001 GAP-002 ... GAP-042")
   ```

3. **Verify test results:**
   ```bash
   pytest --tb=no -q  # Run full test suite
   pytest --co -q     # Count total tests
   ```

4. **Update version reference:**
   ```bash
   python scripts/version.py  # Get current version
   ```

5. **Generate timestamp:**
   ```bash
   date +"%Y-%m-%d %H:%M:%S"
   ```

#### Quarterly Review Procedure

1. **Validate issue counts against Linear/GitHub:**
   - Cross-check ISSUE_TRACKING_INDEX totals vs. Linear project
   - Verify all closed items are marked COMPLETE
   - Identify any orphaned issues

2. **Calculate effort burn-down:**
   - Sum effort of completed items
   - Update estimated total effort
   - Calculate velocity and projection

3. **Review priority assignments:**
   - Check if any HIGH items should be escalated to URGENT
   - Identify any LOW items ready for MEDIUM
   - Update blocking/dependency chains

### 3.2 File Cross-References

| Document | Purpose | Last Updated |
|----------|---------|--------------|
| TODO.md | Primary issue tracking, roadmap | 2026-02-16 |
| GAP-ANALYSIS-REPORT.md | Comprehensive gap analysis (42 new issues) | 2026-02-16 |
| TICKET-*.md | Completion reports for delivered features | 2026-02-16 |
| TESTING_SPEC.md | Test specification and requirements | 2026-02-15 |
| TEST_IMPLEMENTATION_CHECKLIST.md | Test implementation status (24/34 complete) | 2026-02-16 |
| CHANGELOG.md | Version history and release notes | 2026-02-16 |
| CONTRIBUTING.md | Development guidelines (if exists) | - |
| INSTALLATION.md | Setup and configuration | - |

### 3.3 Linear/GitHub Integration Notes

**Current Status:** All issues tracked in documents, not yet in Linear

**Recommended Linear Structure:**
```
Project: FDA Tools Plugin v5.36.0
  Sprint: URGENT Fixes (3 issues, 6-9 hours)
    Issue: GAP-006 CI/CD Pipeline
    Issue: GAP-012 Atomic Manifest Writes
    Issue: GAP-034 Compliance Disclaimer

  Sprint: High Priority Testing (4 issues, 50-85 hours)
    Issue: GAP-004 lib/ Module Tests
    Issue: GAP-005 Script Module Tests
    Issue: GAP-025 Complete TESTING_SPEC
    Issue: FE-001, FE-002 (Mock test suites)

  Sprint: Architecture Cleanup (3 issues, 15-25 hours)
    Issue: GAP-008 OpenClaw Build
    Issue: GAP-009 Predicate-Assistant Plugin
    Issue: GAP-003 __init__.py Structure

  Sprint: Remaining Issues (30 items, 95-155 hours)
    (Prioritized by impact and effort)
```

---

## 4. Issue Status Dashboard

### 4.1 Completion Progress

```
COMPLETED: 6 of 6 Critical Path Items
  ✓ TICKET-001: Pre-Sub eSTAR/PreSTAR XML (v5.25.0-v5.27.0)
  ✓ TICKET-002: PMA SSED Research (CONDITIONAL GO)
  ✓ TICKET-003: PMA Intelligence (v5.29.0-v5.35.0)
  ✓ TICKET-004: Pre-Sub Multi-Pathway (v5.28.0)
  ✓ TICKET-016: Auto-Update & Section Comparison (v5.26.0, v5.36.0)
  ✓ SMART: Smart Auto-Update System (v5.36.0)

ACTIVE: 7 of 13 TODO Items
  → TICKET-005: IDE Pathway (MEDIUM, 100-140h)
  → TICKET-006: PMA Annual Reports (MEDIUM, 40-60h)
  → TICKET-007: PMA Supplements (MEDIUM, 80-120h)
  → TICKET-008: Post-Approval Studies (MEDIUM, 60-80h)
  → TICKET-009-013: Low priority pathways

PENDING: 42 Gap Analysis Issues
  • 3 URGENT (6-9 hours) - BLOCKING
  • 12 HIGH (81-117 hours) - Next sprint
  • 18 MEDIUM (62-87 hours) - 3-month window
  • 9 LOW (28-42 hours) - Backlog

PENDING: 10 Future Enhancements (30-45 hours)
  • 3 HIGH (10-15h) - v5.37.0
  • 4 MEDIUM (12-18h) - v5.38.0
  • 3 LOW (8-12h) - v5.39.0+
```

### 4.2 Test Coverage

```
Overall: ~546 tests passing (100%)

By Module:
  ✓ PMA Phase 0: 95/95 (data store)
  ✓ PMA Phase 1: 108/108 (comparison & intelligence)
  ✓ PMA Phase 1.5: 57/57 (integration)
  ✓ PMA Phase 2: 64/64 (clinical requirements)
  ✓ PMA Phase 3: 54/54 (post-approval)
  ✓ PMA Phase 4: 82/82 (ML analytics)
  ✓ PMA Phase 5: 86/86 (pipelines)
  ✓ Pre-Sub: 15/15 (eSTAR, presub, multipathway)
  ✓ Auto-Update: 14/14 (v5.26.0)

Pending:
  ⚠ change_detector.py: 0 tests (SPEC VERIFIED)
  ⚠ section_analytics.py: 0 tests (SPEC VERIFIED)
  ⚠ 6 lib/ modules: 0 tests (GAP-004)
  ⚠ 20+ script modules: partial tests (GAP-005)
```

### 4.3 Compliance Status

```
CONDITIONAL APPROVAL (Research Use Only)
  ✓ Phase 1 Data Integrity: COMPLETE
  ✓ Phase 2 Intelligence Layer: COMPLETE
  ✓ Automated Tests: 22/22 PASSING
  ⚠ Manual Audit: TEMPLATE READY (RA-2, 8-10h)
  ⚠ Verification: TEMPLATE READY (RA-4, 2-3h)
```

---

## 5. Effort Estimation & Timeline

### 5.1 Estimated Total Effort Remaining

```
By Priority:
  URGENT: 3 issues × 2-3h avg = 6-9 hours (2-3 days)
  HIGH:  12 issues × 8h avg = 81-117 hours (2-3 weeks)
  MEDIUM: 18 issues × 4h avg = 62-87 hours (2-3 weeks)
  LOW: 9 issues × 3.5h avg = 28-42 hours (1-2 weeks)
  ───────────────────────────────────────
  TOTAL: 42 issues = 177-255 hours (5-8 weeks)

By Category:
  Testing: 50-85 hours (35% of effort)
  Architecture: 15-25 hours (12%)
  Code Quality: 15-25 hours (11%)
  Security: 12-16 hours (8%)
  CI/CD: 6-10 hours (5%)
  Documentation: 10-15 hours (8%)
  Data/Schema: 9-13 hours (6%)
  Compliance: 2-4 hours (2%)
```

### 5.2 Recommended Timeline

```
Sprint 1 (Week 1): URGENT Fixes
  Effort: 6-9 hours
  Focus: GAP-034, GAP-006, GAP-012
  Deliverable: v5.36.1 patch

Sprint 2 (Week 2-3): High Priority Testing
  Effort: 50-85 hours
  Focus: GAP-004, GAP-005, GAP-025
  Deliverable: v5.37.0

Sprint 3 (Week 4-5): Architecture Cleanup
  Effort: 15-25 hours
  Focus: GAP-008, GAP-009, GAP-003
  Deliverable: v5.37.1

Sprint 4+ (Week 6-8): Medium Priority Items
  Effort: 62-87 hours
  Focus: GAP-011-040 (prioritized by impact)
  Deliverable: v5.38.0

Backlog: Low Priority + Future Enhancements
  Effort: 28-42 + 30-45 = 58-87 hours
  Timeline: v5.39.0+
```

---

## 6. Key Dependencies & Blockers

### 6.1 Current Blockers

**NONE** - All URGENT/HIGH items are independent or have dependencies resolved.

#### Resolved Blockers

| Blocker | Dependency | Resolution | Date |
|---------|-----------|------------|------|
| TICKET-002 GO Decision | SSED Download Rate | CONDITIONAL GO (82.4% success) | 2026-02-16 |
| TICKET-003 Go-Ahead | TICKET-002 Result | Unblocked by GO decision | 2026-02-16 |
| TICKET-006/007/008 | TICKET-003 Complete | All COMPLETE (v5.35.0) | 2026-02-16 |

### 6.2 Dependency Chains

```
TICKET-001 (Pre-Sub XML, v5.25.0)
    ↓ (dependency)
TICKET-004 (Pre-Sub Multi-Pathway, v5.28.0)
    ↓ (unblocked)
Ready for: TICKET-005 (IDE Pathway)

TICKET-002 (PMA SSED Research, GO)
    ↓ (conditional pass)
TICKET-003 Phases 0-5 (PMA Intelligence, v5.29.0-v5.35.0)
    ↓ (unblocked)
Ready for: TICKET-006/007/008 (Post-Approval)

Independent:
  - TICKET-005 (IDE Pathway)
  - TICKET-009-013 (De Novo, HDE, Breakthrough, etc.)
  - All Gap Analysis Issues
  - All Future Enhancements
```

---

## 7. Next Actions

### 7.1 Immediate (This Week)

Priority Order:

1. **GAP-034: Compliance Disclaimer** (1-2h, URGENT)
   - Add CLI startup banner to standards generation scripts
   - File: standards generation scripts
   - Owner: TBD

2. **GAP-006: CI/CD Python 3.12** (3-4h, URGENT)
   - Add Python 3.12 to test matrix
   - File: `.github/workflows/test.yml`
   - Owner: TBD

3. **GAP-012: Atomic Manifest Writes** (2-3h, URGENT)
   - Implement write-then-rename pattern
   - Files: `fda_data_store.py`, `change_detector.py`
   - Owner: TBD

### 7.2 Short Term (Next 2 Weeks)

4. **GAP-001: Bare except: Clauses** (2-3h, HIGH)
5. **GAP-010: Input Validation** (6-8h, HIGH)
6. **GAP-007: Requirements Pinning** (2-3h, HIGH)
7. **FE-001 & FE-002: Test Suites** (8-12h, HIGH)

### 7.3 Medium Term (1-3 Months)

8-42. Remaining issues prioritized by impact and effort

---

## 8. Documentation References

### 8.1 Primary Source Documents

- **TODO.md**: `/home/linux/.claude/plugins/marketplaces/fda-tools/TODO.md`
  - Roadmap, completed features, pending work
  - Primary tracking document for TICKET items

- **GAP-ANALYSIS-REPORT.md**: `/home/linux/.claude/plugins/marketplaces/fda-tools/docs/planning/GAP-ANALYSIS-REPORT.md`
  - Comprehensive gap analysis with 42 new issues
  - Recommended implementation order
  - Effort estimation by category

- **TESTING_SPEC.md**: `/home/linux/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/docs/TESTING_SPEC.md`
  - Formal test specification
  - 34 test cases (24/34 implemented)
  - Marks for different test types (smart, sim, integration, performance)

- **TEST_IMPLEMENTATION_CHECKLIST.md**: `/home/linux/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/docs/TEST_IMPLEMENTATION_CHECKLIST.md`
  - Implementation status of TESTING_SPEC tests
  - Quick wins and remaining work

### 8.2 Supporting Documentation

- **CHANGELOG.md**: Release history and feature documentation
- **CONTRIBUTING.md**: Development guidelines (if exists)
- **INSTALLATION.md**: Setup and configuration
- **TROUBLESHOOTING.md**: Error recovery guides
- **IDEMPOTENCY_MATRIX.md**: Script rerun safety (if exists)

### 8.3 Ticket Completion Reports

Location: `/home/linux/.claude/plugins/marketplaces/fda-tools/docs/` and subdirectories

- TICKET-001-COMPLETION-REPORT.md
- TICKET-002-COMPLETION-REPORT.md
- TICKET-016-COMPLETE-SUMMARY.md
- TICKET-022-COMPLETION-SUMMARY.md
- And others...

---

## 9. Maintenance & Updates

### 9.1 Update Frequency

- **Daily:** GitHub/Linear sync (if integrated)
- **Weekly:** Test result updates
- **Monthly:** Complete review and summary update
- **Quarterly:** Priority reassessment and effort recalculation
- **Per Release:** Version and status updates

### 9.2 Update Checklist

When updating this document, verify:

- [ ] Total issue count matches source documents
- [ ] Priority distribution sums to 71+ issues
- [ ] Effort estimates align with source documents
- [ ] Version numbers match current release
- [ ] Completion dates are accurate
- [ ] All SPEC files referenced still exist
- [ ] Test counts reflect latest test runs
- [ ] Document timestamp is current

### 9.3 Escalation Procedure

If any of these conditions occur, escalate to leadership:

1. New URGENT issues appear (impacts release schedule)
2. Total effort estimate exceeds 300 hours
3. Critical test coverage drops below 85%
4. Three or more URGENT blockers appear
5. Compliance status changes from CONDITIONAL

---

## 10. Appendices

### A. Linear Issue Format Template

For importing issues into Linear, use this format:

```
Title: [Category] [Ticket ID] - Brief Description
Priority: URGENT/HIGH/MEDIUM/LOW
Effort: X-Y hours
Status: NOT STARTED / IN PROGRESS / BLOCKED / COMPLETE
Dependencies: [List blocking/blocked issues]
Source: TODO.md / GAP-ANALYSIS / TESTING_SPEC / etc.
Files: [List affected source files]
Acceptance Criteria:
  - [ ] Criterion 1
  - [ ] Criterion 2
  - [ ] Criterion 3
```

### B. Estimate Confidence Levels

- **URGENT:** 80-90% confidence (well-defined scope)
- **HIGH:** 70-80% confidence (clear requirements)
- **MEDIUM:** 60-70% confidence (some unknowns)
- **LOW:** 40-60% confidence (speculative features)

Estimates include: coding (60%), testing (25%), documentation (10%), review (5%)

### C. Completed Features Summary

**Version 5.36.0 (Current) - Smart Auto-Update System**
- Smart change detection module (change_detector.py)
- Advanced section analytics (section_analytics.py)
- 100% specification verification

**Version 5.35.0 - Real-time Data Pipelines**
- Data refresh orchestrator
- Approval monitoring
- External data hub integration
- 86 tests passing

**Version 5.34.0 - ML Analytics**
- Review time prediction
- Approval probability scoring
- MAUDE peer comparison
- Competitive dashboards
- 82 tests passing

*(See TODO.md for complete version history)*

---

**Document Footer:**
- Generated: 2026-02-17
- Version: 1.0
- Owner: Technical Writer / Documentation Lead
- License: Same as parent project
- Confidentiality: Internal Use Only
