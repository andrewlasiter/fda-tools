# Changelog

## [5.16.0] - 2026-02-09

### Added — Sprint 4 Remediation (42 items from 8-agent review)

**Sprint 4A — Numbering & Consistency:**
- Fixed section numbering across export.md and assemble.md (CamelCase alignment)
- Restructured openfda-data-dictionary.md (field-centric to endpoint-centric format)
- Updated all standalone "21 CFR 820" references to include QMSR cross-reference
- Removed duplicate recall query in safety.md
- Clear score labeling in extraction-analyzer.md (above-80/below-80 labels aligned)
- Added missing Section 02 (CoverSheet/FDA 3514) to export.md section_map

**Sprint 4B — XML & eSTAR Completeness:**
- Added missing XML section builders for Financial Cert (Section 05) and Human Factors (Section 17) in estar_xml.py
- eSTAR mandatory section completeness check in review-simulator.md (Sections 01-07,09,15 always required)
- Attachment management: `--attach FILE` flag for assemble.md and export.md
- estar-structure.md XML field paths for Sections 05 and 17

**Sprint 4C — Script & Pipeline Improvements:**
- Upgraded predicate_extractor.py: DEN number extraction, consistent CSV columns, ijson fallback
- Context-aware OCR corrections (validate against FDA database before applying)
- data-pipeline.md configurable script references (no hardcoded paths)

**Sprint 4D — Agent Enhancements:**
- Predicate legal status verification: WITHDRAWN and ENFORCEMENT_ACTION flags in review.md, propose.md, lineage.md
- Pre-Sub Planner command orchestration: /fda:inspections, /fda:warnings, /fda:trials
- Labeling Reviewer specialist template in review-simulator.md (21 CFR 801, IFU content, format compliance, UDI)
- Q-Sub type differentiation: Formal Meeting, Written Feedback Only, Information, Pre-IDE
- Progress checkpoints (`[1/N]` format) in all 7 agents
- 3-tier guidance trigger reference in review-simulator.md
- Commands You Orchestrate table in submission-writer.md

**Sprint 4E — User Workflow:**
- Exact binomial method in sample size calculator for proportions near 0/1 (Clopper-Pearson)
- Draft revision workflow: `--revise` flag with USER EDIT marker preservation
- N/A section handling: `--na` flag with rationale templates for all applicable sections
- Portfolio timeline planning: Gantt-style view, `--set-target`, FDA review timeline reference
- PubMed API reference expanded: efetch XML parsing, elink endpoint, publication type evidence levels, filter combinations
- Literature search caching: `--offline` mode, `--refresh` flag, 7-day cache in project directory
- Readiness score (SRI) calculation: 6-component scoring (RTA/predicate/SE/testing/deficiency/documentation)

### Tests
- 193 new tests across 5 sprint test files (4A: 37, 4B: 37, 4C: 32, 4D: 56, 4E: 68, less overlap with existing)
- Total: 1,681 passing (offline), 56 API tests deselected
- Sprint 4F deferred to v5.17+

## [5.15.0] - 2026-02-08

### Changed — Guidance Matching Accuracy Overhaul
- 3-tier guidance trigger system: API flags (Tier 1) → word-boundary keywords (Tier 2) → classification heuristics (Tier 3)
- AccessGUDID sterilization, MRI safety, and latex queries (Step 1.5 in guidance.md)
- Negation-aware `kw_match()` — skips matches preceded by "not", "non-", "without"
- 6 new cross-cutting guidance categories: 3D printing, animal-derived, home use, pediatric, latex, electrical
- Expanded keyword lists — eliminated all 2-3 character ambiguous keywords ("ai" → "artificial intelligence", "rf" → "rf wireless", etc.)
- Word-boundary regex replaces substring matching in guidance.md and research.md

### Changed — Sprint 1 Agent Fixes
- AskUserQuestion added to all 7 agents' tool lists
- Scoring rubric aligned to `confidence-scoring.md` across review-simulator and extraction-analyzer
- RTA checklist expanded from 7 to 16 items (8 administrative + 8 content completeness)
- submission-writer expanded from 16 to 18 draft sections
- Draft file output: `draft_*.md` flat files in project root (removed `drafts/` subdirectory convention)
- data-pipeline-manager paths made configurable via settings
- presub-planner command map added for Pre-Sub → pipeline integration
- All version strings updated to v5.15.0

