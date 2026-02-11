# FDA Predicate Assistant

Your AI-powered regulatory assistant for FDA 510(k) submissions -- predicate research, substantial equivalence analysis, and submission drafting.

> **CONFIDENTIAL DATA WARNING**
>
> This plugin processes text through Anthropic's Claude LLM. **Do not submit trade secrets, proprietary device designs, unpublished clinical data, or confidential regulatory strategies.** See [Protecting Your Data](#protecting-your-data) below.

## Installation

```
/install andrewlasiter/fda-tools fda-predicate-assistant
/start
```

## What's included

### Commands

#### Getting started
- `/start` -- Interactive onboarding wizard
- `/status` -- Check available data, scripts, and record counts
- `/configure` -- Set up API keys, data directories, and preferences

#### Research and analysis
- `/research` -- Comprehensive submission research for a product code
- `/analyze` -- Statistics and pattern analysis across extraction results
- `/validate` -- Look up any device number against FDA databases
- `/pathway` -- Recommend the best regulatory pathway (510(k), De Novo, PMA)
- `/literature` -- Search PubMed for clinical evidence and identify gaps
- `/safety` -- Pull adverse events and recall history
- `/udi` -- Look up UDI/GUDID records and device history
- `/standards` -- FDA Recognized Consensus Standards lookup
- `/guidance` -- Find relevant FDA guidance documents

#### Predicate workflow
- `/extract` -- Download 510(k) PDFs and extract predicate relationships
- `/data-pipeline` -- 4-step data maintenance: gap analysis, download, extract, merge
- `/review` -- Score and triage extracted predicates with justification narratives
- `/propose` -- Manually propose predicates with validation and confidence scoring
- `/compare-se` -- Generate substantial equivalence comparison tables

#### Submission preparation
- `/draft` -- Write regulatory prose for 18 submission sections with citations
- `/pre-check` -- Simulate FDA review team evaluation and RTA screening
- `/consistency` -- Validate device descriptions and predicates match across files
- `/assemble` -- Assemble an eSTAR-structured submission package
- `/export` -- Export project data as eSTAR-compatible XML or zip
- `/presub` -- Create a Pre-Submission meeting package

#### Project management
- `/dashboard` -- Project status with Submission Readiness Index (SRI)
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

## Important notices

**Research purposes only.** This tool analyzes publicly available FDA data. LLM outputs may contain errors, omissions, or hallucinations. Always independently verify every device number, predicate relationship, regulatory citation, and testing recommendation. Consult qualified regulatory affairs professionals before making submission decisions.

## License

MIT
