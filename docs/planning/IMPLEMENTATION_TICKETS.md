# FDA Tools Plugin - Multi-Pathway Implementation Tickets

**Created:** 2026-02-15
**Status:** Planning Phase
**Priority Order:** URGENT → HIGH → MEDIUM → LOW

---

## 🚨 URGENT PRIORITY (Regulatory Mandatory by 2026-2027)

### TICKET-001: Pre-Sub eSTAR/PreSTAR XML Generation
**Status:** ✅ COMPLETE (v5.25.0 + v5.25.1)
**Priority:** URGENT (Regulatory mandate)
**Effort:** 30-40 hours (actual)
**Assignee:** Completed
**Completed Date:** 2026-02-15

**Description:**
FDA draft guidance (May 2025) proposes mandatory electronic Pre-Sub submissions using PreSTAR template after 1-year transition. All Pre-Subs must use PreSTAR format by 2026-2027.

**Requirements:**
1. Research correct PreSTAR XML structure (FDA 5064 v2.1)
2. Integrate with existing `estar_xml.py` (template exists but not used)
3. Add PreSTAR field mapping to `/fda-tools:presub` command
4. Test with FDA eSubmitter tool validation
5. Add pathway detection (510k/PMA/IDE/De Novo) for correct field population

**Acceptance Criteria:**
- [x] PreSTAR XML generates valid FDA 5064 v2.1 format
- [x] Passes FDA eSubmitter validation
- [x] `/fda-tools:presub` exports PreSTAR XML automatically
- [x] Pathway-specific fields populated correctly
- [x] Backward compatible with existing markdown output
- [x] All 8 critical/high security and compliance issues fixed (v5.25.1)

**Related Files:**
- `plugins/fda-tools/scripts/estar_xml.py` (lines 500-600: PreSTAR template)
- `plugins/fda-tools/commands/presub.md`

**References:**
- FDA Draft Guidance: Electronic Submission Template for Medical Device Q-Submissions (May 2025)
- 21 CFR Part 814.20 (PMA Pre-Sub requirements)
- 21 CFR Part 812 (IDE Pre-Sub requirements)

**Dependencies:** None (critical path)

**Risks:**
- PreSTAR schema may change before final guidance
- FDA eSubmitter tool compatibility issues

---

## ⭐ HIGH PRIORITY (High ROI / Strategic Value)

### TICKET-002: PMA Phase 0 - SSED URL Research & Validation
**Status:** In Progress (validation script failed)
**Priority:** HIGH
**Effort:** 8-12 hours
**Assignee:** TBD
**Due Date:** Q1 2026

**Description:**
Validation script failed with 0/20 SSED downloads (100% HTTP 404). Need to research correct FDA SSED URL construction pattern before investing in PMA Intelligence Module.

**Requirements:**
1. Research FDA accessdata.fda.gov SSED URL patterns
2. Test 10 diverse PMA numbers (2024, 2020, 2015, 2010, 2005, 1995)
3. Identify if URL pattern changed over time
4. Check if authentication/cookies required
5. Investigate alternative sources (approval letters, FDA FOIA)
6. Update `pma_prototype.py` with correct URL logic
7. Re-run validation targeting ≥80% success

**Acceptance Criteria:**
- [ ] SSED download success rate ≥80% (16/20 PMAs)
- [ ] URL construction logic handles year variations
- [ ] Fallback strategy for missing SSEDs documented
- [ ] Updated `pma_prototype.py` passes validation
- [ ] GO/NO-GO recommendation for PMA Phase 1

**Related Files:**
- `plugins/fda-tools/scripts/pma_prototype.py` (lines 80-120: download logic)

**Current Issue:**
```
URL pattern: https://www.accessdata.fda.gov/cdrh_docs/pdf{YY}/{PMA}B.pdf
Result: 20/20 failed with HTTP 404
```

**Investigation Tasks:**
- [ ] Manual test: Try P200024 with different URL patterns
- [ ] Check FDA website for SSED archive structure
- [ ] Test with approval letters instead (.A.pdf suffix)
- [ ] Research if bulk download exists (like 510k pmn*.zip)

**Dependencies:** None (blocks TICKET-003)

**Risks:**
- If <70% success, PMA Intelligence Module not viable
- May require FOIA requests for older PMAs
- Could increase implementation time by 40-60 hours

---

### TICKET-003: PMA Phase 1 - Intelligence Module (CONDITIONAL)
**Status:** Blocked by TICKET-002
**Priority:** HIGH (if Phase 0 validates)
**Effort:** 220-300 hours (8-10 weeks)
**Assignee:** TBD
**Due Date:** Q2-Q3 2026 (IF GO decision)

**Description:**
Build PMA competitive intelligence and clinical trial benchmarking module. Focus on intelligence extraction, NOT full section drafting.

**Phase 1 Components:**
1. **OpenFDA PMA API Client** (30-40 hours)
   - Extend `fda_api_client.py` with enhanced PMA methods
   - Add supplement relationship extraction
   - Batch PMA queries with pagination

2. **SSED PDF Scraper** (40-50 hours)
   - Automated SSED download from FDA database
   - Retry logic and error handling
   - Cache management

3. **SSED Parser** (50-60 hours)
   - Extract clinical trial data (enrollment, design, endpoints, results)
   - Extract device description and indications
   - Extract nonclinical testing summary
   - Handle 1976-2024 format variations

4. **Clinical Trial Intelligence** (40-50 hours)
   - Trial design benchmarking across product code
   - Endpoint comparison analysis
   - Enrollment statistics (mean, median, outliers)

5. **Competitive Intelligence Reports** (40-50 hours)
   - Generate `pma_intelligence_report.md`
   - Generate `clinical_trials_summary.md`
   - Generate enriched `pma_data.csv` (40+ columns)

6. **Pathway Decision Support** (20-30 hours)
   - PMA vs 510(k) recommendation engine
   - Generate `pathway_decision.md` report

7. **Integration** (20-30 hours)
   - Extend `/fda-tools:research` with `--pathway=pma`
   - Add `/fda-tools:pma-intelligence` command
   - BatchFetch integration for PMA PDFs
   - Testing and documentation

**Acceptance Criteria:**
- [ ] SSED download success ≥80% in production
- [ ] SSED parsing accuracy ≥80% (enrollment, trial design, indications)
- [ ] API handles 1,000+ PMA records
- [ ] Reports generate in <5 minutes for 20 PMAs
- [ ] Unit test coverage ≥80%
- [ ] User satisfaction ≥4.0/5.0 (pilot testing)
- [ ] Users report ≥10 hours time savings per PMA
- [ ] ≥2 pilot users convert to paid customers

**GO Criteria (Must meet ALL before starting):**
- ✓ TICKET-002 achieves ≥80% SSED download success
- ✓ ≥3 pilot customers recruited
- ✓ ≥2 customers willing to pay $5,000+/year
- ✓ Clear path to 25+ users within 12 months

**Deliverables:**
- `/fda-tools:pma-intelligence` command
- `/fda-tools:research --pathway=pma` flag
- Enhanced `fda_api_client.py` with PMA methods
- `scripts/pma_scraper.py` (SSED downloader)
- `scripts/pma_parser.py` (SSED extractor)

**Related Files:**
- `PMA_IMPLEMENTATION_PLAN.md` (complete technical blueprint)
- `PMA_REQUIREMENTS_SPECIFICATION.md` (detailed specs)

**Dependencies:**
- TICKET-002 (SSED validation) must PASS
- Market validation (3 pilots recruited)

