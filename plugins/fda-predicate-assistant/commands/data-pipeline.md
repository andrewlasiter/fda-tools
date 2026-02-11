---
description: Run the 510(k) data maintenance pipeline — gap analysis, download missing PDFs, extract predicates, and merge results
allowed-tools: Bash, Read, Glob, Grep, Write
argument-hint: "[status|analyze|download|extract|merge|run] [--years RANGE] [--product-codes CODES] [--dry-run]"
---

# FDA 510(k) Data Maintenance Pipeline

> **Important**: This command assists with FDA regulatory workflows but does not provide regulatory advice. Output should be reviewed by qualified regulatory professionals before being relied upon for submission decisions.

> For external API dependencies and connection status, see [CONNECTORS.md](../CONNECTORS.md).

## Resolve Plugin Root

**Before running any bash commands that reference `$FDA_PLUGIN_ROOT`**, resolve the plugin install path:

```bash
FDA_PLUGIN_ROOT=$(python3 -c "
import json, os
f = os.path.expanduser('~/.claude/plugins/installed_plugins.json')
if os.path.exists(f):
    d = json.load(open(f))
    for k, v in d.get('plugins', {}).items():
        if k.startswith('fda-predicate-assistant@'):
            for e in v:
                p = e.get('installPath', '')
                if os.path.isdir(p):
                    print(p); exit()
print('')
")
echo "FDA_PLUGIN_ROOT=$FDA_PLUGIN_ROOT"
```

If `$FDA_PLUGIN_ROOT` is empty, report an error: "Could not locate the FDA Predicate Assistant plugin installation. Make sure the plugin is installed and enabled."

---

You are running the **data maintenance pipeline** — a 4-step process for keeping the local 510(k) corpus up to date:

1. **Analyze** — Gap analysis: cross-reference FDA PMN database vs existing data to find what's missing
2. **Download** — Fetch missing PDF summaries from FDA with rate limiting and resume support
3. **Extract** — Extract predicate device numbers from downloaded PDFs
4. **Merge** — Merge per-year extraction CSVs into the master baseline CSV

**This is NOT the regulatory submission pipeline** (`/fda:pipeline`). This command manages the raw data that feeds into all other plugin commands.

## Determine Subcommand

Parse `$ARGUMENTS` for the subcommand and flags:

- `status` — Show pipeline state (read-only, no changes)
- `analyze` — Step 1 only: run gap analysis
- `download` — Step 2 only: download missing PDFs
- `extract` — Step 3 only: extract predicates from PDFs
- `merge` — Step 4 only: merge extraction CSVs
- `run` — Run all 4 steps in sequence
- No subcommand → default to `status`

### Common flags (parsed from arguments):
- `--years RANGE` — Year filter (e.g., `2024,2025` or `2020-2025`)
- `--product-codes CODES` — Product code filter (e.g., `KGN,DXY`)
- `--dry-run` — Show what would happen without executing
- `--incremental` — Skip years already up to date (extract/run only)

### Download-specific flags:
- `--delay N` — Seconds between downloads (default: 10)
- `--max-retries N` — Max retries per file (default: 3)

### Extract-specific flags:
- `--workers N` — Parallel extraction workers
- `--batch-size N` — Process PDFs in batches of N

### Run-specific flags:
- `--skip-analyze` — Skip gap analysis step
- `--skip-download` — Skip download step

## Locate Data Directories

Check settings and auto-detect the data layout:

```bash
cat ~/.claude/fda-predicate-assistant.local.md 2>/dev/null
```

### Standard Layout Detection

The pipeline expects this directory structure:

```
{repo_dir}/                    ← Scripts, PMN files, manifests
├── gap_analysis.py            ← [BUNDLED] Also at $FDA_PLUGIN_ROOT/scripts/
├── gap_downloader.py          ← [REPO ONLY] Not bundled in plugin
├── Test69a_final_ocr_smart_v2.py ← [REPO ONLY] Not bundled in plugin
├── merge_outputs.py           ← [REPO ONLY] Not bundled in plugin
├── pipeline.py                ← [REPO ONLY] Orchestrator, not bundled
├── pmn96cur.txt               ← FDA PMN database
├── gap_manifest.csv           ← Gap analysis output
└── download_progress.json     ← Download resume state
{pdf_dir}/                     ← PDF corpus + baseline CSV
├── 510k_output.csv            ← Baseline extraction results
├── 510k_output_updated.csv    ← Merged results
└── {YEAR}/                    ← PDFs organized by year
    └── {Applicant}/{ProductCode}/{Type}/{K-number}.pdf
```

**Script availability:**

| Script | Bundled in Plugin? | Fallback |
|--------|--------------------|----------|
| `gap_analysis.py` | Yes (`$FDA_PLUGIN_ROOT/scripts/`) | — |
| `predicate_extractor.py` | Yes (`$FDA_PLUGIN_ROOT/scripts/`) | — |
| `pipeline.py` | No | Run steps individually using bundled scripts |
| `gap_downloader.py` | No | Use `/fda:extract` stage 1 (batchfetch.py) or download manually |
| `merge_outputs.py` | No | Simple CSV merge (inline Python below) |
| `Test69a_final_ocr_smart_v2.py` | No | Use bundled `predicate_extractor.py` instead |

Paths are resolved from settings (`~/.claude/fda-predicate-assistant.local.md`):
- `repo_dir` — from `extraction_dir` setting (default: `~/fda-510k-data/extraction`)
- `pdf_dir` — from `pdf_dir` setting (default: `~/fda-510k-data/pdfs`)

Auto-detect paths:

```bash
python3 -c "
import os, re

# Resolve paths from settings
settings_path = os.path.expanduser('~/.claude/fda-predicate-assistant.local.md')
repo = os.path.expanduser('~/fda-510k-data/extraction')
dl = os.path.expanduser('~/fda-510k-data/pdfs')
if os.path.exists(settings_path):
    with open(settings_path) as f:
        content = f.read()
    m = re.search(r'extraction_dir:\s*(.+)', content)
    if m: repo = os.path.expanduser(m.group(1).strip())
    m = re.search(r'pdf_dir:\s*(.+)', content)
    if m: dl = os.path.expanduser(m.group(1).strip())

checks = {
    'PIPELINE_SCRIPT': os.path.join(repo, 'pipeline.py'),
    'GAP_ANALYSIS': os.path.join(repo, 'gap_analysis.py'),
    'GAP_DOWNLOADER': os.path.join(repo, 'gap_downloader.py'),
    'EXTRACTOR': os.path.join(repo, 'Test69a_final_ocr_smart_v2.py'),
    'MERGE_SCRIPT': os.path.join(repo, 'merge_outputs.py'),
    'PMN_FILE': os.path.join(repo, 'pmn96cur.txt'),
    'BASELINE_CSV': os.path.join(dl, '510k_output_updated.csv'),
    'PDF_DIR': dl,
}
for k, v in checks.items():
    exists = os.path.exists(v)
    print(f'{k}:{\"OK\" if exists else \"MISSING\"}:{v}')

# Check bundled scripts as fallback
print()
print('BUNDLED_SCRIPTS:')
for script in ['gap_analysis.py', 'predicate_extractor.py', 'batchfetch.py']:
    # FDA_PLUGIN_ROOT resolved by caller
    print(f'  {script}: available in $FDA_PLUGIN_ROOT/scripts/')
"
```

If `pipeline.py` is found, use it as the orchestrator. If not, fall back to running individual scripts via `$FDA_PLUGIN_ROOT/scripts/gap_analysis.py` for the analyze step.

**CRITICAL**: The `--pdf-dir` and `--baseline` must point to the `download/510k/` directory, NOT to `PredicateExtraction/`. The bulk PDF corpus lives in `download/510k/`.

## Running Subcommands

### Using pipeline.py (preferred)

If `pipeline.py` exists at the detected path, use it directly:

```bash
REPO_DIR="$REPO_DIR"  # Resolved from settings above
python3 "$REPO_DIR/pipeline.py" {subcommand} {flags}
```

Examples:
- `python3 "$REPO_DIR/pipeline.py" status`
- `python3 "$REPO_DIR/pipeline.py" analyze --years 2025 --product-codes KGN`
- `python3 "$REPO_DIR/pipeline.py" download --delay 10`
- `python3 "$REPO_DIR/pipeline.py" extract --years 2024,2025 --incremental`
- `python3 "$REPO_DIR/pipeline.py" merge`
- `python3 "$REPO_DIR/pipeline.py" run --years 2025 --dry-run`

### Fallback: Using Plugin Scripts

If `pipeline.py` is not found, run steps individually using the plugin's bundled scripts:

**Analyze** (Step 1):
```bash
python3 "$FDA_PLUGIN_ROOT/scripts/gap_analysis.py" \
  --years "$YEARS" \
  --product-codes "$PRODUCT_CODES" \
  --pmn-files "$PMN_FILES" \
  --baseline "$BASELINE_CSV" \
  --pdf-dir "$PDF_DIR" \
  --output "$REPO_DIR/gap_manifest.csv"
```

**Download** (Step 2):
If `gap_downloader.py` is available in the repo:
```bash
python3 "$REPO_DIR/gap_downloader.py" --delay 10
```
If not available, use the plugin's bundled batchfetch.py:
```bash
python3 "$FDA_PLUGIN_ROOT/scripts/batchfetch.py" \
  --input "$REPO_DIR/gap_manifest.csv" \
  --output-dir "$PDF_DIR/$YEAR" \
  --delay 10
```
Or guide the user: "gap_downloader.py is not bundled with the plugin. Either install the PredicateExtraction repo or use `/fda:extract` stage 1 for batch downloading."

**Extract** (Step 3) — uses the plugin's predicate_extractor.py:
```bash
python3 "$FDA_PLUGIN_ROOT/scripts/predicate_extractor.py" \
  --directory "$PDF_DIR/$YEAR" \
  --output-dir "$PDF_DIR/$YEAR"
```

**Merge** (Step 4):
If `merge_outputs.py` is available in the repo:
```bash
python3 "$REPO_DIR/merge_outputs.py"
```
If not available, use inline Python to merge per-year CSVs:
```bash
python3 << 'PYEOF'
import csv, os, glob

pdf_dir = "PDF_DIR"  # Replace with resolved path
baseline = os.path.join(pdf_dir, "510k_output.csv")
updated = os.path.join(pdf_dir, "510k_output_updated.csv")

# Collect all per-year output.csv files
year_csvs = sorted(glob.glob(os.path.join(pdf_dir, "*/output.csv")))
print(f"Found {len(year_csvs)} per-year CSVs to merge")

# Read baseline — preserve the original header if present
rows = {}
source_header = None
if os.path.exists(baseline):
    with open(baseline, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        source_header = next(reader, None)
        for row in reader:
            if row:
                rows[row[0]] = row

# Merge per-year results (newer overwrites older)
for ycsv in year_csvs:
    with open(ycsv, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        yheader = next(reader, None)
        # Use the widest header we encounter as the source header
        if yheader and (source_header is None or len(yheader) > len(source_header)):
            source_header = yheader
        for row in reader:
            if row:
                rows[row[0]] = row

# Write merged output
if rows:
    max_cols = max(len(r) for r in rows.values())

    # Build the correct header.
    # predicate_extractor.py outputs:
    #   510(k), Product Code, Predicate 1, Predicate 2, ..., Reference Device 1, ...
    if source_header and len(source_header) >= max_cols:
        header = source_header[:max_cols]
    elif source_header and len(source_header) >= 2:
        # Extend the source header to cover all columns
        header = list(source_header)
        # Count how many Predicate and Reference Device columns exist
        n_pred = sum(1 for h in source_header if h.startswith('Predicate '))
        n_ref = sum(1 for h in source_header if h.startswith('Reference Device '))
        extra_needed = max_cols - len(header)
        # Extend Reference Device columns first (most common growth)
        for i in range(extra_needed):
            header.append(f'Reference Device {n_ref + i + 1}')
    else:
        # No source header available — reconstruct from scratch.
        # Scan merged data to find the boundary between predicates and
        # reference devices.  predicate_extractor.py puts all Predicate
        # columns first (starting at col 2), then Reference Device columns.
        # Without type info we estimate: use half the remaining cols for
        # each category, matching the most common extraction profile.
        remaining = max_cols - 2
        n_pred = max(remaining // 2, 1)
        n_ref = remaining - n_pred
        header = ['510(k)', 'Product Code'] \
            + [f'Predicate {i+1}' for i in range(n_pred)] \
            + [f'Reference Device {i+1}' for i in range(n_ref)]

    with open(updated, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for k_num in sorted(rows.keys()):
            row = rows[k_num]
            row.extend([''] * (max_cols - len(row)))
            writer.writerow(row)
    print(f"Merged {len(rows)} records → {updated}")
else:
    print("No data to merge")
PYEOF
```

