---
description: Show available FDA pipeline data, file freshness, script availability, and record counts
allowed-tools: Bash, Read, Glob, Grep
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

### 1. Projects

Check for project folders:

```bash
ls -d /mnt/c/510k/Python/510k_projects/*/ 2>/dev/null
```

Also check settings for custom `projects_dir`:
```bash
cat ~/.claude/fda-predicate-assistant.local.md 2>/dev/null
```

For each project found, read its `query.json` to get metadata:
```bash
cat /mnt/c/510k/Python/510k_projects/*/query.json 2>/dev/null
```

Report each project:
- Project name
- Filters used (product codes, years, applicants)
- Stage 1 status: records in 510k_download.csv, PDFs downloaded
- Stage 2 status: devices in output.csv, errors
- Created date and last updated

If no projects exist, note that `/fda:extract` now saves to project folders.

### 2. FDA Database Files (pmn*.txt, pma*.txt, foiaclass.txt)

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

### 3. 510kBF Downloads (Legacy) (510k_download.csv)

```bash
ls -la /mnt/c/510k/Python/510kBF/510k_download.csv 2>/dev/null
```

If found:
- Record count: `wc -l`
- Date range: read first and last DECISIONDATE values
- Filters used: check if header comments or filter metadata exists
- Product codes present: `cut -d',' -f4 | sort -u | wc -l` (approximate)

### 4. Downloaded PDFs (Legacy)

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

### 5. Extraction Results (Legacy) (output.csv, supplement.csv)

```bash
ls -la /mnt/c/510k/Python/PredicateExtraction/output.csv /mnt/c/510k/Python/PredicateExtraction/supplement.csv 2>/dev/null
```

If found:
- Record count for each
- Last modified date
- Quick stats: devices with predicates vs without

### 6. Cached PDF Text (Legacy) (pdf_data.json)

```bash
ls -la /mnt/c/510k/Python/PredicateExtraction/pdf_data.json 2>/dev/null
```

If found:
- File size
- Approximate entry count: `grep -c '"filename"' pdf_data.json` or similar key count

### 7. Merged Data (Legacy) (merged_data.csv)

```bash
ls -la /mnt/c/510k/Python/510kBF/merged_data.csv 2>/dev/null
```

If found:
- Record count
- Last modified date

### 8. Analytics Workbook (Legacy)

```bash
ls -la /mnt/c/510k/Python/510kBF/Applicant_ProductCode_Tables.xlsx 2>/dev/null
```

### 9. Error Log (Legacy)

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

Projects (510k_projects/)
  KGN_2020-2025/     ✓  Stage 1: 247 records, 195 PDFs | Stage 2: 180 devices
  DXY_2023/          ✓  Stage 1: 52 records, 48 PDFs   | Stage 2: not run
  QAS_MEDTRONIC/     ✓  Stage 1: 31 records, 31 PDFs   | Stage 2: 28 devices

Source Data (FDA Databases)
  pmn96cur.txt     ✓  98,580 records  (3 days old)
  pma.txt          ✓  55,663 records  (3 days old)
  foiaclass.txt    ✗  Not found

Legacy Data (pre-project files)
  510k_download.csv    ✓  118 records  (from previous runs)
  output.csv           ✗  Not found
  pdf_data.json        ✓  2.4 MB cached
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
