# FDA Predicate Assistant Plugin

A Claude Code plugin for FDA 510(k) predicate extraction and analysis. This plugin integrates with the Python-based PredicateExtraction tool to help regulatory professionals analyze medical device submissions.

## Features

- **Extract predicates** from FDA 510(k) PDF documents
- **Validate device numbers** against official FDA databases
- **Analyze results** with comprehensive statistics and pattern detection
- **FDA knowledge** for understanding regulatory context

## Installation

The plugin is installed at `~/.claude/plugins/fda-predicate-assistant/`

### Prerequisites

1. Python 3.x with required packages:
   ```bash
   pip install requests tqdm PyMuPDF pdfplumber orjson ijson
   ```

2. The PredicateExtraction Python tool (Test69a_final_ocr_smart_v2.py)

3. FDA database files (downloaded automatically by the tool)

## Commands

### `/fda:extract`

Run predicate extraction on PDF documents.

```
/fda:extract [directory] [--year YEAR] [--product-code CODE] [--ocr MODE]
```

**Arguments:**
- `directory` - Path to PDFs (optional, uses GUI if omitted)
- `--year YEAR` - Filter by year (e.g., 2024)
- `--product-code CODE` - Filter by FDA product code (e.g., DXY)
- `--ocr MODE` - OCR mode: smart (default), always, never

**Examples:**
```
/fda:extract /path/to/pdfs
/fda:extract --year 2024
/fda:extract --product-code DXY --ocr always
```

### `/fda:validate`

Validate FDA device numbers against official databases.

```
/fda:validate K240717
/fda:validate K240717 K235892 P190001
```

Checks K-numbers against pmn*.txt and P-numbers against pma.txt.

### `/fda:analyze`

Analyze extraction results with statistics, patterns, and recommendations.

```
/fda:analyze
/fda:analyze /path/to/output.csv
```

Provides:
- Statistical summary (totals, averages, distributions)
- Pattern detection (common predicates, clusters)
- Anomaly flagging (potential issues)
- Recommendations (next steps)

### `/fda:configure`

View or modify plugin settings.

```
/fda:configure --show
/fda:configure --set ocr_mode always
```

**Available settings:**
| Setting | Default | Description |
|---------|---------|-------------|
| ocr_mode | smart | OCR processing mode |
| batch_size | 100 | PDFs per batch |
| workers | 4 | Parallel workers |
| cache_days | 5 | Database cache duration |

## Agent: extraction-analyzer

The extraction-analyzer agent automatically provides comprehensive analysis after running extractions. It can also be triggered by asking to analyze FDA extraction results.

**Capabilities:**
- Statistical analysis of extraction results
- Pattern recognition in predicate citations
- Quality assessment and anomaly detection
- Regulatory context and explanations
- Actionable recommendations

## Skill: FDA 510(k) Knowledge

The plugin includes FDA regulatory expertise that activates when discussing:
- 510(k) submissions and clearances
- Predicate device selection
- Substantial equivalence
- Device classification (Class I, II, III)
- Product codes and medical specialties

Ask questions like:
- "What is a predicate device?"
- "Explain device Class II"
- "What makes a valid predicate?"

## File Structure

```
fda-predicate-assistant/
├── .claude-plugin/
│   └── plugin.json              # Plugin manifest
├── commands/
│   ├── extract.md               # /fda:extract command
│   ├── validate.md              # /fda:validate command
│   ├── analyze.md               # /fda:analyze command
│   └── configure.md             # /fda:configure command
├── agents/
│   └── extraction-analyzer.md   # Results analyzer
├── skills/
│   └── fda-510k-knowledge/
│       ├── SKILL.md             # FDA regulatory knowledge
│       └── references/
│           ├── device-classes.md
│           ├── predicate-types.md
│           └── common-issues.md
├── scripts/
│   └── run-extraction.sh        # Python wrapper
└── README.md
```

## Configuration File

User settings are stored in `~/.claude/fda-predicate-assistant.local.md`

Example:
```markdown
---
ocr_mode: smart
batch_size: 100
workers: 4
python_script_path: ~/fda-510k-data/extraction/Test69a_final_ocr_smart_v2.py
---

# FDA Predicate Assistant Settings
Personal configuration notes here.
```

## Troubleshooting

### Python script not found

Set the path in your settings:
```
/fda:configure --set python_script_path /path/to/Test69a_final_ocr_smart_v2.py
```

### OCR not working

Ensure PyMuPDF is installed:
```bash
pip install PyMuPDF
```

Try forcing OCR mode:
```
/fda:extract --ocr always
```

### Validation fails

FDA databases may need to be downloaded:
- The extraction tool downloads these automatically
- Files are cached for 5 days
- Check internet connectivity

### Low extraction rate

- Use `/fda:analyze` to identify patterns in failures
- Check if documents are Statements vs Summaries
- Try `--ocr always` for scanned documents

## License

Part of the PredicateExtraction project.
