# Issue Tracking - Linear Import Template

**Purpose:** Template and guidelines for importing all tracked issues into Linear.org

**Current Status:** Issues documented in markdown, ready for import
**Total Issues to Import:** 71+
**Recommended Import Sequence:** URGENT → HIGH → MEDIUM → LOW → FUTURE

---

## Pre-Import Checklist

- [ ] All 42 gap analysis issues documented in GAP-ANALYSIS-REPORT.md
- [ ] All 13 TODO items enumerated in TODO.md
- [ ] All 10 incomplete test cases identified in TESTING_SPEC.md
- [ ] All 10 future enhancements documented in TODO.md
- [ ] Cross-references verified between documents
- [ ] Effort estimates reviewed and finalized
- [ ] Priority assignments reviewed by team
- [ ] Dependencies mapped in section 6.2 of ISSUE_TRACKING_INDEX.md

---

## Linear Project Structure

### Recommended Setup

```
Project: FDA Tools Plugin v5.36.0
├─ Team: Engineering
├─ State Groups:
│  ├─ Backlog (NOT STARTED)
│  ├─ In Progress
│  ├─ Review
│  └─ Done (Completed)
├─ Custom Fields:
│  ├─ Effort (number, hours)
│  ├─ Category (select: Code Quality, Testing, Security, CI/CD, Documentation, Architecture, Data/Schema, Compliance)
│  ├─ Source (select: TODO, GAP-Analysis, TESTING_SPEC, FE, etc.)
│  ├─ Risk Level (select: CRITICAL, HIGH, MEDIUM, LOW)
│  └─ Files Affected (text, comma-separated)
└─ Cycles:
   ├─ Sprint 1: URGENT Fixes (Week 1)
   ├─ Sprint 2: HIGH Testing (Week 2-3)
   ├─ Sprint 3: Architecture (Week 4-5)
   └─ Sprint 4+: MEDIUM Items (Week 6+)
```

---

## Issue Template Format

Use this template when creating each Linear issue:

```
TITLE:
[Category] [Issue ID] - Brief Description

DESCRIPTION:
[Full description from source document]

Acceptance Criteria:
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

Affected Files:
- path/to/file1.py
- path/to/file2.py

Related Issues:
[Link any dependent/blocking issues]

CUSTOM FIELDS:
Priority: URGENT / HIGH / MEDIUM / LOW
Estimate: X-Y hours (use lower estimate for planning)
Category: [Category from above]
Source: TODO | GAP-Analysis | TESTING_SPEC | FE | TICKET
Risk Level: CRITICAL | HIGH | MEDIUM | LOW
Status: NOT STARTED

LABELS:
[category] [source] [priority]

CYCLE:
[Sprint assignment if applicable]

TEAM:
Engineering

DESCRIPTION TEMPLATE:
---
## Overview
[One-paragraph summary]

## Current State
[What's broken or missing]

## Desired State
[What needs to be fixed/implemented]

## Acceptance Criteria
- [ ] [Testable criterion 1]
- [ ] [Testable criterion 2]
- [ ] [Testable criterion 3]

## Affected Files
- [Primary file 1]
- [Primary file 2]

## Estimated Effort
[X-Y hours]

## References
- Document: [filename]
- Section: [section number]
- Source: [TODO.md | GAP-ANALYSIS-REPORT.md | etc.]
---
```

---

## Issue-by-Issue Import Guide

### URGENT Issues (3) - Import First

#### 1. GAP-034: Compliance Disclaimer at CLI Runtime

```
Title: [Compliance] GAP-034 - Add CLI runtime disclaimer for standards generation

Priority: URGENT
Effort: 1-2 hours
Category: Compliance
Source: GAP-Analysis
Risk Level: CRITICAL

Description:
The standards generation scripts (knowledge_based_generator.py, auto_generate_device_standards.py, quick_standards_generator.py) do not display "RESEARCH USE ONLY" disclaimer at runtime. Users running these scripts directly never see the warning.

Acceptance Criteria:
- [ ] CLI shows disclaimer banner before output
- [ ] Disclaimer cannot be bypassed silently
- [ ] --accept-disclaimer flag works for non-interactive use
- [ ] Disclaimer acceptance logged to audit trail
- [ ] All 3 standards generation scripts updated

Affected Files:
- scripts/knowledge_based_generator.py
- scripts/auto_generate_device_standards.py
- scripts/quick_standards_generator.py

References:
- GAP-ANALYSIS-REPORT.md § GAP-034
- TICKET-022 Compliance Review
```

