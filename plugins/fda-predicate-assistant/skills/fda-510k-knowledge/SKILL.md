---
name: fda-510k-knowledge
description: Use this skill when discussing 510(k) submissions, predicate devices, substantial equivalence, FDA clearance, K-numbers, PMA approval, De Novo pathways, product codes, or medical device classification.
---

# FDA 510(k) Regulatory Knowledge

You have expertise in FDA medical device regulations, particularly the 510(k) premarket notification process. You also know how the local data pipeline works and where to find data.

## Data Pipeline Overview

This project uses a two-stage pipeline for FDA 510(k) predicate analysis:

### Stage 1: BatchFetch
- **Script:** `$FDA_PLUGIN_ROOT/scripts/batchfetch.py`
- **Purpose:** Filter the FDA device catalog by year, product code, applicant, etc., then download 510(k) PDF documents
- **CLI flags:** `--date-range`, `--years`, `--product-codes`, `--applicants`, `--committees`, `--decision-codes`, `--output-dir`, `--download-dir`, `--data-dir`, `--save-excel`, `--no-download`, `--interactive`
- **Outputs:**
  - `510k_download.csv` — Full metadata (24 cols: KNUMBER, APPLICANT, DECISIONDATE, PRODUCTCODE, TYPE, STATEORSUMM, REVIEWADVISECOMM, THIRDPARTY, EXPEDITEDREVIEW, etc.)
  - `Applicant_ProductCode_Tables.xlsx` — Analytics workbook (3 sheets)
  - `merged_data.csv` — K-number + up to 6 predicates (7 cols)
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

## Recommended Workflow

The full 510(k) submission preparation workflow:

```
1. /fda:research PRODUCT_CODE        — Research the landscape (clearances, predicates, guidance, safety)
2. /fda:extract both                  — Download PDFs + extract predicates
3. /fda:review --project NAME         — Score, flag, accept/reject predicates
4. /fda:guidance PRODUCT_CODE --save  — Find guidance + extract requirements
5. /fda:presub PRODUCT_CODE           — Plan Pre-Submission meeting with FDA
6. /fda:submission-outline CODE       — Generate submission outline + gap analysis
7. /fda:compare-se --predicates ...   — Build SE comparison table for submission
```

**Alternative start — import existing eSTAR:**
```
1. /fda:import estar.pdf --project NAME  — Import existing eSTAR data
2. /fda:review --project NAME            — Score imported predicates
3. /fda:draft --project NAME             — Draft remaining sections
4. /fda:export --project NAME            — Export as eSTAR XML
5. Submit via CDRH Portal                — https://ccp.fda.gov/prweb/PRAuth/app/default/extsso
```

Each step builds on previous data but degrades gracefully if run independently.

**Supporting commands** (use anytime):
- `/fda:validate K123456` — Validate a device number against FDA databases
- `/fda:safety --product-code CODE` — Deep MAUDE + recall analysis
- `/fda:analyze --project NAME` — Analyze extraction data
- `/fda:summarize --knumbers K123456` — Summarize 510(k) PDF sections
- `/fda:status` — Check pipeline data, file freshness, API connectivity
- `/fda:configure` — View/modify settings, manage exclusion list

## Available Commands (33)

### Core Pipeline
| Command | Purpose |
|---------|---------|
| `/fda:pipeline` | Run the full 7-step pipeline autonomously |
| `/fda:extract` | Download 510(k) PDFs and extract predicate relationships |
| `/fda:review` | Score, flag, and accept/reject extracted predicates |
| `/fda:safety` | MAUDE adverse events and recall history |
| `/fda:guidance` | Look up FDA guidance documents and extract requirements |
| `/fda:presub` | Generate a Pre-Submission meeting package |
| `/fda:submission-outline` | Generate 510(k) submission outline with gap analysis |
| `/fda:compare-se` | Generate Substantial Equivalence comparison tables |

### Research and Analysis
| Command | Purpose |
|---------|---------|
| `/fda:research` | Full submission research — predicates, testing, competitive landscape |
| `/fda:validate` | Validate device numbers against FDA databases |
| `/fda:analyze` | Statistics and patterns across extraction results |
| `/fda:summarize` | Compare sections across 510(k) summary PDFs |
| `/fda:ask` | Natural language Q&A about FDA regulatory topics |
| `/fda:literature` | PubMed/WebSearch literature review with gap analysis |
| `/fda:lineage` | Predicate citation chain tracer across generations |

