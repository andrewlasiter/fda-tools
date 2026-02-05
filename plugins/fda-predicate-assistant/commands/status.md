---
description: Show available FDA pipeline data, file freshness, script availability, and record counts
allowed-tools: Bash, Read, Glob, Grep
argument-hint: ""
---

# FDA Pipeline Status

You are reporting the current state of all FDA data across the pipeline. This answers: "What do I have to work with?"

## Check All Data Sources

Run these checks and compile a status report:

### 0. Plugin Scripts & Dependencies

Check if bundled scripts are available:
```bash
ls -la "$CLAUDE_PLUGIN_ROOT/scripts/predicate_extractor.py" "$CLAUDE_PLUGIN_ROOT/scripts/batchfetch.py" "$CLAUDE_PLUGIN_ROOT/scripts/requirements.txt" 2>/dev/null
```

Check if dependencies are installed:
```bash
python -c "import requests, tqdm, fitz, pdfplumber, orjson, ijson" 2>&1 && echo "Stage 2 deps: OK" || echo "Stage 2 deps: MISSING"
python -c "import requests, pandas, tqdm, colorama, numpy" 2>&1 && echo "Stage 1 deps: OK" || echo "Stage 1 deps: MISSING"
```

Report:
- Script availability (predicate_extractor.py, batchfetch.py)
- Dependency status for each stage
- If missing: `pip install -r "$CLAUDE_PLUGIN_ROOT/scripts/requirements.txt"`

### 1. FDA Database Files (pmn*.txt, pma*.txt, foiaclass.txt)

Check multiple possible locations for FDA database files:

```bash
# Check PredicateExtraction directory
ls -la /mnt/c/510k/Python/PredicateExtraction/pmn*.txt /mnt/c/510k/Python/PredicateExtraction/pma*.txt /mnt/c/510k/Python/PredicateExtraction/foiaclass.txt 2>/dev/null
# Check plugin scripts directory (if --data-dir was used)
ls -la "$CLAUDE_PLUGIN_ROOT/scripts/"pmn*.txt "$CLAUDE_PLUGIN_ROOT/scripts/"pma*.txt 2>/dev/null
# Check BatchFetch fda_data directory
ls -la /mnt/c/510k/Python/510kBF/fda_data/pmn*.txt /mnt/c/510k/Python/510kBF/fda_data/foiaclass.txt 2>/dev/null
```

For each file found, report:
- File size and last modified date
- Record count: `wc -l <file>`
- Age in days (compare modified date to today)
- If older than 5 days, suggest refreshing

### 2. 510kBF Downloads (510k_download.csv)

```bash
ls -la /mnt/c/510k/Python/510kBF/510k_download.csv 2>/dev/null
```

If found:
- Record count: `wc -l`
- Date range: read first and last DECISIONDATE values
- Filters used: check if header comments or filter metadata exists
- Product codes present: `cut -d',' -f4 | sort -u | wc -l` (approximate)

### 3. Downloaded PDFs

```bash
find /mnt/c/510k/Python/510kBF/510ks/ -name "*.pdf" 2>/dev/null | wc -l
```

If PDFs exist:
- Total PDF count
- Year directories present: `ls /mnt/c/510k/Python/510kBF/510ks/`
- Approximate disk usage: `du -sh /mnt/c/510k/Python/510kBF/510ks/`

Also check the PredicateExtraction directory:
```bash
find /mnt/c/510k/Python/PredicateExtraction/ -maxdepth 1 -name "*.pdf" 2>/dev/null | wc -l
```

And organized PDF storage:
```bash
ls -d /mnt/c/510k/Python/PredicateExtraction/2024 /mnt/c/510k/Python/PredicateExtraction/2025 2>/dev/null
```

### 4. Extraction Results (output.csv, supplement.csv)

```bash
ls -la /mnt/c/510k/Python/PredicateExtraction/output.csv /mnt/c/510k/Python/PredicateExtraction/supplement.csv 2>/dev/null
```

If found:
- Record count for each
- Last modified date
- Quick stats: devices with predicates vs without

### 5. Cached PDF Text (pdf_data.json)

```bash
ls -la /mnt/c/510k/Python/PredicateExtraction/pdf_data.json 2>/dev/null
```

If found:
- File size
- Approximate entry count: `grep -c '"filename"' pdf_data.json` or similar key count

### 6. Merged Data (merged_data.csv)

```bash
ls -la /mnt/c/510k/Python/510kBF/merged_data.csv 2>/dev/null
```

If found:
- Record count
- Last modified date

### 7. Analytics Workbook

```bash
ls -la /mnt/c/510k/Python/510kBF/Applicant_ProductCode_Tables.xlsx 2>/dev/null
```

### 8. Error Log

```bash
ls -la /mnt/c/510k/Python/PredicateExtraction/error_log.txt 2>/dev/null
```

If found:
- Number of failed PDFs: `wc -l`

## Output Format

Present a clean status table:

```
FDA Pipeline Status
===================

Plugin Scripts
  predicate_extractor.py   ✓  Available
  batchfetch.py            ✓  Available
  Stage 1 dependencies     ✓  Installed
  Stage 2 dependencies     ✓  Installed

Source Data (FDA Databases)
  pmn96-00.txt     ✓  42,351 records  (3 days old)
  pmn01-05.txt     ✓  38,122 records  (3 days old)
  pma.txt          ✗  Not found
  foiaclass.txt    ✓  8,234 records   (3 days old)

510kBF Downloads
  510k_download.csv    ✓  1,247 records  (2 days old)
  Downloaded PDFs      ✓  892 PDFs in 510ks/
  Analytics workbook   ✓  Present

PredicateExtraction Results
  output.csv           ✓  743 devices extracted  (1 day old)
  supplement.csv       ✓  12 supplement devices
  pdf_data.json        ✓  892 PDFs cached (145 MB)
  error_log.txt        ✓  23 failed PDFs

Merged Data
  merged_data.csv      ✓  743 records  (1 day old)
```

Use ✓ for present and ✗ for missing. Adapt the format to what actually exists — don't show sections where nothing is found.

## Recommendations

After the status report, suggest logical next steps:
- If dependencies missing: "Run `pip install -r \"$CLAUDE_PLUGIN_ROOT/scripts/requirements.txt\"`"
- If no FDA database files: "Run `/fda:extract stage2` to download FDA databases"
- If no 510k_download.csv: "Run `/fda:extract stage1` to filter and download PDFs"
- If PDFs exist but no output.csv: "Run `/fda:extract stage2` to extract predicates"
- If output.csv exists: "Run `/fda:analyze` for insights"
- If database files are old: "Database files are X days old, consider refreshing"
