---
description: Analyze FDA data from any pipeline stage — extraction results, download metadata, predicate relationships, or device lookups
allowed-tools: Read, Glob, Grep, Bash, Write
argument-hint: "[--project NAME | file-path | product-code | K-number]"
---

# FDA Multi-Source Data Analysis

> **Important**: This command assists with FDA regulatory workflows but does not provide regulatory advice. Output should be reviewed by qualified regulatory professionals before being relied upon for submission decisions.

> For external API dependencies and connection status, see [CONNECTORS.md](../CONNECTORS.md).

You are analyzing FDA 510(k) data from across the full pipeline. Multiple data sources may be available — adapt your analysis to whatever exists.

## Data Source Locations

| File | Location | Description |
|------|----------|-------------|
| `510k_download.csv` | `~/fda-510k-data/batchfetch/` | 510kBF metadata (24 cols: KNUMBER, APPLICANT, DECISIONDATE, PRODUCTCODE, TYPE, STATEORSUMM, REVIEWADVISECOMM, THIRDPARTY, EXPEDITEDREVIEW, etc.) |
| `Applicant_ProductCode_Tables.xlsx` | `~/fda-510k-data/batchfetch/` | Analytics workbook (3 sheets: Applicant, ProductCode, Full data) |
| `merged_data.csv` | `~/fda-510k-data/batchfetch/` | K-number + up to 6 predicates (7 cols) |
| `output.csv` | `~/fda-510k-data/extraction/` | Extraction results: K-number, ProductCode, Predicate1..PredicateN |
| `supplement.csv` | `~/fda-510k-data/extraction/` | Devices with supplement suffixes |
| `pdf_data.json` | `~/fda-510k-data/extraction/` | Cached PDF text keyed by filename |
| `error_log.txt` | `~/fda-510k-data/extraction/` | Failed PDFs |
| `pmn*.txt` | `~/fda-510k-data/extraction/` or `fda_data/` | FDA 510(k) database flat files |
| `foiaclass.txt` | `~/fda-510k-data/batchfetch/fda_data/` | FDA device classification data |

**Note:** FDA database files may also be in configurable `--data-dir` locations. Check `~/.claude/fda-predicate-assistant.local.md` for configured paths.

## Project Support

If `--project NAME` is provided, look for data in the project folder first:

```bash
PROJECTS_DIR="~/fda-510k-data/projects"  # or from settings
ls "$PROJECTS_DIR/$PROJECT_NAME/" 2>/dev/null
cat "$PROJECTS_DIR/$PROJECT_NAME/query.json" 2>/dev/null
```

When a project is specified, use its data files (510k_download.csv, output.csv, pdf_data.json, etc.) instead of the legacy global locations. Also read `query.json` to understand the query context.

If no project is specified, fall back to legacy locations.

## Parse Arguments

Determine the analysis mode from `$ARGUMENTS`:

1. **File path** (contains `/` or `.csv` or `.json`) → Analyze that specific file
2. **Device number** (matches K-number `K\d{6}`, P-number `P\d{6}`, DEN number `DEN\d{6}`, or N-number `N\d{4,5}`) → Look up that device across all sources
3. **Product code** (3 uppercase letters like `KGN`) → Filter all data by that code
4. **Device/company name** (text string) → Search all data sources for matches
5. **No arguments** → Discover all available data and provide a comprehensive overview

## Step 1: Discover Available Data

Always start by checking which data files exist:

```bash
ls -la ~/fda-510k-data/batchfetch/510k_download.csv ~/fda-510k-data/batchfetch/merged_data.csv ~/fda-510k-data/extraction/output.csv ~/fda-510k-data/extraction/supplement.csv ~/fda-510k-data/extraction/pdf_data.json ~/fda-510k-data/extraction/error_log.txt 2>/dev/null
```

**Only report sources that have relevant data for the user's query.** If a file exists but contains no records matching the user's product code or device, skip it silently. Don't list empty or irrelevant files.

## Step 2: Analyze Based on Available Sources

### If `510k_download.csv` exists → Metadata Analysis
- Total records and date range
- Applicant distribution (top companies by submission count)
- Product code distribution
- Advisory committee breakdown
- Decision code summary (SESE, SEKN, etc.)
- Review time statistics (mean, median, min, max)
- Third-party review usage
- Expedited review usage
- Statement vs Summary distribution

### Predicate Analysis (from `output.csv` OR extracted from `pdf_data.json`)

If `output.csv` exists, use it directly. If it does NOT exist but `pdf_data.json` does, **extract predicates inline** by scanning PDF text for device number citations (regex `\b(?:K\d{6}|P\d{6}|DEN\d{6}|N\d{4,5})\b` with case-insensitive matching). Do NOT tell the user to run a separate command.

- Total submissions analyzed and unique predicates found
- Average predicates per submission
- Most frequently cited predicate devices (predicate hubs)
- Predicate chains (A→B→C relationships)
- Submissions with high predicate counts (>10)
- Submissions with zero predicates (may need review)
- Product code clustering
- Document type breakdown (Statement vs Summary)