### Fixed — Sprint 2 (7-Agent Self-Review Remediation)
- `export.md` ZIP section map: added 4 missing draftable sections (predicate-justification, testing-rationale, doc, human-factors)
- `draft-templates.md` title corrected from "16" to "18" sections; added full templates for device-description, se-discussion, performance-summary, predicate-justification, testing-rationale
- `predicate_extractor.py` error_log.txt now writes to output directory instead of CWD
- `extraction-analyzer.md` CSV column description corrected (no Document Type column; includes Reference Device columns)
- `extraction-analyzer.md` score label fixed: below-20 threshold labeled "Reject" (was "Weak")
- `references/` directory synced with `skills/fda-510k-knowledge/references/` (34 missing files copied)
- `estar_xml.py` XML generation expanded to 18 sections (added Standards/DoC, Human Factors)
- `review-simulator.md` added specialist templates for Human Factors, Clinical, MRI Safety
- `safety.md` added WebSearch to allowed-tools
- `data-pipeline.md` and `gap-analysis.md` hardcoded WSL paths replaced with settings-based resolution
- `CHANGELOG.md` added entries for versions 5.8.0 through 5.15.0 (was missing 8 versions)

### Added — Testing
- 107 new accuracy tests in `test_guidance_accuracy.py`: false positive resistance (20), false negative resistance (20), API flag priority (10), device scenarios (15), keyword matching (42)
- 1,526 total tests (1,488 offline + 38 API)

## [5.14.0] - 2026-02-08

### Changed — Full Functional Audit & Remediation
- allowed-tools fixes: AskUserQuestion added to review, compare-se; Write added to safety, validate, summarize, analyze, consistency
- SKILL.md updated: 38 commands, 40 references, 7 agents, workflow guide
- Agent cold-start prerequisites documented (what data must exist before agent runs)
- submission-writer/submission-assembler deduplication (clear separation of drafting vs assembly roles)
- review-simulator scoring rubric aligned to confidence-scoring.md
- Cybersecurity USB keyword fix (false positive on "USB" in non-cybersecurity context)

### Added — Testing
- 105 new functional tests in `test_functional_e2e.py`
- 1,419 total tests (1,363 offline + 56 API)

## [5.13.0] - 2026-02-08

### Added — E2E Testing & Agent Architecture
- 3 new agents: research-intelligence, submission-assembler, data-pipeline-manager
- research-intelligence: orchestrates `/fda:research`, `/fda:safety`, `/fda:guidance`, `/fda:literature` for comprehensive regulatory intelligence reports
- submission-assembler: orchestrates `/fda:draft`, `/fda:consistency`, `/fda:assemble` for complete submission package assembly
- data-pipeline-manager: orchestrates `/fda:gap-analysis`, `/fda:data-pipeline`, `/fda:extract` for data corpus maintenance

### Added — Testing
- 360+ new tests: command coverage, agent structural validation, E2E workflow tests, API consistency tests
- `test_agents.py` — 7 agent structural tests (frontmatter, tools, naming, content)
- `test_e2e_workflows.py` — End-to-end pipeline workflow tests
- 1,314 total tests (1,258 offline + 56 API)

## [5.12.0] - 2026-02-08

### Added — FDA Warning Letters & Enforcement
- `/fda:warnings` — Search FDA warning letters by company, product code, or keyword with GMP violation analysis, risk scoring, and QMSR transition guidance
- Warning letter search via FDA Compliance Actions API
- GMP violation pattern analysis with regulatory trend detection
- Risk scoring framework for warning letter findings
- QMSR transition impact assessment for each finding

### Added — Testing
- `test_warnings.py` — 45 new tests for warning letter search, risk scoring, QMSR mapping
- 954 total tests

## [5.11.0] - 2026-02-08

