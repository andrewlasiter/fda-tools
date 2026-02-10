---
description: Validate FDA device numbers against official databases and all available pipeline data — supports K/P/DEN/N-numbers and interactive search mode
allowed-tools: Bash, Read, Grep, Glob, Write
argument-hint: "<number> [number2] [--project NAME] [--search QUERY --product-code CODE --year RANGE --applicant NAME --limit N --sort FIELD]"
---

# FDA Device Number Validation (Enriched)

You are validating FDA device numbers against official databases AND enriching results with data from the full pipeline. **Always report what data IS available, what is MISSING, and exactly how to get the missing data.**

## Device Number Formats

- **K-numbers (510(k))**: K + 6 digits (e.g., K240717, K991234)
- **P-numbers (PMA)**: P + 6 digits (e.g., P190001)
- **DEN numbers (De Novo)**: DEN + 6 digits (e.g., DEN200001)
- **N-numbers (Pre-Amendments)**: N + 4-5 digits (e.g., N0012) — older legacy devices

## Project Support

If `--project NAME` is provided, check the project folder first for all data files:

```bash
PROJECTS_DIR="~/fda-510k-data/projects"  # or from settings
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
ls -la ~/fda-510k-data/extraction/output.csv 2>/dev/null || echo "output.csv: NOT FOUND"
ls -la ~/fda-510k-data/extraction/cache/index.json 2>/dev/null || echo "Per-device cache: NOT FOUND"
ls -la ~/fda-510k-data/extraction/pdf_data.json 2>/dev/null || echo "pdf_data.json (legacy): NOT FOUND"
ls -la ~/fda-510k-data/batchfetch/510k_download.csv 2>/dev/null || echo "510k_download.csv: NOT FOUND"
ls -la ~/fda-510k-data/batchfetch/merged_data.csv 2>/dev/null || echo "merged_data.csv: NOT FOUND"
ls ~/fda-510k-data/extraction/pmn*.txt 2>/dev/null || echo "pmn*.txt: NOT FOUND"
```

Track which sources exist — you'll use this in the final report.

### Step 1: Parse Input Numbers

Parse all device numbers from `$ARGUMENTS`. Handle comma-separated, space-separated, or mixed input.

### Step 2: Primary Validation — openFDA API (then flat-file fallback)

**Try the openFDA API first** for the richest, most current data. Fall back to flat files automatically if the API is disabled or unreachable.

#### 2A: openFDA API Validation (Primary)

Query the API using the template from `references/openfda-api.md`:

```bash
python3 << 'PYEOF'
import urllib.request, urllib.parse, json, os, re

# Read settings
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

if not api_key:
    print("API_KEY_NUDGE:true")

device_number = "DEVICE_NUMBER"  # Replace with actual device number (K, P, DEN, or N)

# Route to the correct endpoint based on device number type
number_upper = device_number.upper()
if number_upper.startswith('P'):
    endpoint = "pma"
    search_field = "pma_number"
elif number_upper.startswith('DEN'):
    # De Novo: some are indexed in the 510k endpoint under k_number
    endpoint = "510k"
    search_field = "k_number"
elif number_upper.startswith('N') and not number_upper.startswith('DEN'):
    # N-numbers (Pre-Amendments) are NOT in openFDA — skip to flat-file fallback
    print("API_SKIP:n_number_not_in_openfda")
    exit(0)
else:
    # K-numbers (default)
    endpoint = "510k"
    search_field = "k_number"

params = {"search": f'{search_field}:"{device_number}"', "limit": "1"}
if api_key:
    params["api_key"] = api_key
url = f"https://api.fda.gov/device/{endpoint}.json?{urllib.parse.urlencode(params)}"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/5.21.0)"})

try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
        if data.get("results"):
            r = data["results"][0]
            print(f"API_FOUND:true")
            print(f"ENDPOINT:{endpoint}")
            print(f"APPLICANT:{r.get('applicant', 'N/A')}")
            print(f"DEVICE_NAME:{r.get('device_name', r.get('generic_name', r.get('trade_name', 'N/A')))}")
            print(f"DECISION_DATE:{r.get('decision_date', 'N/A')}")
            print(f"DECISION_CODE:{r.get('decision_code', 'N/A')}")
            print(f"DECISION_DESC:{r.get('decision_description', 'N/A')}")
            print(f"PRODUCT_CODE:{r.get('product_code', 'N/A')}")
            print(f"CLEARANCE_TYPE:{r.get('clearance_type', 'N/A')}")
            print(f"ADVISORY_COMMITTEE:{r.get('advisory_committee_description', r.get('advisory_committee', 'N/A'))}")
            print(f"THIRD_PARTY:{r.get('third_party_flag', 'N/A')}")
            print(f"STATEMENT_OR_SUMMARY:{r.get('statement_or_summary', 'N/A')}")
            print(f"DATE_RECEIVED:{r.get('date_received', 'N/A')}")
            print(f"EXPEDITED:{r.get('expedited_review_flag', 'N/A')}")
            # Compute review time
            dr = r.get('date_received', '')
            dd = r.get('decision_date', '')
            if dr and dd:
                from datetime import datetime
                try:
                    # API returns YYYY-MM-DD; normalize both formats
                    fmt = '%Y-%m-%d' if '-' in dr else '%Y%m%d'
                    d1 = datetime.strptime(dr, fmt)
                    d2 = datetime.strptime(dd, fmt)
                    print(f"REVIEW_DAYS:{(d2 - d1).days}")
                except:
                    pass
        else:
            print("API_FOUND:false")
            # For DEN numbers, also try the pma endpoint as a fallback
            if number_upper.startswith('DEN'):
                print("DEN_NOTE:not_found_in_510k_endpoint")
except urllib.error.HTTPError as e:
    if e.code == 404:
        print("API_FOUND:false")
    else:
        print(f"API_ERROR:HTTP {e.code}")
except Exception as e:
    print(f"API_ERROR:{e}")
PYEOF
```

