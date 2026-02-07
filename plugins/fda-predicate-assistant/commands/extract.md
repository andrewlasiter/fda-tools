---
description: Run the FDA 510(k) two-stage pipeline — download PDFs with BatchFetch then extract predicates
allowed-tools: Bash, Read, Glob, Grep, Write
argument-hint: "[stage1|stage2|both] [--product-codes CODE] [--years RANGE] [--project NAME]"
---

# FDA 510(k) Extraction Pipeline

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

You are guiding the user through the FDA device data pipeline. This is a **two-stage process**:

- **Stage 1** (BatchFetch): Filter the FDA catalog and download 510(k) PDF documents
- **Stage 2** (PredicateExtraction): Extract predicate device numbers from downloaded PDFs

## Project-Based Output Management

**Every extraction run saves to a project folder.** This prevents overwriting previous results and keeps each query's data self-contained.

### Projects Directory

Configurable via `/fda:configure --set projects_dir /path/to/projects`
Default: `~/fda-510k-data/projects/` (or custom path from settings)

Check settings file for custom path:
```bash
cat ~/.claude/fda-predicate-assistant.local.md 2>/dev/null
```

### Project Naming

If `--project NAME` is provided, use that name. Otherwise, **auto-generate** from the filter criteria:

- Product codes + years: `KGN_2020-2025`
- Product codes + applicant: `KGN_MEDTRONIC`
- Multiple codes: `KGN_DXY_2023`
- Just years: `all_2024`
- No filters: `unfiltered_YYYYMMDD_HHMMSS`

Sanitize the name: lowercase, replace spaces with underscores, remove special characters.

### Project Structure

```
510k_projects/
  KGN_2020-2025/
    query.json               ← Filters used to create this project
    510k_download.csv        ← Stage 1 output
    Applicant_ProductCode_Tables.xlsx  ← Stage 1 analytics
    510ks/                   ← Downloaded PDFs
    output.csv               ← Stage 2 output
    supplement.csv           ← Stage 2 supplements
    pdf_data.json            ← Cached PDF text
    error_log.txt            ← Failed PDFs
    fda_data/                ← FDA database files for this run
```

### Creating the Project

Before running any script, create the project folder and save query metadata:

```bash
mkdir -p "$PROJECTS_DIR/$PROJECT_NAME/510ks"
mkdir -p "$PROJECTS_DIR/$PROJECT_NAME/fda_data"
```

Write `query.json` with the filter metadata:

```json
{
  "project_name": "KGN_2020-2025",
  "created": "2026-02-05T12:00:00Z",
  "stage1": {
    "date_range": "pmn96cur",
    "years": "2020-2025",
    "product_codes": ["KGN"],
    "decision_codes": ["SESE"],
    "applicants": [],
    "committees": [],
    "submission_types": []
  },
  "stage2": {
    "batch_size": 100,
    "workers": 4,
    "ocr_mode": "smart",
    "use_cache": false
  },
  "results": {
    "stage1_records": null,
    "stage1_pdfs_downloaded": null,
    "stage2_devices_extracted": null,
    "stage2_errors": null,
    "last_updated": null
  }
}
```

## Bundled Scripts

Both scripts are bundled in the plugin at `$FDA_PLUGIN_ROOT/scripts/`:

- `batchfetch.py` — Stage 1: Filter & download
- `predicate_extractor.py` — Stage 2: Extract predicates
- `requirements.txt` — All Python dependencies

## Determine What the User Wants

Parse `$ARGUMENTS` to determine which stage(s) to run:
- `stage1` → Run only BatchFetch (download PDFs)
- `stage2` → Run only PredicateExtraction (extract predicates)
- `both` → Run Stage 1 then Stage 2
- No stage argument — three explicit cases:
  1. **`--project` is provided** → Default to `both` (log: "No stage specified, defaulting to 'both' (--project provided)")
  2. **No `--project` but `--product-codes` provided** → Default to `stage1` (log: "No stage specified, defaulting to 'stage1' (no project context)")
  3. **Neither `--project` nor `--product-codes`** → Default to `stage1` (log: "No stage specified, defaulting to 'stage1'")
  - **NEVER prompt the user for stage selection**