### Added — Curated CDRH Guidance Index
- `references/fda-guidance-index.md` — Curated regulation-to-guidance mapping for 10+ device categories
- Covers: cardiovascular, orthopedic, neurological, IVD, ophthalmic, dental, general hospital, SaMD, combination products, home use
- FY2026 guidance agenda priorities
- Cross-cutting guidance documents with applicability criteria

### Added — Testing
- 909 total tests

## [5.10.0] - 2026-02-08

### Added — ClinicalTrials.gov API v2
- `/fda:trials` — Search device clinical studies via ClinicalTrials.gov v2 API with AREA syntax
- Study search by device name, product code, sponsor, or NCT number
- Study parsing: phase, status, enrollment, endpoints, results availability
- `references/clinicaltrials-api.md` — ClinicalTrials.gov v2 API reference

### Added — Testing
- `test_clinical_trials.py` — 38 new tests for study search, AREA syntax, parsing
- 880 total tests

## [5.9.0] - 2026-02-08

### Added — AccessGUDID v3 API
- Enhanced `/fda:udi` — AccessGUDID v3 API with device history, SNOMED CT codes, UDI barcode parsing, implantable device list
- Device history tracking across GUDID versions
- SNOMED CT clinical terminology mapping
- UDI-DI and UDI-PI barcode parsing
- `references/accessgudid-api.md` — AccessGUDID v3 API reference

### Added — Testing
- `test_accessgudid.py` — 42 new tests for GUDID lookup, history, SNOMED, barcode parsing
- 842 total tests

## [5.8.0] - 2026-02-08

### Added — FDA Data Dashboard API
- `/fda:inspections` — Query FDA Data Dashboard for inspections, citations, compliance actions, and import refusals
- Inspection history search by firm, product code, or date range
- Citation and 483 observation analysis
- Compliance action tracking (warning letters, consent decrees, injunctions)
- Import refusal analysis with violation patterns
- `references/fda-dashboard-api.md` — Data Dashboard API reference

### Added — Testing
- `test_inspections.py` — 48 new tests for inspections, citations, compliance actions
- 800 total tests

## [5.7.0] - 2026-02-08

### Added — Data Maintenance Pipeline
- `/fda:data-pipeline` — 4-step data maintenance pipeline: gap analysis → download missing PDFs → extract predicates → merge results
- Wraps `pipeline.py` orchestrator with subcommands: `status`, `analyze`, `download`, `extract`, `merge`, `run`
- Supports `--years`, `--product-codes`, `--dry-run`, `--incremental`, `--delay`, `--workers` flags
- Distinguishes from regulatory pipeline (`/fda:pipeline`) — this manages the raw data corpus

### Added — Testing
- 37 new tests in `test_gap_analysis.py`:
  - 13 tests for gap-analysis.md command structure
  - 10 tests for data-pipeline.md command structure
  - 6 tests for bundled gap_analysis.py script integrity
  - 4 E2E tests with synthetic PMN data (manifest output, product code filtering, year parsing, prefix derivation)
  - 4 tests for plugin metadata (version, command count)
- 712 total tests (670 offline + 42 API), up from 679

### Changed
- GitHub repository renamed from `fda-predicate-assistant-plugin` to `fda-predicate-assistant`
- Updated all install instructions, plugin.json repository URL, and marketplace configuration

## [5.6.0] - 2026-02-08

### Added — Gap Analysis
- `/fda:gap-analysis` — 3-way cross-reference of FDA PMN database, existing extraction CSV, and downloaded PDFs to identify missing K-numbers
- Bundled `scripts/gap_analysis.py` with full argparse CLI: `--years`, `--prefixes`, `--product-codes`, `--baseline`, `--pdf-dir`, `--output`, `--pmn-files`
- Year-to-prefix derivation (e.g., 2024 → K24) and year range parsing (e.g., `2020-2023,2025`)
- Professional CLI output with product code breakdown, PMN database metrics, and next steps

## [5.5.0] - 2026-02-08