If the API returns data, use it as the primary source — this gives you applicant, decision date, product code, clearance type, advisory committee, third party review, statement/summary, and review time all from one call.

If the API returns `API_FOUND:false`, the device may not exist or may be too old for the API. Proceed to flat-file fallback.

If the API returns `API_ERROR`, note the error and proceed to flat-file fallback silently.

#### 2B: Flat-File Fallback

If the API was unavailable, disabled, or returned no results, fall back to flat files.

FDA database files may be in multiple locations. Check these in order:

1. Project `fda_data/` directory (if `--project` specified)
2. `~/fda-510k-data/extraction/` (legacy location)
3. `~/fda-510k-data/batchfetch/fda_data/` (BatchFetch data-dir)

For K-numbers (510(k)):
```bash
grep -i "KNUMBER" ~/fda-510k-data/extraction/pmn*.txt ~/fda-510k-data/batchfetch/fda_data/pmn*.txt 2>/dev/null
```

For P-numbers (PMA):
```bash
grep -i "PNUMBER" ~/fda-510k-data/extraction/pma*.txt ~/fda-510k-data/batchfetch/fda_data/pma*.txt 2>/dev/null
```

For DEN numbers (De Novo):
```bash
grep -i "DENNUMBER" ~/fda-510k-data/extraction/pmn*.txt ~/fda-510k-data/batchfetch/fda_data/pmn*.txt 2>/dev/null
```
Note: Some DEN numbers appear in the pmn*.txt files. If not found, the device may only be in the FDA De Novo database (not available as a flat file).

For N-numbers (Pre-Amendments):
```bash
grep -i "NNUMBER" ~/fda-510k-data/extraction/pmn*.txt ~/fda-510k-data/batchfetch/fda_data/pmn*.txt 2>/dev/null
```
Note: N-numbers are legacy Pre-Amendments devices. They are not in openFDA and may not appear in all flat files.

Report: Found/Not Found + full database record if found.

**Note the data source in the report**: `(source: openFDA API)` or `(source: flat files — API fallback)`.

### Step 3: Enrichment — 510kBF Metadata

Check project folder first (if applicable), then legacy location:

```bash
grep -i "KNUMBER" ~/fda-510k-data/batchfetch/510k_download.csv 2>/dev/null
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
grep -i "KNUMBER" ~/fda-510k-data/extraction/output.csv 2>/dev/null
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
grep -i "KNUMBER" ~/fda-510k-data/extraction/output.csv 2>/dev/null
```
(Search across all columns, not just the first)

If `~/fda-510k-data/batchfetch/merged_data.csv` exists, also check:
```bash
grep -i "KNUMBER" ~/fda-510k-data/batchfetch/merged_data.csv 2>/dev/null
```

### Step 5: Enrichment — PDF Text Availability

Check project folder first (if applicable), then default locations. Try per-device cache first (scalable), then fall back to legacy monolithic file.

