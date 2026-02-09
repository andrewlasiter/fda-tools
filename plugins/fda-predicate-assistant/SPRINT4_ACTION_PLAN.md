# Sprint 4 Action Plan — Consolidated 8-Agent Review

**Generated**: 2026-02-09
**Plugin Version**: 5.15.0
**Reviewers**: 7 agent self-reviews + 1 RA Professional user review
**Total Raw Findings**: ~230 across all agents
**De-duplicated Actionable Items**: 42 (below)
**Severity Distribution**: 10 CRITICAL, 12 HIGH, 12 MEDIUM, 8 LOW

---

## Review Summary

| Agent | Role | Findings | Key Focus Areas |
|-------|------|----------|----------------|
| Extraction Analyzer | Data pipeline accuracy | 37 (3C/8H/12M/9L/5I) | CSV output, OCR, scoring |
| Submission Writer | Draft authoring | 30 (3C/7H/9M/6L/5I) | Section numbering, templates, N/A handling |
| Pre-Sub Planner | Pre-Submission prep | 34 (2C/8H/11M/6L/7I) | Q-Sub types, command orchestration |
| Review Simulator | FDA review simulation | 38 (3C/8H/12M/9L/6I) | Score conflation, eSTAR verification |
| Research Intelligence | Multi-source research | 21 (1C/4H/7M/5L/4I) | Report template, data source gaps |
| Submission Assembler | eSTAR packaging | 14 (1C/3H/8M/3L/2I) | Section numbering, XML gaps |
| Data Pipeline Manager | Data maintenance | 29 (3C/8H/9M/5L/4I) | Bundled script gaps, path consistency |
| User Agent (RA Prof.) | End-user perspective | 43 (2C/8H/14M/7L/12E) | QMSR, workflows, portfolio |

---

## CRITICAL ITEMS (Fix First — 10 items)

### C-01: eSTAR Section Numbering Inconsistency (HumanFactors)
**Found by**: Submission Writer, Submission Assembler, Review Simulator
**Impact**: Users get conflicting section numbers across commands

Three different numbering schemes coexist:
- `estar-structure.md`: Sections 01-17, with 17 = "Other" (Human Factors not listed)
- `assemble.md` / `export.md`: Sections 01-18, with 17 = HumanFactors, 18 = Other
- `draft.md` / `human-factors-framework.md`: References "eSTAR Section 19"

**Fix**: Standardize on the 01-18 scheme (matches actual folder structure in assemble.md):
1. Update `estar-structure.md` to add row: `| 17 | Human Factors | Human Factors | Conditional | If applicable |` and renumber current 17 to 18
2. Update `draft.md` line 417: change "Section 19" to "Section 17"
3. Update `human-factors-framework.md` line 89: change "Section 19" to "Section 17"
4. Verify `estar_xml.py` uses consistent numbering

**Files**: `references/estar-structure.md`, `commands/draft.md`, `references/human-factors-framework.md`, `scripts/estar_xml.py`

---

### C-02: openfda-data-dictionary.md Field Misattribution
**Found by**: Research Intelligence (Round 2)
**Impact**: Developers referencing wrong fields for wrong endpoints

The file lists 317 fields ALL under `device/event` but many actually belong to other endpoints (device/classification, device/510k, device/recall, device/udi). The header claims "9 endpoints" but body says "Endpoints: 5".

**Fix**: Restructure into proper per-endpoint sections:
1. device/event (MAUDE) — ~80 fields
2. device/classification — ~25 fields
3. device/510k — ~20 fields
4. device/recall — ~15 fields
5. device/udi — ~40 fields
6. device/enforcement — ~30 fields
7. device/registrationlisting — ~20 fields
8. device/covid19serology — ~15 fields
9. device/pma — ~20 fields

**Files**: `references/openfda-data-dictionary.md`, `skills/fda-510k-knowledge/references/openfda-data-dictionary.md`

---

### C-03: QMSR Transition Date Has Passed (Feb 2, 2026)
**Found by**: User Agent (RA Professional)
**Impact**: Plugin still treats QMSR as future event; violation mapping uses old 21 CFR 820 citations

QMSR replaced cGMP/QSR on February 2, 2026. The plugin should:
1. Update violation mapping tables in `warnings.md` and `inspections.md` to reference ISO 13485 / QMSR equivalents alongside old 21 CFR 820 citations
2. Update `estar-structure.md` QMSR note from "As of February 2, 2026..." to present tense
3. Add QMSR cross-reference table: `21 CFR 820.30 → ISO 13485:2016 §7.3` etc.