**Risks:**
- SSED parsing may achieve <80% accuracy → Manual fallback needed
- Clinical data too complex → Limit scope to extraction only
- Market too small (<10 users) → Abort after Phase 1

---

### TICKET-004: Pre-Sub Multi-Pathway Enhancement
**Status:** Not Started
**Priority:** HIGH
**Effort:** 60-80 hours
**Assignee:** TBD
**Due Date:** Q2 2026

**Description:**
Expand `/fda-tools:presub` command to support PMA, IDE, and De Novo pathways with pathway-specific templates and question libraries.

**Requirements:**

**1. Pathway Detection (10 hours)**
- Auto-detect from `device_profile.json` (regulation, device class)
- Add `--pathway` flag override (510k|pma|ide|denovo)
- Decision tree: Class III → PMA likely, investigational → IDE

**2. PMA-Specific Sections (20 hours)**
- Clinical study plan template
- Effectiveness endpoint templates
- Determination Meeting guidance
- Risk analysis (ISO 14971) integration
- IDE status crosswalk
- 21 CFR 814.20 compliance checklist

**3. IDE-Specific Sections (15 hours)**
- Study Risk Determination template (SR vs NSR criteria)
- Clinical protocol outline
- IRB coordination guidance
- Safety monitoring plan template

**4. De Novo-Specific Sections (15 hours)**
- Special controls development guidance
- "Why Not Class III" justification template
- Benefit-risk framework
- Existing De Novo comparison

**5. Meeting Type Support (10 hours)**
- Determination Meeting (PMA pathway selection)
- Study Risk Determination (IDE SR vs NSR)
- Informational Meeting (general questions)
- Add auto-detection logic

**6. Question Template Library (10 hours)**
- 30+ pathway-specific question templates
- Best practices guidance (specific, propose solutions, reference standards)
- Auto-populate from project data

**Acceptance Criteria:**
- [ ] Pathway auto-detection ≥90% accuracy
- [ ] PMA Pre-Sub generates 21 CFR 814.20-compliant package
- [ ] IDE Pre-Sub generates 21 CFR 812-compliant package
- [ ] De Novo Pre-Sub includes special controls framework
- [ ] Meeting type auto-selected based on pathway + questions
- [ ] ≥30 question templates across all pathways
- [ ] Backward compatible with existing 510(k) workflow

**Related Files:**
- `plugins/fda-tools/commands/presub.md` (1,129 lines - needs expansion)
- `/home/linux/fda-presub-requirements-matrix.md` (research document)

**Dependencies:**
- TICKET-001 (PreSTAR XML) for export functionality

**Risks:**
- PMA/IDE templates may require regulatory expertise to validate
- De Novo pathway less common, harder to test

---

## 💡 MEDIUM PRIORITY (Good ROI, Not Urgent)

### TICKET-005: IDE Protocol Templates
**Status:** Not Started
**Priority:** MEDIUM
**Effort:** 40-60 hours
**Assignee:** TBD
**Due Date:** Q3 2026

**Description:**
Create `/fda-tools:ide-protocol` command to generate 21 CFR 812.25-compliant Investigational Plan templates.

**Requirements:**

**1. Investigational Plan Generator (25 hours)**
- Purpose and objectives section
- Study protocol (design, sample size, endpoints)
- Risk analysis (21 CFR 812.3 definitions)
- Device description
- Monitoring procedures
- Labeling and informed consent
- IRB information template

**2. SR vs NSR Determination Tool (10 hours)**
- Decision tree based on 21 CFR 812.3(m) criteria
- Generate justification narrative
- Cite FDA Guidance (Significant Risk vs NSR)

**3. Sample Size Calculator Enhancement (15 hours)**
- Add equivalence design calculations
- Add superiority design calculations
- Add survival analysis (time-to-event)
- Adaptive trial design support

**4. Integration (10 hours)**
- Link to `/fda-tools:trials` (find similar IDE studies)
- Link to `/fda-tools:literature` (evidence review)
- Export as PDF and PreSTAR XML

**Acceptance Criteria:**
- [ ] Generates complete 21 CFR 812.25 Investigational Plan
- [ ] SR vs NSR determination with FDA guidance citations
- [ ] Sample size calculations support equivalence/superiority
- [ ] Integrates with ClinicalTrials.gov search
- [ ] Exports as PDF and PreSTAR XML

**Related Files:**
- `IDE_PATHWAY_SPECIFICATION.md` (research document)
- `plugins/fda-tools/commands/calc.md` (current sample size calculator)

**Dependencies:** TICKET-001 (PreSTAR XML for export)

**Risks:**
- IDE market niche, may have low adoption
- Clinical trial design requires statistical expertise

---

### TICKET-006: PMA Annual Report Generator
**Status:** Not Started
**Priority:** MEDIUM
**Effort:** 30-40 hours
**Assignee:** TBD
**Due Date:** Q3 2026

**Description:**
Create `/fda-tools:pma-annual-report` command to auto-generate 21 CFR 814.84-compliant annual report templates.

**Requirements:**

**1. Core Sections (20 hours)**
- Section 1: Identification of Changes (from supplement history)
- Section 2: Summary and Bibliography (literature search integration)
- Section 3: Regulatory Exception Changes
- Section 4: Device Identifier Tracking (UDI)
- Section 5: Complaint Data Summary (MAUDE integration)
- Section 6: MDR Summary (from openFDA)
- Section 7: Distribution Data (manual entry fields)
- Section 8: Changes Summary

**2. Data Integration (10 hours)**
- Query openFDA for supplement history
- Query MAUDE for complaints
- Query openFDA MDR endpoint
- Link to `/fda-tools:literature` for bibliography

**3. Compliance Checker (5 hours)**
- Verify all 8 sections present
- Flag missing required data
- Calculate days until next annual report

**4. Export (5 hours)**
- Generate PDF
- Generate eCopy-compliant format

**Acceptance Criteria:**
- [ ] Generates complete 21 CFR 814.84 annual report
- [ ] Auto-populates supplement history from openFDA
- [ ] Integrates MAUDE complaint data
- [ ] Integrates MDR summary data
- [ ] Exports as PDF and eCopy format
- [ ] Compliance checker flags missing sections

**Related Files:**
- PMA periodic submissions research (agent output)
- `plugins/fda-tools/scripts/fda_api_client.py` (PMA API methods)

**Dependencies:**
- TICKET-003 (PMA API enhancements)

**Risks:**
- Requires active PMA holder to test (limited user base)

---

### TICKET-007: PMA Supplement Wizard
**Status:** Not Started
**Priority:** MEDIUM
**Effort:** 25-35 hours
**Assignee:** TBD
**Due Date:** Q3 2026

**Description:**
Create `/fda-tools:pma-supplement` command with decision tree to guide users through supplement type selection.

**Requirements:**

**1. Decision Tree Logic (10 hours)**
- Is this a manufacturing change? → 30-Day Notice
- Is this safety-enhancing? → Special Supplement
- Is this FDA pre-identified? → Real-Time Supplement
- Otherwise → 180-Day Supplement

**2. Supplement Templates (15 hours)**
- 180-Day Supplement cover letter and content outline
- Real-Time Supplement template
- 30-Day Notice template (21 CFR 814.39(d))
- Special Supplement template (21 CFR 814.39(e))

**3. Validation (5 hours)**
- Check 21 CFR Part 820 compliance for manufacturing changes
- Flag if change requires clinical data
- Estimate FDA review timeline

**4. Export (5 hours)**
- Generate eCopy format
- Generate cover letter

