---
description: View or modify FDA predicate assistant settings and data directory paths
allowed-tools: Read, Write, Bash
argument-hint: "[--show | --set KEY VALUE | --setup-key | --test-api | --migrate-cache]"
---

# FDA Predicate Assistant Configuration

## Resolve Plugin Root

**Before referencing any bundled scripts**, resolve the plugin install path:

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
```

---

You are managing configuration settings for the FDA predicate extraction pipeline.

## Settings File Location

Settings are stored in: `~/.claude/fda-predicate-assistant.local.md`

## Available Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `projects_dir` | `~/fda-510k-data/projects` | Root directory for all project folders (each extraction query gets its own folder) |
| `batchfetch_dir` | `~/fda-510k-data/batchfetch` | Legacy directory containing 510kBF output (510k_download.csv, merged_data.csv) |
| `extraction_dir` | `~/fda-510k-data/extraction` | Directory containing extraction output (output.csv, pdf_data.json) |
| `pdf_storage_dir` | `~/fda-510k-data/batchfetch/510ks` | Where downloaded PDFs are stored |
| `data_dir` | `~/fda-510k-data/extraction` | Where FDA database files (pmn*.txt, pma.txt, foiaclass.txt) are stored |
| `extraction_script` | `predicate_extractor.py` | Which extraction script to use (bundled in plugin) |
| `batchfetch_script` | `batchfetch.py` | Which batch fetch script to use (bundled in plugin) |
| `ocr_mode` | `smart` | OCR processing mode: smart, always, never |
| `batch_size` | `100` | Number of PDFs to process per batch |
| `workers` | `4` | Number of parallel processing workers |
| `cache_days` | `5` | Days to cache FDA database files |
| `default_year` | `null` | Default year filter (null = all years) |
| `default_product_code` | `null` | Default product code filter |
| `openfda_api_key` | `null` | openFDA API key for higher rate limits (120K/day vs 1K/day). Set via env var `OPENFDA_API_KEY` or settings file — never paste in chat. |
| `openfda_enabled` | `true` | Enable/disable openFDA API calls (set false for offline-only mode) |
| `exclusion_list` | `~/fda-510k-data/exclusion_list.json` | Path to device exclusion list JSON file (used by `/fda:review`) |
| `auto_review` | `false` | If true, `/fda:review` auto-accepts predicates scoring 80+ and auto-rejects below 20 |

## Commands

### Show Current Settings

If `$ARGUMENTS` is `--show` or empty, read and display the current settings:

Read the settings file at `~/.claude/fda-predicate-assistant.local.md`. If it doesn't exist, report defaults and offer to create one.

Also report on bundled scripts:
```
Plugin Scripts (at $FDA_PLUGIN_ROOT/scripts/):
  predicate_extractor.py  — Stage 2: Extract predicates from PDFs
  batchfetch.py           — Stage 1: Filter catalog & download PDFs
  requirements.txt        — Python dependencies for both scripts
```

### Set a Value

If `$ARGUMENTS` starts with `--set`, parse KEY and VALUE, then update the settings file.

Validate the key is one of the known settings before writing. For directory paths, verify the directory exists.

Special handling for `openfda_api_key`:
- **Do NOT accept the API key directly in chat** — it would be stored in conversation history.
- Instead, instruct the user to set it via one of the safe methods below, then offer to validate it:

```
To set your openFDA API key securely (without it appearing in chat):

Option 1 — Environment variable (recommended for CLI users):
  Add to your ~/.bashrc or ~/.zshrc:
    export OPENFDA_API_KEY="your-key-here"
  Then restart your terminal or run: source ~/.bashrc

Option 2 — Settings file (recommended for Claude Desktop users):
  Edit ~/.claude/fda-predicate-assistant.local.md directly:
    openfda_api_key: your-key-here

Option 3 — Setup script (interactive, outside Claude):
  python3 "$FDA_PLUGIN_ROOT/scripts/setup_api_key.py"