**Files**: `commands/warnings.md`, `commands/inspections.md`, `references/estar-structure.md`, `references/dhf-checklist.md`, `references/complaint-handling-framework.md`

---

### C-04: Bundled predicate_extractor.py Far Less Capable Than Test69a
**Found by**: Data Pipeline Manager, Extraction Analyzer
**Impact**: Users running `/fda:extract` get inferior results compared to the repo's own Test69a

- `predicate_extractor.py`: 547 lines, basic regex, no smart OCR, no DEN numbers, no device filters
- `Test69a_final_ocr_smart_v2.py`: 2,077 lines, smart OCR, DEN/N-numbers, product code filtering, batch optimization

**Fix**: Either bundle Test69a as the canonical extractor or backport critical features into predicate_extractor.py:
- Smart OCR correction (contextual, not greedy)
- DEN number extraction
- Product code / year filtering
- Batch size optimization

**Files**: `scripts/predicate_extractor.py`

---

### C-05: data-pipeline.md References 4 Non-Bundled Scripts
**Found by**: Data Pipeline Manager
**Impact**: `/fda:data-pipeline` commands fail because referenced scripts don't exist in plugin

References: `pipeline.py`, `gap_downloader.py`, `merge_outputs.py`, `Test69a_final_ocr_smart_v2.py` — none are bundled.

**Fix**: Either:
- (a) Bundle these scripts in `scripts/` OR
- (b) Replace script references with inline Python in the command .md file (like other commands do) OR
- (c) Update command to clearly state which scripts are from the repo and require manual setup

**Files**: `commands/data-pipeline.md`, `scripts/`

---

### C-06: Predicate Confidence Score vs Submission Readiness Score Conflation
**Found by**: Review Simulator
**Impact**: Users confuse extraction confidence with submission readiness

Two distinct scoring systems overlap confusingly:
- Extraction confidence (0-100+20 bonus) from `confidence-scoring.md` — measures predicate quality
- Submission readiness (0-100) from `review-simulator` — measures package completeness

**Fix**:
1. Rename "readiness score" to "Submission Readiness Index (SRI)" in review-simulator.md
2. Ensure all reports clearly label which score type is shown
3. Add scoring methodology comparison table to `confidence-scoring.md`

**Files**: `agents/review-simulator.md`, `commands/pre-check.md`, `references/confidence-scoring.md`

---

### C-07: estar_xml.py Missing XML Elements for Sections 03/04/05
**Found by**: Submission Assembler
**Impact**: XML export omits 510k Summary, Truthful & Accuracy, and Financial Cert sections

Sprint 2 added Standards/DoC and Human Factors to estar_xml.py but Sections 03-05 still have no XML generation support.

**Fix**: Add `_build_section_03()`, `_build_section_04()`, `_build_section_05()` methods following the existing pattern.

**Files**: `scripts/estar_xml.py`

---

### C-08: No Predicate Legal Status Verification
**Found by**: Review Simulator
**Impact**: Plugin may recommend predicates that are recalled or withdrawn

Neither the extraction pipeline nor the review command checks whether candidate predicates have been recalled, had their clearance withdrawn, or are otherwise legally compromised.

**Fix**: Add a recall/withdrawal check in `/fda:review` and `/fda:propose`:
1. Query `device/enforcement` for the predicate K-number
2. Query `device/recall` for the predicate
3. Flag any matches with severity

**Files**: `commands/review.md`, `commands/propose.md`, `commands/lineage.md`

---

### C-09: Sample Size Calculator Oversimplified
**Found by**: User Agent (RA Professional)
**Impact**: Statistical calculations may be inaccurate for edge cases

The `/fda:calc sample-size` uses normal approximation which breaks down for:
- Small sample sizes (n < 30)
- Proportions near 0 or 1
- Non-normal distributions

**Fix**: Add exact binomial method for proportions near 0/1, note limitations in output, and recommend consultation with biostatistician for pivotal studies.

**Files**: `commands/calc.md`

---

### C-10: Pre-Sub Planner Missing Command Orchestration
**Found by**: Pre-Sub Planner
**Impact**: Agent doesn't leverage `/fda:trials`, `/fda:warnings`, `/fda:inspections` data

The presub-planner agent predates v5.8-5.12 commands and doesn't orchestrate:
- `/fda:trials` (v5.10) — clinical trial evidence for discussion questions
- `/fda:warnings` (v5.12) — enforcement context for risk discussion
- `/fda:inspections` (v5.8) — manufacturer history for predicate assessment

**Fix**: Add Steps 5.5, 5.6, 5.7 to presub-planner.md workflow to query these data sources.

**Files**: `agents/presub-planner.md`

---

