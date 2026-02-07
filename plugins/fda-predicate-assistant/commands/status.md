---
description: Show available FDA pipeline data, file freshness, script availability, and record counts
allowed-tools: Bash, Read, Glob, Grep
---

# FDA Pipeline Status

You are reporting the current state of all FDA data across the pipeline. This answers: "What do I have to work with?"

## Resolve Plugin Root

**Before running any checks**, resolve the plugin install path so you can find bundled scripts:

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

If `$FDA_PLUGIN_ROOT` is empty, report that the plugin installation could not be located and skip script checks.

## Check All Data Sources

Run these checks and compile a status report:

### 0. Plugin Scripts & Dependencies

Check if bundled scripts are available:
```bash
ls -la "$FDA_PLUGIN_ROOT/scripts/predicate_extractor.py" "$FDA_PLUGIN_ROOT/scripts/batchfetch.py" "$FDA_PLUGIN_ROOT/scripts/requirements.txt" 2>/dev/null
```

Check if dependencies are installed:
```bash
python -c "import requests, tqdm, fitz, pdfplumber, orjson, ijson" 2>&1 && echo "Stage 2 deps: OK" || echo "Stage 2 deps: MISSING"
python -c "import requests, pandas, tqdm, colorama, numpy" 2>&1 && echo "Stage 1 deps: OK" || echo "Stage 1 deps: MISSING"
```

Report:
- Script availability (predicate_extractor.py, batchfetch.py)
- Dependency status for each stage
- If missing: `pip install -r "$FDA_PLUGIN_ROOT/scripts/requirements.txt"`

### 0.5. openFDA API Status

Check API connectivity and configuration:

```bash
python3 << 'PYEOF'
import urllib.request, urllib.parse, json, os, re, time

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
    print("STATUS:disabled")
    exit(0)

# Quick connectivity check — hit 510k endpoint with limit=1
params = {"search": 'k_number:"K241335"', "limit": "1"}
if api_key:
    params["api_key"] = api_key
url = f"https://api.fda.gov/device/510k.json?{urllib.parse.urlencode(params)}"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/1.0)"})
start = time.time()
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read())
        elapsed = (time.time() - start) * 1000
        print(f"STATUS:online")
        print(f"LATENCY:{elapsed:.0f}ms")
        key_source = 'env' if os.environ.get('OPENFDA_API_KEY') else ('file' if api_key else 'none')
        print(f"API_KEY:{'yes' if api_key else 'no'} (source: {key_source})")
        print(f"RATE_TIER:{'120K/day' if api_key else '1K/day'}")
except Exception as e:
    print(f"STATUS:unreachable")
    print(f"ERROR:{e}")
    print(f"API_KEY:{'yes' if api_key else 'no'}")
PYEOF
```

Report in the status output:
- If `STATUS:disabled`: Show `openFDA API  ○  Disabled (offline mode) — /fda:configure --set openfda_enabled true`
- If `STATUS:online`: Show `openFDA API  ✓  Online ({LATENCY}ms) | Key: {yes/no} | Rate: {RATE_TIER}`
- If `STATUS:unreachable`: Show `openFDA API  ✗  Unreachable — check network connection`

If the API is reachable and no key is configured, add a recommendation: "Get a free API key at https://open.fda.gov/apis/authentication/ for 120K requests/day (vs 1K/day without key). Run `/fda:configure --setup-key` for secure setup instructions."

### 1. Projects

Check for project folders:

```bash
ls -d ~/fda-510k-data/projects/*/ 2>/dev/null
```

Also check settings for custom `projects_dir`:
```bash
cat ~/.claude/fda-predicate-assistant.local.md 2>/dev/null
```

For each project found, read its `query.json` to get metadata:
```bash
cat ~/fda-510k-data/projects/*/query.json 2>/dev/null
```

Also check for review.json to determine predicate source:
```bash
python3 << 'PYEOF'
import json, os, glob
projects_dir = os.path.expanduser("~/fda-510k-data/projects")
for proj_dir in sorted(glob.glob(os.path.join(projects_dir, "*"))):
    if not os.path.isdir(proj_dir):
        continue
    review_path = os.path.join(proj_dir, "review.json")
    if os.path.exists(review_path):
        with open(review_path) as f:
            review = json.load(f)
        mode = review.get("review_mode", "unknown")
        manual = review.get("manual_proposal", False)
        pred_count = len(review.get("predicates", {}))
        ref_count = len(review.get("reference_devices", {}))
        accepted = sum(1 for v in review.get("predicates", {}).values() if v.get("decision") == "accepted")
        proj_name = os.path.basename(proj_dir)
        print(f"REVIEW:{proj_name}|mode={mode}|manual={manual}|predicates={pred_count}|accepted={accepted}|references={ref_count}")
PYEOF
```

