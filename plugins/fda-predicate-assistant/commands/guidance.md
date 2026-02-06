---
description: Look up FDA guidance documents for a device type — extract requirements, map to testing needs, and compare against predicate precedent
allowed-tools: Bash, Read, Glob, Grep, Write, WebFetch, WebSearch
argument-hint: "<product-code> [--regulation NUMBER] [--save] [--offline] [--infer]"
---

# FDA Guidance Document Lookup

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

You are looking up FDA guidance documents applicable to a device type, extracting requirements, and mapping them to testing needs.

**KEY PRINCIPLE: Provide actionable guidance mappings, not just links.** Extract specific requirements and map them to tests the user needs to plan. Use the centralized tables in `references/guidance-lookup.md` for cross-cutting guidance logic and standards mapping.

## Parse Arguments

From `$ARGUMENTS`, extract:

- **Product code** (required) — 3-letter FDA product code (e.g., KGN, DXY, QAS)
- `--regulation NUMBER` — Override regulation number lookup (e.g., `878.4018`)
- `--device-description TEXT` — User's device description (triggers additional cross-cutting guidance)
- `--project NAME` — Associate with a project folder for caching
- `--save` — Cache guidance data locally for offline reuse
- `--offline` — Use only cached guidance data (no web searches)
- `--depth quick|standard|deep` — Level of analysis (default: standard)
- `--infer` — Auto-detect product code from project data instead of requiring explicit input

If no product code provided:
- If `--infer` AND `--project NAME` specified:
  1. Check `$PROJECTS_DIR/$PROJECT_NAME/query.json` for `product_codes` field → use first code
  2. Check `$PROJECTS_DIR/$PROJECT_NAME/output.csv` → find most-common product code in data
  3. Check `~/fda-510k-data/guidance_cache/` for directory names matching product codes
  4. If inference succeeds: log "Inferred product code: {CODE} from {source}"
  5. If inference fails: **ERROR** (not prompt): "Could not infer product code. Provide --product-code CODE or run /fda:extract first."
- If `--infer` without `--project`: check if exactly 1 project exists in projects_dir and use it
- If no `--infer` and no product code: ask the user for it. If they're unsure, help them find it using foiaclass.txt or the openFDA classification API.

## Step 1: Get Device Classification

### If `--offline` mode

Check for cached classification data:

```bash
python3 << 'PYEOF'
import json, os, re

# Determine project dir
settings_path = os.path.expanduser('~/.claude/fda-predicate-assistant.local.md')
projects_dir = os.path.expanduser('~/fda-510k-data/projects')
if os.path.exists(settings_path):
    with open(settings_path) as f:
        m = re.search(r'projects_dir:\s*(.+)', f.read())
        if m:
            projects_dir = os.path.expanduser(m.group(1).strip())

# Check for cached guidance_index.json
product_code = "PRODUCTCODE"  # Replace
project_name = "PROJECT_NAME"  # Replace or empty

# Try project-specific cache first
if project_name:
    index_path = os.path.join(projects_dir, project_name, 'guidance_cache', 'guidance_index.json')
    if os.path.exists(index_path):
        with open(index_path) as f:
            index = json.load(f)
        print(f"CACHED:true")
        print(f"DEVICE_NAME:{index.get('device_name', 'N/A')}")
        print(f"DEVICE_CLASS:{index.get('device_class', 'N/A')}")
        print(f"REGULATION:{index.get('regulation_number', 'N/A')}")
        print(f"CACHED_AT:{index.get('cached_at', 'N/A')}")
        exit(0)

# Check all projects for this product code
import glob
for idx_path in glob.glob(os.path.join(projects_dir, '*/guidance_cache/guidance_index.json')):
    with open(idx_path) as f:
        idx = json.load(f)
    if idx.get('product_code') == product_code:
        print(f"CACHED:true")
        print(f"CACHE_PATH:{idx_path}")
        print(f"DEVICE_NAME:{idx.get('device_name', 'N/A')}")
        print(f"DEVICE_CLASS:{idx.get('device_class', 'N/A')}")
        print(f"REGULATION:{idx.get('regulation_number', 'N/A')}")
        exit(0)

print("CACHED:false")
PYEOF
```

If `--offline` and no cache found, **fall back to skill reference data**:

1. Read the `references/guidance-lookup.md` skill reference file (via `$FDA_PLUGIN_ROOT/skills/fda-510k-knowledge/references/guidance-lookup.md`)
2. Match the product code family/panel to generic cross-cutting guidance recommendations from the reference tables
3. Generate a "Reference-Based Guidance Summary" with the following banner at the top:

```
⚠ REFERENCE-BASED GUIDANCE — Generated from bundled reference data, NOT from current FDA guidance documents.
Verify all recommendations against current FDA guidance at fda.gov before use in any submission.
Last reference update: [date from reference file header or "unknown"]
```

4. Include all applicable cross-cutting guidance from the reference tables (biocompatibility, sterilization, etc.) based on device class and known characteristics
5. Mark all entries as `[Reference-based]` instead of having specific guidance document URLs

This ensures `--offline` mode always produces useful output, even without a prior `--save` cache. Only fail with an error if the reference file itself is missing (plugin installation issue).

### Online: Query openFDA Classification API

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

product_code = "PRODUCTCODE"  # Replace

if api_enabled:
    params = {"search": f'product_code:"{product_code}"', "limit": "1"}
    if api_key:
        params["api_key"] = api_key
    url = f"https://api.fda.gov/device/classification.json?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/1.0)"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            if data.get("results"):
                r = data["results"][0]
                print(f"DEVICE_NAME:{r.get('device_name', 'N/A')}")
                print(f"DEVICE_CLASS:{r.get('device_class', 'N/A')}")
                print(f"REGULATION:{r.get('regulation_number', 'N/A')}")
                print(f"PANEL:{r.get('medical_specialty_description', r.get('review_panel', 'N/A'))}")
                print(f"DEFINITION:{r.get('definition', 'N/A')}")
                print(f"GMP_EXEMPT:{r.get('gmp_exempt_flag', 'N/A')}")
            else:
                print("NOT_FOUND:true")
    except Exception as e:
        print(f"API_ERROR:{e}")
else:
    # Fallback to foiaclass.txt
    print("API_FALLBACK:use_flatfiles")
PYEOF
```

If `--regulation NUMBER` is provided, use that instead of the API result.

Store the classification data — you'll need `device_name`, `device_class`, `regulation_number`, and `review_panel` for subsequent steps.

## Step 2: Search for Device-Specific Guidance

**Skip for `--offline` mode (use cache) or `--depth quick`.**

### 2A: Structured FDA Guidance Database Search

First, try the FDA's searchable guidance database using structured URL patterns:

```
WebFetch: url="https://www.fda.gov/medical-devices/device-advice-comprehensive-regulatory-assistance/guidance-documents-medical-devices-and-radiation-emitting-products" prompt="Find guidance documents related to regulation number {regulation_number} or device type {device_name}. List each guidance title, status (final/draft), and date."
```

If the regulation number is known, also search:
```
WebFetch: url="https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfCFR/CFRSearch.cfm?fr={regulation_number}" prompt="Extract the device classification name, class, and any referenced special controls or guidance documents from this CFR section."
```

### 2B: WebSearch Fallback

If structured search returns no results or is insufficient, fall back to WebSearch:

**Query 1** (always): Regulation-specific guidance
```
WebSearch: "{regulation_number}" guidance site:fda.gov/medical-devices
```

**Query 2** (always): Special controls guidance (for Class II)
```
WebSearch: "{device_name}" "special controls" OR "class II" guidance site:fda.gov
```

**Query 3** (standard/deep): Testing guidance
```
WebSearch: "{device_name}" "510(k)" guidance testing requirements site:fda.gov
```

**Query 4** (deep only): Recent draft guidance
```
WebSearch: "{device_name}" "draft guidance" site:fda.gov 2024 OR 2025 OR 2026
```

### Process search results

For each guidance document found:
1. Record the title, URL, status (final/draft), and publication year
2. Categorize: device-specific, special controls, or general
3. Note if it supersedes or replaces another guidance

## Step 3: Identify Cross-Cutting Guidance

Apply the trigger rules from `references/guidance-lookup.md`. Use the classification data from Step 1 and the user's `--device-description` (if provided) to determine which cross-cutting guidances apply.

```python
# Pseudo-logic for cross-cutting guidance determination
triggers = []

# Always applicable
triggers.append(("Biocompatibility", "Use of ISO 10993-1", "all_devices"))
triggers.append(("510(k) SE Determination", "The 510(k) Program: Evaluating Substantial Equivalence", "all_510k"))

