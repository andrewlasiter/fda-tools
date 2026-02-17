# Issue Tracking Quick Reference Guide

**Quick Links:**
- [Full Index](./ISSUE_TRACKING_INDEX.md) - Comprehensive tracking document
- [Update Script](../scripts/update_issue_index.py) - Automation tool
- [TODO.md](../TODO.md) - Primary roadmap
- [GAP-ANALYSIS-REPORT.md](./planning/GAP-ANALYSIS-REPORT.md) - Comprehensive gap analysis

---

## At a Glance

**Current Status (v5.36.0):**
- Total Issues: 71+ tracked
- URGENT: 3 issues (6-9h) - BLOCKING
- HIGH: 12 issues (81-117h) - Next sprint
- MEDIUM: 18 issues (62-87h) - 3-month
- LOW: 9 issues (28-42h) - Backlog
- FUTURE: 10 enhancements (30-45h) - v5.37+

**Estimated Remaining Effort:** 195-270 hours

---

## Issue Categories

### URGENT (Do This Week)

| Issue | Impact | Effort | File |
|-------|--------|--------|------|
| GAP-034 | Compliance disclaimer missing at CLI | 1-2h | Standards scripts |
| GAP-006 | CI/CD missing Python 3.12 | 3-4h | `.github/workflows/test.yml` |
| GAP-012 | Manifest writes not atomic (DATA LOSS!) | 2-3h | `fda_data_store.py` |

**Action:** These block v5.36.1 release

### HIGH (Next Sprint)

Primary focus areas:
- **Testing (4 issues, 50-85h):** GAP-004, GAP-005, GAP-025, FE-001, FE-002
- **Architecture (3 issues, 15-25h):** GAP-008, GAP-009, GAP-003
- **Security (2 issues, 12-16h):** GAP-010, GAP-011
- **Other (3 issues):** GAP-001, GAP-002, GAP-007, GAP-019

**Action:** Plan for v5.37.0 development cycle

### MEDIUM (3 Months)

18 issues spanning:
- Code quality and refactoring (5 issues)
- Data integrity and schemas (2 issues)
- Documentation (3 issues)
- Other improvements (8 issues)

**Action:** Prioritize by impact after HIGH items

### LOW (Backlog)

9 issues for future enhancement and polish work.

**Action:** Consider for v5.39+

---

## Finding Specific Issues

### By Status

**Completed:** See section 2.1 of [ISSUE_TRACKING_INDEX.md](./ISSUE_TRACKING_INDEX.md)
- 6 TICKET items delivered in v5.25.0-v5.36.0
- All critical path features complete

**Active:** See section 2.3
- 7 items from TICKET-005 through TICKET-013
- 10 Future Enhancements (FE-001-010)

**Pending:** See section 2.2
- 42 gap analysis items (GAP-001 through GAP-042)
- 10 incomplete tests from TESTING_SPEC

### By Effort Level

**Small Tasks (1-3 hours):**
- GAP-034, GAP-001, GAP-007, GAP-015, GAP-018, GAP-023, GAP-026, GAP-027, GAP-031, GAP-038, GAP-040, GAP-041, GAP-042, FE-003, FE-004, FE-006, FE-009

**Medium Tasks (4-8 hours):**
- GAP-006, GAP-011, GAP-013, GAP-014, GAP-016, GAP-020, GAP-022, GAP-028, GAP-032, GAP-035, GAP-037, GAP-039, FE-001, FE-002, FE-005, FE-007, FE-008

**Large Tasks (10+ hours):**
- GAP-002 (8-12h), GAP-004 (12-16h), GAP-005 (20-30h), GAP-008 (8-12h), GAP-010 (6-8h), GAP-019 (6-8h), GAP-024 (2-3h), GAP-025 (5-7h)

### By Risk Level

**Critical (Data Loss):**
- GAP-012 (manifest writes not atomic)

**Regulatory/Compliance:**
- GAP-034 (compliance disclaimer)
- GAP-019 (XML schema validation)
- GAP-027 (user-agent spoofing)

**Security:**
- GAP-010 (input validation)
- GAP-011 (cache integrity)
- GAP-027 (browser UA misrepresentation)

**Testing Gaps:**
- GAP-004 (lib/ module tests)
- GAP-005 (script module tests)
- GAP-025 (incomplete test spec)

---

## Common Questions

### Q: Where do I find details about issue X?

**A:** Check in this order:
1. Search [ISSUE_TRACKING_INDEX.md](./ISSUE_TRACKING_INDEX.md) (sections 2.1-2.6)
2. Look in source document (TODO.md or GAP-ANALYSIS-REPORT.md)
3. Check TICKET completion reports in `/docs/` subdirectories
4. Review test specification in `/docs/TESTING_SPEC.md`

### Q: What's the status of issue GAP-012?

