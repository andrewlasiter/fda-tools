![Version](https://img.shields.io/badge/version-4.0.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Commands](https://img.shields.io/badge/commands-26-orange)
![Claude Code](https://img.shields.io/badge/Claude_Code-plugin-blueviolet)
![FDA 510(k)](https://img.shields.io/badge/FDA-510(k)-red)

# FDA Predicate Assistant

**Your AI-powered regulatory assistant for FDA 510(k) submissions.**

From predicate research to eSTAR assembly — 26 commands that handle the data work so you can focus on the science and strategy. Search FDA databases, identify predicates, analyze safety histories, generate substantial equivalence comparisons, and assemble submission-ready documents, all from within Claude.

---

## Installation

### Claude Code (CLI)

Open Claude Code, then type these two commands:

```
/plugin marketplace add andrewlasiter/fda-predicate-assistant-plugin
/plugin install fda-predicate-assistant@fda-tools
```

Start a new session to load the plugin.

### Claude Desktop

In the Claude Desktop chat window, type the same two commands:

```
/plugin marketplace add andrewlasiter/fda-predicate-assistant-plugin
/plugin install fda-predicate-assistant@fda-tools
```

Restart the session after installing.

### Co-work / Autonomous Sessions

Co-work uses your existing plugin installation — install from Claude Code or Desktop first (steps above). Once installed, the plugin is automatically available in all Co-work sessions.

Use the `--full-auto` flag so the pipeline runs without prompts:

```
/fda:pipeline OVE --project my-device --full-auto \
  --device-description "Cervical interbody fusion cage" \
  --intended-use "For fusion of the cervical spine"
```

### Verify It Works

Type `/fda:status` — you should see a summary of available FDA data files, script availability, and record counts.

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
| `/fda:guidance` | Finds relevant FDA guidance documents and maps them to testing requirements |
| `/fda:test-plan` | Generates a risk-based testing plan with gap analysis |
| `/fda:presub` | Creates a Pre-Submission meeting package (cover letter, topics, questions) |

### Document Generation

| Command | What it does |
|---------|-------------|
| `/fda:submission-outline` | Builds a full 510(k) submission outline with section checklists and gap analysis |
| `/fda:compare-se` | Generates substantial equivalence comparison tables, auto-populated from FDA data |
| `/fda:draft` | Writes regulatory prose for submission sections with citations |
| `/fda:pccp` | Creates a Predetermined Change Control Plan for AI/ML or iterative devices |

### Assembly & Validation

| Command | What it does |
|---------|-------------|
| `/fda:assemble` | Assembles an eSTAR-structured submission package from your project data |
| `/fda:traceability` | Generates a requirements traceability matrix (guidance → risks → tests → evidence) |
| `/fda:consistency` | Validates that device descriptions, intended use, and predicates match across all files |
| `/fda:portfolio` | Cross-project dashboard — shared predicates, common guidance, submission timelines |

### Full Pipeline

| Command | What it does |
|---------|-------------|
| `/fda:pipeline` | Runs all stages autonomously: extract → review → safety → guidance → presub → outline → SE |

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

See [releases](https://github.com/andrewlasiter/fda-predicate-assistant-plugin/releases) for version history.

## License

MIT