### Added — 3-Tier Section Detection System
- `references/section-patterns.md` rewritten as canonical 3-tier system (413 lines):
  - **Tier 1: Regex** — 13 universal + 5 device-type-specific deterministic patterns
  - **Tier 2: OCR-Tolerant** — Substitution table (11 mappings: `1→I/l`, `0→O`, `5→S`, `$→S`, `7→T`, `3→E`, `8→B`, `|→I/l`, `rn→m`, spurious spaces), 12 calibration examples, max 2 corrections per heading
  - **Tier 3: LLM Semantic** — Classification signal table (12 sections, 2+ signals in 200-word window), non-standard heading map (34 EU/novel terms → canonical sections)
- Consolidated two divergent copies of section-patterns.md into one canonical source; skill copy replaced with redirect
- All 7 consuming commands updated to reference 3-tier system: summarize, research, review, compare-se, lineage, presub, propose
- Inline pattern copies removed from summarize.md (10 patterns) and research.md (7-entry Python dict)
- Sync comments + Tier 2/3 fallback notes added to review.md and research.md SE header regexes
- Context-specific notes: OCR for older PDFs (lineage, compare-se), EU terminology (presub)

### Added — openFDA Feature Expansion
- Full openFDA API feature utilization: `sort`, `skip` (pagination), `_count` (aggregation buckets), OR-batched multi-value queries, wildcard search, field-specific queries
- First-run API key onboarding: detects missing key and offers guided setup via `/fda:configure --setup-key`
- `references/openfda-data-dictionary.md` — Field reference for all 7 Device API endpoints (115+ fields)
- Enhanced `fda_api_client.py` with `sort` and `skip` parameters, `count_field()` method for aggregations, `batch_or_query()` for multi-value searches

### Added — Testing
- 30 new tests in `test_regex_patterns.py`: Tier 2 OCR correction (12 parametrized), Tier 3 heading map (14), Tier 3 content signals (3), helper functions (`apply_ocr_corrections`, `count_section_signals`)
- `test_openfda_features.py` — 59 new tests for sort/skip/count/OR-batch/wildcard/enforcement features
- `test_api_onboarding.py` — 19 new tests for first-run detection, key validation, settings persistence
- 679 total tests (633 offline + 46 API), up from 533

### Fixed
- URL encoding bug in API contract tests: `+AND+`/`+OR+` operators were double-encoded by `urllib.parse.quote`

## [5.4.0] - 2026-02-07

### Added — CDRH Portal & eSTAR Template Selection
- `references/cdrh-portal.md` — CDRH Portal submission guide: portal URL, file size limits (4 GB total / 1 GB per attachment), CDRH vs CBER routing, processing timeline, official correspondent rules, oversized file fallback, support contacts
- eSTAR template selection matrix in `estar-structure.md` — which template (nIVD v6, IVD v6, PreSTAR v2) for which submission type, with OMB control numbers
- Mandatory eSTAR dates: 510(k) Oct 1 2023, De Novo Oct 1 2025
- QMSR alignment note: Feb 2 2026 nIVD/IVD templates align with new Quality Management System Regulation
- Technical requirements: Adobe Acrobat Pro 2017+ requirement, file prep guidelines
- "Submit to FDA" next steps in `/fda:export` and `/fda:assemble` with portal URL and pre-upload checklist
- Template selection guide and QMSR note in `/fda:import`
- CDRH Portal cross-references in `ectd-overview.md` with De Novo mandatory date and PMA voluntary eSTAR
- 533 offline tests (up from 499), 38 API tests

## [5.3.0] - 2026-02-07

### Added — Tranche 7: FDA Review Simulation
- `/fda:pre-check` — Simulates an FDA review team's evaluation of a 510(k) submission: RTA checklist screening, deficiency identification across all review disciplines, and submission readiness score
- `review-simulator` agent — Autonomous multi-perspective FDA review simulation: reads all project files, downloads missing predicate data, simulates each reviewer's evaluation independently, cross-references findings, and generates a detailed readiness assessment
- `references/cdrh-review-structure.md` — CDRH review structure reference, OHT mapping, deficiency templates
- 499 offline tests (up from 363), 38 API tests

## [5.2.0] - 2026-02-07