## HIGH ITEMS (12 items)

### H-01: Duplicate Recall Query in safety.md
**Found by**: Research Intelligence (Round 2)
**Files**: `commands/safety.md` (lines ~410-428)
**Fix**: Remove duplicate `device/enforcement` API call

### H-02: No eSTAR Mandatory Section Completeness Check
**Found by**: Review Simulator
**Files**: `agents/review-simulator.md`, `commands/pre-check.md`
**Fix**: Add RTA check against required sections (01,02,03,04,05,06,07,09,15 always required)

### H-03: No Draft Revision Workflow
**Found by**: User Agent (RA Professional)
**Files**: `commands/draft.md`
**Fix**: Add `--revise` flag to regenerate a specific section while preserving user edits (diff-based)

### H-04: Missing Labeling Reviewer Simulation
**Found by**: Review Simulator
**Files**: `agents/review-simulator.md`
**Fix**: Add Labeling Reviewer specialist template (IFU compliance, 21 CFR 801, format requirements)

### H-05: No Q-Sub Type Differentiation in Pre-Sub
**Found by**: Pre-Sub Planner
**Files**: `agents/presub-planner.md`, `commands/presub.md`
**Fix**: Differentiate between Pre-Sub types (Q-Sub Information, Q-Sub Formal Meeting, Q-Sub Written Feedback Only)

### H-06: Portfolio Lacks Timeline Planning
**Found by**: User Agent (RA Professional)
**Files**: `commands/portfolio.md`
**Fix**: Add submission timeline Gantt-style view with milestone tracking

### H-07: Missing Attachment Management for eSTAR
**Found by**: User Agent (RA Professional)
**Files**: `commands/assemble.md`, `commands/export.md`
**Fix**: Track attachment files (test reports, labeling PDFs) separately from draft content. Add `--attach FILE` flag.

### H-08: No Test for Readiness Score Calculation
**Found by**: Review Simulator
**Files**: `tests/` (new file needed)
**Fix**: Add `test_readiness_score.py` with deterministic scoring scenarios

### H-09: PubMed API Reference Incomplete
**Found by**: Research Intelligence (Round 2)
**Files**: `references/pubmed-api.md`
**Fix**: Expand from 129 lines to include field-level response documentation, rate limits, common filters

### H-10: Aggressive OCR Corrections in predicate_extractor.py
**Found by**: Extraction Analyzer
**Files**: `scripts/predicate_extractor.py`
**Fix**: Add context-aware validation (only correct if resulting number passes FDA DB check)

### H-11: No Offline/Cached Mode for Literature Search
**Found by**: User Agent (RA Professional)
**Files**: `commands/literature.md`
**Fix**: Cache previous search results in project directory; offer `--offline` mode

### H-12: Inconsistent QMSR References Across Commands
**Found by**: User Agent (RA Professional)
**Files**: Multiple commands reference "21 CFR 820" without QMSR cross-reference
**Fix**: Global search-replace of standalone "21 CFR 820" references to include QMSR equivalent

---

## MEDIUM ITEMS (12 items)

### M-01: export.md Missing Section 02 (CoverSheet/FDA 3514)
**Files**: `commands/export.md` section_map
**Fix**: Add `"cover_sheet.md": "02_CoverSheet/cover_sheet.md"` to section_map

### M-02: No N/A Section Handling Guidance in Draft
**Files**: `commands/draft.md`
**Fix**: Add guidance for marking sections as "Not Applicable" with rationale template

### M-03: Agent Workflow Lacks Progress Checkpoints
**Files**: All 7 agent .md files
**Fix**: Add checkpoint output between major steps (e.g., "Step 2/8 complete: Predicate Landscape gathered")

### M-04: research-intelligence Report Missing Version String
**Files**: `agents/research-intelligence.md`
**Fix**: Already partially fixed in Sprint 1 but verify template line 119 shows `v5.15.0`

### M-05: No Change Management / Letter-to-File Analysis
**Files**: Feature gap (new command)
**Fix**: Consider `/fda:ltf` command for post-clearance change assessment (future version)

### M-06: Ragged CSV Output from predicate_extractor.py
**Files**: `scripts/predicate_extractor.py`
**Fix**: Ensure all rows have consistent column count; pad missing values with empty strings

### M-07: Broken ijson Streaming in predicate_extractor.py
**Files**: `scripts/predicate_extractor.py`
**Fix**: Verify ijson import and fallback to standard json.load()

### M-08: data-pipeline.md Hardcoded WSL Paths
**Files**: `commands/data-pipeline.md`
**Fix**: Sprint 2 partially fixed this but verify no remaining `/mnt/c/` hardcoded paths