```bash
python3 -c "
import json, os

knumber = 'KNUMBER'
cache_dir = os.path.expanduser('~/fda-510k-data/extraction/cache')
index_file = os.path.join(cache_dir, 'index.json')

# Try per-device cache first (preferred — scalable)
if os.path.exists(index_file):
    with open(index_file) as f:
        index = json.load(f)
    if knumber in index:
        device_path = os.path.join(os.path.expanduser('~/fda-510k-data/extraction'), index[knumber]['file_path'])
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
    pdf_json = os.path.expanduser('~/fda-510k-data/extraction/pdf_data.json')
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

### Step 5.5: openFDA Safety Check (MAUDE Events + Recalls)

**If the API is available and the device was found**, run MAUDE event count and recall checks. This provides critical safety context that flat files cannot.

```bash
python3 << 'PYEOF'
import urllib.request, urllib.parse, json, os, re

# Read settings
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
    print("SAFETY_SKIP:disabled")
    exit(0)

knumber = "KNUMBER"          # Replace with actual K-number
product_code = "PRODUCTCODE" # Replace with product code from Step 2

def fda_query(endpoint, search, limit=100, count_field=None):
    params = {"search": search, "limit": str(limit)}
    if count_field:
        params["count"] = count_field
    if api_key:
        params["api_key"] = api_key
    url = f"https://api.fda.gov/device/{endpoint}.json?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/5.21.0)"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"results": []}
        return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}

# 1. MAUDE event count by type for the product code
print("--- MAUDE EVENTS ---")
maude = fda_query("event", f'device.device_report_product_code:"{product_code}"', count_field="event_type.exact")
if "results" in maude:
    total = sum(r["count"] for r in maude["results"])
    print(f"MAUDE_TOTAL:{total}")
    for r in maude["results"]:
        print(f"MAUDE_TYPE:{r['term']}:{r['count']}")
elif "error" in maude:
    print(f"MAUDE_ERROR:{maude['error']}")
else:
    print("MAUDE_TOTAL:0")

# 2. Recall check for this specific K-number
print("--- RECALLS ---")
recalls = fda_query("recall", f'k_numbers:"{knumber}"')
recall_total = recalls.get("meta", {}).get("results", {}).get("total", 0)
recall_returned = len(recalls.get("results", []))
print(f"SHOWING:{recall_returned}_OF:{recall_total}")
if recalls.get("results"):
    print(f"RECALL_COUNT:{len(recalls['results'])}")
    for r in recalls["results"]:
        status = r.get("recall_status", "Unknown")
        reason = r.get("reason_for_recall", "N/A")[:100]
        date = r.get("event_date_initiated", "N/A")
        print(f"RECALL:{status}|{date}|{reason}")
else:
    print("RECALL_COUNT:0")

# 3. Also check recalls for the product code (broader)
pc_recalls = fda_query("recall", f'product_code:"{product_code}"', count_field="recall_status")
if "results" in pc_recalls:
    total_pc = sum(r["count"] for r in pc_recalls["results"])
    print(f"PC_RECALL_TOTAL:{total_pc}")
    for r in pc_recalls["results"]:
        print(f"PC_RECALL_STATUS:{r['term']}:{r['count']}")
PYEOF
```

**Report in the output**:

- **MAUDE Events** (product code): X total adverse events (Y Injury, Z Malfunction, W Death)
  - If >0 deaths: Flag prominently
  - If >100 total events: Note "high event volume — consider running `/fda:safety --product-code CODE` for detailed analysis"
- **Recalls** (this device): X recalls found — or "No recalls"
  - For each recall: Class (I/II/III), status (Ongoing/Completed), date, reason summary
- **Recalls** (product code): X total recalls across all devices with this product code

If the API is disabled or unreachable, skip this section silently (this data is not available from flat files).

### Step 6: OCR Error Suggestions

If a number is NOT found in the primary database, suggest possible OCR corrections:
- O → 0 (letter O to zero)
- I → 1 (letter I to one)
- S → 5 (letter S to five)
- B → 8 (letter B to eight)

Try common corrections and check if the corrected number exists:
```bash
grep -i "CORRECTED_NUMBER" ~/fda-510k-data/extraction/pmn*.txt 2>/dev/null
```

## Output Format

For each number, present a report using the standard FDA Professional CLI format (see `references/output-formatting.md`):

```
  FDA Device Validation Report
  {KNUMBER} — {FOUND/NOT FOUND}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: {date} | Source: {openFDA API / flat files} | v5.22.0

DEVICE RECORD
────────────────────────────────────────

  Applicant:         {Company name}
  Device Name:       {Official device name}
  Decision:          {date} — {code} ({description})
  Product Code:      {code}
  Clearance Type:    {Traditional / Special / Abbreviated}
  Advisory Committee:{panel}
  Review Time:       {days} days
  Third Party:       {Yes/No}
  Statement/Summary: {type}
  URL:               {FDA submission link}

