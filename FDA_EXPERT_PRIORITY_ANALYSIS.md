# FDA Expert Agent Priority Analysis

**Date:** 2026-02-16
**Based on:** Current Linear issues (FDA-22 through FDA-73)
**Method:** Issue categorization by regulatory expertise area

---

## Issue Distribution by Regulatory Expertise

### Quality Systems & Compliance (18 issues) 🥇 **HIGHEST PRIORITY**

**Expert Needed:** `fda-quality-expert`

**URGENT Issues (3):**
- FDA-34 (GAP-034): Compliance disclaimer not shown at CLI runtime
- FDA-32 (GAP-012): save_manifest() not atomic - data corruption risk
- FDA-33 (GAP-006): CI/CD pipeline gaps

**HIGH Issues (7):**
- FDA-23 (GAP-019): eSTAR XML generation lacks schema validation
- FDA-31 (GAP-001): Bare except clauses in standards generation
- FDA-30 (GAP-002): Silent except...pass patterns (50+ instances)
- FDA-27 (GAP-007): No requirements.txt version pinning
- FDA-24 (GAP-009): fda-predicate-assistant plugin still active (cleanup)
- FDA-35: Version consistency & documentation
- FDA-36: Repository cleanup & organization

**MEDIUM Issues (8):**
- FDA-71 (GAP-011): Cache files have no integrity verification
- FDA-59 (GAP-033): data_manifest.json schema not documented
- FDA-60 (GAP-031): approval_probability.py fallback behavior
- FDA-57 (GAP-038): supplement_tracker.py hardcoded dates
- FDA-49 (GAP-040): Multiple settings files with no schema
- FDA-66: TICKET-006 PMA Annual Report Generator
- FDA-64: TICKET-008 Post-Approval Study Monitoring
- FDA-65: TICKET-007 PMA Supplement Support

**Rationale:** Quality systems, data integrity, compliance, and documentation are foundational to ALL regulatory work. This expert would address:
- 21 CFR 820 (Quality System Regulation)
- 21 CFR Part 11 (Electronic Records)
- ISO 13485 (Medical Device QMS)
- Design controls, DHF, risk management

---

### Software/Testing/Validation (15 issues) 🥈 **SECOND PRIORITY**

**Expert Needed:** `fda-software-ai-expert`

**HIGH Issues (6):**
- FDA-29 (GAP-004): No tests for 6 lib/ modules (0% coverage)
- FDA-28 (GAP-005): No tests for 20+ script modules
- FDA-22 (GAP-025): 10 of 34 TESTING_SPEC test cases unimplemented
- FDA-26 (GAP-008): OpenClaw skill has no build/dist directory
- FDA-25 (GAP-010): Missing input validation on CLI arguments
- FDA-37: Plugin rename (breaking change management)

**MEDIUM Issues (6):**
- FDA-58 (GAP-035): external_data_hub.py integration has no tests
- FDA-56 (GAP-024): Test fixtures use hardcoded FDA data
- FDA-67: TICKET-005 IDE Pathway Support
- FDA-70: FE-001 Mock-based test suite for change_detector.py
- FDA-69: FE-002 Mock-based test suite for section_analytics.py
- FDA-68: FE-003 Cross-module _run_subprocess() reuse

**LOW Issues (3):**
- FDA-54 (GAP-030): Skills directory has no functional tests
- FDA-50 (GAP-039): OpenClaw skill tests cannot run
- FDA-51 (GAP-037): No type checking (mypy) configuration

**Rationale:** Software validation is critical for FDA software submissions. This expert would address:
- IEC 62304 (Medical Device Software Lifecycle)
- FDA Software Validation Guidance
- V&V documentation
- Test coverage and quality metrics
- SaMD-specific requirements

---

### Regulatory Strategy & Submissions (8 issues) 🥉 **THIRD PRIORITY**

**Expert Needed:** `fda-regulatory-strategy-expert`

**HIGH Issues (1):**
- FDA-23 (GAP-019): eSTAR XML validation (also Quality expert)

**MEDIUM Issues (4):**
- FDA-66: TICKET-006 PMA Annual Report Generator
- FDA-65: TICKET-007 PMA Supplement Support
- FDA-64: TICKET-008 Post-Approval Study Monitoring
- FDA-67: TICKET-005 IDE Pathway Support

**LOW Issues (3):**
- FDA-45: TICKET-009 De Novo Classification Request Support
- FDA-44: TICKET-010 Humanitarian Device Exemption (HDE) Support
- FDA-43: TICKET-011 Breakthrough Device Designation Support

**Rationale:** Regulatory pathway selection, submission preparation, and Pre-Sub strategy are high-value activities. This expert would address:
- 510(k) vs. PMA vs. De Novo pathway selection
- Pre-Submission meeting preparation
- RTA deficiency response
- Breakthrough Device Program
- Advisory committee preparation

---

### Post-Market Surveillance (6 issues) 🏅 **FOURTH PRIORITY**

**Expert Needed:** `fda-postmarket-expert`

**MEDIUM Issues (3):**
- FDA-66: TICKET-006 PMA Annual Report Generator (21 CFR 814.84)
- FDA-64: TICKET-008 Post-Approval Study Monitoring
- FDA-52 (GAP-036): review_time_predictor.py and maude_comparison.py ML models not validated