# Class II
if device_class == "2":
    triggers.append(("Special Controls", f"Special controls for {regulation_number}", "class_ii"))

# Check device description keywords
desc = (device_description or "").lower()

if any(kw in desc for kw in ["sterile", "steriliz", "aseptic"]):
    triggers.append(("Sterilization", "Submission and Review of Sterility Information", "sterile_device"))
    triggers.append(("Shelf Life", "Shelf Life of Medical Devices", "sterile_device"))

if any(kw in desc for kw in ["software", "algorithm", "app", "firmware", "samd", "digital"]):
    triggers.append(("Software", "Content of Premarket Submissions for Device Software Functions", "software_device"))

if any(kw in desc for kw in ["wireless", "bluetooth", "wifi", "connected", "iot", "rf"]):
    triggers.append(("Cybersecurity", "Cybersecurity in Medical Devices", "wireless_device"))
    triggers.append(("EMC/Wireless", "Radio Frequency Wireless Technology in Medical Devices", "wireless_device"))

if any(kw in desc for kw in ["reusable", "reprocess"]):
    triggers.append(("Reprocessing", "Reprocessing Medical Devices in Health Care Settings", "reusable_device"))

if any(kw in desc for kw in ["implant", "implantable"]):
    triggers.append(("MRI Safety", "Assessment of MRI Effects", "implantable_device"))

if any(kw in desc for kw in ["ai", "machine learning", "deep learning", "neural network"]):
    triggers.append(("AI/ML", "AI and ML in Software as a Medical Device", "ai_ml_device"))

if any(kw in desc for kw in ["combination", "drug-device", "drug"]):
    triggers.append(("Combination Product", "Classification of Products as Drugs and Devices", "combination"))
```

Only include cross-cutting guidance where the trigger condition is met. Do NOT list every possible cross-cutting guidance for every device.

## Step 4: Extract Requirements (Standard/Deep Depth)

### For `--depth standard`

For the most relevant device-specific guidance found in Step 2, summarize the key requirements based on the search result content and your regulatory knowledge:

- Testing categories required
- Specific standards referenced
- Special submission requirements
- Any clinical data expectations

### For `--depth deep`

Use WebFetch to retrieve the actual guidance document page and extract detailed requirements:

```
WebFetch: url="{guidance_url}" prompt="Extract all specific testing requirements, performance criteria, recommended standards (ISO, ASTM, IEC), and submission content expectations from this FDA guidance document. Organize by testing category."
```

For each extracted requirement, map to a testing category using the mapping table in `references/guidance-lookup.md`.

## Step 5: Map to Standards and Testing Needs

### Build Requirements Matrix

Combine device-specific guidance requirements, cross-cutting guidance requirements, and recognized consensus standards into a structured matrix:

```
REQUIREMENTS MATRIX
────────────────────────────────────────

| Category | Requirement | Source | Standard | Priority |
|----------|-------------|--------|----------|----------|
| Biocompatibility | ISO 10993 evaluation | Cross-cutting | ISO 10993-1, -5, -10 | Required |
| Sterilization | EO validation | Cross-cutting | ISO 11135 | Required |
| Performance | Fluid handling | Device-specific guidance | EN 13726 | Required |
| Performance | MVTR testing | Device-specific guidance | ASTM E96 | Required |
| Antimicrobial | Zone of inhibition | Device-specific guidance | AATCC 100 | If claimed |
| Shelf Life | Accelerated aging | Cross-cutting | ASTM F1980 | Required |
| Software | V&V documentation | Cross-cutting (if applicable) | IEC 62304 | If applicable |
```

### Standards List

List all applicable recognized consensus standards with their purpose:

```
APPLICABLE STANDARDS
────────────────────────────────────────

Required:
  • ISO 10993-1 — Biological evaluation framework
  • ISO 10993-5 — Cytotoxicity testing
  • ISO 10993-10 — Sensitization
  • ISO 10993-23 — Irritation
  • ISO 11135 — EO sterilization validation
  • ASTM F1980 — Accelerated aging
  • ISO 14971 — Risk management

Recommended (based on predicate precedent):
  • EN 13726 — Wound dressing test methods
  • ASTM D1777 — Thickness measurement
  • AATCC 100 — Antimicrobial assessment

If Applicable:
  • IEC 62304 — Software lifecycle (if device contains software)
  • IEC 60601-1 — Electrical safety (if powered)
