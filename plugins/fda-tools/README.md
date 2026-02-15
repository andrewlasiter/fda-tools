# FDA Predicate Assistant

Your AI-powered regulatory assistant for FDA 510(k) submissions -- predicate research, substantial equivalence analysis, and submission drafting.

> **CONFIDENTIAL DATA WARNING**
>
> This plugin processes text through Anthropic's Claude LLM. **Do not submit trade secrets, proprietary device designs, unpublished clinical data, or confidential regulatory strategies.** See [Protecting Your Data](#protecting-your-data) below.

## Installation

```
/install andrewlasiter/fda-tools fda-tools
/start
```

For detailed installation instructions, see [INSTALLATION.md](docs/INSTALLATION.md).

## Getting Started

### Quick Start
New to the plugin? Follow these steps:

1. **Run the setup wizard:** `/fda-tools:start`
2. **Configure your data directory:** `/fda-tools:configure`
3. **Try a simple workflow:** See [QUICK_START.md](docs/QUICK_START.md)

### Common Workflows

**Research predicates for your device:**
```bash
/fda-tools:research --product-code DQY --years 2024 --project my_device
/fda-tools:review
```

**Generate submission outline:**
```bash
/fda-tools:submission-outline
/fda-tools:compare-se
```

**Run full pipeline:**
```bash
/fda-tools:pipeline --product-code DQY --years 2024
```

**Generate Pre-Submission package with FDA eSTAR XML:**
```bash
/fda-tools:presub DQY --project my_device \
  --device-description "Catheter for vascular access" \
  --intended-use "To provide vascular access for medication delivery"
```
Generates:
- `presub_plan.md` - Human-readable Pre-Sub plan (auto-selects 5-7 questions)
- `presub_metadata.json` - Structured meeting data
- `presub_prestar.xml` - FDA Form 5064 XML (import into Adobe Acrobat)

For more workflows, see [QUICK_START.md](docs/QUICK_START.md).

## Feature Spotlight

### NEW in v5.25.0: PreSTAR XML Generation for Pre-Submission Meetings

Complete FDA Pre-Submission workflow with eSTAR-ready XML export for FDA Form 5064.

**Key Features:**
- **6 Meeting Types**: Formal, Written, Info, Pre-IDE, Administrative, Info-Only
- **35-Question Bank**: Centralized questions across 10 regulatory categories
- **Auto-Detection**: Intelligent meeting type selection based on device characteristics
- **Auto-Triggers**: Automatically selects relevant questions (e.g., sterile device → sterilization questions)
- **Template System**: 80+ placeholders auto-populated from project data
- **FDA eSTAR Ready**: Direct XML import into FDA Form 5064 (Adobe Acrobat)

**Workflow:**
1. **Generate Pre-Sub Package**:
   ```bash
   /fda-tools:presub DQY --project catheter_device \
     --device-description "Single-use vascular access catheter" \
     --intended-use "To provide temporary vascular access"
   ```

2. **Output Files Generated**:
   - `presub_plan.md` - Complete Pre-Sub document (formatted, ready for review)
   - `presub_metadata.json` - Structured meeting data
   - `presub_prestar.xml` - FDA eSTAR XML (FDA Form 5064)

3. **Import into FDA Form**:
   - Open FDA Form 5064 (PreSTAR template) in Adobe Acrobat
   - Form > Import Data > Select `presub_prestar.xml`
   - Fields auto-populate: Admin info, device description, IFU, questions, meeting characteristics
   - Add attachments and submit to FDA

**Meeting Type Examples:**
- **Formal** (5-7 questions): Complex devices, novel technology, multiple regulatory questions
- **Written** (1-3 questions): Straightforward devices, well-scoped technical questions
- **Pre-IDE**: Clinical study planning, IDE protocol discussion
- **Administrative**: Pathway determination (510(k) vs De Novo vs PMA), classification questions

**Question Categories:**
- Predicate selection, Classification, Testing (biocompatibility, sterilization, shelf life, performance, electrical, software, cybersecurity, human factors), Clinical evidence, Novel technology, Labeling, Manufacturing, Regulatory pathway