**Acceptance Criteria:**
- [ ] Decision tree correctly routes to supplement type
- [ ] Generates supplement-specific templates
- [ ] Validates 21 CFR 820 compliance for 30-Day Notices
- [ ] Exports in eCopy format
- [ ] Provides timeline estimate

**Related Files:**
- PMA periodic submissions research (agent output)
- 21 CFR 814.39 (supplement regulations)

**Dependencies:** None

**Risks:**
- Manufacturing change determination may require QA expertise

---

## 📊 LOW PRIORITY (Nice-to-Have / Future)

### TICKET-008: IDE Monitoring Dashboard
**Status:** Not Started
**Priority:** LOW
**Effort:** 50-70 hours
**Assignee:** TBD
**Due Date:** Q4 2026 or later

**Description:**
Create `/fda-tools:ide-monitor` command to track IDE compliance obligations.

**Requirements:**
- UADE (Unanticipated Adverse Device Effect) tracking
- Annual report deadline calculator
- Enrollment monitoring dashboard
- IRB approval expiration tracking
- Study progress reports

**Acceptance Criteria:**
- [ ] Tracks UADE reporting (10-working-day timeline)
- [ ] Alerts for annual report deadlines
- [ ] Dashboard shows enrollment vs target
- [ ] Integrates with ClinicalTrials.gov enrollment data

**Related Files:**
- `IDE_PATHWAY_SPECIFICATION.md`

**Dependencies:** TICKET-005 (IDE protocol)

**Risks:**
- Very niche user base, may not justify investment

---

### TICKET-009: PMA Withdrawal Risk Assessment
**Status:** Not Started
**Priority:** LOW
**Effort:** 30-40 hours
**Assignee:** TBD
**Due Date:** Q4 2026 or later

**Description:**
Create `/fda-tools:pma-risk` command to assess PMA withdrawal risk based on post-market data.

**Requirements:**
- Query MAUDE for adverse event trends
- Check recall database for related devices
- Review annual report compliance history
- Identify non-compliance with PAS requirements
- Generate risk mitigation recommendations

**Acceptance Criteria:**
- [ ] Scores withdrawal risk (0-100)
- [ ] Identifies 7 statutory grounds exposure
- [ ] Trends adverse events vs historical baseline
- [ ] Recommends risk mitigation actions

**Related Files:**
- PMA withdrawal research (agent output, section 6)

**Dependencies:** TICKET-003, TICKET-006

**Risks:**
- Requires significant MAUDE data analysis
- May produce false positives

---

### TICKET-010: PMA Post-Approval Study (PAS) Tracker
**Status:** Not Started
**Priority:** LOW
**Effort:** 40-50 hours
**Assignee:** TBD
**Due Date:** Q4 2026 or later

**Description:**
Create `/fda-tools:pma-pas` command to track post-approval study requirements and compliance.

**Requirements:**
- Scrape FDA PAS database for device's PMA number
- Extract study requirements, timelines, deliverables
- Generate compliance timeline
- Alert for upcoming report deadlines
- Track enrollment status

**Acceptance Criteria:**
- [ ] Queries FDA PAS database successfully
- [ ] Extracts study protocol requirements
- [ ] Generates compliance timeline with milestones
- [ ] Alerts for approaching deadlines

**Related Files:**
- PMA periodic submissions research (section 2: PAS)
- FDA PAS Database: https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfPMA/pma_pas.cfm

**Dependencies:** TICKET-003

**Risks:**
- FDA PAS database may require web scraping (no API)
- Database format may change

---

### TICKET-011: PCCP Multi-Pathway Enhancement
**Status:** Not Started
**Priority:** LOW
**Effort:** 20-30 hours
**Assignee:** TBD
**Due Date:** Q4 2026 or later

**Description:**
Update `/fda-tools:pccp` command to distinguish PMA vs 510(k) PCCP requirements.

**Requirements:**
- Add device class detection (Class III → likely PMA)
- Add PMA-specific PCCP template elements
- Emphasize annual report integration for PMA PCCPs
- Reference Section 515C statutory authority
- Add clinical validation requirements for PMA PCCPs

**Acceptance Criteria:**
- [ ] Auto-detects PMA vs 510(k) pathway
- [ ] Generates PMA-specific PCCP sections
- [ ] Includes annual report documentation requirements
- [ ] Cites Section 515C authority

**Related Files:**
- `plugins/fda-tools/commands/pccp.md` (line 314: PMA differences noted)
- PMA periodic submissions research (section 5: PCCP)

**Dependencies:** None

**Risks:**
- PCCP guidance still evolving (final rule Feb 2026)

---

## 📋 Cross-Cutting Tasks

### TICKET-012: Update Plugin Metadata
**Status:** Not Started
**Priority:** HIGH (after pathway implementations)
**Effort:** 2-4 hours
**Assignee:** TBD
**Due Date:** With each major release

**Requirements:**
- Update `plugin.json` description to mention multi-pathway support
- Update README.md with new commands
- Update CHANGELOG.md with version history
- Add keywords: "pma", "ide", "presub", "multi-pathway"

**Acceptance Criteria:**
- [ ] plugin.json version bump
- [ ] README lists all new commands
- [ ] CHANGELOG documents new features
- [ ] Keywords updated for discoverability

---

### TICKET-013: Documentation & Examples
**Status:** Not Started
**Priority:** MEDIUM (ongoing)
**Effort:** 10-15 hours per pathway
**Assignee:** TBD
**Due Date:** With each pathway release

**Requirements:**
- Create PMA usage examples
- Create IDE usage examples
- Create Pre-Sub multi-pathway examples
- Add troubleshooting guides
- Create video tutorials (optional)

**Acceptance Criteria:**
- [ ] ≥3 examples per pathway
- [ ] Troubleshooting FAQ
- [ ] Integration workflows documented

---

### TICKET-014: AI-Powered Standards Generation Feature
**Status:** Files Created, Not Committed
**Priority:** MEDIUM
**Effort:** 15-20 hours (integration + testing)
**Assignee:** TBD
**Due Date:** Q2 2026

**Description:**
AI-powered FDA-recognized consensus standards identification for 510(k) submissions. Agents analyze device characteristics and generate applicable standards lists with 100% product code coverage.

**Current State:**
- ✅ 3 validation agents created:
  - `agents/standards-ai-analyzer.md` - AI-powered standards analysis
  - `agents/standards-coverage-auditor.md` - Coverage validation
  - `agents/standards-quality-reviewer.md` - Quality review
- ✅ Command created: `commands/generate-standards.md`
- ✅ Validation library: `lib/expert_validator.py`
- ⚠️ Files exist but NOT committed to repository

**Requirements:**
1. **Integration Testing (8 hours)**
   - Test with 10 diverse product codes (DQY, OVE, GEI, QKQ, FRO, etc.)
   - Validate standards recommendations against FDA databases
   - Verify agent coordination and workflow
   - Test edge cases (combination products, Class U, novel devices)

2. **Documentation (4 hours)**
   - Add usage examples to README
   - Create standards generation workflow guide
   - Document agent triggering conditions
   - Add troubleshooting section

3. **Version Release (3 hours)**
   - Commit files to repository
   - Update CHANGELOG.md for v5.27.0
   - Update plugin.json metadata
   - Create release notes

**Acceptance Criteria:**
- [ ] Standards generation tested on ≥10 product codes
- [ ] Agent validation accuracy ≥90%
- [ ] Documentation includes workflow examples
- [ ] Files committed and version released (v5.27.0)
- [ ] Integration with existing `/fda-tools:research` workflow