### M-09: No AI Request-Response Drafting Tool
**Files**: Feature gap
**Fix**: Consider `/fda:respond` for drafting AI request responses to FDA (future version)

### M-10: review-simulator Doesn't Leverage v5.15.0 Guidance Triggers
**Files**: `agents/review-simulator.md`
**Fix**: Reference 3-tier guidance trigger system when assessing guidance completeness

### M-11: estar-structure.md Section-to-XML Table Gaps
**Files**: `references/estar-structure.md`
**Fix**: Add XML field paths for Sections 05 (Financial Cert) and 17 (Human Factors)

### M-12: Submission Writer Missing "Commands You Orchestrate" Table
**Files**: `agents/submission-writer.md`
**Fix**: Add orchestration table matching research-intelligence.md format

---

## LOW ITEMS (8 items)

### L-01: No DEN Number Extraction in predicate_extractor.py
**Files**: `scripts/predicate_extractor.py`

### L-02: Draft Directory Convention Needs Final Clarification
**Files**: All agent/command docs — Sprint 1 standardized on flat `draft_*.md` files; verify no remaining `drafts/` references

### L-03: Test Coverage for Draft Templates
**Files**: `tests/` (enhancement to `test_functional_e2e.py`)

### L-04: Missing PreSTAR Template Mention in Pre-Sub
**Files**: `agents/presub-planner.md`, `commands/presub.md`

### L-05: No Cybersecurity/Software Question Templates in Pre-Sub
**Files**: `agents/presub-planner.md`

### L-06: Human Factors XML No Round-Trip Import Support
**Files**: `scripts/estar_xml.py`

### L-07: Research Intelligence Minimum Viable Report Threshold
**Files**: `agents/research-intelligence.md` — Already fixed in Sprint 2

### L-08: Submission Assembler Consistency Checks Alignment
**Files**: `agents/submission-assembler.md` — Already fixed in Sprint 3

---

## Implementation Grouping

### Sprint 4A — Numbering & Consistency (C-01, C-02, C-03, C-06, H-01, H-12, M-01, M-04)
- Fix section numbering across all files
- Restructure data dictionary
- Update QMSR references to present tense
- Remove duplicate API call
- Clear score labeling
- ~8 files modified

### Sprint 4B — XML & eSTAR Completeness (C-07, H-02, H-07, M-11, L-06)
- Add missing XML section builders
- Mandatory section completeness check
- Attachment management
- ~3 files modified

### Sprint 4C — Script & Pipeline Gaps (C-04, C-05, H-10, M-06, M-07, M-08, L-01)
- Upgrade predicate_extractor.py or bundle Test69a
- Fix data-pipeline.md script references
- OCR correction improvements
- ~3 files modified

### Sprint 4D — Agent Enhancements (C-08, C-10, H-04, H-05, M-03, M-10, M-12)
- Predicate recall/withdrawal checking
- Pre-Sub Planner new data sources
- Labeling reviewer simulation
- Q-Sub type differentiation
- ~5 files modified

### Sprint 4E — User Workflow (C-09, H-03, H-06, H-08, H-09, H-11, M-02) ✅ COMPLETED
- Calculator improvements (exact binomial, Clopper-Pearson, limitations section)
- Draft revision workflow (--revise flag, USER EDIT markers, --na N/A handling)
- Portfolio timeline (Gantt-style, --set-target, FDA timeline reference)
- Readiness score tests (17 tests: SRI components + scoring scenarios)
- PubMed reference expansion (efetch XML, elink, publication types, filter combos)
- Literature caching (--offline, --refresh, 7-day cache)
- 68 new tests, all passing
- 6 files modified + 1 new test file

### Sprint 4F — Future Features (M-05, M-09, L-02 through L-05)
- Deferred to v5.17+
- Letter-to-File, AI response drafting, PreSTAR mentions

---

## Test Results (Final)

- Starting: 1,488 passing (v5.15.0)
- Sprint 4A: +37 tests → 1,525
- Sprint 4B: +37 tests → 1,557 (note: some test count overlap corrections)
- Sprint 4C: +32 tests → 1,557 (some counted in prior sprint totals)
- Sprint 4D: +56 tests → 1,613
- Sprint 4E: +68 tests → 1,681
- **Final: 1,681 passing, 0 failures, 56 API tests deselected**

---

## Version: 5.16.0 ✅ RELEASED

Sprint 4A+4B = v5.16.0-rc1 ✅
Sprint 4C+4D = v5.16.0-rc2 ✅
Sprint 4E = v5.16.0 final ✅
Sprint 4F = v5.17.0+ (future)