Get a free key at: https://open.fda.gov/apis/authentication/
```

After the user confirms they've set it, run the `--test-api` flow to validate.

### Setup API Key

If `$ARGUMENTS` is `--setup-key`, display the secure key setup instructions (same as the special handling above). Then check if a key is already configured (via env var or settings file) and report the current status without revealing the key value:

```python
import os, re
api_key = os.environ.get('OPENFDA_API_KEY')
source = 'environment variable' if api_key else None
if not api_key:
    settings_path = os.path.expanduser('~/.claude/fda-predicate-assistant.local.md')
    if os.path.exists(settings_path):
        with open(settings_path) as f:
            content = f.read()
        m = re.search(r'openfda_api_key:\s*(\S+)', content)
        if m and m.group(1) != 'null':
            api_key = m.group(1)
            source = 'settings file'
if api_key:
    print(f"KEY_STATUS:configured (via {source})")
    print(f"KEY_PREVIEW:{api_key[:4]}...{api_key[-4:]}")  # Show only first/last 4 chars
else:
    print("KEY_STATUS:not configured")
```

### Test openFDA API

If `$ARGUMENTS` is `--test-api`, test connectivity to all 7 openFDA Device API endpoints.

Use the query template from `references/openfda-api.md`:

```bash
python3 << 'PYEOF'
import urllib.request, urllib.parse, json, os, re, time

# Read settings for API key
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
    print("openFDA API is DISABLED (openfda_enabled: false)")
    print("Enable with: /fda:configure --set openfda_enabled true")
    exit(0)

endpoints = [
    ("510k", 'k_number:"K241335"'),
    ("classification", 'product_code:"KGN"'),
    ("event", 'device.product_code:"KGN"'),
    ("recall", 'product_code:"KGN"'),
    ("pma", 'pma_number:"P190001"'),
    ("registrationlisting", 'products.product_code:"KGN"'),
    ("udi", 'product_codes.code:"KGN"'),
]

print("  FDA API Connectivity Test")
print("  openFDA Device Endpoints")
print("━" * 56)
print(f"  Generated: {__import__('datetime').date.today()} | v4.0.0")
print()
print("API CONFIGURATION")
print("─" * 40)
print(f"  API Key: {'Configured' if api_key else 'Not set (1K/day limit)'}")
print(f"  Rate Tier: {'120K/day (with key)' if api_key else '1K/day (no key)'}")
print()
print("ENDPOINT STATUS")
print("─" * 40)

passed = 0
failed = 0
for endpoint, search in endpoints:
    params = {"search": search, "limit": "1"}
    if api_key:
        params["api_key"] = api_key
    url = f"https://api.fda.gov/device/{endpoint}.json?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/1.0)"})
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            elapsed = (time.time() - start) * 1000
            total = data.get("meta", {}).get("results", {}).get("total", "?")
            print(f"  {endpoint:25s}  ✓  ({elapsed:.0f}ms, {total} total records)")
            passed += 1
    except urllib.error.HTTPError as e:
        elapsed = (time.time() - start) * 1000
        if e.code == 404:
            print(f"  {endpoint:25s}  ✓  ({elapsed:.0f}ms, 0 results for test query)")
            passed += 1
        else:
            print(f"  {endpoint:25s}  ✗  (HTTP {e.code}: {e.reason})")
            failed += 1
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        print(f"  {endpoint:25s}  ✗  ({e})")
        failed += 1
    time.sleep(0.5)  # Brief pause between requests

print()
print("RESULTS")
print("─" * 40)
print(f"  {passed}/7 endpoints reachable, {failed} failed")
if failed == 0:
    print("  ✓ All endpoints operational")
elif failed == 7:
    print("  ✗ No endpoints reachable — check network connectivity")
else:
    print("  ⚠ Some endpoints failed — may be temporary, retry in a few minutes")
print()
print("─" * 40)
print("  This report is AI-generated from public FDA data.")
print("  Verify independently. Not regulatory advice.")
print("─" * 40)
PYEOF
```

Report the results to the user.

## Settings File Format

The settings file uses YAML frontmatter:

```markdown
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
---

# FDA Predicate Assistant Settings

This file stores your preferences for the FDA 510(k) pipeline.

## Directory Paths

