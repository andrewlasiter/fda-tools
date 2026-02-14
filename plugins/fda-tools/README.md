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

For more workflows, see [QUICK_START.md](docs/QUICK_START.md).

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
- `/presub` -- Create a Pre-Submission meeting package

#### Project management
- `/dashboard` -- Project status with Submission Readiness Index (SRI)
- `/audit` -- View the decision audit trail
- `/cache` -- Show cached FDA data for a project
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

7 autonomous agents for multi-step workflows: extraction analysis, submission writing, pre-sub planning, FDA review simulation, research intelligence, submission assembly, and data pipeline management. Agents are invoked automatically by Claude when relevant.

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
