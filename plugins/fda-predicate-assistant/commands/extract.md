---
description: Run the FDA 510(k) two-stage pipeline — download PDFs with BatchFetch then extract predicates
allowed-tools: Bash, Read, Glob, Grep
argument-hint: "[stage1|stage2|both] [--year YEAR] [--product-code CODE] [--directory PATH]"
---

# FDA 510(k) Extraction Pipeline

You are guiding the user through the FDA device data pipeline. This is a **two-stage process**:

- **Stage 1** (BatchFetch): Filter the FDA catalog and download 510(k) PDF documents
- **Stage 2** (PredicateExtraction): Extract predicate device numbers from downloaded PDFs

## Bundled Scripts

Both scripts are bundled in the plugin at `$CLAUDE_PLUGIN_ROOT/scripts/`:

- `batchfetch.py` — Stage 1: Filter & download
- `predicate_extractor.py` — Stage 2: Extract predicates
- `requirements.txt` — All Python dependencies

## Determine What the User Wants

Parse `$ARGUMENTS` to determine which stage(s) to run:
- `stage1` → Run only BatchFetch (download PDFs)
- `stage2` → Run only PredicateExtraction (extract predicates)
- `both` → Run Stage 1 then Stage 2
- No argument → Ask the user which stage they want

## Dependencies Check

Before running either stage, verify dependencies are installed:

```bash
pip install -r "$CLAUDE_PLUGIN_ROOT/scripts/requirements.txt" 2>/dev/null || echo "Warning: Some dependencies may be missing"
```

Quick check:
```bash
python -c "import requests, tqdm, fitz, pdfplumber" 2>/dev/null || echo "Missing Stage 2 deps - run: pip install -r $CLAUDE_PLUGIN_ROOT/scripts/requirements.txt"
python -c "import requests, pandas, tqdm" 2>/dev/null || echo "Missing Stage 1 deps - run: pip install -r $CLAUDE_PLUGIN_ROOT/scripts/requirements.txt"
```

## Stage 1: BatchFetch — Filter & Download PDFs

**Script:** `$CLAUDE_PLUGIN_ROOT/scripts/batchfetch.py`

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
| `--output-dir` | Where to save CSV | `/path/to/output` |
| `--download-dir` | Where to download PDFs | `/path/to/510ks` |
| `--data-dir` | Where FDA database files go | `/path/to/fda_data` |
| `--save-excel` | Save Excel workbook | (flag) |
| `--no-download` | Skip PDF download, just CSV | (flag) |
| `--interactive` | Force interactive prompts | (flag) |

### Non-Interactive Example

```bash
python "$CLAUDE_PLUGIN_ROOT/scripts/batchfetch.py" \
  --date-range pmn96cur \
  --years 2020-2025 \
  --product-codes KGN \
  --decision-codes SESE \
  --output-dir /mnt/c/510k/Python/510kBF \
  --download-dir /mnt/c/510k/Python/510kBF/510ks \
  --data-dir /mnt/c/510k/Python/510kBF/fda_data
```

### Interactive Mode

If the user wants to browse available options interactively:
```bash
python "$CLAUDE_PLUGIN_ROOT/scripts/batchfetch.py" --interactive
```

### Outputs

- `510k_download.csv` — Full metadata (24 columns: KNUMBER, APPLICANT, DECISIONDATE, PRODUCTCODE, TYPE, etc.)
- `Applicant_ProductCode_Tables.xlsx` — Analytics (if --save-excel)
- Downloaded PDFs in: `DOWNLOAD_DIR/YEAR/APPLICANT/PRODUCTCODE/TYPE/`

## Stage 2: PredicateExtraction — Extract Predicates from PDFs

**Script:** `$CLAUDE_PLUGIN_ROOT/scripts/predicate_extractor.py`

### CLI Flags

| Flag | Description | Default |
|------|-------------|---------|
| `--directory`, `-d` | Path to PDF directory | (required for headless) |
| `--use-cache` | Use existing pdf_data.json | |
| `--no-cache` | Re-extract all PDF text | |
| `--output-dir`, `-o` | Where to write output CSV | Same as --directory |
| `--data-dir` | Where FDA database files go | Script directory |
| `--batch-size`, `-b` | PDFs per batch | 100 |
| `--workers`, `-w` | Parallel workers | 4 |

### Non-Interactive Example

```bash
python "$CLAUDE_PLUGIN_ROOT/scripts/predicate_extractor.py" \
  --directory /mnt/c/510k/Python/510kBF/510ks \
  --use-cache \
  --output-dir /mnt/c/510k/Python/PredicateExtraction \
  --data-dir /mnt/c/510k/Python/PredicateExtraction
```

### Interactive Mode

When `--directory` is omitted, falls back to tkinter GUI:
```bash
python "$CLAUDE_PLUGIN_ROOT/scripts/predicate_extractor.py"
```

### Outputs

- `output.csv` — Main results: K-number, ProductCode, Predicate1..PredicateN, ReferenceDevice1..N
- `supplement.csv` — Devices with supplement suffixes (e.g., K240717/S001)
- `pdf_data.json` — Cached extracted text keyed by filename
- `error_log.txt` — List of PDFs that failed processing

## After Extraction

Once either stage completes:

1. **Check output files exist** using Glob in the appropriate directory
2. **Report a summary:**
   - Stage 1: How many records in 510k_download.csv, how many PDFs downloaded
   - Stage 2: How many devices in output.csv, how many had predicates, any errors
3. **Offer next steps:**
   - If Stage 1 just finished → offer to run Stage 2
   - If Stage 2 just finished → offer to run `/fda:analyze`
   - Always offer `/fda:status` to see what data is available

## Error Handling

- If Python is not found: suggest `python3` or check PATH
- If dependencies missing: run `pip install -r "$CLAUDE_PLUGIN_ROOT/scripts/requirements.txt"`
- If GUI-related error (tkinter): use CLI flags instead (`--directory`, `--use-cache`)
- If FDA download fails: script provides manual download URLs