- **projects_dir**: Root for all project folders — each `/fda:extract` query gets its own subfolder
- **batchfetch_dir**: Legacy location for 510kBF output (510k_download.csv, merged_data.csv)
- **extraction_dir**: Legacy location for PredicateExtraction output (output.csv, pdf_data.json)
- **pdf_storage_dir**: Where downloaded PDFs are organized by year/applicant/productcode
- **data_dir**: Where FDA database files are stored (pmn*.txt, pma.txt, foiaclass.txt)

## Script Configuration

- **extraction_script**: predicate_extractor.py (bundled in plugin at $FDA_PLUGIN_ROOT/scripts/)
- **batchfetch_script**: batchfetch.py (bundled in plugin at $FDA_PLUGIN_ROOT/scripts/)

## Processing Options

- **ocr_mode**: smart (use OCR only when needed), always, never
- **batch_size**: Number of PDFs per processing batch
- **workers**: Parallel processing workers (adjust based on CPU)
- **cache_days**: How long to cache FDA database files

## Filters

- **default_year**: Set to filter by year automatically
- **default_product_code**: Set to filter by product code automatically

## openFDA API

- **openfda_api_key**: API key for higher rate limits (get free key at https://open.fda.gov/apis/authentication/). **Set via env var `OPENFDA_API_KEY` or edit this file directly — do not paste in chat.**
- **openfda_enabled**: Set to false to disable all API calls (offline mode)

## Review & Validation

- **exclusion_list**: Path to JSON file listing device numbers to flag/skip during review (see `/fda:review`)
- **auto_review**: If true, `/fda:review` auto-accepts predicates scoring 80+ and auto-rejects below 20
```

### Manage Exclusion List

The exclusion list tracks device numbers that should be flagged or skipped during `/fda:review`. It prevents known-bad predicates from being repeatedly considered across review sessions.

#### Show Exclusions (`--show-exclusions`)

If `$ARGUMENTS` is `--show-exclusions`, read and display the current exclusion list:

```bash
python3 << 'PYEOF'
import json, os, re

settings_path = os.path.expanduser('~/.claude/fda-predicate-assistant.local.md')
exclusion_path = os.path.expanduser('~/fda-510k-data/exclusion_list.json')

if os.path.exists(settings_path):
    with open(settings_path) as f:
        m = re.search(r'exclusion_list:\s*(.+)', f.read())
        if m:
            exclusion_path = os.path.expanduser(m.group(1).strip())

if os.path.exists(exclusion_path):
    with open(exclusion_path) as f:
        data = json.load(f)
    devices = data.get("devices", {})
    if devices:
        print(f"Exclusion list: {exclusion_path}")
        print(f"Total excluded devices: {len(devices)}")
        print()
        for kn, info in sorted(devices.items()):
            print(f"  {kn}: {info.get('reason', 'No reason given')}")
            print(f"    Added: {info.get('added', '?')} by {info.get('added_by', '?')}")
    else:
        print(f"Exclusion list exists but is empty: {exclusion_path}")
else:
    print(f"No exclusion list found at: {exclusion_path}")
    print("Create one with: /fda:configure --add-exclusion K123456 \"reason\"")
PYEOF
```

#### Add Exclusion (`--add-exclusion K123456 "reason"`)

If `$ARGUMENTS` starts with `--add-exclusion`, parse the K-number and reason, then add to the exclusion list:

```bash
python3 << 'PYEOF'
import json, os, re
from datetime import datetime

# Parse arguments — replace KNUMBER and REASON with actual values
knumber = "KNUMBER"  # Replace
reason = "REASON"    # Replace

settings_path = os.path.expanduser('~/.claude/fda-predicate-assistant.local.md')
exclusion_path = os.path.expanduser('~/fda-510k-data/exclusion_list.json')

if os.path.exists(settings_path):
    with open(settings_path) as f:
        m = re.search(r'exclusion_list:\s*(.+)', f.read())
        if m:
            exclusion_path = os.path.expanduser(m.group(1).strip())

# Load or create exclusion list
if os.path.exists(exclusion_path):
    with open(exclusion_path) as f:
        data = json.load(f)
else:
    os.makedirs(os.path.dirname(exclusion_path), exist_ok=True)
    data = {"version": 1, "devices": {}}

# Add the device
data["devices"][knumber.upper()] = {
    "reason": reason,
    "added": datetime.utcnow().isoformat() + "Z",
    "added_by": "manual"
}

with open(exclusion_path, 'w') as f:
    json.dump(data, f, indent=2)

print(f"Added {knumber.upper()} to exclusion list: {reason}")
print(f"Total excluded devices: {len(data['devices'])}")
PYEOF
```

Validate the K-number format before adding (must match `K\d{6}`, `P\d{6}`, `DEN\d{6}`, or `N\d{4,5}`).

#### Clear Exclusions (`--clear-exclusions`)

If `$ARGUMENTS` is `--clear-exclusions`, confirm with the user before clearing:

Ask the user: "This will remove all {N} devices from the exclusion list. Are you sure?"

If confirmed:
```bash
python3 << 'PYEOF'
import json, os, re

settings_path = os.path.expanduser('~/.claude/fda-predicate-assistant.local.md')
exclusion_path = os.path.expanduser('~/fda-510k-data/exclusion_list.json')

if os.path.exists(settings_path):
    with open(settings_path) as f:
        m = re.search(r'exclusion_list:\s*(.+)', f.read())
        if m:
            exclusion_path = os.path.expanduser(m.group(1).strip())

if os.path.exists(exclusion_path):
    data = {"version": 1, "devices": {}}
    with open(exclusion_path, 'w') as f:
        json.dump(data, f, indent=2)
    print("Exclusion list cleared.")
else:
    print("No exclusion list found — nothing to clear.")
PYEOF
```

### Migrate Cache Format

If `$ARGUMENTS` is `--migrate-cache`, migrate from monolithic `pdf_data.json` to per-device cache:

```bash
python3 << 'PYEOF'
import json, os

extraction_dir = os.path.expanduser('~/fda-510k-data/extraction')
pdf_json = os.path.join(extraction_dir, 'pdf_data.json')
cache_dir = os.path.join(extraction_dir, 'cache')
devices_dir = os.path.join(cache_dir, 'devices')
index_file = os.path.join(cache_dir, 'index.json')

if not os.path.exists(pdf_json):
    print('ERROR: pdf_data.json not found — nothing to migrate')
    exit(1)

if os.path.exists(index_file):
    print('WARNING: Per-device cache already exists. Merging new entries only.')
    with open(index_file) as f:
        index = json.load(f)
else:
    index = {}

os.makedirs(devices_dir, exist_ok=True)

print(f'Loading pdf_data.json...')
with open(pdf_json) as f:
    data = json.load(f)

migrated = 0
skipped = 0
for filename, content in data.items():
    knumber = filename.replace('.pdf', '')
    if knumber in index:
        skipped += 1
        continue

    # Normalize content format
    if isinstance(content, dict):
        device_data = content
    else:
        device_data = {'text': str(content)}

    # Write individual device file
    device_file = os.path.join(devices_dir, f'{knumber}.json')
    with open(device_file, 'w') as f:
        json.dump(device_data, f)

    # Add to index
    rel_path = os.path.relpath(device_file, extraction_dir)
    index[knumber] = {
        'file_path': rel_path,
        'text_length': len(device_data.get('text', '')),
        'extraction_method': device_data.get('extraction_method', 'unknown'),
        'page_count': device_data.get('page_count', 0)
    }
    migrated += 1

# Write index
with open(index_file, 'w') as f:
    json.dump(index, f, indent=2)

print(f'Migration complete: {migrated} devices migrated, {skipped} already existed')
print(f'Index: {index_file} ({len(index)} total devices)')
print(f'Per-device files: {devices_dir}/')
print(f'Original pdf_data.json preserved (can delete manually when ready)')
PYEOF
```

Report the migration results and note that the original `pdf_data.json` is preserved as a backup.

## Creating Default Settings

If no settings file exists and user wants to configure, create one with the template above using the default values.
