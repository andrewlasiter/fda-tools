---
name: fda-510k-knowledge
description: Use when working with the local FDA 510(k) data pipeline, plugin scripts, configured data paths, or openFDA integration details. Also use for quick reference on 510(k) terminology and numbering when needed. For predicate strategy use fda-predicate-assessment; for safety signal analysis use fda-safety-signal-triage; for submission outlines use fda-510k-submission-outline.
---

# FDA 510(k) Regulatory Knowledge

You have expertise in FDA medical device regulations, particularly the 510(k) premarket notification process. You also know how the local data pipeline works and where to find data.

For focused workflows, prefer the specialized skills: `fda-predicate-assessment` for predicate strategy, `fda-safety-signal-triage` for safety/recall analysis, and `fda-510k-submission-outline` for submission structure and RTA readiness.

## Data Pipeline Overview

This project uses a two-stage pipeline for FDA 510(k) predicate analysis:

### Stage 1: BatchFetch

**Interactive Command (Recommended for AI-assisted workflows):**
- **Command:** `/fda-tools:batchfetch`
- **Purpose:** AI-guided filter selection through Claude Code's native interface with preview before download
- **Modes:**
  - `--quick`: Express mode (2 questions: product codes + years)
  - Full interactive: All 7 filter layers with AI recommendations
  - `--full-auto`: Skip all questions, use CLI args only
- **Features:** Embedded reference data, preview with confirmation, project-based organization, query.json metadata
- **Optional Enrichment:** `--enrich` flag adds 18 columns of real FDA API data with Phase 1 data integrity features
- **Best for:** Exploratory research, first-time users, complex filtering, collaborative workflows