Report each project:
- Project name
- Filters used (product codes, years, applicants)
- Stage 1 status: records in 510k_download.csv, PDFs downloaded
- Stage 2 status: devices in output.csv, errors
- **Predicates**: If review.json exists, show: "{accepted} accepted predicates ({mode})" where mode is "extraction review", "manual proposal", or "auto review". If `manual_proposal == true`, display "Predicates: manual proposal ({N} predicates, {M} references)"
- Created date and last updated

If no projects exist, note that `/fda:extract` now saves to project folders.

### 2. FDA Database Files (pmn*.txt, pma*.txt, foiaclass.txt)

Check multiple possible locations for FDA database files:

```bash
# Check PredicateExtraction directory
ls -la ~/fda-510k-data/extraction/pmn*.txt ~/fda-510k-data/extraction/pma*.txt ~/fda-510k-data/extraction/foiaclass.txt 2>/dev/null
# Check plugin scripts directory (if --data-dir was used)
ls -la "$FDA_PLUGIN_ROOT/scripts/"pmn*.txt "$FDA_PLUGIN_ROOT/scripts/"pma*.txt 2>/dev/null
# Check BatchFetch fda_data directory
ls -la ~/fda-510k-data/batchfetch/fda_data/pmn*.txt ~/fda-510k-data/batchfetch/fda_data/foiaclass.txt 2>/dev/null
```

For each file found, report:
- File size and last modified date
- Record count: `wc -l <file>`
- Age in days (compare modified date to today)
- If older than 5 days, suggest refreshing

### 3. 510kBF Downloads (Legacy) (510k_download.csv)

```bash
ls -la ~/fda-510k-data/batchfetch/510k_download.csv 2>/dev/null
```

If found:
- Record count: `wc -l`
- Date range: read first and last DECISIONDATE values
- Filters used: check if header comments or filter metadata exists
- Product codes present: `cut -d',' -f4 | sort -u | wc -l` (approximate)

### 4. Downloaded PDFs (Legacy)

```bash
find ~/fda-510k-data/batchfetch/510ks/ -name "*.pdf" 2>/dev/null | wc -l
```

If PDFs exist:
- Total PDF count
- Year directories present: `ls ~/fda-510k-data/batchfetch/510ks/`
- Approximate disk usage: `du -sh ~/fda-510k-data/batchfetch/510ks/`

Also check the PredicateExtraction directory:
```bash
find ~/fda-510k-data/extraction/ -maxdepth 1 -name "*.pdf" 2>/dev/null | wc -l
```

And organized PDF storage:
```bash
ls -d ~/fda-510k-data/extraction/2024 ~/fda-510k-data/extraction/2025 2>/dev/null
```

### 5. Extraction Results (Legacy) (output.csv, supplement.csv)

```bash
ls -la ~/fda-510k-data/extraction/output.csv ~/fda-510k-data/extraction/supplement.csv 2>/dev/null
```

If found:
- Record count for each
- Last modified date
- Quick stats: devices with predicates vs without

### 6. Cached PDF Text (Legacy) (pdf_data.json)

```bash
ls -la ~/fda-510k-data/extraction/pdf_data.json 2>/dev/null
```

If found:
- File size
- Approximate entry count: `grep -c '"filename"' pdf_data.json` or similar key count

### 7. Merged Data (Legacy) (merged_data.csv)

```bash
ls -la ~/fda-510k-data/batchfetch/merged_data.csv 2>/dev/null
```

If found:
- Record count
- Last modified date

### 8. Analytics Workbook (Legacy)

```bash
ls -la ~/fda-510k-data/batchfetch/Applicant_ProductCode_Tables.xlsx 2>/dev/null
```

### 9. Error Log (Legacy)

```bash
ls -la ~/fda-510k-data/extraction/error_log.txt 2>/dev/null
```

If found:
- Number of failed PDFs: `wc -l`

## Output Format

Present a clean status report using the standard FDA Professional CLI format (see `references/output-formatting.md`):