**Full-auto requirement**: If `--full-auto` is active, `--project` is **REQUIRED**. Error if missing: "In --full-auto mode, --project is required to organize pipeline outputs. Usage: /fda:extract both --project NAME --product-codes CODE --full-auto"

Also parse filter arguments: `--product-codes`, `--years`, `--applicants`, `--committees`, `--decision-codes`, `--project`

## Dependencies Check

Before running either stage, verify dependencies are installed:

```bash
python3 -c "import requests, tqdm, fitz, pdfplumber" 2>/dev/null || echo "Missing Stage 2 deps"
python3 -c "import requests, pandas, tqdm" 2>/dev/null || echo "Missing Stage 1 deps"
```

If missing: `pip install -r "$FDA_PLUGIN_ROOT/scripts/requirements.txt"`

## Stage 1: BatchFetch — Filter & Download PDFs

**Script:** `$FDA_PLUGIN_ROOT/scripts/batchfetch.py`

### CLI Flags

| Flag | Description | Example |
|------|-------------|---------|
| `--date-range` | Comma-separated pmn keys | `pmn96cur,pmnlstmn` |
| `--years` | Year range or list | `2020-2025` or `2020,2022` |
| `--submission-types` | Comma-separated types | `Traditional,Special` |
| `--committees` | Advisory committee codes | `CV,OR` |
| `--decision-codes` | Decision codes | `SESE,SESK` |
| `--applicants` | Semicolon-separated names | `"MEDTRONIC;ABBOTT"` |
| `--product-codes` | Comma-separated codes | `KGN,DXY` |
| `--output-dir` | Where to save CSV | **Set to project folder** |
| `--download-dir` | Where to download PDFs | **Set to project/510ks** |
| `--data-dir` | Where FDA database files go | **Set to project/fda_data** |
| `--save-excel` | Save Excel workbook | (flag) |
| `--no-download` | Skip PDF download, just CSV | (flag) |
| `--interactive` | Force interactive prompts | (flag) |

### Running Stage 1

**Always point output to the project folder:**

```bash
python3 "$FDA_PLUGIN_ROOT/scripts/batchfetch.py" \
  --date-range pmn96cur \
  --years 2020-2025 \
  --product-codes KGN \
  --decision-codes SESE \
  --output-dir "$PROJECTS_DIR/$PROJECT_NAME" \
  --download-dir "$PROJECTS_DIR/$PROJECT_NAME/510ks" \
  --data-dir "$PROJECTS_DIR/$PROJECT_NAME/fda_data" \
  --save-excel
```

### After Stage 1

Update `query.json` with results:
```bash
# Count records and PDFs
wc -l "$PROJECTS_DIR/$PROJECT_NAME/510k_download.csv"
find "$PROJECTS_DIR/$PROJECT_NAME/510ks" -name "*.pdf" | wc -l
```

Update the `results` section of `query.json` with actual counts.

## Stage 2: PredicateExtraction — Extract Predicates from PDFs

**Script:** `$FDA_PLUGIN_ROOT/scripts/predicate_extractor.py`

### CLI Flags

| Flag | Description | Default |
|------|-------------|---------|
| `--directory`, `-d` | Path to PDF directory | **Set to project/510ks** |
| `--use-cache` | Use existing pdf_data.json | |
| `--no-cache` | Re-extract all PDF text | |
| `--output-dir`, `-o` | Where to write output CSV | **Set to project folder** |
| `--data-dir` | Where FDA database files go | **Set to project/fda_data** |
| `--batch-size`, `-b` | PDFs per batch | 100 |
| `--workers`, `-w` | Parallel workers | 4 |

### Running Stage 2

**Point to the project's PDF directory and output to the project folder:**

```bash
python3 "$FDA_PLUGIN_ROOT/scripts/predicate_extractor.py" \
  --directory "$PROJECTS_DIR/$PROJECT_NAME/510ks" \
  --output-dir "$PROJECTS_DIR/$PROJECT_NAME" \
  --data-dir "$PROJECTS_DIR/$PROJECT_NAME/fda_data"
```

If running Stage 2 on a project that already ran Stage 1, add `--use-cache` if pdf_data.json exists.

If running Stage 2 without a project context (e.g., on an arbitrary PDF directory), still create a project folder for the output.

### After Stage 2

