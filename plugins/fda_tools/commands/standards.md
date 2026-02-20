
<!-- NOTE: This command has been migrated to use centralized FDAClient (FDA-114)
     Old pattern: urllib.request.Request + urllib.request.urlopen
     New pattern: FDAClient with caching, retry, and rate limiting
     Migration date: 2026-02-20
-->

---
description: Look up FDA Recognized Consensus Standards — search by product code, standard number, or keyword for applicable testing standards
allowed-tools: Bash, Read, Glob, Grep, WebSearch, WebFetch, Write
argument-hint: "--product-code CODE [--standard NUMBER] [--search QUERY] [--check-currency] [--save] [--project NAME]"
---

# FDA Recognized Consensus Standards Lookup

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
        if k.startswith('fda-tools@'):
            for e in v:
                p = e.get('installPath', '')
                if os.path.isdir(p):
                    print(p); exit()
print('')
")
echo "FDA_PLUGIN_ROOT=$FDA_PLUGIN_ROOT"
```

---

You are looking up FDA Recognized Consensus Standards from the FDA's database and the plugin's built-in standards tracking reference.

## Parse Arguments

From `$ARGUMENTS`, extract:

- `--product-code CODE` — Look up standards commonly associated with a device product code
- `--standard NUMBER` — Look up a specific standard by number (e.g., "ISO 10993-1", "IEC 60601-1", "ASTM F1980")
- `--search QUERY` — Free-text search for standards (e.g., "biocompatibility", "sterilization", "cybersecurity")
- `--check-currency` — Compare cited standards against current editions; flag superseded versions
- `--save` — Save results to project folder
- `--project NAME` — Target project for --save
- `--infer` — Auto-detect product code from project data
- `--index` — Scan `standards_dir` and build `standards_index.json` inventory
- `--compare` — Cross-reference local standards inventory against device requirements (requires `--product-code`)

At least one of `--product-code`, `--standard`, or `--search` is required (unless `--check-currency` with `--project`, or `--index`).

## Step 1: Load Built-In Standards Reference

Read the plugin's standards tracking reference for curated standard data:

```bash
cat "$FDA_PLUGIN_ROOT/skills/fda-510k-knowledge/references/standards-tracking.md" 2>/dev/null
```

This gives you the curated list of key standards by category with titles, applicability, and supersession information.

## Step 2: Query FDA RCSD (Recognized Consensus Standards Database)

The FDA RCSD is available at: `https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfStandards/search.cfm`

### 2A: Search by Standard Number

If `--standard NUMBER` is provided:

```
WebSearch: "{standard_number}" site:accessdata.fda.gov/scripts/cdrh/cfdocs/cfStandards
```

Also search for the standard's current edition:

```
WebSearch: "{standard_number}" current edition {YYYY} medical device
```

### 2B: Search by Product Code

If `--product-code CODE` is provided:

1. First, determine the device class, regulation number, and device type from classification:

```bash
python3 << 'PYEOF'
import urllib.request, urllib.parse, json, os, re

settings_path = os.path.expanduser('~/.claude/fda-tools.local.md')
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

product_code = "CODE"  # Replace
if api_enabled:
    params = {"search": f'product_code:"{product_code}"', "limit": "100"}
    if api_key:
        params["api_key"] = api_key
    url = f"https://api.fda.gov/device/classification.json?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/4.7.0)"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            total = data.get("meta", {}).get("results", {}).get("total", 0)
            print(f"CLASSIFICATION_MATCHES:{total}")
            if data.get("results"):
                r = data["results"][0]
                print(f"DEVICE_NAME:{r.get('device_name', 'N/A')}")
                print(f"DEVICE_CLASS:{r.get('device_class', 'N/A')}")
                print(f"REGULATION:{r.get('regulation_number', 'N/A')}")
                print(f"IMPLANT:{r.get('implant_flag', 'N')}")
                print(f"LIFE_SUSTAIN:{r.get('life_sustain_support_flag', 'N')}")
    except Exception as e:
        print(f"API_ERROR:{e}")