#### 2. GAP-006: CI/CD Pipeline Missing Python 3.12

```
Title: [CI/CD] GAP-006 - Add Python 3.12 support to CI pipeline

Priority: URGENT
Effort: 3-4 hours
Category: CI/CD
Source: GAP-Analysis
Risk Level: HIGH

Description:
GitHub Actions workflow tests only Python 3.9-3.11. Development environment uses Python 3.12, and TESTING_SPEC.md requires Python 3.12+. Missing CI coverage means Python 3.12 bugs won't be caught.

Acceptance Criteria:
- [ ] CI matrix includes Python 3.12 (and optionally 3.13)
- [ ] All dependencies from requirements.txt installed in CI
- [ ] Coverage reporting enabled (--cov flag)
- [ ] Coverage uploaded to Codecov/Coveralls
- [ ] Linting step added (ruff or flake8)
- [ ] All tests pass on Python 3.12

Affected Files:
- .github/workflows/test.yml
- requirements.txt
- pytest.ini

References:
- GAP-ANALYSIS-REPORT.md § GAP-006
```

#### 3. GAP-012: save_manifest() Not Atomic (Data Loss Risk)

```
Title: [Data Integrity] GAP-012 - Implement atomic writes for manifest file

Priority: URGENT
Effort: 2-3 hours
Category: Data/Schema
Source: GAP-Analysis
Risk Level: CRITICAL

Description:
save_manifest() writes directly to data_manifest.json using open(..., "w"). If the process crashes during write, the manifest is corrupted and all project data references are lost. This affects fda_data_store.py and change_detector.py.

Acceptance Criteria:
- [ ] All manifest writes use atomic pattern (write temp, then rename)
- [ ] Backup created before write (data_manifest.json.bak)
- [ ] Recovery procedure implemented for corrupted manifest
- [ ] Same pattern applied to change_detector.py fingerprints
- [ ] 5+ tests cover crash recovery scenarios
- [ ] Data integrity verified after simulated crash

Affected Files:
- scripts/fda_data_store.py
- scripts/change_detector.py

References:
- GAP-ANALYSIS-REPORT.md § GAP-012
```

### HIGH Priority Issues (12) - Import Next

[Continue with similar format for each HIGH issue...]

#### 4. GAP-001: Bare except: Clauses

```
Title: [Code Quality] GAP-001 - Replace bare except: clauses with specific types

Priority: HIGH
Effort: 2-3 hours
Category: Code Quality
Source: GAP-Analysis
Risk Level: MEDIUM

Description:
Six bare except: clauses catch ALL exceptions including SystemExit and KeyboardInterrupt. This silently swallows errors, making debugging impossible for regulatory data processing.

Affected Files:
- scripts/knowledge_based_generator.py (line 159)
- scripts/quick_standards_generator.py (line 150)
- scripts/auto_generate_device_standards.py (lines 158, 180, 287, 298)

Acceptance Criteria:
- [ ] All bare except: replaced with specific exception types
- [ ] Logging added for caught exceptions
- [ ] Audit trail captures exceptions
- [ ] Tests verify exception handling

References:
- GAP-ANALYSIS-REPORT.md § GAP-001
```

#### 5. GAP-004: No Tests for 6 lib/ Modules