**Auto-Triggers** (automatically add questions based on device description):
- Patient-contacting device → Biocompatibility questions
- Sterile device → Sterilization + Shelf life questions
- Powered device → Electrical safety questions
- Software device → Software V&V questions
- Implantable device → Long-term biocompatibility questions
- Reusable device → Reprocessing validation questions
- Novel technology → Novel feature discussion questions

**Time Savings**: 2-4 hours per Pre-Sub (automated question selection + template population + XML export)

## Documentation

- **[Quick Start Guide](docs/QUICK_START.md)** - Get started in minutes
- **[Installation Guide](docs/INSTALLATION.md)** - Detailed setup instructions
- **[Troubleshooting Guide](docs/TROUBLESHOOTING.md)** - Common issues and solutions
- **[Migration Notice](MIGRATION_NOTICE.md)** - Upgrading from fda-predicate-assistant
- **[Changelog](CHANGELOG.md)** - Version history and release notes

## What's included

### Commands

#### Getting started
- `/start` -- Interactive onboarding wizard
- `/status` -- Check available data, scripts, and record counts
- `/configure` -- Set up API keys, data directories, and preferences

#### NEW: AI-Powered Standards Generation (v5.23.0)
- `/generate-standards` -- Generate FDA Recognized Consensus Standards for any device using AI analysis (agent-based, no API keys)
  - Processes specific codes, top N by volume, or ALL ~2000 codes
  - AI determines applicable standards based on device characteristics
  - Multi-agent validation framework (coverage + quality + consensus)
  - Uses installing user's Claude Code access

#### Research and analysis
- `/research` -- Comprehensive submission research for a product code
- `/analyze` -- Statistics and pattern analysis across extraction results
- `/ask` -- Natural language Q&A about FDA regulatory topics
- `/validate` -- Look up any device number against FDA databases
- `/pathway` -- Recommend the best regulatory pathway (510(k), De Novo, PMA)
- `/literature` -- Search PubMed for clinical evidence and identify gaps
- `/safety` -- Pull adverse events and recall history
- `/inspections` -- FDA inspection history, CFR citations, and compliance actions
- `/trials` -- Search ClinicalTrials.gov for similar device studies
- `/warnings` -- FDA warning letters and enforcement actions
- `/udi` -- Look up UDI/GUDID records and device history
- `/standards` -- FDA Recognized Consensus Standards lookup
- `/guidance` -- Find relevant FDA guidance documents
- `/lineage` -- Trace predicate citation chains across clearance generations

#### Predicate workflow
- `/extract` -- Download 510(k) PDFs and extract predicate relationships
- `/data-pipeline` -- 4-step data maintenance: gap analysis, download, extract, merge
- `/review` -- Score and triage extracted predicates with justification narratives
- `/propose` -- Manually propose predicates with validation and confidence scoring
- `/compare-se` -- Generate substantial equivalence comparison tables
- `/compare-sections` -- Batch section comparison across devices for regulatory intelligence

#### Submission preparation
- `/draft` -- Write regulatory prose for 18 submission sections with citations
- `/submission-outline` -- Generate a 510(k) submission outline with section checklists
- `/traceability` -- Generate a requirements traceability matrix
- `/summarize` -- Summarize and compare sections from 510(k) summary PDFs
- `/pccp` -- Generate a Predetermined Change Control Plan for AI/ML devices
- `/test-plan` -- Generate a risk-based testing plan with gap analysis
- `/pre-check` -- Simulate FDA review team evaluation and RTA screening
- `/consistency` -- Validate device descriptions and predicates match across files
- `/assemble` -- Assemble an eSTAR-structured submission package
- `/export` -- Export project data as eSTAR-compatible XML or zip
- `/presub` -- Create Pre-Submission meeting package with PreSTAR XML export (v5.25.0: 6 meeting types, 35-question bank, auto-detection)