### Added — Tranche 6: Manual Predicate Proposal & Deep Analysis
- `/fda:propose` — Manually propose predicate and reference devices for a 510(k) submission: validates against openFDA, scores confidence, compares IFU, writes review.json
- `/fda:presub` Section 4.2 expanded to 7 subsections for deep predicate analysis: selection rationale, comparison methodology, key similarities, key differences, technological evolution, clinical equivalence, literature support
- Reference devices tracked in review.json alongside predicates

## [5.1.0] - 2026-02-07

### Added — Tranche 5: Competitive Parity
- BOM/materials tracking in `/fda:compare-se` with biocompatibility difference flagging
- eCTD reference note in `/fda:export` (clarifies eSTAR is required for 510(k), not eCTD)
- Artwork management in `/fda:assemble` with file format manifest and Section 09 labeling integration
- `/fda:draft human-factors` — Human factors section (IEC 62366-1) with use environment, user profiles, critical tasks, and summative testing table
- Complaint handling template in `/fda:safety` with MDR reportability assessment and complaint categories

## [5.0.0] - 2026-02-07

### Added — Tranche 4: Templates & Calculators
- `/fda:calc` — Regulatory calculators: shelf life (ASTM F1980 accelerated aging), sample size (statistical), and sterilization dose
- `/fda:draft doc` — Declaration of Conformity template generation
- `/fda:draft` risk management section — ISO 14971 risk management framework with hazard analysis templates
- DHF checklist in `/fda:assemble` — Design History File completeness verification
- Clinical study guidance in `/fda:presub` — clinical data requirements and study design recommendations

## [4.9.0] - 2026-02-07

### Added — Tranche 3: Extended Capabilities
- `/fda:udi` — UDI/GUDID lookup from openFDA: search by device identifier, product code, company, or brand name
- AI/ML trends analysis in `/fda:research` — tracks AI/ML-enabled device clearances and technology evolution
- FDA correspondence tracking in `/fda:presub` — references and integrates prior FDA interactions

## [4.8.0] - 2026-02-07

### Added — Tranche 2: Monitoring & Analytics
- Automated alerts in `/fda:monitor` — configurable notifications for new clearances, recalls, and MAUDE events matching watched product codes
- Standards supersession checking in `/fda:standards` — flags outdated standards and identifies current replacements
- Clearance timeline analytics in `/fda:research` — historical clearance trends, review time analysis, seasonal patterns

## [4.7.0] - 2026-02-06

### Added — Tranche 1: Intelligence Expansion
- `/fda:standards` — Look up FDA Recognized Consensus Standards by product code, standard number, or keyword with currency checking
- PMA/De Novo search in `/fda:validate` and `/fda:research` — expanded beyond 510(k) to include PMA approvals and De Novo classifications
- Interactive 510(k) search mode in `/fda:validate` — search by applicant, device name, or product code with results filtering

## [4.6.0] - 2026-02-06

### Added — Documentation & Polish
- `docs/WORKFLOWS.md` — 3 golden-path workflows: Full 510(k) from scratch (10 steps), Import & modify existing eSTAR (7 steps), Pre-Sub preparation (6 steps)
- `docs/EXAMPLES.md` — Per-device-type command examples for CGM (MDS), wound dressing (KGN), orthopedic implant (OVE), cardiovascular (DQY), SaMD (QAS)
- README.md updated with troubleshooting table, badges (29 commands, 3 agents, 139+ tests), and links to docs/

## [4.5.1] - 2026-02-06

### Added — Error Handling & Caching
- `scripts/fda_api_client.py` — Centralized API client with LRU caching (7-day TTL), exponential backoff retry (3 attempts), rate limit handling (HTTP 429), and degraded mode responses
- `references/error-handling-patterns.md` — 6 standardized error categories, degraded mode specification, standard error footer format
- `/fda:configure --cache-stats` — Show API cache hit/miss/size statistics
- `/fda:configure --clear-cache [api|pdf|guidance|all]` — Clear cached data by category

## [4.5.0] - 2026-02-06

