![Version](https://img.shields.io/badge/version-5.4.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Commands](https://img.shields.io/badge/commands-33-orange)
![Agents](https://img.shields.io/badge/agents-4-purple)
![Tests](https://img.shields.io/badge/tests-533-brightgreen)
![Claude Code](https://img.shields.io/badge/Claude_Code-plugin-blueviolet)
![FDA 510(k)](https://img.shields.io/badge/FDA-510(k)-red)

# FDA Predicate Assistant

**Your AI-powered regulatory assistant for FDA 510(k) submissions.**

From predicate research to CDRH Portal submission — 33 commands, 4 autonomous agents, and 533 tests that handle the data work so you can focus on the science and strategy. Search FDA databases, identify predicates, analyze safety histories, look up standards, generate substantial equivalence comparisons, draft all 18 eSTAR sections, simulate FDA review, assemble submission-ready packages, and get step-by-step submission guidance, all from within Claude.

---

## Installation

### From your terminal

```bash
claude plugin marketplace add andrewlasiter/fda-predicate-assistant-plugin
claude plugin install fda-predicate-assistant@fda-tools
```

### From inside a Claude Code or Claude Desktop session

```
/plugin marketplace add andrewlasiter/fda-predicate-assistant-plugin
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
/fda:status                              # Check what data is available
/fda:validate K241335                    # Look up any device number
/fda:research QAS                        # Full submission research for a product code
/fda:ask "What class is a cervical fusion cage?"   # Regulatory Q&A
/fda:pipeline OVE --project demo         # Run the full pipeline end-to-end
```

---

## Commands

### Getting Started

| Command | What it does |
|---------|-------------|
| `/fda:status` | Shows what FDA data you have downloaded, how fresh it is, and what's available |
| `/fda:configure` | Sets up API keys, data directories, and your preferences |
| `/fda:ask` | Answers regulatory questions in plain language — classification, pathways, testing |
| `/fda:validate` | Checks any device number (K, P, DEN, N) against FDA databases |

### Research & Intelligence

| Command | What it does |
|---------|-------------|
| `/fda:research` | Comprehensive submission research — predicates, testing landscape, competitive analysis |
| `/fda:pathway` | Recommends the best regulatory pathway (Traditional/Special/Abbreviated 510(k), De Novo, PMA) |
| `/fda:literature` | Searches PubMed and the web for clinical evidence, then identifies gaps vs. guidance |
| `/fda:lineage` | Traces predicate citation chains across generations and flags recalled ancestors |
| `/fda:safety` | Pulls adverse events (MAUDE) and recall history for any product code or device |
| `/fda:standards` | Looks up FDA Recognized Consensus Standards by product code, standard number, or keyword |
| `/fda:udi` | Looks up UDI/GUDID records from openFDA — search by device identifier, product code, company, or brand |

### Data Extraction

| Command | What it does |
|---------|-------------|
| `/fda:extract` | Downloads 510(k) PDFs and extracts predicate relationships from them |
| `/fda:analyze` | Runs statistics and finds patterns across your extraction results |
| `/fda:summarize` | Compares sections (testing, IFU, device description) across multiple devices |
| `/fda:monitor` | Watches FDA databases for new clearances, recalls, and MAUDE events |

### Review & Planning

| Command | What it does |
|---------|-------------|
| `/fda:review` | Scores and triages extracted predicates — accept, reject, or flag each one |
| `/fda:propose` | Manually propose predicate and reference devices — validates against openFDA, scores confidence, compares IFU |
| `/fda:guidance` | Finds relevant FDA guidance documents and maps them to testing requirements |
| `/fda:test-plan` | Generates a risk-based testing plan with gap analysis |
| `/fda:presub` | Creates a Pre-Submission meeting package (cover letter, topics, questions) |

### Document Generation

| Command | What it does |
|---------|-------------|
| `/fda:submission-outline` | Builds a full 510(k) submission outline with section checklists and gap analysis |
| `/fda:compare-se` | Generates substantial equivalence comparison tables, auto-populated from FDA data |
| `/fda:draft` | Writes regulatory prose for 18 submission sections with citations |
| `/fda:pccp` | Creates a Predetermined Change Control Plan for AI/ML or iterative devices |
| `/fda:calc` | Regulatory calculators — shelf life (ASTM F1980), sample size, sterilization dose |

### Assembly & Validation

| Command | What it does |
|---------|-------------|
| `/fda:import` | Imports eSTAR data from PDF or XML into project data |
| `/fda:export` | Exports project data as eSTAR-compatible XML or zip package |
| `/fda:assemble` | Assembles an eSTAR-structured submission package from your project data |
| `/fda:traceability` | Generates a requirements traceability matrix (guidance → risks → tests → evidence) |
| `/fda:consistency` | Validates that device descriptions, intended use, and predicates match across all files |
| `/fda:portfolio` | Cross-project dashboard — shared predicates, common guidance, submission timelines |

### Quality & Pre-Filing

| Command | What it does |
|---------|-------------|
| `/fda:pre-check` | Simulates an FDA review team's evaluation — RTA screening, deficiency identification, readiness score |
| `/fda:pipeline` | Runs all stages autonomously: extract → review → safety → guidance → presub → outline → SE |

---

## Agents

The plugin includes 4 autonomous agents that can run multi-step workflows without manual intervention. Agents are invoked automatically by Claude when relevant, or can be triggered via the Task tool.

| Agent | What it does |
|-------|-------------|
| `extraction-analyzer` | Analyzes predicate extraction results — identifies patterns, reviews quality, auto-triages by confidence |
| `submission-writer` | Drafts all 18 eSTAR sections sequentially, runs consistency checks, assembles the package, and reports a readiness score |
| `presub-planner` | Researches the regulatory landscape, analyzes guidance, gathers safety intelligence, reviews literature, and generates a complete Pre-Sub package |
| `review-simulator` | Simulates a multi-perspective FDA review — each reviewer evaluates independently, findings are cross-referenced, and a detailed readiness assessment is generated |

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

## openFDA Integration

The plugin connects to all 7 openFDA Device API endpoints for real-time access to clearances, classifications, adverse events, recalls, registrations, UDI data, and COVID-related authorizations.

It also works offline using cached FDA flat files — no internet required for basic lookups.

**Optional:** Set up a free API key for higher rate limits:

```
/fda:configure --setup-key
```

---

## Data Pipeline

The plugin bundles two Python scripts for batch processing:

1. **BatchFetch** — Filters the FDA catalog by product code, date range, or company, then downloads 510(k) summary PDFs
2. **Predicate Extractor** — Extracts device numbers from downloaded PDFs with OCR error correction and FDA database validation

Run `/fda:extract` to use either or both stages.

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

<details>
<summary><strong>Important Notices</strong></summary>

**Research purposes only.** This tool analyzes publicly available FDA data (510(k) summaries, classification databases, MAUDE reports, and other records published by the U.S. Food and Drug Administration).

**Do not use with confidential documents.** All text you provide — including device descriptions, intended use statements, and file contents — is processed by Claude (Anthropic's LLM). Depending on your Anthropic account settings, this content may be used for model training. Even when training is disabled, there is no independent means to verify that data is excluded. Do not submit trade secrets, proprietary designs, or confidential regulatory strategies.

**LLM accuracy is not guaranteed.** Large language models make mistakes. Device number extraction, predicate identification, section classification, and all other outputs may contain errors, omissions, or hallucinations. Always independently verify every device number, predicate relationship, regulatory citation, and testing recommendation before relying on it.

**Not legal or regulatory advice.** Consult qualified regulatory affairs professionals and legal counsel before making submission decisions. The developers and Anthropic accept no liability for regulatory outcomes based on this tool's output.

</details>

---

## Changelog

See [CHANGELOG.md](./CHANGELOG.md) for version history.

## License

MIT