**A:** GAP-012 is URGENT (data loss risk from non-atomic manifest writes).
- **Priority:** URGENT
- **Effort:** 2-3 hours
- **Category:** Data Integrity
- **Status:** NOT STARTED
- **Files:** `fda_data_store.py`, `change_detector.py`
- **See:** [ISSUE_TRACKING_INDEX.md § 2.2](./ISSUE_TRACKING_INDEX.md#22-gap-analysis-issues)

### Q: How many tests are pending?

**A:** 10 tests from TESTING_SPEC remain unimplemented:
- 2 CRITICAL (SMART-007, INT-001)
- 6 HIGH
- 4 MEDIUM/LOW

**See:** [ISSUE_TRACKING_INDEX.md § 2.5](./ISSUE_TRACKING_INDEX.md#25-testing-specification)

### Q: What's blocking development?

**A:** Nothing currently. All blockers have been resolved:
- TICKET-002 GO decision (82.4% SSED success)
- TICKET-003 Phases 0-5 complete

**See:** [ISSUE_TRACKING_INDEX.md § 6.1](./ISSUE_TRACKING_INDEX.md#61-current-blockers)

### Q: How do I estimate effort for my issue?

**A:** See section 5.2 of the index for typical estimates by priority/category:
- URGENT: 2-4 hours average
- HIGH: 8 hours average
- MEDIUM: 4 hours average
- LOW: 3.5 hours average

### Q: What's the recommended sprint order?

**A:**
1. **Sprint 1 (Week 1):** Fix 3 URGENT issues (6-9h)
2. **Sprint 2 (Week 2-3):** Address 4 HIGH testing issues (50-85h)
3. **Sprint 3 (Week 4-5):** Clean up architecture (15-25h)
4. **Sprint 4+ (Week 6-8):** MEDIUM priority (62-87h)
5. **Backlog:** LOW + Future Enhancements (58-87h)

**See:** [ISSUE_TRACKING_INDEX.md § 5.2](./ISSUE_TRACKING_INDEX.md#52-recommended-timeline)

---

## Using the Automation Tool

The `update_issue_index.py` script helps maintain the index:

```bash
# View statistics
python3 scripts/update_issue_index.py --stats

# Scan all sources
python3 scripts/update_issue_index.py --scan

# Verify cross-references are valid
python3 scripts/update_issue_index.py --verify

# Generate full report
python3 scripts/update_issue_index.py --report

# Update timestamp to today
python3 scripts/update_issue_index.py --update-timestamp
```

---

## Updating the Index

### Monthly Update Checklist

- [ ] Run `./scripts/update_issue_index.py --scan` to get counts
- [ ] Update TODO.md completion counts (if changed)
- [ ] Verify all TICKET files still exist
- [ ] Update test results (if new tests added)
- [ ] Check for new gaps (compare GAP-ANALYSIS-REPORT sections)
- [ ] Run `./scripts/update_issue_index.py --verify` for broken links
- [ ] Run `./scripts/update_issue_index.py --update-timestamp`
- [ ] Commit updates: `git add docs/ISSUE_TRACKING_INDEX.md && git commit -m "Update issue index"`

### Quarterly Review Checklist

- [ ] Run full `--report` to review all statistics
- [ ] Verify priority assignments still match current roadmap
- [ ] Recalculate total effort based on completed work
- [ ] Check if any LOW issues should be promoted
- [ ] Identify new dependency chains
- [ ] Update timeline estimates if needed
- [ ] Review Linear/GitHub integration needs

---

## Integration with Linear/GitHub

### Recommended Structure

```
Project: FDA Tools Plugin - v5.36.0+
  ├─ Epic: URGENT Fixes
  │  ├─ Issue: GAP-006 (CI/CD Python 3.12)
  │  ├─ Issue: GAP-012 (Atomic writes)
  │  └─ Issue: GAP-034 (Compliance disclaimer)
  │
  ├─ Epic: HIGH Priority Testing
  │  ├─ Issue: GAP-004 (lib/ tests)
  │  ├─ Issue: GAP-005 (script tests)
  │  ├─ Issue: GAP-025 (test spec completion)
  │  └─ Issue: FE-001/FE-002 (mock tests)
  │
  ├─ Epic: Architecture Cleanup
  │  ├─ Issue: GAP-008 (OpenClaw build)
  │  ├─ Issue: GAP-009 (predicate-assistant)
  │  └─ Issue: GAP-003 (__init__.py)
  │
  └─ Epic: MEDIUM Priority (30 items)
```

### Import Template

For each issue, create a Linear item with:
```
Title: [Category] [Issue ID] - Description
Description: [Full description from GAP-ANALYSIS-REPORT]
Priority: URGENT/HIGH/MEDIUM/LOW
Estimate: X hours
Status: NOT STARTED
Dependencies: [List other issue IDs]
Labels: [category], [source]
```

---

## Key Metrics

**Project Health:**
- Lines of code: ~50,000+
- Test coverage: ~546 tests (100% passing)
- Issues tracked: 71+
- Estimated burndown: 195-270 hours remaining

**Velocity (Estimated):**
- URGENT: 2-3 days
- HIGH: 2-3 weeks
- MEDIUM: 2-3 weeks
- LOW: 1-2 weeks

**Quality:**
- Pre-Sub XML: ✓ Regulatory compliant
- PMA Intelligence: ✓ 546 tests (100%)
- Compliance Status: ⚠ CONDITIONAL APPROVAL (research use)

---

## Escalation Contacts

If any of these occur, escalate immediately:

1. **Data Loss Events** (GAP-012) → Engineering Lead
2. **Compliance/Regulatory Issues** (GAP-034, GAP-019) → Compliance Officer
3. **Critical Test Failures** → QA Lead
4. **Security Vulnerabilities** (GAP-010, GAP-011) → Security Lead
5. **Blockers that halt development** → Project Manager

---

## Related Documents

- [ISSUE_TRACKING_INDEX.md](./ISSUE_TRACKING_INDEX.md) - Full index
- [../TODO.md](../TODO.md) - Detailed roadmap
- [GAP-ANALYSIS-REPORT.md](./planning/GAP-ANALYSIS-REPORT.md) - Full gap analysis
- [TESTING_SPEC.md](./TESTING_SPEC.md) - Test specification
- [TEST_IMPLEMENTATION_CHECKLIST.md](./TEST_IMPLEMENTATION_CHECKLIST.md) - Test status

---

**Last Updated:** 2026-02-17
**Version:** 1.0
**Owner:** Technical Writer / Documentation Lead