### Added — Agents & Autonomous Workflows
- `submission-writer` agent — Autonomous 510(k) drafting: data inventory → sequential 16-section drafting → consistency validation → eSTAR assembly → readiness scoring
- `presub-planner` agent — Autonomous Pre-Sub preparation: research → guidance → safety → literature → Pre-Sub generation → quality check
- `extraction-analyzer` enhanced with Step 7 (auto-triage via confidence scoring) and Step 8 (guidance lookup for accepted predicates with gap analysis)

## [4.4.0] - 2026-02-06

### Added — Testing & CI
- `tests/test_knumber_extraction.py` — 15+ tests for K/P/DEN/N number regex, OCR error detection, sample text extraction
- `tests/test_regex_patterns.py` — 80+ parametrized tests for all 11 section detection patterns
- `tests/test_estar_parser.py` — 20+ tests for XML escaping, field mapping, K-number pattern, section detection (skipped if pikepdf/lxml not installed)
- `tests/test_api_contracts.py` — 10+ tests for openFDA API response shapes (marked `@pytest.mark.api`, run only on push)
- `.github/workflows/test.yml` — GitHub Actions CI: Python 3.9-3.11 matrix, offline tests on PR, API tests on push
- `pytest.ini` — Test configuration with custom `api` marker

### Fixed
- Clinical section regex `studies?` → `stud(?:y|ies)` to match singular "Clinical Study"

## [4.3.1] - 2026-02-06

### Changed — Enhanced Pre-Sub Pipeline
- `/fda:presub` expanded from 7 to 11 sections:
  - Section 7: Regulatory Background (clearance history, clinical need, guidance landscape)
  - Section 8: Preliminary Data Summary (completed tests, literature, prior submissions)
  - Section 9: Safety Intelligence (MAUDE events, recall history, severity distribution)
  - Section 10: Supporting Data (renumbered from Section 7)
  - Section 11: Meeting Logistics (timeline, format, agenda, attendee list, 75-day deadline calculation)
- New flags: `--include-literature`, `--include-safety`, `--no-literature`, `--no-safety`
- Auto-integration of safety, literature, and guidance data when available in project directory

## [4.3.0] - 2026-02-06

### Added — Complete 510(k) Writing Pipeline
- `/fda:draft` expanded from 6 to 16 sections: added `labeling`, `sterilization`, `shelf-life`, `biocompatibility`, `software`, `emc-electrical`, `clinical`, `cover-letter`, `truthful-accuracy`, `financial-certification`
- `/fda:export` — Assemble eSTAR package with completeness validation, XML generation, ZIP packaging, and readiness report
- `references/draft-templates.md` — Prose templates for all 16 eSTAR sections with `[TODO:]` placeholders for company-specific data
- `/fda:consistency` enhanced with Check 9 (cross-section draft consistency) and Check 10 (eSTAR import data alignment)

## [4.2.0] - 2026-02-06

### Added — eSTAR Import & Export via XML
- `/fda:import` — Import eSTAR PDF or XML data into project structure (XFA extraction, openFDA validation, structured output)
- `scripts/estar_xml.py` — XFA XML extraction from eSTAR PDFs, XML parsing into project data, XML generation for re-import (~600 lines)
- `references/estar-structure.md` — XFA field mapping (30+ field paths), eSTAR section structure, section-to-draft mapping
- `references/section-patterns.md` — K/P/DEN/N number regex, 11 section heading detection patterns, eSTAR section-to-XML element mapping
- `scripts/templates/README.md` — Placeholder for bundled eSTAR template PDFs (nIVD v6, IVD v6, PreSTAR v2)
- New dependencies: `pikepdf>=8.0.0`, `beautifulsoup4>=4.12.0`, `lxml>=4.9.0`
- `/fda:assemble` updated to pre-populate from `import_data.json` when available
- SKILL.md updated with 29 commands, 26 references, and eSTAR import/export workflow

## [4.1.1] - 2026-02-06

### Fixed
- LYZ product code removed from wound dressing list in section-patterns.md (LYZ is "Vinyl Patient Examination Glove", not a wound dressing)
- plugin.json version aligned from 4.0.0 to 4.1.1
- All command/agent/reference version strings bumped from v4.1.0 to v4.1.1

