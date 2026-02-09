---
description: Analyze gaps in 510(k) data — identify missing K-numbers, PDFs needing download, and extractions not yet processed
allowed-tools: Bash, Read, Glob, Grep, Write
argument-hint: "[--years RANGE] [--product-codes CODES] [--project NAME]"
---

# FDA 510(k) Gap Analysis

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

You are running a **3-way gap analysis** that cross-references:

1. **FDA PMN database** (pmn96cur.txt / pmnlstmn.txt) — the authoritative catalog of all 510(k) submissions
2. **Existing extraction CSV** (output.csv / 510k_output.csv) — K-numbers already processed
3. **Downloaded PDFs on disk** — files already fetched but not yet extracted

This produces a **gap manifest** showing exactly what's missing and what action is needed for each K-number.

## Determine Context

Parse `$ARGUMENTS` for:
- `--years RANGE` — Year filter (e.g., `2024,2025` or `2020-2025`)
- `--product-codes CODES` — Product code filter (e.g., `KGN,DXY`)
- `--prefixes PREFIXES` — K-number prefix override (e.g., `K24,K25,DEN`)
- `--project NAME` — Run gap analysis within a project context
- `--baseline PATH` — Custom baseline CSV path
- `--pdf-dir PATH` — Custom PDF directory path

## Project Context

Check settings file for custom paths:
```bash
cat ~/.claude/fda-predicate-assistant.local.md 2>/dev/null
```

### If `--project NAME` is provided

Look for the project's data to use as baseline and PDF directory:
```bash
PROJECTS_DIR="${PROJECTS_DIR:-$HOME/fda-510k-data/projects}"
PROJECT_DIR="$PROJECTS_DIR/$PROJECT_NAME"
```

Use project paths:
- Baseline CSV: `$PROJECT_DIR/output.csv`
- PDF directory: `$PROJECT_DIR/510ks`
- PMN data files: `$PROJECT_DIR/fda_data/pmn96cur.txt` (if exists, else system default)
- Output manifest: `$PROJECT_DIR/gap_manifest.csv`

### If no project specified

Use the system-level data directory. Check for the standard PredicateExtraction repo layout:
- Look for PMN files in: current directory, `~/fda-510k-data/`, or common paths
- Baseline CSV: auto-detect from `510k_output.csv` or `510k_output_updated.csv`
- PDF directory: auto-detect from directory structure

## Dependencies Check

The gap analysis script only needs Python standard library (csv, os, re, argparse). No pip install needed.

## Running the Gap Analysis

**Script:** `$FDA_PLUGIN_ROOT/scripts/gap_analysis.py`

### CLI Flags

| Flag | Description | Example |
|------|-------------|---------|
| `--years` | Year range or list | `2024,2025` or `2020-2025` |
| `--prefixes` | K-number prefixes (overrides --years) | `K24,K25,DEN` |
| `--product-codes` | Filter to specific product codes | `KGN,DXY` |
| `--baseline` | Baseline CSV path | `/path/to/output.csv` |
| `--pdf-dir` | PDF base directory | `/path/to/pdfs` |
| `--output` | Output manifest path | `/path/to/gap_manifest.csv` |
| `--pmn-files` | Comma-separated PMN database files | `pmn96cur.txt,pmnlstmn.txt` |

### Locating PMN Database Files

The script needs PMN database files from FDA. Search for them:

```bash
python3 -c "
import os, glob
search_paths = [
    os.path.expanduser('~/fda-510k-data'),
    os.path.expanduser('~/fda-510k-data/extraction'),
    os.getcwd(),
]
for base in search_paths:
    for name in ['pmn96cur.txt', 'pmnlstmn.txt']:
        path = os.path.join(base, name)
        if os.path.exists(path):
            size_mb = os.path.getsize(path) / 1024 / 1024
            print(f'FOUND:{name}|{path}|{size_mb:.1f}MB')
print('SEARCH_DONE')
"
```

If no PMN files found, inform the user: "PMN database files (pmn96cur.txt, pmnlstmn.txt) not found. These are needed for gap analysis. You can download them from FDA: https://www.fda.gov/medical-devices/510k-clearances/downloadable-510k-files or run `/fda:extract stage1` which downloads them automatically."

### Running the Script

Build the command with discovered paths and user arguments:

```bash
python3 "$FDA_PLUGIN_ROOT/scripts/gap_analysis.py" \
  --years "$YEARS" \
  --product-codes "$PRODUCT_CODES" \
  --baseline "$BASELINE_CSV" \
  --pdf-dir "$PDF_DIR" \
  --output "$OUTPUT_MANIFEST" \
  --pmn-files "$PMN_FILES"
```

Only include flags that have values (omit empty ones).

## Output Format

Present the results using the standard FDA Professional CLI format:

```
  FDA Gap Analysis
  510(k) Data Completeness Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: {date} | v5.16.0

FILTERS
────────────────────────────────────────

  | Filter        | Value              |
  |---------------|--------------------|
  | Years         | {years or "All"}   |
  | Product codes | {codes or "All"}   |
  | Prefixes      | {prefixes}         |

PMN DATABASE
────────────────────────────────────────

  | Metric                   | Count   |
  |--------------------------|---------|
  | Records matching filters | {N}     |
  | Already extracted (skip) | {N}     |
  | Have PDF, need extract   | {N}     |
  | Need download + extract  | {N}     |
  | Total gaps               | {N}     |

  Completeness: {pct}%

{If product codes specified:}
BY PRODUCT CODE
────────────────────────────────────────

  | Code | Have PDF | Need DL | Total Gap |
  |------|----------|---------|-----------|
  | {pc} | {n}      | {n}     | {n}       |

{If multiple year prefixes:}
BY YEAR PREFIX
────────────────────────────────────────

  | Prefix | Have PDF | Need DL | Total Gap |
  |--------|----------|---------|-----------|
  | K24    | {n}      | {n}     | {n}       |
  | K25    | {n}      | {n}     | {n}       |

ESTIMATED EFFORT
────────────────────────────────────────

  Download: ~{hours} hours ({N} files @ 10s each)
  Extraction: ~{hours} hours ({N} PDFs)

FILES
────────────────────────────────────────

  Manifest: {manifest_path}
  Baseline: {baseline_path}
  PMN data: {pmn_paths}

NEXT STEPS
────────────────────────────────────────

  {Based on gap results, recommend specific actions:}
  1. Download missing PDFs — `/fda:extract stage1 --product-codes {CODES} --years {YEARS}`
  2. Extract from existing PDFs — `/fda:extract stage2 --project {NAME}`
  3. View full status — `/fda:status`

────────────────────────────────────────
  This report is AI-generated from public FDA data.
  Verify independently. Not regulatory advice.
────────────────────────────────────────
```

## Error Handling

- If PMN files not found → Guide user to download them or run `/fda:extract stage1`
- If baseline CSV not found → Note this is the first analysis (no prior extractions exist)
- If PDF directory not found → All matching records will show as "need_download"
- If Python error → Show full error and suggest checking PMN file format