**Related Files:**
- `agents/standards-ai-analyzer.md`
- `agents/standards-coverage-auditor.md`
- `agents/standards-quality-reviewer.md`
- `commands/generate-standards.md`
- `lib/expert_validator.py`

**Dependencies:** None (can proceed immediately)

**Value:**
- Time savings: 3-5 hours per project (automated standards research)
- Coverage: 100% of FDA product codes supported
- Accuracy: AI-powered validation reduces gaps

---

### TICKET-015: Phase 1-2 Compliance Verification (RA Professional Review)
**Status:** Templates Ready, Execution Pending
**Priority:** HIGH (blocks production use)
**Effort:** 10-13 hours (RA professional + auditor time)
**Assignee:** TBD (requires qualified RA professional)
**Due Date:** Q2 2026

**Description:**
Complete independent verification of Phase 1-2 enrichment features (batchfetch data integrity and intelligence layers) to elevate from "RESEARCH USE ONLY" to "PRODUCTION READY" status.

**Current State:**
- ✅ Code complete: `lib/fda_enrichment.py` (520 lines), `lib/disclaimers.py` (330 lines)
- ✅ Testing complete: 22/22 tests passing (100%)
- ✅ Integrated into batchfetch.md
- ⚠️ Status: CONDITIONAL APPROVAL - RESEARCH USE ONLY
- ⚠️ Blockers: RA-2, RA-4 require qualified RA professional completion

**Requirements:**

**1. RA-2: Genuine Manual Audit (8-10 hours)**
- Execute `GENUINE_MANUAL_AUDIT_TEMPLATE.md` on 5 devices
- Cross-verify API enrichment data against FDA website
- Manual MAUDE search cross-check
- Verify recall history accuracy
- Target: ≥95% pass rate (47/50 audit points)

**2. RA-4: CFR/Guidance Verification (2-3 hours)**
- Complete `CFR_VERIFICATION_WORKSHEET.md` for 3 CFRs:
  - 21 CFR Part 803 (MDR)
  - 21 CFR Part 7 (Recalls)
  - 21 CFR Part 807 (Establishment Registration)
- Complete `GUIDANCE_VERIFICATION_WORKSHEET.md` for 3 guidance docs:
  - MDR Final Guidance (2016)
  - Recalls Guidance (2019)
  - Substantial Equivalence Guidance (2014)
- RA professional sign-off required

**Acceptance Criteria:**
- [ ] Manual audit achieves ≥95% pass rate
- [ ] CFR citations verified by qualified RA professional
- [ ] Guidance currency validated (no superseded documents)
- [ ] RA professional sign-off obtained
- [ ] Status updated: RESEARCH USE ONLY → PRODUCTION READY
- [ ] Documentation updated with verification dates

**Related Files:**
- `lib/fda_enrichment.py`
- `lib/disclaimers.py`
- `GENUINE_MANUAL_AUDIT_TEMPLATE.md` (ready for execution)
- `CFR_VERIFICATION_WORKSHEET.md` (ready for execution)
- `GUIDANCE_VERIFICATION_WORKSHEET.md` (ready for execution)
- `TESTING_COMPLETE_FINAL_SUMMARY.md`

**Dependencies:**
- Requires engagement of qualified RA professional (2-3 hours)
- Requires auditor for manual verification (8-10 hours)

**Risks:**
- If audit pass rate <95%, additional fixes required
- RA professional availability may delay completion

**Value:**
- Unlocks production use of Phase 1-2 enrichment features
- Provides compliance audit trail for regulatory submissions
- Increases user confidence in data integrity

---

### TICKET-016: v5.26.0 Feature Testing & Polish
**Status:** Not Started
**Priority:** MEDIUM
**Effort:** 12-18 hours
**Assignee:** TBD
**Due Date:** Q1 2026

**Description:**
End-to-end testing and polish for v5.26.0 features (automated data updates and multi-device section comparison) to ensure production quality.

**Current State:**
- ✅ v5.26.0 released with 2 new features
- ✅ Commands created: `update-data.md`, `compare-sections.md`
- ✅ Scripts created: `update_manager.py`, `compare_sections.py`
- ✅ Basic import testing passed
- ⚠️ No end-to-end testing with real projects yet

**Requirements:**

**1. Feature 1 Testing: Automated Data Updates (6 hours)**
- Test scan with existing projects (OVE, DQY, GEI)
- Execute dry-run mode on all projects
- Perform actual batch update with rate limiting verification
- Test system cache cleanup
- Verify TTL logic correctness (7-day vs 24-hour)
- Error handling: API failures, network timeouts
- Edge cases: empty projects, all-fresh data

**2. Feature 2 Testing: Section Comparison (6 hours)**
- Build structured cache for ≥3 product codes
- Test section comparison with clinical/biocompatibility sections
- Verify coverage matrix accuracy
- Test standards frequency detection
- Test outlier detection (Z-score analysis)
- Verify CSV and Markdown output formats
- Test with 100+ devices (performance validation)
- Edge cases: sparse data, missing sections

**3. Documentation & Examples (4-6 hours)**
- Create usage examples for both features
- Add troubleshooting guides
- Update README.md with command examples
- Create workflow integration guide
- Add performance benchmarks

**Acceptance Criteria:**
- [ ] Both features tested with ≥3 real projects each
- [ ] Rate limiting verified (500ms = 2 req/sec)
- [ ] Section comparison handles 100+ devices in <10 minutes
- [ ] Error handling graceful for all failure modes
- [ ] Documentation includes ≥3 examples per feature
- [ ] No critical bugs identified
- [ ] Performance meets specifications

**Related Files:**
- `commands/update-data.md`
- `commands/compare-sections.md`
- `scripts/update_manager.py`
- `scripts/compare_sections.py`
- README.md (needs update)

**Dependencies:** None (can proceed immediately)

**Value:**
- Ensures production quality for v5.26.0 features
- Identifies and fixes bugs before widespread use
- Provides users with clear usage examples
- Validates performance specifications

---

## 🚨 CRITICAL FIXES (Expert Panel Findings - TICKET-014 Follow-Up)

### TICKET-017: Standards Generation Accuracy Validation
**Status:** Not Started
**Priority:** URGENT (blocks TICKET-014 production use)
**Effort:** 40-60 hours
**Assignee:** TBD + Independent RA Consultant
**Due Date:** Q2 2026
**Verification Spec:** `plugins/fda-tools/TICKET-017-VERIFICATION-SPEC.md` (80 pages, expert-created by Senior RA Testing Engineer)

**Description:**
Expert panel review identified unverified accuracy claims (spec claims 95%, actual testing found 50% error rate). Must validate tool accuracy before production regulatory use.

**Expert Panel Findings:**
- Testing Engineer: "Found 50% error rate in sample review (6 errors / 12 standards)"
- QA Director: "validation_reports/ directory is EMPTY. No auditor or reviewer agent has EVER run."
- RA Manager: "75-85% accuracy for medium confidence requires manual verification that erases time savings"

**Requirements:**

**1. Independent Validation Study (30 hours)**
- Hire qualified RA consultant to manually review 500 product codes
- Compare tool output to consultant's expert determinations
- Calculate actual accuracy metrics (precision, recall, F1 score)
- Test cases must include:
  - Universal standards (ISO 13485, ISO 14971) - expect 100% accuracy
  - Device-specific standards (expect ≥98% accuracy)
  - Edge cases (combination products, novel materials, Class U) - document limitations

**2. Validation Report (8 hours)**
- Document test methodology
- Publish accuracy metrics by standard category
- Identify systematic errors (e.g., "tool misses ISO 10993-4 for blood-contacting devices")
- Create error taxonomy (over-application vs. under-application)