PREDICATE RELATIONSHIPS
────────────────────────────────────────

  Predicates cited:  {list or explanation of why unavailable}
  Cited by:          {list of devices citing this as predicate}

SAFETY SIGNALS
────────────────────────────────────────

  MAUDE Events:      {X total (Y Injury, Z Malfunction)}
  Recalls (device):  {X recalls or "None found"}
  Recalls (product): {Y total for product code}

PDF TEXT
────────────────────────────────────────

  Status:            {✓ Cached (X chars) / ✗ Not cached}
  Action:            {guidance on what to do}
```

**IMPORTANT**: For every field where data is unavailable, explain WHY it's unavailable and HOW to get it. Never just say "Not found" without context.

## Data Gaps & Next Steps

After presenting all device results, add a **Data Gaps & Next Steps** section that aggregates all missing data into actionable commands:

```
DATA GAPS
────────────────────────────────────────

  ✗ output.csv — No predicate extraction results exist
    → Run: `/fda:extract stage2`

  ✓ pdf_data.json — 209 PDFs cached (text available)
    → Run: `/fda:summarize --knumbers K022854 --sections all`

  ✓ 510k_download.csv — 118 records with metadata
  ✓ pmn96cur.txt — FDA database available
  ✗ merged_data.csv — Not found

NEXT STEPS
────────────────────────────────────────

  1. Extract predicates — `/fda:extract stage2`
  2. Analyze device sections — `/fda:summarize --knumbers {KNUMBER}`
  3. Run safety analysis — `/fda:safety --product-code {CODE}`

{If API_KEY_NUDGE:true was printed, add this line before the disclaimer:}
  Tip: Get 120x more API requests/day with a free key → /fda:configure --setup-key

────────────────────────────────────────
  This report is AI-generated from public FDA data.
  Verify independently. Not regulatory advice.
────────────────────────────────────────
```

This section should:
1. List ALL data sources checked with ✓/✗ status
2. For each missing source, give the exact command to create it
3. For each available source, suggest what analysis it enables
4. Prioritize recommendations (most impactful first)

## Interactive Search Mode (--search)

When invoked with `--search`, validate operates as an interactive 510(k) database search tool instead of single-device validation.

### Parse Search Arguments

From `$ARGUMENTS`, extract:
- `--search QUERY` — Free-text search against device names (e.g., "spinal fusion", "wound dressing")
- `--product-code CODE` — Filter by product code
- `--year RANGE` — Year range filter (e.g., "2023-2025", "2024", "2020-2025")
- `--applicant NAME` — Filter by company name
- `--limit N` — Max results (default 25, max 100)
- `--sort FIELD` — Sort by: date, applicant, device_name (default: date descending)

### Search Execution

```bash
python3 << 'PYEOF'
import urllib.request, urllib.parse, json, os, re

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

if not api_enabled:
    print("ERROR:Search mode requires openFDA API. Enable with /fda:configure")
    exit(1)

# Build combined search filters
parts = []
query = "SEARCH_QUERY"  # Replace with --search value
product_code = "PRODUCT_CODE"  # Replace or empty
applicant = "APPLICANT"  # Replace or empty
year_start = "YEAR_START"  # Replace or empty
year_end = "YEAR_END"  # Replace or empty
limit = 25  # Replace with --limit value

if query and query != "SEARCH_QUERY":
    parts.append(f'device_name:"{query}"')
if product_code and product_code != "PRODUCT_CODE":
    parts.append(f'product_code:"{product_code}"')
if applicant and applicant != "APPLICANT":
    parts.append(f'applicant:"{applicant}"')
if year_start and year_start != "YEAR_START":
    start = f"{year_start}0101"
    end = f"{year_end}1231" if year_end and year_end != "YEAR_END" else "29991231"
    parts.append(f"decision_date:[{start}+TO+{end}]")

if not parts:
    print("ERROR:Provide at least --search, --product-code, or --applicant")
    exit(1)

search = "+AND+".join(parts)
params = {"search": search, "limit": str(limit)}

# Add sort parameter — default: most recent first
sort_field = "SORT_FIELD"  # Replace with --sort value if provided
if sort_field and sort_field != "SORT_FIELD":
    params["sort"] = sort_field
else:
    params["sort"] = "decision_date:desc"

if api_key:
    params["api_key"] = api_key

url = f"https://api.fda.gov/device/510k.json?{urllib.parse.urlencode(params)}"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/5.21.0)"})