## [4.1.0] - 2026-02-06

### Changed
- Retired "Level of Concern" references (concept retired by FDA)
- eSTAR mandatory date corrected to October 1, 2023
- `/fda:test-plan` expanded to 11+ device types with device-specific test batteries
- `/fda:pccp` updated with real examples and expanded guidance

### Added
- Basic/Enhanced performance framework for software devices
- MDUFA V fee schedule references
- PubMed E-utilities integration in `/fda:literature`
- Section 524B cybersecurity requirements in `/fda:safety` and `/fda:assemble`
- DEN number handling in `/fda:validate`
- Peer device benchmarking in `/fda:research`
- 5 new skill references: rta-checklist, pubmed-api, special-controls, clinical-data-framework, post-market-requirements

## [4.0.0] - 2026-02-05

### Added — Tier 1: Full Autonomy Fixes
- Guard all `AskUserQuestion` calls behind explicit `--full-auto` conditionals in review, compare-se, presub, submission-outline
- `--infer` fallback chain in compare-se: review.json → output.csv (top 3 by citation) → pdf_data.json → ERROR (never prompts)
- `--full-auto` validation: require `--device-description` and `--intended-use` in presub and submission-outline (with synthesis fallback from query.json + openFDA)
- Placeholder conversion: all surviving `[INSERT: ...]` → `[TODO: Company-specific — ...]` across presub, submission-outline, compare-se
- Pipeline step criticality: Steps 1-2 (extract/review) CRITICAL (halt on failure), Steps 3-7 NON-CRITICAL (continue with DEGRADED warning)
- Pipeline pre-flight validation: writable project dir, valid product code, full-auto requirements, dependency check
- Pipeline argument threading table: explicit mapping of every arg to downstream steps
- Guidance offline fallback: reference-based guidance summary from skill reference data when cache unavailable
- Safety graceful degradation: structured JSON warning with `safety_data_available: false` when API unavailable
- Extract stage defaults: 3 explicit cases, `--full-auto` requires `--project`
- Headless mode in `predicate_extractor.py`: skip manual download messages, one-line error + `sys.exit(2)` on failure
- Audit logging infrastructure: `references/audit-logging.md` schema, JSONL append per command, consolidated `pipeline_audit.json`

### Added — Tier 2: Best-in-Class Feature Parity
- `/fda:lineage` — Predicate citation chain tracer (up to 5 generations, recall checking, Chain Health Score 0-100)
- `/fda:draft` — Regulatory prose generator for 6 submission sections with citation tracking
- `/fda:literature` — PubMed/WebSearch literature review with gap analysis vs guidance requirements
- `/fda:traceability` — Requirements Traceability Matrix (guidance → risks → tests → evidence)
- `/fda:consistency` — Cross-document consistency validation (8 checks, PASS/WARN/FAIL, optional --fix)
- eSTAR auto-population in `/fda:assemble`: Sections 6/7/8/12/15 auto-written from project data (DRAFT/TEMPLATE/READY markers)
- Cybersecurity auto-detection in `/fda:assemble`: threat model, SBOM, and patch plan templates for software/connected devices
- `--watch-standards` in `/fda:monitor`: track FDA recognized consensus standards changes and impact on projects
- `--identify-code` in `/fda:research`: auto-identify product code from device description via openFDA + foiaclass.txt
- Pipeline Step 0: auto-identify product code when `--product-code` not provided but `--device-description` available

### Added — References
- `audit-logging.md` — JSONL audit log schema and pipeline consolidated log format
- `predicate-lineage.md` — Chain Health Scoring methodology and lineage patterns
- `standards-tracking.md` — FDA recognized consensus standards families and alert schema
- `cybersecurity-framework.md` — Cybersecurity documentation framework, templates, and applicable standards

## [3.0.0] - 2026-02-06