**3. Fix Systematic Errors (10-15 hours)**
- Address errors found in validation study
- Update standards database with missing critical standards
- Refine keyword matching logic or AI determination rules
- Re-run validation on fixed version (target ≥95% accuracy)

**4. ISO 17025 Lab Review (7 hours, optional)**
- Get accredited testing lab to verify tool outputs for 50 product codes
- Third-party validation adds credibility

**Acceptance Criteria:**
- [ ] ≥500 product codes validated by independent RA consultant
- [ ] Overall accuracy ≥95% for high-confidence standards
- [ ] Overall accuracy ≥85% for medium-confidence standards
- [ ] Published validation report with methodology and metrics
- [ ] Systematic errors identified and fixed
- [ ] Re-validation confirms ≥95% accuracy target met
- [ ] Optional: ISO 17025 lab third-party verification

**Related Files:**
- `agents/standards-ai-analyzer.md` (needs fixes based on validation)
- `agents/standards-coverage-auditor.md` (must actually run in validation)
- `agents/standards-quality-reviewer.md` (must actually run in validation)
- `EXPERT-PANEL-REVIEW-SUMMARY.md` (findings document)

**Dependencies:**
- TICKET-014 (Standards Generation) - builds on existing implementation

**Estimated Cost:**
- RA consultant: 30 hours × $300/hr = $9,000
- ISO 17025 lab (optional): $3,000-5,000

**Risks:**
- If accuracy <90%, tool may not be viable for regulatory use
- May discover database gaps requiring TICKET-018 (full FDA database)

**Value:**
- Provides objective evidence for accuracy claims
- Enables users to trust tool output with documented validation
- Meets QMS requirements (21 CFR 820.70(i) for automated processes)

---

### TICKET-018: Connect to Full FDA Standards Database
**Status:** Not Started
**Priority:** URGENT (blocks production regulatory use)
**Effort:** 50-70 hours
**Assignee:** TBD
**Due Date:** Q2 2026
**Verification Spec:** `plugins/fda-tools/TICKET-018-VERIFICATION-SPEC.md` (2,214 lines, expert-created by Senior RA Database Architect)

**Description:**
Expert panel unanimously identified 96.5% database coverage gap as "regulatory malpractice." Current tool has 54 standards; FDA recognizes ~1,900 standards.

**Expert Panel Findings:**
- Pre-Sub Specialist: "54 vs. 1,900 standards = 3.5% coverage. Missing ASTM F2516 for nitinol could cost $200K-400K in delays."
- Testing Engineer: "For spinal fusion (OVE), tool outputs F1717 but MISSES F136, F2077, ISO 10993-11, ISO 14607 - all SHOWSTOPPERS."
- All 5 experts: Database gap is the #1 critical flaw

**Requirements:**

**1. FDA Database API Integration (25 hours)**
- Use FDA's Recognized Consensus Standards database API
- Endpoint: https://catalog.data.gov/dataset/fda-recognized-consensus-standards
- Download full database (1,550-1,900 standards as of 2026)
- Parse structure:
  - Standard number (e.g., "ISO 10993-1:2018")
  - Title
  - Recognition date
  - Scope/applicability
  - Product code mappings (if available)
  - Withdrawal/superseded status

**2. Daily Update Automation (15 hours)**
- Automated daily check for FDA database updates
- FDA publishes List updates every 2-4 months (Lists 61, 62, 63, etc.)
- Detect new standards, withdrawn standards, updated versions
- Generate change log for user notification
- Alert users when previously-generated determinations may be outdated

**3. Version-Specific Guidance (10 hours)**
- For each standard, track:
  - Which edition is FDA-recognized (e.g., IEC 62304:2006 vs. 2015)
  - Effective recognition date
  - Superseded versions (can still use under grandfather clause)
- Provide guidance: "FDA recognizes IEC 60601-1:2005+A1:2012. 2020 edition exists but not yet recognized."