## Output Format

Present results using the standard FDA Professional CLI format:

### Status Output

```
  FDA Data Pipeline Status
  510(k) Corpus Overview
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: {date} | v5.22.0

BASELINE
────────────────────────────────────────

  | Dataset      | Records  |
  |--------------|----------|
  | Baseline CSV | {N}      |
  | Updated CSV  | {N}      |

GAP ANALYSIS
────────────────────────────────────────

  | Metric                  | Count |
  |-------------------------|-------|
  | Total in PMN database   | {N}   |
  | Already extracted       | {N}   |
  | Have PDF, need extract  | {N}   |
  | Need download           | {N}   |

DOWNLOAD PROGRESS
────────────────────────────────────────

  | Status    | Count |
  |-----------|-------|
  | Success   | {N}   |
  | 404       | {N}   |
  | Failed    | {N}   |
  | Remaining | {N}   |

PER-YEAR SUMMARY
────────────────────────────────────────

  | Year | PDFs  | Extracted | Status          |
  |------|-------|-----------|-----------------|
  | 2023 | 3,158 | 3,080     | Partial (78)    |
  | 2024 | 2,854 | 2,854     | Complete        |
  | 2025 | 355   | 349       | Partial (6)     |

NEXT STEPS
────────────────────────────────────────

  {Context-dependent recommendations:}
  - If gaps exist: `/fda:data-pipeline analyze` then `/fda:data-pipeline download`
  - If PDFs unextracted: `/fda:data-pipeline extract --years YEAR`
  - If extractions unmerged: `/fda:data-pipeline merge`
  - If everything up to date: "Corpus is current. No action needed."

────────────────────────────────────────
  This report is AI-generated from public FDA data.
  Verify independently. Not regulatory advice.
────────────────────────────────────────
```

### Run/Step Output

For individual steps or full run, display the raw script output and then summarize with the CLI format after completion.

## Long-Running Operations

**Downloads and extractions can take hours.** For these steps:

1. Run the script in the background when appropriate
2. Inform the user of estimated time
3. Note that progress is saved automatically — safe to interrupt and resume later
4. Show how to check progress: `python3 pipeline.py status`

## Error Handling

- If `pipeline.py` not found → Fall back to bundled scripts (`gap_analysis.py`, `predicate_extractor.py`, `batchfetch.py`) + inline merge. Non-bundled scripts (`gap_downloader.py`, `merge_outputs.py`, `Test69a_final_ocr_smart_v2.py`) require the PredicateExtraction repo.
- If PMN files not found → Guide to download from FDA or run `/fda:extract stage1`
- If download/510k directory not found → Guide to create it and run initial batch fetch
- If extraction fails for a year → Log and continue to next year (pipeline doesn't halt)
- If merge fails → Show the individual per-year CSVs that can be used directly
