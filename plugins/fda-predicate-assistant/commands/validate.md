---
description: Validate FDA device numbers against official databases and all available pipeline data
allowed-tools: Bash, Read, Grep, Glob
argument-hint: "<number> [number2] [--project NAME]"
---

# FDA Device Number Validation (Enriched)

You are validating FDA device numbers against official databases AND enriching results with data from the full pipeline. **Always report what data IS available, what is MISSING, and exactly how to get the missing data.**

## Device Number Formats

- **K-numbers (510(k))**: K + 6 digits (e.g., K240717, K991234)
- **P-numbers (PMA)**: P + 6 digits (e.g., P190001)
- **N-numbers (De Novo)**: DEN + digits (e.g., DEN200001)

## Project Support

If `--project NAME` is provided, check the project folder first for all data files:

```bash
PROJECTS_DIR="/mnt/c/510k/Python/510k_projects"  # or from settings
cat ~/.claude/fda-predicate-assistant.local.md 2>/dev/null
ls "$PROJECTS_DIR/$PROJECT_NAME/output.csv" "$PROJECTS_DIR/$PROJECT_NAME/510k_download.csv" "$PROJECTS_DIR/$PROJECT_NAME/pdf_data.json" 2>/dev/null
```

When a project is specified, search its files first, then fall back to legacy locations for additional data.

## Validation Process

### Step 0: Discover Available Data Sources

**Before validating, check which enrichment sources exist.** This determines what you can report and what's missing:

```bash
# Check ALL possible data locations
echo "=== Checking data sources ==="
ls -la /mnt/c/510k/Python/PredicateExtraction/output.csv 2>/dev/null || echo "output.csv: NOT FOUND"
ls -la /mnt/c/510k/Python/PredicateExtraction/cache/index.json 2>/dev/null || echo "Per-device cache: NOT FOUND"
ls -la /mnt/c/510k/Python/PredicateExtraction/pdf_data.json 2>/dev/null || echo "pdf_data.json (legacy): NOT FOUND"
ls -la /mnt/c/510k/Python/510kBF/510k_download.csv 2>/dev/null || echo "510k_download.csv: NOT FOUND"
ls -la /mnt/c/510k/Python/510kBF/merged_data.csv 2>/dev/null || echo "merged_data.csv: NOT FOUND"
ls /mnt/c/510k/Python/PredicateExtraction/pmn*.txt 2>/dev/null || echo "pmn*.txt: NOT FOUND"
```

Track which sources exist — you'll use this in the final report.

### Step 1: Parse Input Numbers

Parse all device numbers from `$ARGUMENTS`. Handle comma-separated, space-separated, or mixed input.

### Step 2: Primary Validation — FDA Database Files

FDA database files may be in multiple locations. Check these in order:

1. Project `fda_data/` directory (if `--project` specified)
2. `/mnt/c/510k/Python/PredicateExtraction/` (legacy location)
3. `/mnt/c/510k/Python/510kBF/fda_data/` (BatchFetch data-dir)

For K-numbers (510(k)):
```bash
grep -i "KNUMBER" /mnt/c/510k/Python/PredicateExtraction/pmn*.txt /mnt/c/510k/Python/510kBF/fda_data/pmn*.txt 2>/dev/null
```

For P-numbers (PMA):
```bash
grep -i "PNUMBER" /mnt/c/510k/Python/PredicateExtraction/pma*.txt /mnt/c/510k/Python/510kBF/fda_data/pma*.txt 2>/dev/null
```

Report: Found/Not Found + full database record if found.

### Step 3: Enrichment — 510kBF Metadata

Check project folder first (if applicable), then legacy location:

```bash
grep -i "KNUMBER" /mnt/c/510k/Python/510kBF/510k_download.csv 2>/dev/null
```

If found, report additional metadata:
- Applicant name
- Decision date and decision code
- Product code and device type
- Review advisory committee
- Third-party review (yes/no)
- Review time
- FDA submission URL

### Step 4: Enrichment — Predicate Relationships

Check project folder first (if applicable), then legacy:

```bash
grep -i "KNUMBER" /mnt/c/510k/Python/PredicateExtraction/output.csv 2>/dev/null
```

**If `output.csv` does NOT exist**: Do NOT just say "Not in output.csv". Instead report:
> **Predicates**: Not available — `output.csv` not found. Run `/fda:extract stage2` to extract predicates from cached PDFs.

**If `output.csv` exists but the device is not in it**: Report:
> **Predicates**: Device not in extraction results. Its PDF may not have been downloaded or processed.

If found, report:
- Known predicates cited by this device
- Document type (Statement vs Summary)
- Product code from extraction

Also check if this device is cited AS a predicate by others:
```bash
grep -i "KNUMBER" /mnt/c/510k/Python/PredicateExtraction/output.csv 2>/dev/null
```
(Search across all columns, not just the first)