### If both `510k_download.csv` AND `output.csv` exist → Cross-Reference Analysis
- Match predicates to their metadata (applicant, date, product code)
- Identify predicate age (how old are the cited predicates?)
- Cross-validate product codes between sources
- Find devices in download list that are also cited as predicates
- Review time correlation with predicate count

### If `merged_data.csv` exists → Predicate Relationship Analysis
- Direct predicate mapping (K-number → up to 6 predicates)
- Build predicate chains across generations
- Identify most-cited predicate hubs

### If `pdf_data.json` exists → Text Availability Report
- How many PDFs have cached text
- Text extraction coverage percentage
- Can offer deep-dive into specific device's PDF text

### If `supplement.csv` exists → Supplement Analysis
- Count of supplement devices
- Which base devices have supplements
- Supplement numbering patterns

## Step 3: Targeted Lookups

If the user provided a specific device, product code, or company name:

1. Search ALL available data sources for matches
2. Aggregate findings into a single device profile
3. Show: metadata, predicates, related devices, PDF text availability
4. For company names: show all their submissions and common predicates

## Output Format

Present the analysis using the standard FDA Professional CLI format (see `references/output-formatting.md`):

```
  FDA Data Analysis Report
  {product_code} — {device_name} (or {analysis_mode})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: {date} | Project: {name} | v5.22.0

DATA SOURCES
────────────────────────────────────────

  | Source             | Records | Freshness |
  |--------------------|---------|-----------|
  | 510k_download.csv  | {N}     | {date}    |
  | output.csv         | {N}     | {date}    |
  | pdf_data.json      | {N}     | {date}    |

EXECUTIVE SUMMARY
────────────────────────────────────────

  {Key findings in 2-3 sentences}

STATISTICS
────────────────────────────────────────

  | Metric                        | Value |
  |-------------------------------|-------|
  | Total submissions analyzed    | {N}   |
  | Unique predicates found       | {N}   |
  | Avg predicates per submission | {N}   |
  | Zero-predicate submissions    | {N}   |

PREDICATE HUBS
────────────────────────────────────────

  | K-Number | Citations | Applicant  | Year |
  |----------|-----------|------------|------|
  | {kn}     | {count}   | {company}  | {yr} |

NOTABLE PATTERNS
────────────────────────────────────────

  {Interesting relationships discovered}

ISSUES FOUND
────────────────────────────────────────

  {Problems requiring attention — OCR errors, missing data, etc.}

NEXT STEPS
────────────────────────────────────────

  1. Review predicate scoring — `/fda:review --project NAME`
  2. Run safety analysis — `/fda:safety --product-code CODE`
  3. Trace predicate lineage — `/fda:lineage --project NAME`

────────────────────────────────────────
  This report is AI-generated from public FDA data.
  Verify independently. Not regulatory advice.
────────────────────────────────────────
```

## Step 4: API Enrichment (Optional)

**If the openFDA API is enabled** and the user is analyzing a specific product code or K-number, offer to enrich the analysis with live API data:

### MAUDE Event Counts per Device

When analyzing predicate relationships, add adverse event context from the API:

```bash
python3 << 'PYEOF'
import urllib.request, urllib.parse, json, os, re

settings_path = os.path.expanduser('~/.claude/fda-predicate-assistant.local.md')
api_key = os.environ.get('OPENFDA_API_KEY')  # Env var takes priority (never enters chat)
api_enabled = True
if os.path.exists(settings_path):
    with open(settings_path) as f:
        content = f.read()
    if not api_key:  # Only check file if env var not set
        m = re.search(r'openfda_api_key:\s*(\S+)', content)
        if m and m.group(1) != 'null':
            api_key = m.group(1)
    m = re.search(r'openfda_enabled:\s*(\S+)', content)
    if m and m.group(1).lower() == 'false':
        api_enabled = False

if not api_enabled:
    print("API_SKIP:disabled")
    exit(0)

product_code = "PRODUCTCODE"  # Replace

# Event count by type for this product code
params = {"search": f'device.device_report_product_code:"{product_code}"', "limit": "1", "count": "event_type.exact"}
if api_key:
    params["api_key"] = api_key
url = f"https://api.fda.gov/device/event.json?{urllib.parse.urlencode(params)}"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/5.21.0)"})
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
        if data.get("results"):
            total = sum(r["count"] for r in data["results"])
            print(f"MAUDE_TOTAL:{total}")
            for r in data["results"]:
                print(f"EVENT_TYPE:{r['term']}:{r['count']}")
except:
    print("MAUDE_ERROR:unreachable")
PYEOF
```

Include this as an "Adverse Event Context" subsection when analyzing product codes or predicate hubs. Flag devices or product codes with disproportionately high event counts.

## Tips

- Use `wc -l` for quick row counts on large CSV files
- Use `head -1` to read column headers before parsing
- For large files, use Grep to search rather than reading the whole file
- Cross-reference K-numbers between sources to build complete device profiles
- If the openFDA API is available, use it to enrich analysis with MAUDE event counts and recall data