try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
        total = data.get("meta", {}).get("results", {}).get("total", 0)
        print(f"TOTAL:{total}")
        for r in data.get("results", []):
            print(f"RESULT:{r.get('k_number','?')}|{r.get('device_name','?')}|{r.get('applicant','?')}|{r.get('decision_date','?')}|{r.get('product_code','?')}|{r.get('clearance_type','?')}")
except urllib.error.HTTPError as e:
    if e.code == 404:
        print("TOTAL:0")
    else:
        print(f"ERROR:HTTP {e.code}")
except Exception as e:
    print(f"ERROR:{e}")
PYEOF
```

### Search Output Format

```
  FDA 510(k) Database Search Results
  Query: "{search terms}"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: {date} | Total matches: {N} | Showing: {limit} | v5.22.0

RESULTS
────────────────────────────────────────

  | # | K-Number | Device Name           | Applicant     | Decision Date | Product Code | Type        |
  |---|----------|-----------------------|---------------|---------------|--------------|-------------|
  | 1 | K241335  | Cervical Fusion Cage  | COMPANY A     | 2024-03-15    | OVE          | Traditional |
  | 2 | K240123  | Spinal Spacer System  | COMPANY B     | 2024-02-28    | OVE          | Traditional |
  ...

  {N} total matches found. Showing first {limit}.
  For detailed validation of a specific device: `/fda:validate K241335`
  To see more results: `/fda:validate --search "{query}" --limit 50`

────────────────────────────────────────
  This report is AI-generated from public FDA data.
  Verify independently. Not regulatory advice.
────────────────────────────────────────
```

## PMA-Specific Validation Output

When validating a P-number (PMA), show PMA-specific fields in addition to the standard fields:

```
DEVICE RECORD (PMA)
────────────────────────────────────────

  PMA Number:        {P-number}
  Applicant:         {Company name}
  Trade Name:        {Commercial trade name}
  Generic Name:      {Generic device name}
  Decision:          {date} — {code} ({description})
  Product Code:      {code}
  Advisory Committee:{panel}
  Supplement Number:  {if supplement}
  Supplement Type:    {if supplement}
  Docket Number:     {if available}
  URL:               https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpma/pma.cfm?id={P-number}

PMA SUPPLEMENT HISTORY
────────────────────────────────────────

  {Number of supplements found}
  Most recent: {supplement number} — {date} — {type}
```

Query for supplement history:

```bash
python3 << 'PYEOF'
import urllib.request, urllib.parse, json, os, re

# Standard API setup...
settings_path = os.path.expanduser('~/.claude/fda-predicate-assistant.local.md')
api_key = os.environ.get('OPENFDA_API_KEY')
if os.path.exists(settings_path):
    with open(settings_path) as f:
        content = f.read()
    if not api_key:
        m = re.search(r'openfda_api_key:\s*(\S+)', content)
        if m and m.group(1) != 'null':
            api_key = m.group(1)

pma_number = "P870024"  # Replace with actual
params = {"search": f'pma_number:"{pma_number}"', "limit": "100"}
if api_key:
    params["api_key"] = api_key

url = f"https://api.fda.gov/device/pma.json?{urllib.parse.urlencode(params)}"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/5.21.0)"})

try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
        total = data.get("meta", {}).get("results", {}).get("total", 0)
        print(f"PMA_TOTAL:{total}")
        for r in data.get("results", []):
            supp = r.get('supplement_number', '')
            supp_type = r.get('supplement_type', '')
            print(f"PMA_RECORD:{r.get('pma_number','?')}|{supp}|{supp_type}|{r.get('trade_name','?')}|{r.get('generic_name','?')}|{r.get('decision_date','?')}|{r.get('decision_code','?')}")
except Exception as e:
    print(f"PMA_ERROR:{e}")
PYEOF
```

## De Novo (DEN) Validation Notes

When validating a DEN-number:

1. **openFDA has no dedicated De Novo endpoint.** Some DEN numbers are indexed in the `/device/510k` endpoint.
2. If not found in `/device/510k`, search by device name in the classification endpoint to find the De Novo classification order.
3. Report the limitation clearly:

```
DEVICE RECORD (De Novo)
────────────────────────────────────────

  DEN Number:        {DEN-number}
  Status:            {Found in 510k endpoint / Not found}
  Note:              openFDA has no dedicated De Novo endpoint.
                     Some DEN numbers are indexed in the 510k database.
                     For comprehensive De Novo data, check:
                     https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/denovo.cfm
```
