---
description: Import eSTAR data from PDF or XML — extract form fields, predicates, and section content into project data for submission preparation
allowed-tools: Bash, Read, Glob, Grep, Write, WebFetch
argument-hint: "<pdf-or-xml-path> --project NAME [--template nIVD|IVD|PreSTAR] [--validate]"
---

# FDA eSTAR Import

> **Important**: This command assists with FDA regulatory workflows but does not provide regulatory advice. Output should be reviewed by qualified regulatory professionals before being relied upon for submission decisions.

> For external API dependencies and connection status, see [CONNECTORS.md](../CONNECTORS.md).


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

You are importing eSTAR data from a PDF (XFA form) or exported XML file into the project data structure. This enables downstream commands (`/fda:draft`, `/fda:assemble`, `/fda:export`) to use real submission data.

> **Note:** eSTAR PDFs use XFA (XML Forms Architecture). The import extracts form field values — not attached documents (test reports, images). Attachments must be added manually.

## Parse Arguments

From `$ARGUMENTS`, extract:

- **File path** (required) — Path to eSTAR PDF or exported XML file
- `--project NAME` (required) — Project to import into
- `--template nIVD|IVD|PreSTAR` — eSTAR template type (default: auto-detect)
- `--validate` — After import, validate extracted data against openFDA
- `--dry-run` — Show what would be extracted without writing files

## Step 1: Validate Input

Verify the input file exists and is a supported format (.pdf or .xml):

```bash
python3 << 'PYEOF'
import os, sys
file_path = "FILE_PATH"  # Replace with actual path
if not os.path.exists(file_path):
    print(f"ERROR: File not found: {file_path}")
    sys.exit(1)
ext = os.path.splitext(file_path)[1].lower()
if ext not in ('.pdf', '.xml'):
    print(f"ERROR: Unsupported file type: {ext}. Provide a .pdf or .xml file.")
    sys.exit(1)
print(f"FILE_OK:{file_path}|{ext}|{os.path.getsize(file_path)} bytes")
PYEOF
```

## Step 2: Check Dependencies

```bash
python3 -c "
try:
    import pikepdf; print('pikepdf:', pikepdf.__version__)
except ImportError:
    print('MISSING:pikepdf')
try:
    from bs4 import BeautifulSoup; import bs4; print('beautifulsoup4:', bs4.__version__)
except ImportError:
    print('MISSING:beautifulsoup4')
try:
    from lxml import etree; print('lxml:', etree.__version__)
except ImportError:
    print('MISSING:lxml')
"
```

If any dependency is missing, install it:
```bash
pip install pikepdf>=8.0.0 beautifulsoup4>=4.12.0 lxml>=4.9.0
```

## Step 3: Run Extraction

```bash
python3 "$FDA_PLUGIN_ROOT/scripts/estar_xml.py" extract "FILE_PATH" --project "PROJECT_NAME"
```

This writes `import_data.json` to the project directory containing:
- **applicant**: Company name, contact info, address
- **classification**: Product code, regulation number, device class, review panel
- **indications_for_use**: IFU text, Rx/OTC status
- **predicates**: List of K/P/DEN numbers found in form data
- **sections**: Narrative text for device description, SE discussion, performance, etc.
- **raw_fields**: All XFA field paths and values (for debugging)

## Step 4: Validate Imported Data (if --validate)

If `--validate` was specified, cross-check extracted data against openFDA:

