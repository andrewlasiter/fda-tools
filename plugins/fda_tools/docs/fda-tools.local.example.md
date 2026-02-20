---
projects_dir: ~/fda-510k-data/projects
batchfetch_dir: ~/fda-510k-data/batchfetch
extraction_dir: ~/fda-510k-data/extraction
pdf_storage_dir: ~/fda-510k-data/batchfetch/510ks
data_dir: ~/fda-510k-data/extraction
extraction_script: predicate_extractor.py
batchfetch_script: batchfetch.py
ocr_mode: smart
batch_size: 100
workers: 4
cache_days: 5
default_year: null
default_product_code: null
openfda_api_key: null
openfda_enabled: true
exclusion_list: ~/fda-510k-data/exclusion_list.json
auto_review: false
webhook_url: null
alert_severity_threshold: info
alert_frequency: immediate
standards_dir: null
---

# FDA Tools Local Settings

This file stores your preferences for the FDA predicate extraction pipeline.
Copy this file to `~/.claude/fda-tools.local.md` and edit the values above.

## Directory Paths

- **projects_dir**: Root for all project folders -- each `/fda:extract` query gets its own subfolder.
- **batchfetch_dir**: Location for BatchFetch output (510k_download.csv, merged_data.csv).
- **extraction_dir**: Location for extraction output (output.csv, pdf_data.json).
- **pdf_storage_dir**: Where downloaded PDFs are organized by year/applicant/product code.
- **data_dir**: Where FDA database files are stored (pmn*.txt, pma.txt, foiaclass.txt).

## Script Configuration

- **extraction_script**: predicate_extractor.py (bundled in plugin).
- **batchfetch_script**: batchfetch.py (bundled in plugin).

## Processing Options

- **ocr_mode**: `smart` (use OCR only when needed), `always`, or `never`.
- **batch_size**: Number of PDFs per processing batch.
- **workers**: Parallel processing workers (adjust based on CPU cores).
- **cache_days**: How long to cache FDA database files before re-downloading.

## Filters

- **default_year**: Set to filter by year automatically (e.g., `2024`). `null` = all years.
- **default_product_code**: Set to filter by product code automatically (e.g., `DQY`).

## openFDA API

- **openfda_api_key**: API key for higher rate limits (120K/day vs 1K/day).
  Get a free key at https://open.fda.gov/apis/authentication/
  Set via environment variable `OPENFDA_API_KEY` or edit this field directly.
  Do NOT paste the key in chat -- it would be stored in conversation history.
- **openfda_enabled**: Set to `false` to disable all API calls (offline mode).

## Review and Validation

- **exclusion_list**: Path to JSON file listing device numbers to flag/skip during `/fda:review`.
- **auto_review**: If `true`, `/fda:review` auto-accepts predicates scoring 80+ and auto-rejects below 20.

## Alert Configuration (for /fda:monitor --notify)

- **webhook_url**: Default webhook URL for POST delivery.
- **alert_severity_threshold**: Minimum severity to deliver: `info` (all), `warning`, `critical`.
- **alert_frequency**: Delivery timing: `immediate`, `daily`, `weekly`.

## Local Standards

- **standards_dir**: Path to a directory containing standards PDFs (ISO, IEC, ASTM, AAMI, ANSI).
  When set, enables `/fda:standards --index` and `/fda:standards --compare`.