```
Title: [Testing] GAP-004 - Create test suite for 6 untested lib/ modules

Priority: HIGH
Effort: 12-16 hours
Category: Testing
Source: GAP-Analysis
Risk Level: HIGH

Description:
Six production modules in lib/ have ZERO test coverage: gap_analyzer.py, predicate_ranker.py, combination_detector.py, predicate_diversity.py, ecopy_exporter.py, expert_validator.py.

Acceptance Criteria:
- [ ] tests/test_gap_analyzer.py created (10+ tests)
- [ ] tests/test_predicate_ranker.py created (10+ tests)
- [ ] tests/test_combination_detector.py created (8+ tests)
- [ ] tests/test_predicate_diversity.py created (8+ tests)
- [ ] tests/test_ecopy_exporter.py created (8+ tests)
- [ ] tests/test_expert_validator.py created (6+ tests)
- [ ] Minimum 50 tests total across all 6 modules
- [ ] Coverage >= 80% for each module
- [ ] No network access in tests (all mocked)

Affected Files:
- lib/gap_analyzer.py
- lib/predicate_ranker.py
- lib/combination_detector.py
- lib/predicate_diversity.py
- lib/ecopy_exporter.py
- lib/expert_validator.py

References:
- GAP-ANALYSIS-REPORT.md § GAP-004
```

[Continue with GAP-005, GAP-007, GAP-008, GAP-009, GAP-010, GAP-019, GAP-025...]

---

## Import Prioritization Matrix

### Week 1: URGENT (3 issues, 6-9 hours)

1. **GAP-034** - Compliance disclaimer (1-2h) - BLOCKER
2. **GAP-006** - CI/CD Python 3.12 (3-4h) - BLOCKER
3. **GAP-012** - Atomic writes (2-3h) - DATA LOSS RISK

### Week 2-3: HIGH Testing (4-6 issues, 50-85 hours)

1. **GAP-004** - lib/ module tests (12-16h)
2. **GAP-005** - Script module tests (20-30h)
3. **GAP-025** - Complete TESTING_SPEC (5-7h)
4. **FE-001** - change_detector mock tests (4-6h)
5. **FE-002** - section_analytics mock tests (4-6h)

### Week 4-5: HIGH Architecture (3 issues, 15-25 hours)

1. **GAP-008** - OpenClaw build (8-12h)
2. **GAP-009** - Predicate-assistant plugin (4-6h)
3. **GAP-003** - __init__.py structure (1-2h)

### Week 6+: HIGH Other (5 issues, 25-35 hours)

1. **GAP-001** - Bare except (2-3h)
2. **GAP-002** - Silent except...pass (8-12h)
3. **GAP-007** - Requirements pinning (2-3h)
4. **GAP-010** - Input validation (6-8h)
5. **GAP-019** - XML schema validation (6-8h)

### Remaining: MEDIUM + LOW (27 issues, 90-155 hours)

---

## Bulk Import via Linear CLI

If Linear supports bulk import, use this format:

```csv
Title,Priority,Estimate,Category,Status,Description,Effort,Affected Files
"[Compliance] GAP-034 - CLI disclaimer",URGENT,1-2,Compliance,NOT_STARTED,"Add runtime disclaimer to standards generation scripts","1-2 hours","scripts/knowledge_based_generator.py,scripts/auto_generate_device_standards.py,scripts/quick_standards_generator.py"
"[CI/CD] GAP-006 - Python 3.12 support",URGENT,3-4,CI/CD,NOT_STARTED,"Add Python 3.12 to CI test matrix","3-4 hours",".github/workflows/test.yml,requirements.txt,pytest.ini"
"[Data Integrity] GAP-012 - Atomic writes",URGENT,2-3,Data/Schema,NOT_STARTED,"Implement atomic write pattern for manifest","2-3 hours","scripts/fda_data_store.py,scripts/change_detector.py"
```

---

## Post-Import Verification

After importing all issues into Linear, verify:

1. **Count Check:**
   ```
   URGENT: 3 issues ✓
   HIGH: 12 issues ✓
   MEDIUM: 18 issues ✓
   LOW: 9 issues ✓
   FUTURE: 10 issues ✓
   TOTAL: 71+ issues ✓
   ```

2. **Cross-Reference Check:**
   - [ ] All dependencies mapped
   - [ ] All related issues linked
   - [ ] Cycle assignments correct
   - [ ] Team assignments set