#### Project management
- `/dashboard` -- Project status with Submission Readiness Index (SRI)
- `/audit` -- View the decision audit trail
- `/cache` -- Show cached FDA data for a project
- `/update-data` -- Scan and batch update stale cached FDA data across all projects
- `/gap-analysis` -- Analyze gaps in 510(k) data pipeline
- `/portfolio` -- Cross-project portfolio dashboard
- `/pipeline` -- Run all stages autonomously end-to-end
- `/import` -- Import eSTAR data from PDF or XML
- `/monitor` -- Watch FDA databases for new clearances, recalls, and events
- `/calc` -- Regulatory calculators (shelf life, sample size, sterilization dose)

### Skills

- **FDA 510(k) Knowledge** -- Local data pipeline, openFDA integration, 510(k) terminology
- **Predicate Assessment** -- Predicate strategy, substantial equivalence, confidence scoring
- **Safety Signal Triage** -- Recalls, MAUDE adverse events, complaint trends, risk summaries
- **510(k) Submission Outline** -- Section-by-section outlines, RTA readiness checklists, evidence plans
- **E2E Smoke Tests** -- Deterministic live smoke tests for plugin scripts

### Agents

12 autonomous agents for multi-step workflows, including:
- **Standards Generation**: AI-powered standards analyzer, coverage auditor, quality reviewer
- **Core Workflows**: Extraction analysis, submission writing, pre-sub planning, FDA review simulation
- **Intelligence**: Research intelligence, data pipeline management, submission assembly
- **Validation**: Multi-agent consensus framework

Agents are invoked automatically by Claude when relevant, or manually via commands.

### Connected data sources

10 connector categories for FDA clearances, adverse events, clinical trials, literature, and more.
See [CONNECTORS.md](CONNECTORS.md) for details and [.mcp.json](.mcp.json) for MCP server configuration.

## Protecting Your Data

All text you provide -- device descriptions, intended use statements, file contents, command arguments -- is sent to Anthropic's Claude LLM for processing.

| Account Type | Trained On? | Recommendation |
|-------------|-------------|----------------|
| **Free / Pro / Max** | Yes, by default | Disable model improvement in [privacy settings](https://claude.ai/settings/data-privacy-controls) before using with sensitive content |
| **Team / Enterprise** | No | Already protected by commercial terms |
| **API / Bedrock / Vertex** | No | Already protected |

**Never submit** trade secrets, unpublished clinical data, proprietary designs, patient-identifiable information, or confidential regulatory strategies through any consumer account.

The plugin does NOT send your files to any server other than Anthropic's API. openFDA queries go directly to api.fda.gov. PDF downloads come directly from accessdata.fda.gov.

## Testing & Compliance Status

### Test Results (v5.22.0)
- **Overall Pass Rate:** 96.6% (28/29 tests)
- **Phase 1 (Data Integrity):** 22/22 tests passing ✓
- **Phase 2 (Intelligence):** 4/4 devices verified ✓
- **Phase 3 (Intelligence Suite):** 31/31 tests passing ✓
- **Phase 4A (Gap Analysis):** 9/9 tests passing ✓
- **Phase 4B (Smart Predicates):** 10/10 tests passing ✓
- **Phase 5 (Workflows):** 19/19 tests passing ✓

### Compliance Status
- **Status:** CONDITIONAL APPROVAL - Research use only
- **CFR Citations:** 100% accurate (3/3 verified)
- **FDA Guidance:** 100% current (3/3 verified)

**Important:** This plugin is approved for research and intelligence gathering ONLY. Not approved for direct FDA submission use without independent verification by qualified RA professionals.

See [Testing Complete Summary](docs/testing/TESTING_COMPLETE_FINAL_SUMMARY.md) for details.

## Important notices

**Research purposes only.** This tool analyzes publicly available FDA data. LLM outputs may contain errors, omissions, or hallucinations. Always independently verify every device number, predicate relationship, regulatory citation, and testing recommendation. Consult qualified regulatory affairs professionals before making submission decisions.

## License

MIT