Update `query.json` with results:
```bash
wc -l "$PROJECTS_DIR/$PROJECT_NAME/output.csv"
wc -l "$PROJECTS_DIR/$PROJECT_NAME/error_log.txt" 2>/dev/null
```

## Running on an Existing Project

If the user specifies `--project NAME` and the project already exists:
1. Read `query.json` to understand the previous filters
2. For Stage 1: warn that `510k_download.csv` will be overwritten, offer to create a new project instead
3. For Stage 2: can reuse the existing PDFs, just re-extract

## After Extraction

Once either stage completes, present results using the standard FDA Professional CLI format (see `references/output-formatting.md`):

### Stage 1 Summary

```
  FDA BatchFetch Summary
  {product_code} — Stage 1 Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: {date} | Project: {name} | v4.6.0

RESULTS
────────────────────────────────────────

  | Metric            | Value           |
  |-------------------|-----------------|
  | Records found     | {N}             |
  | PDFs downloaded   | {N}             |
  | Download errors   | {N}             |
  | Year range        | {start} - {end} |
  | Product codes     | {codes}         |

FILES WRITTEN
────────────────────────────────────────

  510k_download.csv              {path}
  Applicant_ProductCode_Tables   {path}
  PDFs                           {path}/510ks/

NEXT STEPS
────────────────────────────────────────

  1. Extract predicates — `/fda:extract stage2 --project {NAME}`
  2. Check data status — `/fda:status`

{If API_KEY_NUDGE:true was printed, add this line before the disclaimer:}
  Tip: Get 120x more API requests/day with a free key → /fda:configure --setup-key

────────────────────────────────────────
  This report is AI-generated from public FDA data.
  Verify independently. Not regulatory advice.
────────────────────────────────────────
```

### Stage 2 Summary

```
  FDA Predicate Extraction Summary
  {product_code} — Stage 2 Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: {date} | Project: {name} | v4.6.0

RESULTS
────────────────────────────────────────

  | Metric                    | Value |
  |---------------------------|-------|
  | Devices processed         | {N}   |
  | Devices with predicates   | {N}   |
  | Total predicates found    | {N}   |
  | Avg predicates per device | {N}   |
  | Processing errors         | {N}   |

TOP CITED PREDICATES
────────────────────────────────────────

  | K-Number | Citations | Status |
  |----------|-----------|--------|
  | {kn}     | {count}   | {✓/⚠} |

QUICK SAFETY SCAN
────────────────────────────────────────

  {safety scan results — ✓ clean or ⚠ recalls found}

FILES WRITTEN
────────────────────────────────────────

  output.csv       {path}
  supplement.csv   {path}
  pdf_data.json    {path}
  error_log.txt    {path}

NEXT STEPS
────────────────────────────────────────

  1. Review and score predicates — `/fda:review --project {NAME}`
  2. Analyze extraction data — `/fda:analyze --project {NAME}`
  3. Summarize PDF sections — `/fda:summarize --project {NAME}`

{If API_KEY_NUDGE:true was printed, add this line before the disclaimer:}
  Tip: Get 120x more API requests/day with a free key → /fda:configure --setup-key

────────────────────────────────────────
  This report is AI-generated from public FDA data.
  Verify independently. Not regulatory advice.
────────────────────────────────────────
```

### Quick Safety Scan (after Stage 2)

