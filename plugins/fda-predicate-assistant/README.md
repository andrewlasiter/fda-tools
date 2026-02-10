![Version](https://img.shields.io/badge/version-5.21.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Commands](https://img.shields.io/badge/commands-40-orange)
![Agents](https://img.shields.io/badge/agents-7-purple)
![Tests](https://img.shields.io/badge/tests-1998-brightgreen)
![References](https://img.shields.io/badge/references-41-informational)
![Scripts](https://img.shields.io/badge/scripts-8-yellow)
![Claude Code](https://img.shields.io/badge/Claude_Code-plugin-blueviolet)
![FDA 510(k)](https://img.shields.io/badge/FDA-510(k)-red)

> **CONFIDENTIAL DATA WARNING**
>
> This plugin processes text through Anthropic's Claude LLM. **Do not submit trade secrets, proprietary device designs, unpublished clinical data, or confidential regulatory strategies.** See [Protecting Your Data](#protecting-your-data) below for details on training policies and opt-out options by account type.

# FDA Predicate Assistant

**Your AI-powered regulatory assistant for FDA 510(k) submissions.**

From predicate research to CDRH Portal submission — 40 commands, 7 autonomous agents, and 1,998 tests that handle the data work so you can focus on the science and strategy. New in v5.18: onboarding wizard (`/fda:start`), project dashboard with readiness scoring (`/fda:dashboard`), and IVD review support. Search FDA databases, identify predicates, analyze safety histories, look up standards, generate substantial equivalence comparisons, draft all 18 eSTAR sections, simulate FDA review, maintain your extraction corpus, assemble submission-ready packages, and get step-by-step submission guidance, all from within Claude.

---

## Installation

### From your terminal

```bash
claude plugin marketplace add andrewlasiter/fda-predicate-assistant
claude plugin install fda-predicate-assistant@fda-tools
```

### From inside a Claude Code or Claude Desktop session

```
/plugin marketplace add andrewlasiter/fda-predicate-assistant
/plugin install fda-predicate-assistant@fda-tools
```

Start a new session after installing to load the plugin.

### Co-work / Autonomous Sessions

Co-work uses your existing plugin installation — install using either method above first. Once installed, the plugin is automatically available in all Co-work sessions.

### Verify It Works

```
/fda:status
```

You should see a summary of available FDA data files, script availability, and record counts.

---

## Quick Start

```
/fda:start                               # Interactive onboarding wizard (new users start here)
/fda:status                              # Check what data is available
/fda:validate K241335                    # Look up any device number
/fda:research QAS                        # Full submission research for a product code
/fda:ask "What class is a cervical fusion cage?"   # Regulatory Q&A
/fda:pipeline OVE --project demo         # Run the full pipeline end-to-end
/fda:dashboard --project demo            # Project status dashboard with readiness score
```

---

## Commands

### Stage 1: Setup (3 commands)

| Command | What it does |
|---------|-------------|
| `/fda:configure` | Sets up API keys, data directories, and your preferences |
| `/fda:status` | Shows what FDA data you have downloaded, how fresh it is, and what's available |
| `/fda:start` | Interactive onboarding wizard — guides new users through first project setup |

### Stage 2: Data Collection (14 commands)

| Command | What it does |
|---------|-------------|
| `/fda:extract` | Downloads 510(k) PDFs and extracts predicate relationships from them |
| `/fda:validate` | Checks any device number (K, P, DEN, N) against FDA databases |
| `/fda:research` | Comprehensive submission research — predicates, testing landscape, competitive analysis |
| `/fda:safety` | Pulls adverse events (MAUDE) and recall history for any product code or device |
| `/fda:guidance` | Finds relevant FDA guidance documents and maps them to testing requirements |
| `/fda:literature` | Searches PubMed and the web for clinical evidence, then identifies gaps vs. guidance |
| `/fda:warnings` | Searches FDA warning letters and enforcement actions — GMP violations, risk scoring, QMSR transition |
| `/fda:inspections` | Searches FDA establishment inspections, citations, compliance actions, and import refusals |
| `/fda:trials` | Searches ClinicalTrials.gov for device clinical studies with AREA syntax and study parsing |
| `/fda:standards` | Looks up FDA Recognized Consensus Standards by product code, standard number, or keyword |
| `/fda:udi` | Looks up UDI/GUDID records — device history, sterilization, SNOMED CT, UDI barcode parsing |
| `/fda:summarize` | Compares sections (testing, IFU, device description) across multiple devices |
| `/fda:monitor` | Watches FDA databases for new clearances, recalls, and MAUDE events |
| `/fda:gap-analysis` | Cross-references FDA PMN database vs. your data to find missing K-numbers, PDFs, and extractions |

### Stage 3: Analysis (8 commands)

| Command | What it does |
|---------|-------------|
| `/fda:analyze` | Runs statistics and finds patterns across your extraction results |
| `/fda:review` | Scores and triages extracted predicates — accept, reject, or flag each one with justification narratives |
| `/fda:compare-se` | Generates substantial equivalence comparison tables, auto-populated from FDA data |
| `/fda:lineage` | Traces predicate citation chains across generations and flags recalled ancestors |
| `/fda:pathway` | Recommends the best regulatory pathway (Traditional/Special/Abbreviated 510(k), De Novo, PMA) |
| `/fda:propose` | Manually propose predicate and reference devices — validates against openFDA, scores confidence, compares IFU |
| `/fda:test-plan` | Generates a risk-based testing plan with gap analysis |
| `/fda:pccp` | Creates a Predetermined Change Control Plan for AI/ML or iterative devices |

### Stage 4: Drafting (6 commands)

| Command | What it does |
|---------|-------------|
| `/fda:draft` | Writes regulatory prose for 18 submission sections with citations and revision support |
| `/fda:presub` | Creates a Pre-Submission meeting package (cover letter, topics, questions) |
| `/fda:submission-outline` | Builds a full 510(k) submission outline with section checklists and gap analysis |
| `/fda:traceability` | Generates a requirements traceability matrix (guidance → risks → tests → evidence) |
| `/fda:consistency` | Validates that device descriptions, intended use, and predicates match across all files |
| `/fda:portfolio` | Cross-project dashboard — shared predicates, common guidance, submission timelines with Gantt view |

### Stage 5: Assembly (5 commands)

| Command | What it does |
|---------|-------------|
| `/fda:assemble` | Assembles an eSTAR-structured submission package from your project data |
| `/fda:export` | Exports project data as eSTAR-compatible XML or zip package |
| `/fda:import` | Imports eSTAR data from PDF or XML into project data |
| `/fda:pre-check` | Simulates an FDA review team's evaluation — RTA screening, deficiency identification, readiness score |
| `/fda:dashboard` | Project status dashboard — submission readiness index (SRI), section completion, next actions |

### Utility (4 commands)

| Command | What it does |
|---------|-------------|
| `/fda:ask` | Answers regulatory questions in plain language — classification, pathways, testing |
| `/fda:calc` | Regulatory calculators — shelf life (ASTM F1980), sample size (exact binomial), sterilization dose |
| `/fda:data-pipeline` | 4-step data maintenance pipeline — gap analysis, download missing PDFs, extract predicates, merge results |
| `/fda:pipeline` | Runs all stages autonomously: extract → review → safety → guidance → presub → outline → SE |

---

## Agents

The plugin includes 7 autonomous agents that can run multi-step workflows without manual intervention. Agents are invoked automatically by Claude when relevant, or can be triggered via the Task tool.

| Agent | What it does |
|-------|-------------|
| `extraction-analyzer` | Analyzes predicate extraction results — identifies patterns, reviews quality, auto-triages by confidence |
| `submission-writer` | Drafts all 18 eSTAR sections sequentially, runs 11-check consistency validation, assembles the package, and reports a Submission Readiness Index (SRI) score |
| `presub-planner` | Researches the regulatory landscape, analyzes guidance, gathers safety intelligence, reviews literature, and generates a complete Pre-Sub package |
| `review-simulator` | Simulates a multi-perspective FDA review — includes IVD reviewer (CLIA, CLSI EP series) — each reviewer evaluates independently, findings are cross-referenced, and a detailed readiness assessment is generated |
| `research-intelligence` | 11-step deep regulatory research — predicate landscape, competitive intelligence, testing precedent, IFU comparisons, and AccessGUDID device intelligence |
| `submission-assembler` | Validates submission completeness, assembles eSTAR-structured packages, runs cross-file consistency checks, and generates assembly reports |
| `data-pipeline-manager` | Orchestrates the 4-step data maintenance pipeline — gap analysis, PDF download, predicate extraction, and data merge with progress tracking |

---

## Autonomous Mode

The plugin can run fully unattended — no prompts, no manual steps. This is ideal for Co-work sessions, batch processing, or overnight runs.

| Flag | What it does |
|------|-------------|
| `--full-auto` | Makes all decisions automatically using score thresholds (never prompts) |
| `--infer` | Auto-detects your product code from project data |
| `--headless` | Non-interactive mode for use inside Python scripts |

**Example — fully autonomous pipeline:**

```
/fda:pipeline OVE --project my-device --full-auto \
  --device-description "Cervical interbody fusion cage" \
  --intended-use "For fusion of the cervical spine"
```

---

## FDA Database Coverage

The plugin connects to multiple FDA data sources. Here is what is covered and what is not.

### APIs Used

| API | Endpoints / Scope | Plugin Commands |
|-----|-------------------|-----------------|
| **openFDA** (api.fda.gov) | `device/510k`, `device/classification`, `device/enforcement`, `device/event`, `device/pma`, `device/recall`, `device/registrationlisting`, `device/udi`, `device/covid19serology` (9 endpoints) | `/fda:validate`, `/fda:safety`, `/fda:research`, `/fda:guidance`, `/fda:monitor`, `/fda:udi`, `/fda:pathway` |
| **AccessGUDID v3** (accessgudid.nlm.nih.gov) | Device lookup, UDI parsing, SNOMED CT, device history, sterilization data | `/fda:udi`, `/fda:guidance` |
| **FDA Data Dashboard** (api-datadashboard.fda.gov) | Inspections, citations, compliance actions, import refusals | `/fda:inspections` |
| **ClinicalTrials.gov v2** (clinicaltrials.gov) | Device clinical study search, AREA syntax | `/fda:trials` |
| **PubMed E-utilities** (eutils.ncbi.nlm.nih.gov) | Article search (esearch), abstract fetch (efetch), related articles (elink) | `/fda:literature` |

**API features used:** `sort`, `skip` (pagination), `_count` (aggregations), OR-batched multi-value queries, wildcard search, field-specific queries. Responses are cached with 7-day TTL and exponential backoff retry.

**First run:** The plugin detects when no API key is configured and offers guided setup:

```
/fda:configure --setup-key
```

### FDA Medical Device Databases — Coverage Map

The FDA lists [27 medical device databases](https://www.fda.gov/medical-devices/device-advice-comprehensive-regulatory-assistance/medical-device-databases). The plugin covers the most commonly needed ones:

| FDA Database | Covered? | How |
|-------------|----------|-----|
| 510(k) Premarket Notification (PMN) | Yes | openFDA `device/510k` + flat files |
| Classification (Product Codes) | Yes | openFDA `device/classification` |
| MAUDE (Adverse Events) | Yes | openFDA `device/event` |
| Recalls | Yes | openFDA `device/recall` + `device/enforcement` |
| PMA (Premarket Approval) | Yes | openFDA `device/pma` |
| Establishment Registration & Listing | Yes | openFDA `device/registrationlisting` |
| UDI / GUDID | Yes | openFDA `device/udi` + AccessGUDID v3 |
| Recognized Consensus Standards | Yes | `/fda:standards` (web search) |
| FDA Guidance Documents | Yes | `/fda:guidance` (curated index + web search) |
| Inspections & Compliance | Yes | FDA Data Dashboard API |
| Clinical Trials | Yes | ClinicalTrials.gov v2 API |
| Warning Letters | Yes | `/fda:warnings` (web search + analysis) |
| CFR Title 21 | Partial | Referenced in guidance mapping, not directly queried |
| Devices@FDA | No | Use accessdata.fda.gov directly |
| De Novo | Partial | Some indexed in openFDA 510k endpoint; no dedicated API |
| CLIA / CLIA Waived | No | Not applicable to most 510(k) submissions |
| Mammography Facilities | No | Specialty database |
| HDE (Humanitarian Device) | No | Low-volume pathway |
| Post-Approval Studies | No | PMA-specific |
| 522 Postmarket Surveillance | No | PMA-specific |
| Radiation-Emitting Products | No | Specialty database |

---

## Data Pipeline

The plugin bundles 8 Python scripts for batch processing, corpus maintenance, and FDA API integration:

1. **Gap Analysis** (`gap_analysis.py`) — Cross-references FDA PMN database, your extraction CSV, and downloaded PDFs to identify what's missing
2. **BatchFetch** (`batchfetch.py`) — Filters the FDA catalog by product code, date range, or company, then downloads 510(k) summary PDFs. Supports `--from-manifest` (chain from gap analysis output) and `--resume` (restart interrupted downloads)
3. **Predicate Extractor** (`predicate_extractor.py`) — Extracts device numbers from downloaded PDFs with OCR error correction and FDA database validation. Supports `--section-aware` (weight SE sections) and `--enrich` (augment with openFDA data)
4. **Merge** — Combines per-year extraction CSVs into the master baseline
5. **FDA HTTP** (`fda_http.py`) — Shared HTTP utility for all FDA API calls with retry, caching, and rate limiting

**Pipeline chaining:** Gap analysis can feed directly into BatchFetch — run `/fda:gap-analysis` to generate a manifest, then `/fda:data-pipeline run --from-manifest` to download and extract the missing data.

Run `/fda:data-pipeline status` to see the current state, or `/fda:data-pipeline run --years 2025` to execute the full pipeline for a specific year.

---

## Readiness Scoring

The plugin calculates a **Submission Readiness Index (SRI)** — a 0-100 score reflecting how close your project is to FDA submission. The SRI is based on 6 weighted components: RTA checklist completion, predicate strength, SE comparison quality, testing coverage, deficiency count, and documentation completeness.

| SRI Range | Tier | Meaning |
|-----------|------|---------|
| 85-100 | Ready | Submission-ready; final human review recommended |
| 60-84 | Near Ready | Minor gaps remain; address flagged items |
| 40-59 | In Progress | Core sections drafted but significant gaps exist |
| 30-39 | Early Draft | Foundational work started |
| 0-29 | Early Stage | Project initialized; most work ahead |

Use `/fda:dashboard --project NAME` to see your current SRI, or `/fda:pre-check --project NAME` for a detailed breakdown by review discipline. The canonical formula is documented in `references/readiness-score-formula.md`.

---

## Section Detection

510(k) PDFs vary widely in formatting — different section headings, OCR artifacts from scanned documents, EU-style terminology. The plugin uses a **3-tier section detection system** to handle this:

1. **Tier 1: Regex** — Fast deterministic matching against 13 universal and 5 device-type-specific heading patterns
2. **Tier 2: OCR-Tolerant** — Applies an OCR substitution table (e.g., `1→I`, `0→O`, `5→S`) and retries Tier 1, allowing up to 2 character corrections per heading
3. **Tier 3: LLM Semantic** — Classifies sections by content signals (2+ keyword matches in a 200-word window) and maps non-standard headings (34 EU/novel terms) to canonical FDA section names

All commands that read PDF sections (`/fda:summarize`, `/fda:research`, `/fda:review`, `/fda:compare-se`, `/fda:lineage`, `/fda:presub`, `/fda:propose`) use this system. The patterns are maintained in a single canonical file (`references/section-patterns.md`) to prevent drift.

---

## Requirements

- Claude Code 1.0.33 or later
- Python 3.x (for extraction scripts)
- `pip install requests tqdm PyMuPDF pdfplumber` (for PDF processing)

---

## Updating

To update to the latest version:

```
/plugin update fda-predicate-assistant
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Commands don't appear after install | Start a new session — plugins load at startup |
| `/plugin install` fails | Check your internet connection; verify the marketplace is registered with `/plugin list` |
| Python errors during extraction | Run `pip install requests tqdm PyMuPDF pdfplumber` |
| "Rate limited" from openFDA | Set up a free API key: `/fda:configure --setup-key` |
| Plugin seems outdated | Run `/plugin update fda-predicate-assistant` |

---

## Protecting Your Data

All text you provide to this plugin — device descriptions, intended use statements, file contents, command arguments — is sent to Anthropic's Claude LLM for processing. Your data protection depends on your Anthropic account type.

### Training Policy by Account Type

| Account Type | Data Used for Training? | Retention | How to Opt Out |
|-------------|------------------------|-----------|----------------|
| **Free / Pro / Max** (consumer) | **Yes, by default** (since Sep 28, 2025) | 5 years if training enabled; 30 days if disabled | [claude.ai/settings/data-privacy-controls](https://claude.ai/settings/data-privacy-controls) |
| **Team / Enterprise** (commercial) | **No** — Anthropic does not train on commercial data | 30 days (customizable for Enterprise) | Already protected by commercial terms |
| **API** (direct) | **No** (unless opted in to Developer Partner Program) | 30 days (7 days for API logs) | Already protected by API terms |
| **Bedrock / Vertex / Foundry** | **No** — third-party provider terms apply | Provider-specific | Already protected |

### Recommendations for Confidential Work

1. **Use a Team or Enterprise account** — commercial terms explicitly prohibit training on your data
2. **If on a consumer plan**: disable model improvement at [claude.ai/settings/data-privacy-controls](https://claude.ai/settings/data-privacy-controls) before using the plugin with any sensitive content
3. **Enterprise users**: configure custom data retention (minimum 30 days) via Admin Settings > Data and Privacy
4. **Zero data retention**: available for Enterprise and API customers by arrangement with Anthropic
5. **Never submit**: trade secrets, unpublished clinical data, proprietary designs, patient-identifiable information, or confidential regulatory strategies through any consumer account regardless of settings

### What This Plugin Sends to Claude

- Device descriptions and intended use statements you provide
- K-numbers, product codes, and regulatory identifiers (public FDA data)
- File contents when you use `/fda:import` or reference local files
- Command arguments and conversation context

The plugin does NOT send your files to any server other than Anthropic's API. openFDA queries go directly to api.fda.gov. PDF downloads come directly from accessdata.fda.gov.

> **Sources**: [Anthropic Data Usage (Claude Code)](https://code.claude.com/docs/en/data-usage) | [Anthropic Privacy Center](https://privacy.claude.com) | [Consumer Terms Update (Sep 2025)](https://www.anthropic.com/news/updates-to-our-consumer-terms)

---

### Important Notices

**Research purposes only.** This tool analyzes publicly available FDA data (510(k) summaries, classification databases, MAUDE reports, and other records published by the U.S. Food and Drug Administration).

**LLM accuracy is not guaranteed.** Large language models make mistakes. Device number extraction, predicate identification, section classification, and all other outputs may contain errors, omissions, or hallucinations. Always independently verify every device number, predicate relationship, regulatory citation, and testing recommendation before relying on it.

**Not legal or regulatory advice.** Consult qualified regulatory affairs professionals and legal counsel before making submission decisions. The developers and Anthropic accept no liability for regulatory outcomes based on this tool's output.

---

## Changelog

See [CHANGELOG.md](./CHANGELOG.md) for version history.

## License

MIT