PYEOF
```

2. Based on device characteristics, determine applicable standard categories:

| Device Characteristic | Applicable Standards |
|----------------------|---------------------|
| All devices | ISO 14971 (risk management), ISO 13485 (QMS) |
| Patient-contacting | ISO 10993 series (biocompatibility) |
| Sterile device | ISO 11135 (EO), ISO 11137 (radiation), ISO 17665 (steam) |
| Powered/electrical | IEC 60601-1 family |
| Contains software | IEC 62304, IEC 82304-1 |
| Connected/wireless | IEC 62443, AAMI TIR57, IEC 81001-5-1 |
| Has user interface | IEC 62366-1 |
| Implantable | ISO 10993-6 (implantation), specific ASTM/ISO per device type |
| Has shelf life | ASTM F1980 (accelerated aging), ISO 11607 (packaging) |
| IVD device | ISO 15189, ISO 18113, device-specific performance standards |

3. Search the FDA RCSD for standards associated with this regulation number:

```
WebSearch: "{regulation_number}" "recognized consensus standards" site:fda.gov
```

### 2C: Free-Text Search

If `--search QUERY` is provided:

```
WebSearch: "{query}" "consensus standard" medical device site:fda.gov
```

Also search the built-in reference for matching standards.

## Step 3: Standards Currency Check (--check-currency)

If `--check-currency` is specified:

1. Load the project's cited standards from:
   - `$PROJECTS_DIR/$PROJECT_NAME/test_plan.md` (standards cited in testing plan)
   - `$PROJECTS_DIR/$PROJECT_NAME/guidance_cache/` (standards from guidance analysis)
   - The built-in `standards-tracking.md` reference (known supersessions)

2. For each cited standard, check if a newer edition exists:

```bash
python3 << 'PYEOF'
import re

# Known supersessions from standards-tracking.md
supersessions = {
    "ISO 10993-1:2018": {"new": "ISO 10993-1:2025", "transition": "2027-11-18"},
    "ISO 11137-1:2006": {"new": "ISO 11137-1:2025", "transition": "2027-06-01"},
    "ISO 17665-1:2006": {"new": "ISO 17665:2024", "transition": "2026-12-01"},
}

# Parse cited standards from project files
cited_standards = []  # Populate from project data

for std in cited_standards:
    if std in supersessions:
        info = supersessions[std]
        print(f"SUPERSEDED:{std}|{info['new']}|{info['transition']}")
    else:
        print(f"CURRENT:{std}")
PYEOF
```

3. For standards not in the built-in supersession list, search for updates:

```
WebSearch: "{standard_number}" new edition {YYYY} superseded
```

## Step 4: Local Standards Inventory (--index)

If `--index` is specified:

1. Read `standards_dir` from `~/.claude/fda-tools.local.md`
2. If not set, report error: "No standards_dir configured. Run `/fda:configure --set standards_dir /path/to/Standards/`"
3. Scan the directory recursively for PDF files
4. Parse filenames for standard identifiers using these patterns:
   - ISO: `ISO[\s_-]?\d{4,5}(-\d+)?`
   - IEC: `IEC[\s_-]?\d{4,5}(-\d+)?`
   - ASTM: `ASTM[\s_-]?[A-Z]\d{1,5}`
   - AAMI: `AAMI[\s_-]?[A-Z]+\d*`
   - ANSI: `ANSI[\s_-]?[A-Z]+[\s_-]?\d+`
5. For each matched PDF, also read the first page to confirm the standard number and extract the year/edition
6. Build `standards_index.json` in the configured `standards_dir`:

```json
{
  "generated": "2026-02-09T...",
  "standards_dir": "/path/to/Standards",
  "standards": [
    {
      "standard_id": "ISO 10993-1",
      "edition_year": "2018",
      "full_title": "ISO 10993-1:2018 — Biological evaluation of medical devices — Part 1",
      "file_path": "Biocompatability/ISO 10993-1 2018.pdf",
      "file_size_kb": 1234,
      "category": "biocompatibility"
    }
  ],
  "summary": {
    "total_files": 22,
    "categories": {"biocompatibility": 22, "sterilization": 0}
  }
}
```

7. Cross-reference against `references/standards-tracking.md` to flag superseded editions
8. Output in the standard FDA Professional CLI format:

```
LOCAL STANDARDS INVENTORY
────────────────────────────────────────

  Scanned: {path}
  Standards found: {N} across {N} categories

  | Standard | Edition | Status | File |
  |----------|---------|--------|------|
  | ISO 10993-1 | 2018 | ⚠ SUPERSEDED (2025 available) | Biocompatability/ISO 10993-1 2018.pdf |
  | ISO 10993-5 | 2009 | ✓ Current | Biocompatability/ISO 10993-5 2009.pdf |
  ...

  Superseded editions: {N}
  Missing for device type: {list}

  Saved: {path}/standards_index.json