**If Stage 2 just finished — Quick Safety Scan:**

   Automatically scan the top 5 most-cited predicates for recalls. This takes ~10 seconds and catches critical safety issues early.

   ```bash
   python3 << 'PYEOF'
   import csv, os, re, urllib.request, urllib.parse, json, time
   from collections import Counter

   # Read output.csv to find most-cited predicates
   project_dir = os.path.expanduser(f'$PROJECTS_DIR/$PROJECT_NAME')  # Replace with actual path
   output_csv = os.path.join(project_dir, 'output.csv')

   if not os.path.exists(output_csv):
       print("SAFETY_SKIP:no_output_csv")
       exit(0)

   # Count predicate citations
   predicate_counts = Counter()
   with open(output_csv, newline='', encoding='utf-8') as f:
       reader = csv.reader(f)
       header = next(reader, None)
       if header:
           # Find predicate columns (columns containing "Predicate" in header)
           pred_cols = [i for i, h in enumerate(header) if 'predicate' in h.lower()]
           for row in reader:
               for col in pred_cols:
                   if col < len(row) and row[col].strip():
                       predicate_counts[row[col].strip().upper()] += 1

   top_5 = [kn for kn, _ in predicate_counts.most_common(5)]
   if not top_5:
       print("SAFETY_SKIP:no_predicates_found")
       exit(0)

   # Check settings for API key
   settings_path = os.path.expanduser('~/.claude/fda-predicate-assistant.local.md')
   api_key = os.environ.get('OPENFDA_API_KEY')
   api_enabled = True
   if os.path.exists(settings_path):
       with open(settings_path) as f:
           content = f.read()
       if not api_key:
           m = re.search(r'openfda_api_key:\s*(\S+)', content)
           if m and m.group(1) != 'null':
               api_key = m.group(1)
       m = re.search(r'openfda_enabled:\s*(\S+)', content)
       if m and m.group(1).lower() == 'false':
           api_enabled = False

   if not api_key:
       print("API_KEY_NUDGE:true")

   if not api_enabled:
       print("SAFETY_SKIP:api_disabled")
       exit(0)

   print("=== QUICK SAFETY SCAN ===")
   recalled = []
   for knumber in top_5:
       # Look up product code first
       params = {"search": f'k_number:"{knumber}"', "limit": "1"}
       if api_key:
           params["api_key"] = api_key
       url = f"https://api.fda.gov/device/510k.json?{urllib.parse.urlencode(params)}"
       req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/1.0)"})
       try:
           with urllib.request.urlopen(req, timeout=15) as resp:
               data = json.loads(resp.read())
               if data.get("results"):
                   r = data["results"][0]
                   pc = r.get("product_code", "")
                   applicant = r.get("applicant", "")
                   # Check recalls for this applicant + product code
                   time.sleep(0.5)
                   rparams = {"search": f'product_code:"{pc}"+AND+recalling_firm:"{applicant}"', "limit": "1"}
                   if api_key:
                       rparams["api_key"] = api_key
                   rurl = f"https://api.fda.gov/device/recall.json?{urllib.parse.urlencode(rparams)}"
                   rreq = urllib.request.Request(rurl, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/1.0)"})
                   try:
                       with urllib.request.urlopen(rreq, timeout=15) as rresp:
                           rdata = json.loads(rresp.read())
                           total = rdata.get("meta", {}).get("results", {}).get("total", 0)
                           if total > 0:
                               recall = rdata["results"][0]
                               recalled.append(f"{knumber}|{applicant}|{recall.get('recall_status', '?')}|{recall.get('reason_for_recall', 'N/A')[:80]}")
                               print(f"RECALLED:{knumber}|{applicant}|{recall.get('recall_status', '?')}|{recall.get('reason_for_recall', 'N/A')[:80]}")
                           else:
                               print(f"CLEAN:{knumber}")
                   except:
                       print(f"RECALL_CHECK_FAILED:{knumber}")
       except:
           print(f"LOOKUP_FAILED:{knumber}")
       time.sleep(0.5)

   if recalled:
       print(f"\nWARNING:Found {len(recalled)} predicate(s) with recall history")
   else:
       print(f"\nALL_CLEAN:Top {len(top_5)} predicates have no recall history")
   PYEOF
   ```

   **Report safety scan results to the user:**
   - If any recalled predicates found: Display a warning with the recall details
   - If all clean: Brief "Top predicates have clean recall history" note
   - If API unavailable: Skip silently (don't block the extraction workflow)

4. **Offer next steps:**
   - If Stage 1 just finished → offer to run Stage 2 on this project
   - If Stage 2 just finished:
     - **Always suggest**: "Run `/fda:review --project PROJECT_NAME` to score, flag, and validate predicates"
     - Offer `/fda:analyze --project PROJECT_NAME`
     - Offer `/fda:summarize --project PROJECT_NAME` for section analysis
     - Offer `/fda:research PRODUCTCODE` for submission planning
   - Offer `/fda:status` to see all projects

## Error Handling

- If Python is not found: suggest `python3` or check PATH
- If dependencies missing: run `pip install -r "$FDA_PLUGIN_ROOT/scripts/requirements.txt"`
- If GUI-related error (tkinter): use CLI flags instead (`--directory`, `--use-cache`)
- If FDA download fails: script provides manual download URLs
- If projects directory doesn't exist: create it automatically
