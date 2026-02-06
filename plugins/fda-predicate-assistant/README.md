# FDA Predicate Assistant

A Claude Code plugin that helps you navigate FDA 510(k) submissions. It finds predicate devices, validates device numbers, analyzes safety data, and builds substantial equivalence comparisons — all from within Claude.

## Install

```
/plugin marketplace add andrewlasiter/fda-predicate-assistant-plugin
/plugin install fda-predicate-assistant@fda-tools
```

## What it does

### Core Pipeline

| Command | Purpose |
|---------|---------|
| `/fda:pipeline` | Run the full 7-step pipeline autonomously (extract → review → safety → guidance → presub → outline → SE) |
| `/fda:extract` | Download 510(k) PDFs and extract predicate relationships |
| `/fda:review` | Score, flag, and accept/reject extracted predicates |
| `/fda:safety` | MAUDE adverse events and recall history for a product code |
| `/fda:guidance` | Look up FDA guidance documents and map to testing requirements |
| `/fda:presub` | Generate a Pre-Submission meeting package |
| `/fda:submission-outline` | Generate a full 510(k) submission outline with gap analysis |
| `/fda:compare-se` | Generate substantial equivalence comparison tables |

### Research and Analysis

| Command | Purpose |
|---------|---------|
| `/fda:research` | Full submission research — predicates, testing, competitive landscape |
| `/fda:validate` | Look up any device number (K, P, DEN, N) against FDA databases |
| `/fda:analyze` | Statistics and patterns across your extraction results |
| `/fda:summarize` | Compare sections (testing, IFU, device description) across devices |
| `/fda:ask` | Natural language Q&A about FDA regulatory topics |

### Planning and Decision Support

| Command | Purpose |
|---------|---------|
| `/fda:pathway` | Recommend the optimal regulatory pathway with algorithmic scoring |
| `/fda:test-plan` | Generate a risk-based testing plan with gap analysis |
| `/fda:pccp` | Generate a Predetermined Change Control Plan (AI/ML devices) |
| `/fda:monitor` | Watch FDA databases for new clearances, recalls, and MAUDE events |

### Assembly and Management

| Command | Purpose |
|---------|---------|
| `/fda:assemble` | Assemble an eSTAR-structured submission package from project data |
| `/fda:portfolio` | Cross-project dashboard — shared predicates, common guidance, timelines |
| `/fda:configure` | Set up API keys, data paths, and preferences |
| `/fda:status` | Check what data you have and what's available |

## Important Notices

> **This tool is provided for research purposes only.** It analyzes publicly
> available FDA data (510(k) summaries, classification databases, MAUDE reports,
> and other records published by the U.S. Food and Drug Administration).

> **Do not use this tool with private, confidential, or IP-protected documents.**
> All text you provide — including device descriptions, intended use statements,
> and file contents — is processed by Claude (Anthropic's LLM). Depending on
> your Anthropic account settings, this content may be used for model training.
> Even when training is disabled, there is no independent means to verify that
> data is excluded. Do not submit trade secrets, proprietary designs, or
> confidential regulatory strategies.

> **LLM accuracy is not guaranteed.** Large language models make mistakes.
> Device number extraction, predicate identification, section classification,
> and all other outputs may contain errors, omissions, or hallucinations.
> **Always independently verify** every device number, predicate relationship,
> regulatory citation, and testing recommendation before relying on it.
> Inaccuracy is inherent to this technology — treat all output as a starting
> point for human review, not a finished product.

> **This is not legal or regulatory advice.** Consult qualified regulatory
> affairs professionals and legal counsel before making submission decisions.
> The developers and Anthropic accept no liability for regulatory outcomes
> based on this tool's output.

## Autonomous mode

The plugin can run fully headless with zero user prompts — ideal for co-work sessions and automated workflows:

```
/fda:pipeline OVE --project my-device --full-auto \
  --device-description "Cervical interbody fusion cage" \
  --intended-use "For fusion of the cervical spine"
```

Key autonomy flags:
- `--full-auto` — Deterministic decisions based on score thresholds (never prompts)
- `--infer` — Auto-detect product code from project data
- `--headless` — Non-interactive mode for Python scripts

## Quick start

```
/fda:status                          # See what data is available
/fda:validate K241335                # Look up a device
/fda:research QAS                    # Full research for a product code
/fda:pipeline OVE --project demo     # Run full pipeline for a product code
/fda:ask "What class is a cervical fusion cage?"  # Regulatory Q&A
```

## openFDA API

The plugin works offline using FDA flat files, but connects to all 7 openFDA Device API endpoints when available — giving you real-time access to clearances, classifications, adverse events, recalls, and more.

Set up an API key for higher rate limits (optional):
```
/fda:configure --setup-key
```

## Data pipeline

The plugin bundles two Python scripts for batch processing:

1. **BatchFetch** — Filter the FDA catalog and download 510(k) PDFs
2. **Predicate Extractor** — Extract device numbers from PDFs with OCR error correction

Run `/fda:extract` to use either or both stages.

## Requirements

- Claude Code 1.0.33+
- Python 3.x (for extraction scripts)
- `pip install requests tqdm PyMuPDF pdfplumber` (for PDF processing)

## License

MIT