### Planning and Decision Support
| Command | Purpose |
|---------|---------|
| `/fda:pathway` | Recommend optimal regulatory pathway with scoring |
| `/fda:test-plan` | Risk-based testing plan with gap analysis |
| `/fda:pccp` | Predetermined Change Control Plan for AI/ML devices |
| `/fda:monitor` | Watch FDA databases for new clearances, recalls, events |
| `/fda:draft` | Generate regulatory prose for submission sections |

### Import, Export, and Assembly
| Command | Purpose |
|---------|---------|
| `/fda:import` | Import eSTAR data from PDF or XML into project data |
| `/fda:export` | Export project data as eSTAR XML or zip package |
| `/fda:assemble` | Assemble eSTAR-structured submission package from project data |
| `/fda:traceability` | Requirements Traceability Matrix (guidance → risks → tests → evidence) |
| `/fda:consistency` | Cross-document consistency validation across project files |
| `/fda:portfolio` | Cross-project dashboard — shared predicates, common guidance |
| `/fda:configure` | Set up API keys, data paths, and preferences |
| `/fda:status` | Check what data you have and what's available |

## Resources (25 references)

For detailed reference information, see:
- `references/output-formatting.md` - FDA Professional CLI output formatting guide (rules R1-R12)
- `references/openfda-api.md` - openFDA Device API reference (all 7 endpoints)
- `references/device-classes.md` - Device classification details
- `references/predicate-types.md` - Predicate selection and defensibility guidance
- `references/common-issues.md` - Troubleshooting extraction problems
- `references/section-patterns.md` - PDF section detection patterns, regexes, and eSTAR XML element mapping
- `references/confidence-scoring.md` - Predicate confidence scoring algorithm (with DEN handling)
- `references/guidance-lookup.md` - FDA guidance document lookup reference
- `references/submission-structure.md` - 510(k) submission structure and Pre-Sub format
- `references/path-resolution.md` - Plugin root resolution patterns
- `references/estar-structure.md` - eSTAR section structure, XFA field mapping, XML schema, and applicability matrix
- `references/pathway-decision-tree.md` - Regulatory pathway decision flow, scoring, exemptions, and breakthrough designation
- `references/test-plan-framework.md` - ISO 14971 risk categories and device-type test lists (10+ device types)
- `references/pccp-guidance.md` - FDA PCCP guidance, regulatory citations, and real-world examples
- `references/audit-logging.md` - JSONL audit log schema and pipeline consolidated log
- `references/predicate-lineage.md` - Chain Health Scoring and lineage patterns
- `references/standards-tracking.md` - FDA recognized consensus standards tracking (with version numbers)
- `references/cybersecurity-framework.md` - Cybersecurity documentation framework, Section 524B, and templates
- `references/rta-checklist.md` - Refuse to Accept (RTA) checklist and prevention guide
- `references/pubmed-api.md` - NCBI E-utilities API reference for structured PubMed searches
- `references/special-controls.md` - Class II special controls identification and conformance
- `references/clinical-data-framework.md` - Clinical data decision tree and evidence types
- `references/post-market-requirements.md` - Post-market obligations (MDR, recalls, registration, surveillance)
- `references/draft-templates.md` - Prose templates for all 16 eSTAR sections with `[TODO:]` placeholders
- `references/cdrh-portal.md` - CDRH Portal submission guide, file size limits, CDRH vs CBER routing

## Disclaimers (always include when providing regulatory guidance)

When providing analysis, extraction results, or regulatory recommendations, remind users:
- This tool analyzes **publicly available** FDA data only — it is not for use with private, confidential, or IP-protected documents
- LLM accuracy is **not guaranteed** — always independently verify device numbers, predicate relationships, and regulatory citations
- Anything sent through Claude may be used for Anthropic model training depending on account settings — there is no independent means to verify exclusion even when training is disabled
- This is a **research aid**, not legal or regulatory advice — consult qualified professionals before making submission decisions