```

## Step 5: Local Standards Comparison (--compare)

If `--compare` is specified (requires `--product-code` and `standards_index.json` to exist):

1. Load `standards_index.json` from `standards_dir`
2. Determine required standards for the product code (from Step 2B lookup table)
3. Cross-reference: which required standards have local copies? Which are missing?
4. Output a Standards Evidence Matrix:

```
STANDARDS EVIDENCE MATRIX
────────────────────────────────────────

  Product Code: {CODE} — {device_name}

  | Required Standard | Local Copy? | Edition | Current? |
  |-------------------|-------------|---------|----------|
  | ISO 10993-1 | ✓ Available | 2018 | ⚠ Superseded |
  | ISO 10993-5 | ✓ Available | 2009 | ✓ Current |
  | IEC 60601-1 | ✗ Not found | — | — |
  ...

  Coverage: {N}/{total} required standards available locally ({pct}%)
  Action items: {N} standards need acquisition
```

## Output Format

Present results using the standard FDA Professional CLI format:

```
  FDA Recognized Consensus Standards
  {context — product code or search query}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: {date} | Source: FDA RCSD + Plugin Reference | v5.22.0

APPLICABLE STANDARDS
────────────────────────────────────────

  Quality Management:
    ISO 13485:2016    Medical devices — QMS
    ISO 14971:2019    Application of risk management

  Biocompatibility:
    ISO 10993-1:2025  Biological evaluation framework [CURRENT]
    ISO 10993-5:2009  In vitro cytotoxicity
    ISO 10993-10:2021 Sensitization testing

  Sterilization:
    ISO 11135:2014    EO sterilization validation
    ISO 11137-1:2025  Radiation sterilization [CURRENT]

  Performance Testing:
    {Device-specific ASTM/ISO standards}

  Software (if applicable):
    IEC 62304:2006+A1:2015  Software lifecycle

  Electrical Safety (if applicable):
    IEC 60601-1:2005+A2:2020  Basic safety

FDA RECOGNITION STATUS
────────────────────────────────────────

  Standard              Status        Recognition Date
  ISO 10993-1:2025      Recognized    2025-11-18
  ISO 14971:2019        Recognized    2020-03-15
  IEC 62304:2006+A1     Recognized    2016-09-14

{If --check-currency:}
STANDARDS CURRENCY CHECK
────────────────────────────────────────

  ✓ ISO 14971:2019         Current edition
  ⚠ ISO 10993-1:2018       Superseded by ISO 10993-1:2025
    → Transition deadline: 2027-11-18
    → Action: Update biocompatibility testing to cite 2025 edition
  ✓ IEC 62304:2006+A1      Current edition

RECOMMENDATIONS
────────────────────────────────────────

  1. {Specific standard recommendations for this device type}
  2. For detailed testing plan: `/fda:test-plan {CODE}`
  3. For guidance document requirements: `/fda:guidance {CODE}`

────────────────────────────────────────
  This report is AI-generated from public FDA data.
  Verify independently. Not regulatory advice.
────────────────────────────────────────
```

### Sources Checked

Append a sources table to every output showing which external APIs were queried and their status. See [CONNECTORS.md](../CONNECTORS.md) for the standard format. Only include rows for sources this command actually uses.

## Save Results (--save)

If `--save` is specified:

```bash
PROJECTS_DIR="~/fda-510k-data/projects"
cat ~/.claude/fda-tools.local.md 2>/dev/null
# Write standards data to project
cat << 'EOF' > "$PROJECTS_DIR/$PROJECT_NAME/standards_lookup.json"
{json data}
EOF
```

## Error Handling

- **No arguments**: Show usage with examples
- **API unavailable**: Use built-in standards-tracking.md reference only (note reduced coverage)
- **Standard not found**: Suggest alternative search terms or broader queries
- **No project for --check-currency**: ERROR — "Standards currency check requires --project NAME with existing test plan or guidance data"