```

## Step 6: Output

### Report format

Use the standard FDA Professional CLI format (see `references/output-formatting.md`):

```
  FDA Guidance Analysis
  {PRODUCT_CODE} — {DEVICE_NAME}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: {date} | Class: {class} | 21 CFR {regulation} | v4.6.0

DEVICE CLASSIFICATION
────────────────────────────────────────

  Product Code: {CODE}
  Device Name: {name}
  Class: {class}
  Regulation: 21 CFR {regulation_number}
  Panel: {review_panel}

DEVICE-SPECIFIC GUIDANCE
────────────────────────────────────────

  [If found]:
  ✓ "{Guidance Title}" ({Year}, {Status})
    {URL}
    Key Requirements:
    - {requirement 1}
    - {requirement 2}
    - {requirement 3}

  [If not found]:
  ✗ No device-specific guidance found for regulation {regulation_number}
    → Submission should rely on predicate precedent and general guidance

CROSS-CUTTING GUIDANCE
────────────────────────────────────────

  - Biocompatibility: "Use of ISO 10993-1" (2023, Final)
    → ISO 10993-5, -10 required; -11 if prolonged contact
  - Sterilization: "Sterility Information in 510(k) Submissions" (2016, Final)
    → Validate per ISO 11135 (EO) or ISO 11137 (radiation)

REQUIREMENTS MATRIX
────────────────────────────────────────

  [Structured pipe table from Step 5]

APPLICABLE STANDARDS
────────────────────────────────────────

  [Standards list from Step 5]

NOTES
────────────────────────────────────────

  - {Any special considerations for this device type}
  - {Any recent draft guidance that may affect requirements}

NEXT STEPS
────────────────────────────────────────

  1. Plan testing to requirements — `/fda:test-plan {CODE}`
  2. Research predicate testing precedent — `/fda:research {CODE}`
  3. Build traceability matrix — `/fda:traceability --project NAME`

────────────────────────────────────────
  This report is AI-generated from public FDA data.
  Verify independently. Not regulatory advice.
────────────────────────────────────────
```

## Step 7: Save to Cache (if `--save`)

If `--save` is specified, write guidance data to the project's guidance cache:

```bash
python3 << 'PYEOF'
import json, os, re
from datetime import datetime

# Determine cache directory
settings_path = os.path.expanduser('~/.claude/fda-predicate-assistant.local.md')
projects_dir = os.path.expanduser('~/fda-510k-data/projects')
if os.path.exists(settings_path):
    with open(settings_path) as f:
        m = re.search(r'projects_dir:\s*(.+)', f.read())
        if m:
            projects_dir = os.path.expanduser(m.group(1).strip())

project_name = "PROJECT_NAME"  # Replace
product_code = "PRODUCTCODE"    # Replace

cache_dir = os.path.join(projects_dir, project_name, 'guidance_cache', product_code)
os.makedirs(os.path.join(cache_dir, 'device_specific'), exist_ok=True)
os.makedirs(os.path.join(cache_dir, 'cross_cutting'), exist_ok=True)

print(f"Cache directory created: {cache_dir}")
PYEOF
```

Write `guidance_index.json` with the structure defined in `references/guidance-lookup.md`.

Write individual guidance content files (`.md`) for each guidance document that was fetched.

Write `requirements_matrix.json` with the structured requirements data.

Write `standards_list.json` with the applicable standards.

Report to the user:
```
Guidance data cached to: ~/fda-510k-data/projects/{PROJECT_NAME}/guidance_cache/
Use --offline to access cached data without web searches.
```

If no `--project` was specified, ask the user if they want to save to a specific project or to a global cache at `~/fda-510k-data/guidance_cache/{PRODUCT_CODE}/`.

## Error Handling

- **Product code not found**: "Product code '{CODE}' not found in FDA classification database. Check the code and try again, or use `--regulation NUMBER` to specify the regulation directly."
- **No guidance found**: "No device-specific guidance found for this product code. Cross-cutting guidance still applies — see the requirements matrix above."
- **WebSearch/WebFetch fails**: Fall back to known guidance from `references/guidance-lookup.md` cross-cutting table. Note: "Web search unavailable — guidance analysis based on device characteristics and known cross-cutting requirements."
- **API unavailable**: Use flat files for classification. Note which data was API-derived vs. flat-file-derived.