### Added — Tier 1: Autonomy
- `--full-auto` and `--auto-threshold` on `/fda:review` for zero-prompt predicate review
- `--infer` flag on guidance, presub, research, submission-outline, and compare-se for auto-detecting product codes from project data
- `--output FILE` on `/fda:summarize` for file persistence
- `--headless` flag on `predicate_extractor.py` with display detection
- TTY-aware prompts in `batchfetch.py` with non-interactive fallback
- `/fda:pipeline` command — full 7-step autonomous pipeline orchestrator
- Placeholder auto-fill: `[INSERT: ...]` → populated from `--device-description` and `--intended-use`
- Default stage selection in `/fda:extract` (no more prompts)

### Added — Tier 2: Best-in-Class Features
- `/fda:monitor` — real-time FDA clearance, recall, and MAUDE event monitoring
- `/fda:pathway` — algorithmic regulatory pathway recommendation (5 pathways scored 0-100)
- `/fda:test-plan` — risk-based testing plan with ISO 14971 gap analysis
- `/fda:assemble` — eSTAR directory structure assembly (17 sections with readiness tracking)
- `/fda:portfolio` — cross-project portfolio dashboard with shared predicate analysis
- `/fda:pccp` — Predetermined Change Control Plan generator for AI/ML devices
- `/fda:ask` — natural language regulatory Q&A
- `--competitor-deep` on `/fda:research` for applicant frequency, technology trends, and market timeline
- Extended confidence scoring (+20 bonus points: chain depth, SE table, applicant similarity, IFU overlap)

### Added — References
- `estar-structure.md` — eSTAR section structure and applicability matrix
- `pathway-decision-tree.md` — regulatory pathway decision flow and scoring weights
- `test-plan-framework.md` — ISO 14971 risk categories and device-type test lists
- `pccp-guidance.md` — FDA PCCP guidance overview and modification categories

## [2.0.0] - 2026-02-05

### Added
- `/fda:review` — interactive predicate review with 5-component confidence scoring
- `/fda:guidance` — FDA guidance lookup with requirements extraction and testing mapping
- `/fda:presub` — Pre-Submission meeting package generator
- `/fda:submission-outline` — full 510(k) outline with gap analysis
- `confidence-scoring.md` reference with scoring methodology
- `guidance-lookup.md` reference with search strategies
- `submission-structure.md` reference with outline templates

### Changed
- `/fda:extract` now includes safety scan integration
- `/fda:configure` now supports exclusion lists
- `/fda:research` now caches guidance for reuse
- `/fda:compare-se` now integrates with submission outline data
- Marketplace renamed from `local` to `fda-tools`

## [1.2.0] - 2026-02-05

### Added
- Disclaimers and warnings across all user-facing surfaces:
  - README.md: "Important Notices" section (privacy, accuracy, training data, not legal advice)
  - SKILL.md: Always-loaded disclaimer context for regulatory guidance responses
  - research.md: Disclaimer footer in research report output
  - compare-se.md: Disclaimer footer in SE comparison table output
- Section-aware predicate extraction in research command (SE sections weighted 3x)
- [SE]/[Ref] provenance tags on predicate candidates
- Extraction confidence transparency caveat in research output

## [1.1.0] - 2026-02-05

### Changed
- Portable plugin root resolution via `installed_plugins.json` runtime lookup
- Removed hardcoded paths; all data directories default to `~/fda-510k-data/`
- Added SessionStart hook as backup for `FDA_PLUGIN_ROOT` env injection
- Fixed SKILL.md frontmatter to comply with official plugin spec

### Added
- `hooks/hooks.json` with SessionStart hook for `CLAUDE_ENV_FILE` integration
- `hooks/export-plugin-root.sh` for deriving plugin root from script location
- `.gitignore` to exclude `__pycache__/`
- `LICENSE` (MIT)
- `CHANGELOG.md`
- `references/path-resolution.md` with standard resolution patterns

## [1.0.0] - 2026-02-04

### Added
- Initial release with 9 commands: extract, validate, analyze, configure, status, safety, research, compare-se, summarize
- 1 agent: extraction-analyzer
- 1 skill: fda-510k-knowledge with reference docs
- Bundled scripts: `predicate_extractor.py`, `batchfetch.py`, `setup_api_key.py`
- openFDA API integration with configurable API key
- K/P/DEN/N device number regex support