**4. Database Schema Update (15 hours)**
- Expand from 54-standard JSON to 1,900+ standard relational database
- Add fields:
  - `recognition_date` (when FDA added to list)
  - `withdrawal_date` (if standard removed)
  - `superseded_by` (if newer version exists)
  - `product_code_hints` (FDA's suggested applicability)
  - `guidance_references` (which FDA guidance mentions this standard)

**5. Backward Compatibility (5 hours)**
- Maintain existing 54-standard "core" database for offline use
- Add flag: `is_core_standard` (the 54 most common standards)
- Allow users to filter: "Show me ONLY core standards" vs. "Show all FDA-recognized"

**Acceptance Criteria:**
- [ ] Database contains ≥1,500 FDA-recognized standards (vs. current 54)
- [ ] Automated daily updates from FDA database
- [ ] Version-specific guidance (which edition is recognized)
- [ ] Change log tracks FDA List updates
- [ ] User notification when standards added/removed
- [ ] Backward compatible with existing 54-standard database
- [ ] Performance: Full database query in <2 seconds

**Related Files:**
- `data/fda_standards_database.json` (needs major expansion)
- `agents/standards-ai-analyzer.md` (update to use full database)
- `scripts/fda_api_client.py` (add FDA standards API methods)

**Dependencies:**
- None (can proceed immediately)

**Technical Approach:**
```python
# New API method in fda_api_client.py
def get_fda_recognized_standards():
    """Download full FDA Recognized Consensus Standards database."""
    url = "https://catalog.data.gov/api/3/action/datastore_search"
    params = {
        "resource_id": "fda-recognized-standards-id",
        "limit": 2000
    }
    # Fetch, parse, update local database
```

**Value:**
- Eliminates #1 critical flaw identified by all 5 experts
- Provides complete standards coverage (not just 3.5%)
- Reduces risk of missing critical device-specific standards
- Keeps tool current with FDA's quarterly database updates

---

### TICKET-019: Add Predicate Analysis Integration
**Status:** Not Started
**Priority:** HIGH
**Effort:** 60-80 hours
**Assignee:** TBD
**Due Date:** Q3 2026
**Verification Spec:** `plugins/fda-tools/TICKET-019-VERIFICATION-SPEC.md` (2,468 lines, expert-created by Senior RA Intelligence Analyst)

**Description:**
Expert panel consensus: "Tool shows theoretical standards, but users need to know what ACTUALLY CLEARS for this product code." Integrate with 510(k) database to show predicate-based standards patterns.

**Expert Panel Findings:**
- RA Manager: "In 510(k), you test to match the predicate. Tool doesn't know what predicates tested to."
- Pre-Sub Specialist: "Shift from 'theoretical standards' to 'proven clearance path.'"
- Consultant: "Need device-specific data, not aggregates. Show me what 83% of DQY devices cite."

**Requirements:**

**1. 510(k) Summary PDF Scraping (30 hours)**
- For a given product code, identify recent cleared predicates (last 3-5 years)
- Download 510(k) summary PDFs from FDA database
- Extract Section 17 (Standards Compliance) from PDFs
- Parse standards citations:
  - Standard number (e.g., "ISO 10993-1:2018")
  - Whether tested or literature-based
  - Testing lab used (if mentioned)

**2. Standards Frequency Analysis (20 hours)**
- Aggregate standards across 50-100 predicates per product code
- Calculate:
  - "ISO 10993-1 cited in 46/47 DQY clearances (98%)"
  - "ASTM F2394 cited in 38/47 DQY clearances (81%)"
  - "ISO 10993-4 cited in 12/47 DQY clearances (26%)" - flag as optional
- Identify patterns:
  - Universal standards (used by 95%+ of predicates)
  - Common standards (used by 50-95%)
  - Rare standards (used by <50%) - likely device-specific

**3. Gap Analysis (15 hours)**
- Compare tool's AI determination to predicate patterns
- Flag discrepancies:
  - "AI recommends ISO 10993-11, but only 12% of predicates cite it. VERIFY applicability."
  - "AI didn't include ASTM F2394, but 81% of predicates use it. MISSING STANDARD."
- Generate verification checklist for user

**4. Predicate Comparison Report (15 hours)**
- Generate markdown report:
  ```markdown
  ## Standards Analysis: Product Code DQY

  ### Tool Recommendations vs. Predicate Reality

  | Standard | AI Confidence | Predicate Frequency | Match? | Action |
  |----------|---------------|---------------------|--------|--------|
  | ISO 10993-1 | HIGH | 98% (46/47) | ✅ MATCH | Use |
  | ISO 10993-11 | HIGH | 26% (12/47) | ⚠️ DISCREPANCY | VERIFY device has systemic exposure |
  | ASTM F2394 | Not recommended | 81% (38/47) | ❌ MISSING | ADD to test plan |

  ### Recommended Predicates to Review
  - K240123 (most recent, 2024)
  - K233456 (comprehensive test battery)
  - K232789 (similar device design)
  ```

**Acceptance Criteria:**
- [ ] Scrapes ≥50 predicate 510(k) summaries per product code
- [ ] Extracts standards from Section 17 with ≥90% accuracy
- [ ] Calculates frequency statistics across predicates
- [ ] Generates gap analysis report (AI vs. reality)
- [ ] Identifies 3-5 most relevant predicates for manual review
- [ ] Integrates with existing generate-standards workflow

**Related Files:**
- `commands/generate-standards.md` (add predicate analysis step)
- `scripts/build_structured_cache.py` (extract Section 17 from PDFs)
- New file: `scripts/predicate_standards_analyzer.py`

**Dependencies:**
- TICKET-014 (Standards Generation) - builds on existing workflow
- Optional: TICKET-018 (Full FDA database) for complete coverage

**Technical Challenges:**
- Section 17 format varies across 510(k) summaries (2000-2024)
- Some predicates use non-consensus methods (hard to parse)
- Older predicates may cite superseded standard versions

**Value:**
- Shifts from "theoretical" to "proven clearance path"
- Reduces over-testing (don't include standards 95% of predicates skip)
- Reduces under-testing (flag when tool misses common predicate standards)
- Provides verification framework (user sees AI vs. reality comparison)

---

### TICKET-020: Implement Verification Framework
**Status:** Not Started
**Priority:** URGENT (QMS compliance requirement)
**Effort:** 30-40 hours
**Assignee:** TBD
**Due Date:** Q2 2026
**Verification Spec:** `plugins/fda-tools/TICKET-020-VERIFICATION-SPEC.md` (82 pages, expert-created by Senior QMS Auditor)

**Description:**
Expert panel unanimous: "Tool must REQUIRE user verification to meet 21 CFR 820.30 design control requirements. AI output alone is not objective evidence."

**Expert Panel Findings:**
- QA Director: "During FDA audit, I can't say 'An AI told me.' Need TRACEABLE RATIONALE with design-specific justification."
- RA Manager: "Verification erases time savings, but it's MANDATORY for regulatory use."
- All experts: "Tool should be suggestion engine with mandatory human verification, not decision-maker."

**Requirements:**

**1. Verification Workflow (15 hours)**
- Tool generates DRAFT standards list (as currently implemented)
- User MUST verify each standard against:
  - Current FDA Recognition Database (auto-check: is standard still recognized?)
  - 3-5 predicate 510(k) summaries (manual step: what did predicates use?)
  - Device-specific risk assessment (manual step: does OUR device have this risk?)
  - SME consultation (manual step: biocompatibility expert, electrical safety expert)
- User documents verification in Design History File (DHF)

**2. Verification Checklist Generator (10 hours)**
- For each standard in AI output, generate verification questions:
  ```markdown
  ## ISO 10993-11 Verification Checklist

  ☐ FDA Recognition: ISO 10993-11:2017 is FDA-recognized (List 63, effective 2024-12-22) ✅
  ☐ Predicate Precedent: 46/47 DQY predicates cite this standard (98% frequency) ✅
  ☐ Device Risk Assessment: Our device has:
      ☐ Blood contact? [YES/NO]
      ☐ Contact duration >24 hours? [YES/NO]
      ☐ Systemic exposure pathway? [YES/NO]
      → If ALL YES: ISO 10993-11 is APPLICABLE
  ☐ SME Review: Biocompatibility expert sign-off [NAME/DATE]
  ☐ Rationale Documented: DHF Section 4.2 includes ISO 10993-11 justification [LINK]

  **Verification Status:** ☐ PENDING  ☐ VERIFIED  ☐ NOT APPLICABLE
  ```

**3. Verification Tracking (8 hours)**
- Add verification status field to standards JSON:
  ```json
  {
    "number": "ISO 10993-11:2017",
    "ai_confidence": "HIGH",
    "verification_status": "pending",  // pending | verified | not_applicable
    "verified_by": null,
    "verified_date": null,
    "verification_rationale": null
  }
  ```
- Prevent export/use until verification complete
- Generate verification report for DHF inclusion

**4. Objective Evidence Template (7 hours)**
- Generate 21 CFR 820.30-compliant documentation:
  ```markdown
  ## Design Input: ISO 10993-11 Systemic Toxicity Testing

  **Device Characteristics:**
  - Blood contact: Yes (intravascular catheter)
  - Contact duration: <24 hours (short-term use)
  - Material: Medical-grade silicone + polyurethane

  **Risk Assessment (ISO 14971):**
  - Hazard: Leachable chemicals from polymer → systemic toxicity
  - Risk: Medium (P2 × S3 = Risk 6)
  - Mitigation: Systemic toxicity testing per ISO 10993-11

  **Regulatory Basis:**
  - FDA Recognition: ISO 10993-11:2017 (List 63, effective 2024-12-22)
  - Predicate Precedent: 46/47 DQY predicates (K240123, K233456...) cite ISO 10993-11
  - Guidance: FDA 2016 Biocompatibility Guidance, Section 5.3

  **Determination:** ISO 10993-11 is APPLICABLE and REQUIRED for this device.

  **Approved By:** [RA Manager Name], [Date]
  **SME Review:** [Biocompatibility Expert Name], [Date]
  ```

**Acceptance Criteria:**
- [ ] Verification workflow blocks use of unverified standards lists
- [ ] Checklist generator creates device-specific verification questions
- [ ] Verification status tracked in JSON metadata
- [ ] Objective evidence template meets 21 CFR 820.30 requirements
- [ ] Verification report integrates into Design History File
- [ ] User cannot export/submit without completing verification

**Related Files:**
- `commands/generate-standards.md` (add verification workflow)
- `agents/standards-ai-analyzer.md` (output includes verification checklist)
- New file: `templates/verification_checklist.md`
- New file: `templates/objective_evidence.md`

**Dependencies:**
- TICKET-014 (Standards Generation) - builds on existing implementation
- TICKET-019 (Predicate Analysis) - provides predicate frequency for verification

**Compliance Impact:**
- **Without this ticket:** Tool violates 21 CFR 820.30(c) (no traceability)
- **With this ticket:** Tool provides audit-ready objective evidence

**Value:**
- Meets QMS requirements for design control documentation
- Provides FDA audit trail (not just "AI said so")
- Forces user review (catches AI errors before submission)
- Generates DHF-ready documentation

---

### TICKET-021: Add Test Protocol Context
**Status:** Not Started
**Priority:** HIGH
**Effort:** 40-50 hours
**Assignee:** TBD
**Due Date:** Q3 2026
**Verification Spec:** `plugins/fda-tools/TICKET-021-VERIFICATION-SPEC.md` (1,915 lines, expert-created by Senior Testing Laboratory Manager)

**Description:**
Expert panel (especially Testing Engineer): "Tool provides standard numbers without actionable context. We need sample sizes, lead times, cost estimates, lab recommendations."

**Expert Panel Findings:**
- Testing Engineer: "I need to know which SECTIONS of ISO 10993-1, sample sizes, lead times, accredited labs. Tool provides NONE of this."
- RA Manager: "The LIST is trivial. The PROTOCOL is the value."
- Consultant: "If it generated draft test protocols, I'd pay $5,000/year instead of $1,000."

**Requirements:**

**1. Standard Section Mapping (15 hours)**
- For each standard, identify applicable sections/parts:
  ```json
  {
    "number": "ISO 10993-1:2018",
    "applicable_sections": [
      {
        "section": "5.1",
        "title": "Cytotoxicity",
        "applicability": "ALL devices with patient contact",
        "required_samples": 3,
        "typical_duration": "2-3 weeks"
      },
      {
        "section": "5.2",
        "title": "Sensitization",
        "applicability": "Skin contact devices",
        "required_samples": 10,
        "typical_duration": "4-6 weeks"
      }
    ]
  }
  ```

**2. Sample Size Requirements (8 hours)**
- Add typical sample requirements per standard:
  - ISO 10993-1: 3-6 samples per endpoint
  - ASTM F1717: 6 specimens (static) + 6 specimens (dynamic)
  - IEC 60601-1: 3 production-equivalent units
- Include variability: "3-6 samples (3 for single material, 6 for multi-material)"

**3. Cost Estimation Database (10 hours)**
- Partner with 3-5 testing labs to get cost ranges:
  - ISO 10993-5 (Cytotoxicity): $8K-$12K
  - ISO 10993-11 (Systemic Toxicity): $20K-$35K (long-term study)
  - IEC 60601-1 (Electrical Safety): $25K-$40K (full suite)
  - ASTM F1717 (Spinal Fatigue): $30K-$50K (custom fixtures)
- Display as ranges: "$8K-$12K (low-complexity), $12K-$18K (high-complexity)"

**4. Lead Time Database (5 hours)**
- Typical testing timelines:
  - Cytotoxicity: 2-3 weeks
  - Biocompatibility full panel: 8-12 weeks
  - Electrical safety: 4-6 weeks
  - Mechanical testing: 6-10 weeks (includes fixture design)
  - Sterilization validation: 12-16 weeks (shelf life component)
- Critical path analysis: Identify long-lead tests

**5. Accredited Lab Directory (12 hours)**
- Build database of ISO 17025-accredited testing labs:
  - Biocompatibility: Nelson Labs, WuXi AppTec, Toxikon
  - Electrical safety: TÜV SÜD, UL, Intertek
  - Mechanical testing: Element, SGS, Exponent
- Include: Capabilities, turnaround time, cost tier ($/$$/$$$)

**6. Test Protocol Template Generator (15 hours)**
- Generate draft test protocol for each standard:
  ```markdown
  ## ISO 10993-5 Cytotoxicity Test Protocol

  **Standard:** ISO 10993-5:2009 (In vitro cytotoxicity)

  **Sample Requirements:**
  - 3 production-equivalent samples (worst-case material combination)
  - Surface area: 6 cm² per sample
  - Extraction vehicle: DMEM with 10% FBS
  - Extraction conditions: 37°C for 24 hours

  **Test Method:**
  - Direct contact method (for non-leaching materials)
  - Extract method (for materials with leachables)
  - MTT assay (cell viability endpoint)

  **Acceptance Criteria:**
  - Cell viability ≥70% (Grade 0-1: non-cytotoxic)
  - Controls: Negative (HDPE), Positive (latex with zinc)

  **Recommended Labs:**
  - Nelson Labs (Costa Mesa, CA) - $8K-$10K, 2-week turnaround
  - WuXi AppTec (Suzhou, China) - $6K-$8K, 3-week turnaround

  **Integration with Test Plan:**
  - Critical path dependency: Must complete before ISO 10993-10 (sensitization)
  - Sample sharing: Can use same extracts for ISO 10993-5, -10, -11
  ```

**Acceptance Criteria:**
- [ ] ≥80% of standards have section-level detail (not just standard number)
- [ ] Sample size requirements documented for 50+ common standards
- [ ] Cost estimates (ranges) for 50+ common standards
- [ ] Lead time estimates for 50+ common standards
- [ ] Accredited lab directory with ≥20 testing labs across categories
- [ ] Test protocol templates for top 20 most common standards
- [ ] Integrated into generate-standards workflow

**Related Files:**
- `data/fda_standards_database.json` (expand with protocol details)
- New file: `data/testing_labs_directory.json`
- New file: `templates/test_protocol_templates/`
- `commands/generate-standards.md` (add protocol generation option)

**Dependencies:**
- TICKET-014 (Standards Generation) - builds on existing implementation
- Optional: TICKET-018 (Full FDA database) for complete coverage

**Value:**
- Saves 3-5 hours per device on test protocol development
- Provides actionable test planning (not just standard numbers)
- Reduces testing costs (shows cost ranges, enables lab comparison)
- Enables timeline planning (critical path identification)
- Addresses Testing Engineer's #1 complaint

---

### TICKET-022: Remove Misleading Claims & Add Disclaimers
**Status:** Not Started
**Priority:** URGENT (compliance and ethics requirement)
**Effort:** 8-12 hours
**Assignee:** TBD
**Due Date:** Immediately (Q1 2026)

**Description:**
Expert panel unanimous: "Marketing claims ('AI-Powered,' '95% accuracy,' 'ensure complete testing coverage') are misleading and create liability. Must fix IMMEDIATELY."

**Expert Panel Findings:**
- Testing Engineer: "Spec says 'AI-Powered' but implementation is keyword matching. This is either incompetence or fraud."
- QA Director: "Claiming 'ensures complete testing coverage' when 96% of standards are missing is regulatory malpractice."
- All 5 experts: "False confidence" created by unsubstantiated claims is dangerous

**Requirements:**

**1. Specification Corrections (3 hours)**
- Change: "AI-Powered FDA Standards Generation"
- To: "Knowledge-Based FDA Standards Recommendation Engine"
- Remove: "95% accuracy" (until TICKET-017 validates actual accuracy)
- Remove: "Ensure complete testing coverage" (96% gap makes this false)
- Remove: "Multi-agent validation" (agents never run in current implementation)
- Add: "PRELIMINARY RESEARCH TOOL - REQUIRES EXPERT VERIFICATION"

**2. Command Description Updates (2 hours)**
- Update `commands/generate-standards.md` frontmatter:
  ```yaml
  description: Generate preliminary FDA standards recommendations (REQUIRES EXPERT VERIFICATION)
  ```
- Add warning at top of command:
  ```markdown
  ⚠️ **RESEARCH USE ONLY**
  This tool provides preliminary standards recommendations based on device classification
  and keyword analysis. ALL recommendations MUST be independently verified by a qualified
  regulatory professional before use in FDA submissions.

  **Limitations:**
  - Database coverage: 54 core standards (FDA recognizes ~1,900 total)
  - Accuracy: Not validated (see TICKET-017 for validation status)
  - Device-specific applicability: Cannot account for unique design features
  ```

**3. README.md Disclaimer (2 hours)**
- Add prominent disclaimer before generate-standards documentation:
  ```markdown
  ### ⚠️ IMPORTANT: Research Use Only

  The `/fda-tools:generate-standards` command is a RESEARCH TOOL for preliminary
  standards identification. It is NOT a substitute for:
  - Regulatory professional judgment
  - Device-specific risk assessment
  - Predicate 510(k) analysis
  - FDA guidance interpretation
  - Test lab consultation

  **DO NOT use this tool as the sole basis for:**
  - Design History File standards justification
  - Test protocol selection
  - FDA submission standards claims
  - Pre-Submission meeting preparation

  **Always verify ALL recommendations with:**
  - Current FDA Recognized Consensus Standards database
  - Recent cleared predicate devices (3-5 predicates)
  - Device-specific risk assessment (ISO 14971)
  - Subject matter expert review (biocompatibility, electrical, mechanical)
  - Testing lab consultation
  ```

**4. UI/Output Disclaimers (3 hours)**
- Add disclaimer to every generated JSON file:
  ```json
  {
    "disclaimer": "RESEARCH USE ONLY. This standards determination is preliminary and MUST be independently verified by a qualified regulatory professional. Not validated for FDA submissions. See TICKET-017 for validation status.",
    "limitations": [
      "Database contains 54 core standards (FDA recognizes ~1,900 total)",
      "Product code-level analysis only (cannot account for device-specific design)",
      "Keyword-based determination (not AI-powered as of v5.26.0)",
      "No accuracy validation performed"
    ],
    "required_verification": [
      "Check current FDA Recognized Consensus Standards database",
      "Review 3-5 recent predicate 510(k) summaries",
      "Perform device-specific risk assessment",
      "Obtain subject matter expert review",
      "Consult accredited testing laboratory"
    ]
  }
  ```

**5. CHANGELOG.md Correction (2 hours)**
- Add "IMPORTANT CORRECTION" section for v5.26.0:
  ```markdown
  ### IMPORTANT CORRECTION (2026-02-15)

  Following independent expert panel review, we have identified the following
  inaccuracies in the original v5.26.0 release announcement:

  **CORRECTED CLAIMS:**
  - ❌ "AI-Powered" → ✅ "Knowledge-Based" (keyword matching, not AI as of v5.26.0)
  - ❌ "95% accuracy" → ✅ "Accuracy not validated" (see TICKET-017)
  - ❌ "Ensure complete testing coverage" → ✅ "Preliminary recommendations only"
  - ❌ "Multi-agent validation" → ✅ "Validation framework implemented but not yet executed"

  **CURRENT STATUS:**
  - Tool is RESEARCH USE ONLY until validation complete (TICKET-017)
  - Database contains 54 core standards (3.5% of FDA's ~1,900 recognized standards)
  - All recommendations MUST be independently verified
  - Not approved for FDA submission use without expert review

  **UPCOMING FIXES:**
  - TICKET-017: Independent accuracy validation study
  - TICKET-018: Connect to full FDA database (1,900+ standards)
  - TICKET-020: Implement verification framework for QMS compliance

  We apologize for any confusion and are committed to transparency and accuracy.
  ```

**Acceptance Criteria:**
- [ ] All "AI-Powered" claims replaced with "Knowledge-Based"
- [ ] All "95% accuracy" claims removed or marked "not validated"
- [ ] All "ensure complete coverage" claims removed
- [ ] Prominent disclaimers added to README, command docs, and output files
- [ ] CHANGELOG includes correction notice
- [ ] User-facing documentation emphasizes "RESEARCH USE ONLY"
- [ ] Limitations clearly stated (54 vs. 1,900 standards, no validation)

**Related Files:**
- `GENERATE-STANDARDS-SPEC.md` (major corrections needed)
- `README.md` (add disclaimer section)
- `CHANGELOG.md` (add correction notice)
- `commands/generate-standards.md` (add warning)
- `agents/standards-ai-analyzer.md` (update description)

**Dependencies:**
- None (can proceed immediately - URGENT)

**Compliance Impact:**
- **Without this fix:** Misleading marketing creates legal/ethical liability
- **With this fix:** Honest representation of tool capabilities and limitations

**Value:**
- Protects users from making uninformed regulatory decisions
- Protects developer from liability claims ("you said it was 95% accurate!")
- Sets realistic expectations (research tool, not production solution)
- Maintains professional credibility

---

## 🎯 Success Metrics

### Phase 0 (Validation)
- [x] Research complete (5 agents deployed)
- [ ] PMA SSED validation ≥80% (FAILED: 0/20, needs TICKET-002)
- [ ] 3 pilot customers recruited
- [ ] Pricing validated ($5K/year for PMA)

### Phase 1 (PMA Intelligence)
- [ ] SSED parsing accuracy ≥80%
- [ ] User satisfaction ≥4.0/5.0
- [ ] Time savings ≥10 hours per PMA
- [ ] ≥2 pilots convert to paid

### Phase 2 (Multi-Pathway)
- [ ] Pre-Sub eSTAR/PreSTAR mandatory compliance (2026-2027)
- [ ] ≥25 paid users across all pathways
- [ ] $125K+ ARR
- [ ] 80%+ user retention

---

## 🔄 Implementation Order (Recommended)

**Q1 2026:**
1. ~~TICKET-001: Pre-Sub eSTAR/PreSTAR (30-40 hrs)~~ ✅ COMPLETE (v5.25.0/v5.25.1)
2. TICKET-002: PMA SSED URL Research (8-12 hrs) - CRITICAL
3. TICKET-016: v5.26.0 Testing & Polish (12-18 hrs) - RECOMMENDED
4. Market validation (recruit pilots)
5. GO/NO-GO decision

**Q2 2026:**
6. TICKET-015: Phase 1-2 Compliance Verification (10-13 hrs) - HIGH PRIORITY
7. TICKET-014: Standards Generation (15-20 hrs) - MEDIUM PRIORITY
8. TICKET-004: Pre-Sub Multi-Pathway (60-80 hrs) - HIGH VALUE

**Q2-Q3 2026 (IF PMA GO):**
6. TICKET-003: PMA Intelligence Module (220-300 hrs) - MAJOR INVESTMENT

**Q3 2026:**
7. TICKET-005: IDE Protocol Templates (40-60 hrs) - CONDITIONAL
8. TICKET-006: PMA Annual Report (30-40 hrs) - CONDITIONAL
9. TICKET-007: PMA Supplement Wizard (25-35 hrs) - CONDITIONAL

**Q4 2026:**
10. LOW priority tickets (IDE monitor, PMA risk, PAS tracker)

---

## 📞 Contact & Resources

**Research Documents:**
- `PMA_REQUIREMENTS_SPECIFICATION.md`
- `IDE_PATHWAY_SPECIFICATION.md`
- `/home/linux/fda-presub-requirements-matrix.md`

**Validation Scripts:**
- `scripts/pma_prototype.py`

**Agent Research:**
- Current plugin capabilities analysis (embedded in conversation)
- PMA research (7 documents)
- IDE research (1 document)
- PMA periodic submissions (agent output)
- Pre-Sub requirements (60-page analysis)

---

**Last Updated:** 2026-02-15
**Total Tickets:** 16
**Total Estimated Effort:** 887-1,201 hours (across all pathways)
**Critical Path:** ~~TICKET-001 (PreSTAR)~~ ✅ COMPLETE, TICKET-002 (PMA validation)
**Completed Tickets:** 1/16 (TICKET-001)