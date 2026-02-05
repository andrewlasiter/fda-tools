---
description: Run the FDA 510(k) two-stage pipeline — download PDFs with BatchFetch then extract predicates
allowed-tools: Bash, Read, Glob, Grep, Write
argument-hint: "[stage1|stage2|both] [--product-codes CODE] [--years RANGE] [--project NAME]"
---

# FDA 510(k) Extraction Pipeline

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
- No stage argument → Ask the user which stage they want

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

Once either stage completes:

1. **Report the project location**: Tell the user where all files are saved
2. **Report a summary:**
   - Stage 1: How many records in 510k_download.csv, how many PDFs downloaded
   - Stage 2: How many devices in output.csv, how many had predicates, any errors
3. **Offer next steps:**
   - If Stage 1 just finished → offer to run Stage 2 on this project
   - If Stage 2 just finished → offer `/fda:analyze --project PROJECT_NAME`
   - Offer `/fda:summarize --project PROJECT_NAME` for section analysis
   - Offer `/fda:research PRODUCTCODE` for submission planning
   - Offer `/fda:status` to see all projects

## Error Handling

- If Python is not found: suggest `python3` or check PATH
- If dependencies missing: run `pip install -r "$FDA_PLUGIN_ROOT/scripts/requirements.txt"`
- If GUI-related error (tkinter): use CLI flags instead (`--directory`, `--use-cache`)
- If FDA download fails: script provides manual download URLs
- If projects directory doesn't exist: create it automatically