```
  FDA Pipeline Status
  Data inventory and connectivity check
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: {date} | v4.6.0

PLUGIN SCRIPTS
────────────────────────────────────────

  predicate_extractor.py   ✓  Available
  batchfetch.py            ✓  Available
  Stage 1 dependencies     ✓  Installed
  Stage 2 dependencies     ✓  Installed

OPENFDA API
────────────────────────────────────────

  Connectivity             ✓  Online (245ms)
  API Key                  ✗  Not configured (1K/day limit)
  Rate Tier                   1K/day (get free key for 120K/day)

PROJECTS
────────────────────────────────────────

  | Project | Stage 1 | Stage 2 | Status |
  |---------|---------|---------|--------|
  | KGN_2020-2025 | 247 records, 195 PDFs | 180 devices | ✓ Complete |
  | DXY_2023 | 52 records, 48 PDFs | not run | ○ Partial |

SOURCE DATA
────────────────────────────────────────

  pmn96cur.txt     ✓  98,580 records  (3 days old)
  pma.txt          ✓  55,663 records  (3 days old)
  foiaclass.txt    ✗  Not found

LEGACY DATA
────────────────────────────────────────

  510k_download.csv    ✓  118 records
  output.csv           ✗  Not found
  pdf_data.json        ✓  2.4 MB cached

NEXT STEPS
────────────────────────────────────────

  1. {based on what's missing}

────────────────────────────────────────
  This report is AI-generated from public FDA data.
  Verify independently. Not regulatory advice.
────────────────────────────────────────
```

Use ✓ for present, ✗ for missing, ○ for pending/disabled, and ⚠ for degraded. Adapt sections to what actually exists — don't show sections where nothing is found.

### 7. FDA Correspondence Tracking

For each project, check for `fda_correspondence.json`:

```bash
python3 << 'PYEOF'
import json, os, glob
from datetime import date, datetime

projects_dir = os.path.expanduser("~/fda-510k-data/projects")
if not os.path.isdir(projects_dir):
    print("CORR:NO_PROJECTS")
    exit(0)

for proj_dir in sorted(glob.glob(os.path.join(projects_dir, "*"))):
    if not os.path.isdir(proj_dir):
        continue
    corr_path = os.path.join(proj_dir, "fda_correspondence.json")
    if not os.path.exists(corr_path):
        continue
    proj_name = os.path.basename(proj_dir)
    with open(corr_path) as f:
        data = json.load(f)
    entries = data.get("entries", [])
    if not entries:
        continue

    today = date.today()
    total = len(entries)
    open_count = sum(1 for e in entries if e.get("status") == "open")
    overdue = []
    for e in entries:
        if e.get("status") == "open" and e.get("deadline"):
            try:
                dl = datetime.strptime(e["deadline"], "%Y-%m-%d").date()
                if dl < today:
                    overdue.append({"id": e.get("id"), "summary": e.get("summary", ""), "days": (today - dl).days})
            except ValueError:
                pass
    resolved = sum(1 for e in entries if e.get("status") == "resolved")
    next_deadline = None
    for e in entries:
        if e.get("status") == "open" and e.get("deadline"):
            try:
                dl = datetime.strptime(e["deadline"], "%Y-%m-%d").date()
                if dl >= today and (next_deadline is None or dl < next_deadline):
                    next_deadline = dl
            except ValueError:
                pass
    print(f"CORR_PROJECT:{proj_name}")
    print(f"CORR_TOTAL:{total}")
    print(f"CORR_OPEN:{open_count}")
    print(f"CORR_OVERDUE:{len(overdue)}")
    print(f"CORR_RESOLVED:{resolved}")
    print(f"CORR_NEXT_DEADLINE:{next_deadline or 'None'}")
    for o in overdue:
        print(f"CORR_OVERDUE_ITEM:#{o['id']}|{o['summary'][:60]}|{o['days']} days")
PYEOF
```

Display in the status report:

```
FDA CORRESPONDENCE
────────────────────────────────────────

  | Project | Open | Overdue | Resolved | Next Deadline |
  |---------|------|---------|----------|---------------|
  | {name}  | {n}  | {n}     | {n}      | {date}        |

  ⚠ Overdue items:
    #{id}: {summary} — {days} days past deadline
```

## Recommendations

After the status report, suggest logical next steps:
- If dependencies missing: "Run `pip install -r \"$FDA_PLUGIN_ROOT/scripts/requirements.txt\"`"
- If no FDA database files: "Run `/fda:extract stage2` to download FDA databases"
- If no 510k_download.csv: "Run `/fda:extract stage1` to filter and download PDFs"
- If PDFs exist but no output.csv: "Run `/fda:extract stage2` to extract predicates"
- If output.csv exists: "Run `/fda:analyze` for insights"
- If database files are old: "Database files are X days old, consider refreshing"
- If overdue correspondence: "Run `/fda:presub --correspondence --project NAME` to review overdue FDA commitments"