If `/mnt/c/510k/Python/510kBF/merged_data.csv` exists, also check:
```bash
grep -i "KNUMBER" /mnt/c/510k/Python/510kBF/merged_data.csv 2>/dev/null
```

### Step 5: Enrichment — PDF Text Availability

Check project folder first (if applicable), then default locations. Try per-device cache first (scalable), then fall back to legacy monolithic file.

```bash
python3 -c "
import json, os

knumber = 'KNUMBER'
cache_dir = '/mnt/c/510k/Python/PredicateExtraction/cache'
index_file = os.path.join(cache_dir, 'index.json')

# Try per-device cache first (preferred — scalable)
if os.path.exists(index_file):
    with open(index_file) as f:
        index = json.load(f)
    if knumber in index:
        device_path = os.path.join('/mnt/c/510k/Python/PredicateExtraction', index[knumber]['file_path'])
        if os.path.exists(device_path):
            with open(device_path) as f:
                device_data = json.load(f)
            text = device_data.get('text', '')
            print(f'CACHED (per-device): {len(text)} characters of text available')
            print(f'Preview: {text[:200]}...')
        else:
            print('INDEX ENTRY EXISTS but file missing')
    else:
        print('NOT CACHED (not in per-device index)')
else:
    # Legacy: monolithic pdf_data.json
    pdf_json = '/mnt/c/510k/Python/PredicateExtraction/pdf_data.json'
    if os.path.exists(pdf_json):
        with open(pdf_json) as f:
            data = json.load(f)
        key = knumber + '.pdf'
        if key in data:
            entry = data[key]
            text = entry.get('text', '') if isinstance(entry, dict) else str(entry)
            print(f'CACHED (legacy pdf_data.json): {len(text)} characters of text available')
            print(f'Preview: {text[:200]}...')
        else:
            print('NOT CACHED (not in pdf_data.json)')
    else:
        print('NO CACHE: Neither per-device cache nor pdf_data.json found')
" 2>/dev/null
```

Do NOT use `grep -c "KNUMBER"` on pdf_data.json — it may match inside other documents' text and give misleading results.

**If text IS cached**: Report:
> **PDF Text**: Cached (X characters) — available for section analysis via `/fda:summarize --knumbers KNUMBER`

**If text is NOT cached but 510k_download.csv shows it's a Summary**: Report:
> **PDF Text**: Not cached — this is a Summary document so text extraction would yield useful data. Run `/fda:extract stage2` to extract.

**If text is NOT cached and it's a Statement**: Report:
> **PDF Text**: Not cached — this is a Statement-only filing (limited public data available)

### Step 6: OCR Error Suggestions

If a number is NOT found in the primary database, suggest possible OCR corrections:
- O → 0 (letter O to zero)
- I → 1 (letter I to one)
- S → 5 (letter S to five)
- B → 8 (letter B to eight)

Try common corrections and check if the corrected number exists:
```bash
grep -i "CORRECTED_NUMBER" /mnt/c/510k/Python/PredicateExtraction/pmn*.txt 2>/dev/null
```

## Output Format

For each number, provide a consolidated report:

**KNUMBER** — [FOUND/NOT FOUND]
- **FDA Database**: Record details or "Not found"
- **Applicant**: Company name (from 510k_download.csv)
- **Decision**: Date, decision code (from 510k_download.csv)
- **Product Code**: Code and description
- **Review Time**: Days (from 510k_download.csv)
- **Predicates**: List of cited predicates — or clear explanation of why unavailable
- **Cited By**: Other devices that cite this as a predicate
- **PDF Text**: Cached (X chars) / Not cached — with actionable guidance
- **URL**: FDA submission link (from 510k_download.csv)

**IMPORTANT**: For every field where data is unavailable, explain WHY it's unavailable and HOW to get it. Never just say "Not found" without context.

## Data Gaps & Next Steps

After presenting all device results, add a **Data Gaps & Next Steps** section that aggregates all missing data into actionable commands:

```
Data Gaps & Next Steps
──────────────────────
The following data sources are missing or incomplete:

  ✗ output.csv — No predicate extraction results exist
    → Run: /fda:extract stage2
    → This will extract predicates from 209 cached PDFs in pdf_data.json

  ✓ pdf_data.json — 209 PDFs cached (text available for analysis)
    → Run: /fda:summarize --knumbers K022854 --sections all
    → To analyze specific sections of this device's summary

  ✓ 510k_download.csv — 118 records with metadata
  ✓ pmn96cur.txt — FDA database available
  ✗ merged_data.csv — Not found (alternative predicate source)
```

This section should:
1. List ALL data sources checked with ✓/✗ status
2. For each missing source, give the exact command to create it
3. For each available source, suggest what analysis it enables
4. Prioritize recommendations (most impactful first)
