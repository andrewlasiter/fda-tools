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