```bash
python3 << 'PYEOF'
import urllib.request, urllib.parse, json, os, re

settings_path = os.path.expanduser('~/.claude/fda-predicate-assistant.local.md')
api_key = os.environ.get('OPENFDA_API_KEY')
if os.path.exists(settings_path):
    with open(settings_path) as f:
        content = f.read()
    if not api_key:
        m = re.search(r'openfda_api_key:\s*(\S+)', content)
        if m and m.group(1) != 'null':
            api_key = m.group(1)

projects_dir = os.path.expanduser('~/fda-510k-data/projects')
if os.path.exists(settings_path):
    with open(settings_path) as f:
        m = re.search(r'projects_dir:\s*(.+)', f.read())
        if m: projects_dir = os.path.expanduser(m.group(1).strip())

project = "PROJECT_NAME"  # Replace
import_file = os.path.join(projects_dir, project, 'import_data.json')
with open(import_file) as f:
    data = json.load(f)

# Validate product code
pc = data.get('classification', {}).get('product_code', '')
if pc:
    params = {"search": f'product_code:"{pc}"', "limit": "100"}
    if api_key:
        params["api_key"] = api_key
    url = f"https://api.fda.gov/device/classification.json?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/1.0)"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            total = result.get("meta", {}).get("results", {}).get("total", 0)
            print(f"CLASSIFICATION_MATCHES:{total}")
            if result.get("results"):
                r = result["results"][0]
                print(f"PRODUCT_CODE_VALID:{pc} = {r.get('device_name', 'N/A')}")
            else:
                print(f"PRODUCT_CODE_UNKNOWN:{pc}")
    except Exception as e:
        print(f"API_ERROR:{e}")

# Validate predicate K-numbers — batch OR query (1 call instead of N)
pred_knumbers = [p.get('k_number', '') for p in data.get('predicates', [])[:5] if p.get('k_number', '').startswith('K')]
if pred_knumbers:
    batch_search = "+OR+".join(f'k_number:"{kn}"' for kn in pred_knumbers)
    params = {"search": batch_search, "limit": str(len(pred_knumbers))}
    if api_key:
        params["api_key"] = api_key
    # Fix URL encoding: replace + with space before urlencode
    params["search"] = params["search"].replace("+", " ")
    url = f"https://api.fda.gov/device/510k.json?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/5.5.0)"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            found = {r.get("k_number", ""): r for r in result.get("results", [])}
            for kn in pred_knumbers:
                r = found.get(kn)
                if r:
                    print(f"PREDICATE_VALID:{kn} = {r.get('device_name', 'N/A')} ({r.get('applicant', 'N/A')})")
                else:
                    print(f"PREDICATE_NOT_FOUND:{kn}")
    except Exception as e:
        for kn in pred_knumbers:
            print(f"API_ERROR:{kn}:{e}")
PYEOF
```

## Step 5: Report Results

Present the import results using the standard FDA Professional CLI format (see `references/output-formatting.md`):

```
  FDA eSTAR Import Report
  {product_code} — {device_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: {date} | Project: {name} | v5.22.0

IMPORT SUMMARY
────────────────────────────────────────

  Source: {file_path}
  Format: {PDF (XFA) / XML}
  Template: {nIVD v6 / IVD v6 / PreSTAR v2}

  | Category             | Fields | Status |
  |----------------------|--------|--------|
  | Applicant Info       | {N}/5  | {✓/⚠}  |
  | Classification       | {N}/5  | {✓/⚠}  |
  | Indications for Use  | {N}/2  | {✓/⚠}  |
  | Predicates           | {N}    | {✓/⚠}  |
  | Section Narratives   | {N}    | {✓/⚠}  |
  | Total Fields         | {N}    | —      |

EXTRACTED PREDICATES
────────────────────────────────────────

  | # | K-Number | Source    | Validated |
  |---|----------|----------|-----------|
  | 1 | {kn}     | {source} | {✓/✗/○}   |

NEXT STEPS
────────────────────────────────────────

  1. Review import_data.json for accuracy
  2. Run `/fda:review --project NAME` to score extracted predicates
  3. Run `/fda:draft --project NAME` to generate section drafts
  4. Run `/fda:assemble --project NAME` to build eSTAR package

────────────────────────────────────────
  This report is AI-generated from public FDA data.
  Verify independently. Not regulatory advice.
────────────────────────────────────────
```

## Template Selection Guide

If the user hasn't specified `--template`, auto-detect from the file. If auto-detection fails, use this decision matrix:

| Template | Use When |
|----------|----------|
| **nIVD v6** | Non-IVD devices (most medical devices) — 510(k), De Novo, or PMA |
| **IVD v6** | In Vitro Diagnostic devices — 510(k), De Novo, or PMA |
| **PreSTAR v2** | Pre-Submission meetings (Q-Sub), IDE, or 513(g) requests |

See `references/estar-structure.md` → "Template Selection Matrix" for full details including OMB control numbers.

**QMSR alignment note:** eSTAR templates downloaded after February 2, 2026 align with the new Quality Management System Regulation (QMSR). If importing from an older template, QMS-related fields may differ from the current template structure. Report any field mapping mismatches in the import summary.

## Also Supports Plain XML Input

If the user has already exported XML from an eSTAR form (via Adobe Acrobat > Form > Export Data), the same command works:

```
/fda:import exported_data.xml --project my-device
```

The `estar_xml.py` script auto-detects the file type from the extension.

## Error Handling

- **File not found**: "ERROR: File not found: {path}"
- **Not an XFA PDF**: "This PDF does not contain XFA form data. It may be a regular PDF (not an eSTAR template). If you have the eSTAR XML export, provide the .xml file directly."
- **Missing dependencies**: Install instructions with `pip install pikepdf beautifulsoup4 lxml`
- **No project name**: "ERROR: --project NAME is required. Usage: /fda:import file.pdf --project my-device"
- **Empty extraction**: "WARNING: No form data found. The eSTAR may be a blank template. Fill it in Adobe Acrobat first, then re-export."