**API Enrichment (Optional `--enrich` flag):**
- **Requires:** Free openFDA API key (120K requests/day, sign up at https://open.fda.gov/apis/authentication/)
- **Adds 18 columns (12 core + 6 Phase 1 data integrity):**

  **Core Enrichment (12 columns):**
  - `maude_productcode_5y` — MAUDE events (⚠️ product code level, not device-specific)
  - `maude_trending` — Event trend (increasing/decreasing/stable)
  - `maude_recent_6m` — Events in last 6 months
  - `maude_scope` — Data scope disclaimer (PRODUCT_CODE or UNAVAILABLE)
  - `recalls_total` — Number of recalls (✓ device-specific, accurate)
  - `recall_latest_date` — Most recent recall date
  - `recall_class` — Recall severity (I/II/III)
  - `recall_status` — Recall status (ongoing/completed)
  - `api_validated` — K-number exists in FDA database (Yes/No)
  - `decision_description` — Clearance decision type
  - `expedited_review_flag` — Expedited review status (Y/N)
  - `summary_type` — Public document type (Summary/Statement)

  **Phase 1: Data Integrity (6 columns):**
  - `enrichment_timestamp` — ISO 8601 timestamp of data fetch
  - `api_version` — openFDA API version (v2.1)
  - `data_confidence` — HIGH/MEDIUM/LOW based on completeness
  - `enrichment_quality_score` — 0-100 quality score (completeness, API success, freshness, validation)
  - `cfr_citations` — Comma-separated CFR parts (21 CFR 803, 7, 807)
  - `guidance_refs` — Count of applicable FDA guidance documents

- **Generates 4 files:**
  - `enrichment_report.html` — Recall analysis dashboard with data limitations
  - `quality_report.md` — Quality scoring (0-100), validation summary, confidence distribution
  - `enrichment_metadata.json` — Full provenance tracking (source API, timestamp, confidence per field)
  - `regulatory_context.md` — CFR citations, guidance references, proper use guidelines

- **Time savings:** ~3-4 hours per competitive analysis (automated recall/validation checks)
- **Data integrity:** Every data point traceable to source with timestamp; automated quality validation; CFR/guidance linkage for regulatory compliance
- **RA Professional Features:** Meets stringent RA requirements for data provenance, quality validation, and regulatory citation

**CLI Script (For automation and scripted workflows):**
- **Script:** `$FDA_PLUGIN_ROOT/scripts/batchfetch.py`
- **Purpose:** Direct command-line filtering and download without interactive prompts
- **CLI flags:** `--date-range`, `--years`, `--product-codes`, `--applicants`, `--committees`, `--decision-codes`, `--output-dir`, `--download-dir`, `--data-dir`, `--save-excel`, `--no-download`, `--interactive`
- **Best for:** Repeatable workflows, CI/CD pipelines, batch processing, automation

**Common Outputs (both approaches):**
  - `510k_download.csv` — Full metadata (24 cols base, 42 cols with --enrich including Phase 1)
  - `Applicant_ProductCode_Tables.xlsx` — Analytics workbook (3 sheets)
  - `merged_data.csv` — K-number + up to 6 predicates (7 cols)
  - `query.json` — Filter metadata and results summary (command only)
  - **With `--enrich` flag (Phase 1 Data Integrity):**
    - `enrichment_report.html` — Recall analysis dashboard with data limitations
    - `quality_report.md` — Quality scoring and validation summary
    - `enrichment_metadata.json` — Complete provenance tracking
    - `regulatory_context.md` — CFR citations and guidance references
  - Downloaded PDFs in: `DOWNLOAD_DIR/YEAR/APPLICANT/PRODUCTCODE/TYPE/`

### Stage 2: PredicateExtraction
- **Script:** `$FDA_PLUGIN_ROOT/scripts/predicate_extractor.py`
- **Purpose:** Extract predicate device numbers from PDF documents using text extraction, regex parsing, and OCR error correction
- **CLI flags:** `--directory`, `--use-cache`, `--no-cache`, `--output-dir`, `--data-dir`, `--batch-size`, `--workers`
- **Outputs:**
  - `output.csv` — K-number, ProductCode, Predicate1..PredicateN, ReferenceDevice1..N
  - `supplement.csv` — Devices with supplement suffixes
  - `pdf_data.json` — Cached PDF text keyed by filename
  - `error_log.txt` — Failed PDFs

### Key Data Locations

**All data directories are configurable** via `~/.claude/fda-predicate-assistant.local.md`. Run `/fda:configure --show` to see current paths.

| Data | Default Path | Settings Key |
|------|-------------|-------------|
| Plugin scripts | `$FDA_PLUGIN_ROOT/scripts/` | (bundled with plugin) |
| Projects root | `~/fda-510k-data/projects/` | `projects_dir` |
| 510kBF output | `~/fda-510k-data/batchfetch/` | `batchfetch_dir` |
| Extraction output | `~/fda-510k-data/extraction/` | `extraction_dir` |
| Downloaded PDFs | `~/fda-510k-data/batchfetch/510ks/` | `pdf_storage_dir` |
| FDA database files | `~/fda-510k-data/extraction/` | `data_dir` |
| Dependencies | `$FDA_PLUGIN_ROOT/scripts/requirements.txt` | (bundled with plugin) |

**Before running any command:**
1. **Resolve plugin root** — Run the plugin root resolution snippet from `references/path-resolution.md` to set `$FDA_PLUGIN_ROOT` (reads `~/.claude/plugins/installed_plugins.json`)
2. **Read user settings** — Read `~/.claude/fda-predicate-assistant.local.md` for configured data paths
3. If a path is not set in settings, use the defaults above. If data is not found at the configured path, check the default path before reporting "not found".

When answering questions about specific devices, check these data sources for real information before relying solely on general knowledge.

## Core Concepts

### 510(k) Premarket Notification

A 510(k) is a premarket submission made to FDA to demonstrate that a device is **substantially equivalent** to a legally marketed device (predicate) that is not subject to premarket approval (PMA).

**Key points:**
- Required for most Class II devices and some Class I devices
- Submission must establish substantial equivalence to a predicate
- FDA targets 90 days for review (MDUFA performance goal, not a legal deadline) or 30 days (special 510(k))
- Clearance allows commercial distribution in the US

### Predicate Device

A predicate device is a legally marketed device to which a new device is compared:

**Criteria for valid predicates:**
1. Same intended use as the new device
2. Same technological characteristics, OR
3. Different technology but doesn't raise new safety/effectiveness questions

**Predicate strategies:**
- Single predicate: Most straightforward
- Multiple predicates: Different aspects from different devices
- Split predicate: Intended use from one, technology from another

### Substantial Equivalence

A device is substantially equivalent if:
1. It has the **same intended use** as the predicate, AND
2. It has the **same technological characteristics**, OR
3. Has different technological characteristics but:
   - Information demonstrates equivalent safety and effectiveness
   - Doesn't raise new questions about safety and effectiveness

### Reference Devices

Not all cited devices are predicates. Reference devices may be cited for:
- Comparison data
- Clinical study context
- State-of-the-art discussion
- But NOT for establishing substantial equivalence

## Device Classification

### Class I (Low Risk)
- General controls sufficient
- Examples: bandages, tongue depressors
- Most exempt from 510(k)

### Class II (Moderate Risk)
- General controls + special controls
- Examples: powered wheelchairs, pregnancy tests
- Most require 510(k)

### Class III (High Risk)
- General controls + PMA required
- Examples: heart valves, pacemakers
- 510(k) not applicable (usually)

## Device Numbering

### K-Numbers (510(k))
- Format: K + 6 digits (e.g., K240717)
- First 2 digits = fiscal year
- K24xxxx = assigned in FY2024 (FDA fiscal year starts October 1; K-number is assigned at submission, not clearance)

### P-Numbers (PMA)
- Format: P + 6 digits (e.g., P190001)
- Indicates PMA approval, not 510(k)

### DEN Numbers (De Novo)
- Format: DEN + 6 digits (e.g., DEN200001)
- Novel low/moderate risk devices without predicates

### N-Numbers (Pre-Amendments)
- Format: N + 4-5 digits (e.g., N0012)
- Legacy devices marketed before the 1976 Medical Device Amendments
- Not available in openFDA API — flat files (pmn*.txt) only

## Product Codes

FDA assigns 3-letter product codes indicating:
- Medical specialty (panel)
- Device type
- Regulation number

Examples:
- **QAS**: Picture Archiving and Communications System (PACS) — Radiology panel
- **DQY**: Percutaneous Transluminal Coronary Balloon Catheter — Cardiovascular panel
- **HQF**: Orthodontic Bracket — Dental panel
- **OVE**: Intervertebral Fusion Device — Orthopedic panel

## Common Extraction Issues

### OCR Errors
- O (letter) → 0 (zero)
- I (letter) → 1 (one)
- S → 5
- B → 8

### Document Types
- **510(k) Summary**: Public summary of submission (more detail)
- **510(k) Statement**: Brief statement (less detail, harder to extract)

### Missing Predicates
Possible causes:
- Document is a Statement (minimal detail)
- Predicates mentioned in tables/images (OCR needed)
- Non-standard document format
- Redacted information

## openFDA API Integration

The plugin integrates with all 7 openFDA Device API endpoints for real-time data access:

### Endpoints Available
| Endpoint | Purpose | Used By |
|----------|---------|---------|
| `/device/510k` | 510(k) clearance lookups | validate, research, compare-se |
| `/device/classification` | Device classification, product codes | research |
| `/device/event` | MAUDE adverse events | safety, validate, research, analyze |
| `/device/recall` | Device recalls | safety, validate, research |
| `/device/pma` | PMA approvals | validate (P-numbers) |
| `/device/registrationlisting` | Facility registrations | (available for queries) |
| `/device/udi` | Unique Device Identification | (available for queries) |

### Configuration
- **API key**: Optional. Without key: 1K requests/day. With key: 120K/day.
  - **Priority 1**: Environment variable `OPENFDA_API_KEY` (recommended — never enters chat history)
  - **Priority 2**: Settings file `~/.claude/fda-predicate-assistant.local.md` field `openfda_api_key`
  - **Never paste your API key into chat** — use `/fda:configure --setup-key` for safe setup instructions
- **Kill switch**: `openfda_enabled: false` disables all API calls for offline environments.
- **Fallback**: All commands fall back to flat files (pmn*.txt, foiaclass.txt) when the API is unavailable.
- **Test connectivity**: `/fda:configure --test-api` tests all 7 endpoints.

### API-Enhanced Commands
- **`/fda:validate`**: API-first validation with MAUDE event counts and recall checks
- **`/fda:safety`**: Full MAUDE + recall analysis for pre-submission preparation
- **`/fda:research`**: API classification, safety intelligence, API-enriched predicate profiles
- **`/fda:review`**: Confidence scoring with API-powered risk flags (recalls, MAUDE events)
- **`/fda:guidance`**: Classification lookup and guidance document search
- **`/fda:compare-se`**: API fallback for predicate metadata when flat files don't have the record
- **`/fda:presub`**: Classification data for Pre-Sub package generation
- **`/fda:submission-outline`**: Classification and gap analysis powered by API data
- **`/fda:analyze`**: Optional API enrichment with event counts per device
- **`/fda:status`**: Reports API connectivity, key status, and rate limit tier
- **`/fda:configure`**: `--test-api`, `--set openfda_api_key`, `--set openfda_enabled`, `--add-exclusion`

### Reference
See `references/openfda-api.md` for the full API reference with query templates, field mappings, and error handling patterns.

## Quick-Start Workflow

See the **Workflow Guide** section above for the full 5-stage workflow. Here's the minimal path:

**Option A (Interactive filtering with enrichment - Recommended):**
```
/fda-tools:batchfetch --product-codes CODE --years RANGE --quick --enrich
→ /fda:extract stage2 --project NAME → /fda:review --project NAME
→ /fda:draft --project NAME → /fda:assemble --project NAME → /fda:pre-check --project NAME
```

**Option B (Interactive filtering without enrichment):**
```
/fda-tools:batchfetch --product-codes CODE --years RANGE --quick
→ /fda:extract stage2 --project NAME → /fda:review --project NAME
→ /fda:draft --project NAME → /fda:assemble --project NAME → /fda:pre-check --project NAME
```

**Option C (Direct extraction - existing workflow):**
```
/fda:configure --setup-key → /fda:extract both → /fda:review --project NAME
→ /fda:draft --project NAME → /fda:assemble --project NAME → /fda:pre-check --project NAME
```

**Supporting commands** (use anytime):
- `/fda:validate K123456` — Validate a device number against FDA databases
- `/fda:safety --product-code CODE` — Deep MAUDE + recall analysis
- `/fda:analyze --project NAME` — Analyze extraction data
- `/fda:summarize --knumbers K123456` — Summarize 510(k) PDF sections
- `/fda:status` — Check pipeline data, file freshness, API connectivity
- `/fda:configure` — View/modify settings, manage exclusion list
- `/fda:standards --product-code CODE` — FDA recognized consensus standards
- `/fda:udi --product-code CODE` — UDI/GUDID device lookup
- `/fda:inspections --firm NAME` — FDA facility inspections and citations
- `/fda:trials --device TERM` — ClinicalTrials.gov device study search
- `/fda:warnings --query TERM` — FDA warning letters and enforcement

## Available Commands (43)

### Stage 1: Setup
| Command | Purpose |
|---------|---------|
| `/fda:configure` | Set up API keys, data paths, and preferences |
| `/fda:status` | Check what data you have and what's available |
| `/fda:start` | Interactive onboarding wizard — detects data, recommends workflow |

### Stage 2: Data Collection
| Command | Purpose |
|---------|---------|
| `/fda-tools:batchfetch` | **Interactive FDA 510(k) filtering** — AI-guided filter selection with preview (quick/full/full-auto modes). Optional `--enrich` flag adds 12 columns of real FDA API data (recalls, MAUDE, validation) |
| `/fda:extract` | Download 510(k) PDFs and extract predicate relationships |
| `/fda:validate` | Validate device numbers against FDA databases |
| `/fda:research` | Full submission research — predicates, testing, competitive landscape |
| `/fda:safety` | MAUDE adverse events and recall history |
| `/fda:guidance` | Look up FDA guidance documents and extract requirements |
| `/fda:literature` | PubMed/WebSearch literature review with gap analysis |
| `/fda:warnings` | FDA warning letters and enforcement intelligence with risk scoring |
| `/fda:inspections` | FDA Data Dashboard API — inspections, citations, compliance actions, import refusals |
| `/fda:trials` | ClinicalTrials.gov device study search via AREA syntax |
| `/fda:standards` | FDA Recognized Consensus Standards lookup by product code, number, or keyword |
| `/fda:udi` | UDI/GUDID device lookup via openFDA + AccessGUDID v3 |

### Stage 3: Analysis
| Command | Purpose |
|---------|---------|
| `/fda:analyze` | Statistics and patterns across extraction results |
| `/fda:review` | Score, flag, and accept/reject extracted predicates |
| `/fda:compare-se` | Generate Substantial Equivalence comparison tables |
| `/fda:lineage` | Predicate citation chain tracer across generations |
| `/fda:pathway` | Recommend optimal regulatory pathway with scoring |
| `/fda:propose` | Manually propose predicate and reference devices with validation and confidence scoring |
| `/fda:test-plan` | Risk-based testing plan with gap analysis |
| `/fda:pccp` | Predetermined Change Control Plan for AI/ML devices |

### Stage 4: Drafting
| Command | Purpose |
|---------|---------|
| `/fda:draft` | Generate regulatory prose for submission sections |
| `/fda:presub` | Generate a Pre-Submission meeting package |
| `/fda:submission-outline` | Generate 510(k) submission outline with gap analysis |
| `/fda:traceability` | Requirements Traceability Matrix (guidance → risks → tests → evidence) |
| `/fda:consistency` | Cross-document consistency validation across project files |
| `/fda:portfolio` | Cross-project dashboard — shared predicates, common guidance |

### Stage 5: Assembly
| Command | Purpose |
|---------|---------|
| `/fda:assemble` | Assemble eSTAR-structured submission package from project data |
| `/fda:export` | Export project data as eSTAR XML or zip package |
| `/fda:import` | Import eSTAR data from PDF or XML into project data |
| `/fda:pre-check` | FDA review simulation — RTA screening, deficiency prediction, readiness score |
| `/fda:dashboard` | Project status dashboard — readiness score, section progress, next steps |

### Utility
| Command | Purpose |
|---------|---------|
| `/fda:ask` | Natural language Q&A about FDA regulatory topics |
| `/fda:cache` | Show cached FDA data for a project — freshness, summaries, clear/refresh |
| `/fda:calc` | Regulatory calculators — shelf life (ASTM F1980), sample size, sterilization dose |
| `/fda:data-pipeline` | Data maintenance pipeline — analyze, download, extract, merge |
| `/fda:gap-analysis` | 3-way PMN/CSV/PDF cross-reference to find missing data |
| `/fda:monitor` | Watch FDA databases for new clearances, recalls, events |
| `/fda:pipeline` | Run the full 7-step pipeline autonomously |
| `/fda:audit` | View the decision audit trail — filter by command, action, date, subject; full exclusion rationale |
| `/fda:summarize` | Compare sections across 510(k) summary PDFs |
| `/fda:example` | Full E2E exercise of all plugin commands — generates a complete example project from a random or specified 510(k) clearance |

## Agents (7)

Autonomous agents handle complex multi-step workflows. Launch them with the Task tool specifying `subagent_type: "fda-tools:<agent-name>"`.

| Agent | Purpose | When to Use |
|-------|---------|-------------|
| `extraction-analyzer` | Analyze extraction results quality — patterns, confidence distribution, gap identification | After running `/fda:extract` to assess extraction quality |
| `submission-writer` | Draft regulatory prose for all applicable submission sections | After review is complete; writes section drafts using `/fda:draft` |
| `submission-assembler` | Package existing drafts into eSTAR directory structure with consistency checks | After all sections are drafted; creates the final submission package |
| `presub-planner` | Research regulatory landscape and generate a complete Pre-Submission package | When starting Pre-Sub preparation for a new device |
| `review-simulator` | Simulate FDA review team evaluation with RTA screening and deficiency prediction | When submission is nearly complete; identifies likely FDA questions |
| `research-intelligence` | Deep regulatory intelligence gathering — competitive landscape, safety signals, guidance analysis | At project start for comprehensive landscape assessment |
| `data-pipeline-manager` | Orchestrate data maintenance — gap analysis, downloads, extraction, merging | For bulk data operations across multiple product codes or years |

**Recommended agent sequence:** `research-intelligence` → `extraction-analyzer` → `submission-writer` → `submission-assembler` → `review-simulator`

## Workflow Guide

### Skill Routing
- Use `fda-predicate-assessment` for predicate strategy, SE rationale, lineage, and confidence scoring.
- Use `fda-safety-signal-triage` for MAUDE/recall signals, complaint trends, and risk framing.
- Use `fda-510k-submission-outline` for section-by-section 510(k) structure and RTA readiness.
- Use `fda-510k-knowledge` for data pipeline operations, configured paths, and reference lookups.

### Stage 1: Setup
```
/fda:configure --setup-key         — Get a free openFDA API key (120K/day vs 1K)
/fda:status                         — Check pipeline data and API connectivity
```

### Stage 2: Data Collection

**Interactive filtering with enrichment (recommended for AI assistance):**
```
/fda-tools:batchfetch --product-codes KGN --years 2024 --quick --enrich
/fda:extract stage2 --project NAME  — Extract predicates from downloaded PDFs
```

**Or basic filtering (without enrichment):**
```
/fda-tools:batchfetch --product-codes KGN --years 2024 --quick
/fda:extract stage2 --project NAME  — Extract predicates from downloaded PDFs
```

**Or direct extraction (existing workflow):**
```
/fda:extract both                   — Download PDFs + extract predicates
/fda:gap-analysis --project NAME    — Find missing K-numbers, PDFs, and extractions
/fda:data-pipeline run              — Download missing data and re-extract
```

**Note on enrichment:**
- Adds ~3-5 minutes to workflow for 50 devices
- Requires free openFDA API key (configure with `/fda:configure --set openfda_api_key YOUR_KEY`)
- Saves 3-4 hours of manual recall/validation research
- Data is conservative: only real FDA data, no calculated scores

### Stage 3: Analysis & Review
```
/fda:review --project NAME          — Score, flag, accept/reject predicates
/fda:research PRODUCT_CODE          — Competitive landscape, predicate profiles
/fda:safety --product-code CODE     — MAUDE + recall analysis
/fda:guidance PRODUCT_CODE --save   — Find guidance + extract requirements
/fda:standards --product-code CODE  — Applicable consensus standards
```

### Stage 4: Drafting
```
/fda:draft --project NAME           — Generate regulatory prose for all sections
/fda:compare-se --predicates ...    — Build SE comparison table
/fda:traceability --project NAME    — Requirements → risks → tests → evidence
/fda:consistency --project NAME     — Cross-document consistency check
```

### Stage 5: Assembly & Submission
```
/fda:assemble --project NAME        — Create eSTAR directory + index
/fda:export --project NAME          — Export as eSTAR XML or zip
/fda:pre-check --project NAME       — Simulate FDA review + RTA screening
```

### Alternative: Import Existing eSTAR
```
/fda:import estar.pdf --project NAME → /fda:review → /fda:draft → /fda:export
```

Each step builds on previous data but degrades gracefully if run independently.

## Resources (42 references)

For detailed reference information, see:
- `references/accessgudid-api.md` - AccessGUDID v3 API reference for UDI/device history lookups
- `references/aiml-device-intelligence.md` - AI/ML device trends, SaMD classification, and PCCP patterns
- `references/audit-logging.md` - JSONL audit log schema and pipeline consolidated log
- `references/cdrh-portal.md` - CDRH Portal submission guide, file size limits, CDRH vs CBER routing
- `references/cdrh-review-structure.md` - CDRH review team structure, OHT mapping, and deficiency templates
- `references/clinical-data-framework.md` - Clinical data decision tree and evidence types
- `references/clinical-study-framework.md` - Clinical study guidance, IDE requirements, and study design
- `references/clinicaltrials-api.md` - ClinicalTrials.gov API v2 reference with AREA syntax
- `references/common-issues.md` - Troubleshooting extraction problems
- `references/complaint-handling-framework.md` - 21 CFR 820.198 complaint handling procedures
- `references/confidence-scoring.md` - Predicate confidence scoring algorithm (with DEN handling)
- `references/decision-traceability.md` - Zero-trust decision traceability system for audit trail reviewability
- `references/cybersecurity-framework.md` - Cybersecurity documentation framework, Section 524B, and templates
- `references/device-classes.md` - Device classification details
- `references/dhf-checklist.md` - Design History File (DHF) checklist per 21 CFR 820
- `references/ectd-overview.md` - eCTD (electronic Common Technical Document) structure reference
- `references/estar-structure.md` - eSTAR section structure, XFA field mapping, XML schema, and applicability matrix
- `references/fda-dashboard-api.md` - FDA Data Dashboard API (inspections, citations, compliance actions)
- `references/fda-enforcement-intelligence.md` - Enforcement data sources, GMP violation patterns, risk scoring
- `references/fda-guidance-index.md` - Curated CDRH guidance documents index with regulation-to-guidance mapping
- `references/guidance-lookup.md` - FDA guidance document lookup reference
- `references/human-factors-framework.md` - IEC 62366-1 human factors engineering and usability testing
- `references/openfda-api.md` - openFDA Device API reference (all 7 endpoints)
- `references/openfda-data-dictionary.md` - openFDA field dictionary with sort/skip/count/OR-batch/wildcard support
- `references/path-resolution.md` - Plugin root resolution patterns
- `references/pathway-decision-tree.md` - Regulatory pathway decision flow, scoring, exemptions, and breakthrough designation
- `references/pccp-guidance.md` - FDA PCCP guidance, regulatory citations, and real-world examples
- `references/post-market-requirements.md` - Post-market obligations (MDR, recalls, registration, surveillance)
- `references/predicate-analysis-framework.md` - Deep predicate analysis with 7-subsection methodology
- `references/predicate-lineage.md` - Chain Health Scoring and lineage patterns
- `references/predicate-types.md` - Predicate selection and defensibility guidance
- `references/pubmed-api.md` - NCBI E-utilities API reference for structured PubMed searches
- `references/risk-management-framework.md` - ISO 14971 risk management process and templates
- `references/rta-checklist.md` - Refuse to Accept (RTA) checklist and prevention guide
- `references/section-patterns.md` - PDF section detection patterns, regexes, and eSTAR XML element mapping
- `references/special-controls.md` - Class II special controls identification and conformance
- `references/standards-database.md` - FDA recognized consensus standards database with supersession tracking
- `references/standards-tracking.md` - FDA recognized consensus standards tracking (with version numbers)
- `references/submission-structure.md` - 510(k) submission structure and Pre-Sub format
- `references/test-plan-framework.md` - ISO 14971 risk categories and device-type test lists (10+ device types)
- `references/readiness-score-formula.md` - Submission Readiness Index (SRI) canonical 0-100 scoring formula
- `references/udi-requirements.md` - UDI labeling requirements and compliance reference

## Disclaimers (always include when providing regulatory guidance)

When providing analysis, extraction results, or regulatory recommendations, remind users:
- This tool analyzes **publicly available** FDA data only — it is not for use with private, confidential, or IP-protected documents
- LLM accuracy is **not guaranteed** — always independently verify device numbers, predicate relationships, and regulatory citations
- Anything sent through Claude may be used for Anthropic model training depending on account settings — there is no independent means to verify exclusion even when training is disabled
- This is a **research aid**, not legal or regulatory advice — consult qualified professionals before making submission decisions