**LOW Issues (3):**
- FDA-53 (GAP-032): No telemetry or usage analytics
- FDA-41: TICKET-013 Real World Evidence (RWE) Integration
- FDA-42: TICKET-012 510(k) Third Party Review Integration

**Rationale:** Post-market activities are ongoing regulatory obligations. This expert would address:
- 21 CFR 803 (MDR - Medical Device Reporting)
- 21 CFR 806 (Recalls and corrections)
- 21 CFR 814.84 (PMA Annual Reports)
- 522 Post-Market Surveillance Orders

---

### Infrastructure/DevOps (4 issues) ⚙️ **SUPPORTING**

**Expert Needed:** Generic `voltagent-infra:devops-engineer` (OK to use non-FDA expert)

**URGENT Issues (1):**
- FDA-33 (GAP-006): CI/CD pipeline missing Python 3.12

**HIGH Issues (2):**
- FDA-27 (GAP-007): No requirements.txt version pinning
- FDA-26 (GAP-008): OpenClaw skill build

**MEDIUM Issues (1):**
- FDA-48 (GAP-041): Zone.Identifier files committed to git

**Rationale:** These are infrastructure issues that don't require FDA expertise. Generic DevOps agents are appropriate.

---

### Documentation/Technical Writing (4 issues) 📝 **SUPPORTING**

**Expert Needed:** Generic `voltagent-biz:technical-writer` (OK to use non-FDA expert)

**HIGH Issues (1):**
- FDA-35: Version consistency & documentation

**MEDIUM Issues (2):**
- FDA-49 (GAP-040): Multiple settings files with no schema documentation
- FDA-46: FE-007 Enhanced trend visualization

**LOW Issues (1):**
- FDA-47 (GAP-042): batchfetch.md.backup committed to repository

**Rationale:** General documentation issues. Technical writer agents are appropriate.

---

## Implementation Priority Recommendation

### Phase 1: Build Top 3 FDA Experts (Weeks 1-2)

1. **fda-quality-expert** (18 issues)
   - Creates: `skills/fda-quality-expert/SKILL.md`
   - Addresses: URGENT compliance, data integrity, QMS issues
   - Re-assigns: FDA-34, FDA-32, FDA-31, FDA-30, FDA-23, FDA-71, FDA-59

2. **fda-software-ai-expert** (15 issues)
   - Creates: `skills/fda-software-ai-expert/SKILL.md`
   - Addresses: Software validation, testing, V&V documentation
   - Re-assigns: FDA-29, FDA-28, FDA-22, FDA-26, FDA-25, FDA-58

3. **fda-regulatory-strategy-expert** (8 issues)
   - Creates: `skills/fda-regulatory-strategy-expert/SKILL.md`
   - Addresses: Pathway selection, Pre-Sub, submission planning
   - Re-assigns: FDA-66, FDA-65, FDA-64, FDA-67

### Phase 2: Build Device-Specific Experts (Weeks 3-4)

4. **fda-postmarket-expert** (6 issues)
5. **fda-cardiovascular-expert** (if cardiovascular issues emerge)
6. **fda-orthopedic-expert** (if orthopedic issues emerge)

### Phase 3: Expand as Needed (Weeks 5-6)

Build additional device-specific experts based on:
- User device type
- Emerging Linear issues
- Real project needs

---

## Issue Re-Assignment Plan

Once experts are built, re-assign issues from generic agents:

### From `voltagent-qa-sec:compliance-auditor` → `fda-quality-expert`
- FDA-34 (Compliance disclaimer)

### From `voltagent-lang:python-pro` → `fda-quality-expert`
- FDA-32 (Atomic file operations - data integrity concern)

### From `voltagent-qa-sec:code-reviewer` → `fda-software-ai-expert`
- FDA-31 (Bare except clauses - software quality)
- FDA-30 (Silent except...pass - software quality)

### From `voltagent-qa-sec:test-automator` → `fda-software-ai-expert`
- FDA-29 (No tests for lib/ modules - V&V)
- FDA-28 (No tests for scripts - V&V)

### From `voltagent-qa-sec:qa-expert` → `fda-software-ai-expert`
- FDA-22 (TESTING_SPEC implementation - validation)

### From `voltagent-qa-sec:security-auditor` → `fda-quality-expert`
- FDA-71 (Cache integrity - data integrity per 21 CFR Part 11)
- FDA-25 (Input validation - Part 11 compliance)

### From `fda-510k-submission-outline` → `fda-regulatory-strategy-expert`
- FDA-23 (eSTAR XML validation - submission readiness)

---

## Success Metrics

For each expert built, measure:
- **Issues resolved:** Track completion rate for assigned issues
- **Time savings:** Measure regulatory professional time saved
- **Accuracy:** >95% alignment with FDA expectations
- **User satisfaction:** Regulatory professional feedback

---

## Next Steps

1. ✅ Start with `fda-quality-expert` (highest priority, 18 issues)
2. Build comprehensive SKILL.md with:
   - 20+ years FDA QMS review experience profile
   - 21 CFR 820 expertise
   - ISO 13485 knowledge
   - Design control workflows
   - Common deficiency patterns
3. Re-assign quality/compliance issues
4. Validate with 5+ historical submissions
5. Move to `fda-software-ai-expert`

---

**Status:** ANALYSIS COMPLETE - Ready to build fda-quality-expert
**Priority:** URGENT - 3 URGENT issues waiting for this expert