3. **Documentation Check:**
   - [ ] Each issue has acceptance criteria
   - [ ] Affected files documented
   - [ ] References include source documents
   - [ ] Effort estimates clear

4. **Status Check:**
   - [ ] No issues in undefined state
   - [ ] Completed items in "Done"
   - [ ] New items in "NOT STARTED"
   - [ ] Custom fields populated

---

## Keeping Linear in Sync

### Weekly Sync Procedure

```bash
# Check if any documentation has been updated
git diff HEAD~1 docs/ISSUE_TRACKING_INDEX.md
git diff HEAD~1 TODO.md

# Update Linear if changes detected
# 1. Note new/changed issues
# 2. Update corresponding Linear issues
# 3. Log in commit message: "Sync Linear with issue updates"
```

### Monthly Sync Procedure

1. Export Linear project to CSV
2. Compare with ISSUE_TRACKING_INDEX.md
3. Identify any drift (created in Linear only, status mismatches)
4. Update either document to match
5. Document decisions

---

## Labels Schema

### Category Labels
- `code-quality` - Code improvements, refactoring
- `testing` - Test coverage, test suite improvements
- `security` - Security vulnerabilities, validation
- `ci-cd` - CI/CD pipeline, automation
- `documentation` - Docs, guides, help text
- `architecture` - Design, structure, dependencies
- `data-schema` - Data model, storage, migration
- `compliance` - Regulatory, FDA compliance

### Priority Labels
- `urgent` - URGENT priority (6-9h, this week)
- `high` - HIGH priority (81-117h, next sprint)
- `medium` - MEDIUM priority (62-87h, 3-month)
- `low` - LOW priority (28-42h, backlog)
- `future` - Future enhancements (30-45h, v5.37+)

### Source Labels
- `source/todo` - From TODO.md
- `source/gap` - From GAP-ANALYSIS-REPORT.md
- `source/spec` - From TESTING_SPEC.md
- `source/fe` - Future Enhancement (FE-001-010)

### Risk Labels
- `risk/critical` - Data loss, compliance exposure
- `risk/high` - Blocking development, security
- `risk/medium` - Important but not blocking
- `risk/low` - Nice-to-have improvements

---

## Sync Automation (Future)

Consider automating sync using Linear API:

```python
# Pseudo-code for Linear API integration
from linear_api import LinearClient

client = LinearClient(api_key="...")

# Import issues from ISSUE_TRACKING_INDEX.md
for issue in parse_markdown_issues():
    linear_issue = client.issues.create(
        projectId="...",
        title=issue.title,
        description=issue.description,
        priority=issue.priority,
        estimate=issue.effort,
        labels=issue.labels,
        cycle=issue.cycle,
    )
    print(f"Created: {linear_issue.id}")
```

---

## FAQ

**Q: Should completed items be imported?**
A: No. Only import active and pending items (TICKET-005 onwards). Mark completed items as reference only in Linear.

**Q: How do I handle dependency cycles?**
A: There are none currently. All dependencies are acyclic (see ISSUE_TRACKING_INDEX.md § 6).

**Q: What if a Linear issue already exists?**
A: Update existing issue with latest details from markdown. Don't create duplicate.

**Q: When should issues be removed from Linear?**
A: Move completed issues to "Done" cycle, but keep them in the project for historical record.

**Q: Can team members create issues outside this list?**
A: Yes, but they should be checked against ISSUE_TRACKING_INDEX.md to avoid duplication.

---

## Related Documents

- [ISSUE_TRACKING_INDEX.md](./ISSUE_TRACKING_INDEX.md) - Source of truth
- [GAP-ANALYSIS-REPORT.md](./planning/GAP-ANALYSIS-REPORT.md) - Detailed gap analysis
- [ISSUE_TRACKING_QUICK_REFERENCE.md](./ISSUE_TRACKING_QUICK_REFERENCE.md) - Quick lookup guide
- [../TODO.md](../TODO.md) - Roadmap and deliverables

---

**Document Version:** 1.0
**Created:** 2026-02-17
**Last Updated:** 2026-02-17
**Owner:** Technical Writer / Project Management
**License:** Same as parent project
