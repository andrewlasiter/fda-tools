---
description: Research and plan a 510(k) submission — predicate selection, testing strategy, IFU landscape, regulatory intelligence, and competitive analysis
allowed-tools: Read, Glob, Grep, Bash, Write, WebFetch, WebSearch
argument-hint: "<product-code> [--project NAME] [--device-description TEXT] [--intended-use TEXT] [--infer] [--competitor-deep] [--include-pma] [--browse] [--analytics] [--aiml]"
---

# FDA 510(k) Submission Research

You are helping the user research and plan a 510(k) submission. Given a product code (and optionally a device description and intended use), produce a comprehensive research package drawing from ALL available pipeline data.

**KEY PRINCIPLE: Do the work, don't ask the user to run other commands.** If PDF text is available, extract predicates from it yourself. If a data file exists but has no relevant records, don't mention it. The user should get a complete answer, not a todo list.

## Parse Arguments

From `$ARGUMENTS`, extract:

- **Product code** (required) — 3-letter FDA product code (e.g., KGN, DXY, QAS)
- `--device-description TEXT` — Brief description of the user's device
- `--intended-use TEXT` — The user's intended indications for use
- `--years RANGE` — Focus on specific year range (default: last 10 years)
- `--depth quick|standard|deep` — Level of analysis (default: standard)
- `--project NAME` — Use data from a specific project folder
- `--infer` — Auto-detect product code from project data instead of requiring explicit input
- `--competitor-deep` — Extended competitive analysis: applicant frequency, technology trends, market timeline, IFU evolution
- `--identify-code` — Auto-identify product code from `--device-description` text (no product code required). Searches openFDA classification + foiaclass.txt, returns top 5 candidates ranked by relevance.

If `--identify-code` is set:
1. Require `--device-description` (error if missing)
2. Extract keywords from the device description
3. Query openFDA classification API: `device_name:{keywords}`
4. Also grep foiaclass.txt for matching terms
5. Rank results by keyword overlap score
6. Present top 5 candidates:
   ```
   Product Code Identification Results:
   Rank  Code  Device Name                     Class  Regulation    Score
   1     OVE   Intervertebral Fusion Device    II     888.3080      95%
   2     OVF   Cervical Disc Prosthesis        III    888.3082      72%
   3     ORC   Spinal Plate                    II     888.3070      65%
   4     MAX   Bone Void Filler                II     888.3045      40%
   5     OOQ   Spinal Spacer                   II     888.3075      38%
   ```
7. If `--full-auto`: auto-select rank 1 and continue with that product code
8. Otherwise: present candidates and let user confirm

If no product code provided and no `--identify-code`:
- If `--infer` AND `--project NAME` specified:
  1. Check `$PROJECTS_DIR/$PROJECT_NAME/query.json` for `product_codes` field → use first code
  2. Check `$PROJECTS_DIR/$PROJECT_NAME/output.csv` → find most-common product code in data
  3. Check `~/fda-510k-data/guidance_cache/` for directory names matching product codes
  4. If inference succeeds: log "Inferred product code: {CODE} from {source}"
  5. If inference fails: **ERROR** (not prompt): "Could not infer product code. Provide --product-code CODE or run /fda:extract first."
- If `--infer` without `--project`: check if exactly 1 project exists in projects_dir and use it
- If no `--infer` and no product code: ask the user for it. If they're unsure of their product code, help them find it:
```bash
grep -i "DEVICE_KEYWORD" ~/fda-510k-data/extraction/foiaclass.txt ~/fda-510k-data/batchfetch/fda_data/foiaclass.txt 2>/dev/null | head -20
```

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

## Check Available Data

Before making API calls, check what data already exists for this project:

```bash
python3 $FDA_PLUGIN_ROOT/scripts/fda_data_store.py --project "$PROJECT_NAME" --show-manifest 2>/dev/null
```

If the manifest shows cached data that matches your needs (same product code, not expired), **use the cached summaries** instead of re-querying. This prevents redundant API calls and ensures consistency across commands.

## Step 1: Discover Available Data

### If `--project NAME` is provided — Use project data first

```bash
PROJECTS_DIR="~/fda-510k-data/projects"  # or from settings
ls "$PROJECTS_DIR/$PROJECT_NAME/"*.csv "$PROJECTS_DIR/$PROJECT_NAME/"*.json 2>/dev/null
cat "$PROJECTS_DIR/$PROJECT_NAME/query.json" 2>/dev/null
```

### Also check for matching projects automatically

If no `--project` specified, check if a project exists for this product code:
```bash
ls ~/fda-510k-data/projects/*/query.json 2>/dev/null
```

### Check data sources silently — only report what's RELEVANT

Check these locations, but **only mention sources to the user if they contain data for the requested product code**:

```bash
# FDA database files (always relevant — contain ALL product codes)
ls ~/fda-510k-data/extraction/pmn*.txt 2>/dev/null

# PDF text cache (check if it has relevant PDFs)
ls -la ~/fda-510k-data/extraction/pdf_data.json 2>/dev/null

# Download metadata (check if it has relevant product code records)
ls -la ~/fda-510k-data/batchfetch/510k_download.csv 2>/dev/null

# Device classification
ls ~/fda-510k-data/batchfetch/fda_data/foiaclass.txt ~/fda-510k-data/extraction/foiaclass.txt 2>/dev/null
```

**IMPORTANT**: Do NOT report files that exist but contain no data for this query. For example, if `merged_data.csv` has 100 records but none match the requested product code, do not mention it at all. The user doesn't care about files that aren't relevant to their device.

## Step 2: Product Code Profile

### 2A: openFDA API Classification (Primary)

Query the classification endpoint for the richest data via the project data store (caches results for cross-command reuse):

```bash
python3 "$FDA_PLUGIN_ROOT/scripts/fda_data_store.py" \
  --project "$PROJECT_NAME" \
  --query classification \
  --product-code "$PRODUCT_CODE"
```

**Deliberation:** If `CLASSIFICATION_MATCHES` > 1, list all returned records and select the one whose `device_name` and `definition` best match the user's device description. If no device description is available, use the first result but note the ambiguity.

### 2B: Flat-File Fallback

If API is unavailable, fall back to foiaclass.txt:

```bash
grep "^PRODUCTCODE" ~/fda-510k-data/batchfetch/fda_data/foiaclass.txt ~/fda-510k-data/extraction/foiaclass.txt 2>/dev/null
```

And count total clearances from flat files:
```bash
grep -c "|PRODUCTCODE|" ~/fda-510k-data/extraction/pmn96cur.txt ~/fda-510k-data/extraction/pmn9195.txt 2>/dev/null
```

Report:
- **Device name** (official FDA classification name)
- **Device class** (I, II, III)
- **Regulation number** (21 CFR section)
- **Advisory committee** (review panel)
- **Definition** (if available)
- **Total clearances** (all-time)

## Step 3: Regulatory Intelligence

### From FDA database files (pmn*.txt)

Filter all records for this product code:

```bash
grep "|PRODUCTCODE|" ~/fda-510k-data/extraction/pmn96cur.txt 2>/dev/null
```

Analyze and report:
- **Total clearances** all-time and by decade
- **Decision code distribution**: SESE (substantially equivalent), SEKN (SE with conditions), SESK, etc.
- **Submission type breakdown**: Traditional vs Special 510(k) vs Abbreviated
- **Statement vs Summary ratio**: What percentage file summaries (more data available) vs statements
- **Third-party review usage**: How common for this product code
- **Review time statistics**: Average, median, fastest, slowest (compute from DATERECEIVED to DECISIONDATE)
- **Recent trend**: Are submissions increasing or decreasing in the last 5 years?

### From 510k_download.csv (only if it contains this product code)

```bash
grep "PRODUCTCODE" ~/fda-510k-data/batchfetch/510k_download.csv 2>/dev/null
```

Additional metadata available: expedited review, review advisory committee details.

## Step 3.5: Safety Intelligence (API)

**Query MAUDE event counts and recall data** for this product code via the project data store. This provides critical safety context for predicate selection and testing strategy, and caches results for reuse by `/fda:safety` and other commands.

```bash
# MAUDE event counts by type
python3 "$FDA_PLUGIN_ROOT/scripts/fda_data_store.py" \
  --project "$PROJECT_NAME" \
  --query events \
  --product-code "$PRODUCT_CODE" \
  --count event_type.exact

# Recall history
python3 "$FDA_PLUGIN_ROOT/scripts/fda_data_store.py" \
  --project "$PROJECT_NAME" \
  --query recalls \
  --product-code "$PRODUCT_CODE"
```

**Include in the research report as a brief safety summary:**
- Total MAUDE events (by type) and events-per-clearance ratio
- Total recalls (by class) and any active recalls
- If high event rate or Class I recalls: Flag as a pre-submission discussion point
- If death events >0: Flag prominently

**For deeper analysis**: Suggest `/fda:safety --product-code CODE` in the Recommendations section. Do NOT run the full safety analysis inline (it's too detailed for the research report).

## Step 3.75: Applicable FDA Guidance

**Skip this step entirely for `--depth quick`.**

Search for FDA guidance documents applicable to the user's device. Use data already obtained from Step 2 — `regulation_number`, `device_name`, and `device_class` from the openFDA classification API response.

### Check for Cached Guidance First

Before searching the web, check if `/fda:guidance --save` was previously run for this product code:

```bash
python3 << 'PYEOF'
import json, os, re, glob

settings_path = os.path.expanduser('~/.claude/fda-predicate-assistant.local.md')
projects_dir = os.path.expanduser('~/fda-510k-data/projects')
if os.path.exists(settings_path):
    with open(settings_path) as f:
        m = re.search(r'projects_dir:\s*(.+)', f.read())
        if m:
            projects_dir = os.path.expanduser(m.group(1).strip())

product_code = "PRODUCTCODE"  # Replace

# Search all projects for cached guidance for this product code
for idx_path in glob.glob(os.path.join(projects_dir, '*/guidance_cache/guidance_index.json')):
    try:
        with open(idx_path) as f:
            idx = json.load(f)
        if idx.get('product_code') == product_code:
            print(f"GUIDANCE_CACHED:true")
            print(f"CACHE_PATH:{os.path.dirname(idx_path)}")
            print(f"CACHED_AT:{idx.get('cached_at', '?')}")
            # Output cached guidance data
            for g in idx.get('device_specific_guidance', []):
                print(f"DEVICE_GUIDANCE:{g.get('title', '?')}|{g.get('url', '?')}|{g.get('year', '?')}")
            for g in idx.get('cross_cutting_guidance', []):
                print(f"CROSS_CUTTING:{g.get('topic', '?')}|{g.get('title', '?')}")
            for s in idx.get('standards', []):
                print(f"STANDARD:{s.get('standard', '?')}|{s.get('purpose', '?')}|{'required' if s.get('required') else 'recommended'}")
            exit(0)
    except:
        continue

# Also check global guidance cache
global_cache = os.path.expanduser(f'~/fda-510k-data/guidance_cache/{product_code}/guidance_index.json')
if os.path.exists(global_cache):
    with open(global_cache) as f:
        idx = json.load(f)
    print(f"GUIDANCE_CACHED:true")
    print(f"CACHE_PATH:{os.path.dirname(global_cache)}")
    print(f"CACHED_AT:{idx.get('cached_at', '?')}")
    for g in idx.get('device_specific_guidance', []):
        print(f"DEVICE_GUIDANCE:{g.get('title', '?')}|{g.get('url', '?')}|{g.get('year', '?')}")
    for g in idx.get('cross_cutting_guidance', []):
        print(f"CROSS_CUTTING:{g.get('topic', '?')}|{g.get('title', '?')}")
    for s in idx.get('standards', []):
        print(f"STANDARD:{s.get('standard', '?')}|{s.get('purpose', '?')}|{'required' if s.get('required') else 'recommended'}")
    exit(0)

print("GUIDANCE_CACHED:false")
PYEOF
```

**If cached guidance is found**: Use it directly — read the cached guidance files and incorporate into the report. Skip the WebSearch queries below. Note in the output: "Guidance data loaded from cache (cached {date}). Run `/fda:guidance {PRODUCT_CODE} --save` to refresh."

**If no cache found**: Proceed with the live web search below.

### Guidance Document Search

Run WebSearch queries to find applicable guidance:

**Query 1** (always run for standard/deep): Device-specific guidance tied to the CFR regulation
```
WebSearch: "{regulation_number}" guidance site:fda.gov/medical-devices
```

**Query 2** (always run for standard/deep): Special controls guidance (Class II regulatory roadmap)
```
WebSearch: "{device_name}" "special controls" OR "class II" guidance site:fda.gov
```

**Query 3** (deep depth only): Submission-specific testing guidance
```
WebSearch: "{device_name}" "510(k)" guidance testing requirements site:fda.gov
```

Replace `{regulation_number}` with the actual regulation (e.g., `878.4018`) and `{device_name}` with the FDA classification name (e.g., `Dressing, Wound, Drug`).

### Cross-Cutting Guidance Logic (3-Tier System)

Determine which cross-cutting guidances to mention using a **3-tier priority system**: API-authoritative flags → enhanced keyword matching → classification heuristics. Uses classification data from Step 2 and the user's `--device-description`.

**Tier 1 — API Flags** (authoritative, from openFDA classification + AccessGUDID):

| API Field | Trigger | Guidance Topic |
|-----------|---------|---------------|
| Always | All devices | Biocompatibility: "Use of ISO 10993-1" |
| `device_class == "2"` | Class II | Special controls for the specific regulation number |
| `device_class == "3"` | Class III | PMA-level scrutiny, clinical data likely required |
| `implant_flag == "Y"` | Implantable | MRI safety + ISO 10993 extended + fatigue testing |
| `life_sustain_support_flag == "Y"` | Life-sustaining | Enhanced clinical review |
| AccessGUDID `is_sterile == true` | Sterile | Sterilization + shelf life guidance |
| AccessGUDID `sterilization_methods` | Method-specific | ISO 11135 (EO), ISO 11137 (radiation), ISO 17665 (steam) |
| AccessGUDID `is_single_use == true` | Single-use | Reprocessing suppressed (note: third-party reprocessing per 21 CFR 820.3(p) may still apply) |
| AccessGUDID `is_single_use == false` | Reusable | Reprocessing guidance |
| AccessGUDID `mri_safety != null` | MRI-relevant | MRI safety testing (even non-implants) |
| AccessGUDID `is_labeled_as_nrl == true` | Latex | Latex labeling + ISO 10993 extended |
| Review panel in IVD set | IVD | IVD-specific guidance (CLSI standards) |

**Tier 2 — Enhanced Keyword Matching** (word-boundary regex, negation-aware):

```python
import re
def kw_match(desc, keywords):
    for kw in keywords:
        match = re.search(r'\b' + re.escape(kw) + r'\b', desc, re.IGNORECASE)
        if match:
            prefix = desc[max(0, match.start()-20):match.start()].lower()
            if not any(neg in prefix for neg in ['not ', 'non-', 'non ', 'no ', 'without ']):
                return True
    return False
```

Applied to BOTH user `--device-description` AND API `definition` field:

| Category | Keywords | Guidance Topic |
|----------|----------|---------------|
| Sterilization | `sterile`, `sterilized`, `sterilization`, `aseptic`, `gamma irradiated`, `eo sterilized`, `ethylene oxide` | Sterilization + shelf life |
| Software | `software`, `algorithm`, `mobile app`, `software app`, `firmware`, `samd`, `software as a medical device`, `digital health` | Software: IEC 62304 |
| AI/ML | `artificial intelligence`, `ai-enabled`, `ai-based`, `ai/ml`, `machine learning`, `deep learning`, `neural network`, `computer-aided detection`, `cadx`, `cade` | AI/ML guidance |
| Wireless | `wireless`, `bluetooth`, `wifi`, `wi-fi`, `network-connected`, `cloud-connected`, `iot device`, `rf communication`, `radio frequency`, `cellular` | Cybersecurity + EMC |
| USB | `usb data`, `usb communication`, `usb port`, `usb connectivity`, `usb interface`, `usb connection` | Cybersecurity only (not EMC) |
| Combination | `combination product`, `drug-device`, `drug-eluting`, `drug-coated`, `biologic-device`, `antimicrobial agent` | Combination product |
| Implantable | `implant`, `implantable`, `prosthesis`, `prosthetic`, `indwelling`, `endoprosthesis` | MRI + fatigue + extended biocompat |
| Reusable | `reusable`, `reprocessing`, `reprocessed`, `multi-use` | Reprocessing |
| 3D Printing | `3d print`, `3d-printed`, `additive manufactur`, `additively manufactured`, `selective laser`, `electron beam melting` | Additive manufacturing guidance |
| Animal-Derived | `collagen`, `gelatin`, `bovine`, `porcine`, `animal-derived`, `animal tissue`, `xenograft` | BSE/TSE guidance |
| Home Use | `home use`, `over-the-counter`, `otc device`, `patient self-test`, `lay user` | Home use design guidance |
| Pediatric | `pediatric`, `neonatal`, `infant`, `children`, `child`, `neonate` | Pediatric assessment guidance |
| Latex | `latex`, `natural rubber` | Latex labeling + ISO 10993 |
| Electrical | `battery-powered`, `ac mains`, `rechargeable`, `electrically powered`, `lithium battery` | IEC 60601-1 electrical safety |

**Tier 3 — Classification Heuristics** (safety net): Regulation number family mapping (870.* → cardiovascular, 888.* → orthopedic, etc.). If Class II and no specific triggers found, flag for deeper web search.

### For `--depth deep`: Fetch Key Guidance Content

For the single most relevant device-specific guidance found, use WebFetch to retrieve the guidance page and extract:
- Specific testing requirements or performance criteria
- Recommended standards (ISO, ASTM, IEC, etc.)
- Special submission requirements or content expectations
- Any specific clinical data expectations

Store these extracted requirements — they will be cross-referenced against predicate testing data in Step 5.

### Output Format for This Section

```
APPLICABLE FDA GUIDANCE
────────────────────────────────────────

Device-Specific Guidance:
  ✓ "{Guidance Title}" ({Year})
    {URL}
    Key requirements: {summarized requirements from the guidance}

  OR (if none found):

  ✗ No device-specific guidance found for regulation {regulation_number}
    → Submission should rely on predicate precedent and general guidance

Cross-Cutting Guidance (based on device characteristics):
  • Biocompatibility: "Use of ISO 10993-1: Biological evaluation" (2023)
  • Sterilization: "Submission and Review of Sterility Info" (2016)
  • [If software]: "Content of Premarket Submissions for Device Software" (2023)
  • [If cybersecurity]: "Cybersecurity in Medical Devices" (2023)
  • [Other applicable cross-cutting guidance based on triggers above]

Recognized Consensus Standards (commonly cited for this product code):
  • [List specific ISO/ASTM/IEC standards mentioned in guidance or commonly associated]
```

Only list cross-cutting guidance items where the trigger condition is met. Do NOT list all possible cross-cutting guidance for every device.

## Step 4: Predicate Landscape

### Extract predicates directly from PDF text

**Do NOT tell the user to run `/fda:extract stage2`.** Instead, extract predicate device numbers yourself from cached PDF text.

**Cache format detection**: The system may use either per-device cache (new) or a monolithic pdf_data.json (legacy). Check both:

```python
import json, re, os
from collections import Counter

device_pattern = re.compile(r'\b(?:K\d{6}|P\d{6}|DEN\d{6}|N\d{4,5})\b', re.IGNORECASE)

# Section header that identifies where predicates are formally cited
# SYNC: Tier 1 "Predicate / SE" pattern from references/section-patterns.md
# If this regex fails, apply Tier 2 OCR corrections then Tier 3 semantic signals
se_header = re.compile(r'(?i)(substantial\s+equivalence|se\s+comparison|predicate\s+(comparison|device|analysis|identification)|comparison\s+to\s+predicate|technological\s+characteristics|comparison\s+(table|chart|matrix)|similarities\s+and\s+differences|comparison\s+of\s+(the\s+)?(features|technological|device))')

SE_WINDOW = 2000  # chars after SE header to consider as "SE zone"
SE_WEIGHT = 3
GENERAL_WEIGHT = 1

se_cited_by = Counter()       # Device numbers found in SE sections
general_cited_by = Counter()  # Device numbers found in general text
graph = {}

def extract_with_context(text, source_id):
    """Extract device numbers, tagging whether they appear in SE sections."""
    se_devices = set()
    general_devices = set()

    # Find SE section boundaries
    se_zones = []
    for m in se_header.finditer(text):
        start = m.start()
        end = min(m.start() + SE_WINDOW, len(text))
        se_zones.append((start, end))

    # Check each device number match against SE zones
    for m in device_pattern.finditer(text):
        num = m.group().upper()
        if num == source_id:
            continue
        in_se = any(start <= m.start() <= end for start, end in se_zones)
        if in_se:
            se_devices.add(num)
        else:
            general_devices.add(num)

    # A device found in BOTH zones counts as SE (stronger signal wins)
    general_only = general_devices - se_devices
    all_devices = se_devices | general_only

    graph[source_id] = all_devices
    for d in se_devices:
        se_cited_by[d] += 1
    for d in general_only:
        general_cited_by[d] += 1

# Try per-device cache first (scalable)
cache_dir = os.path.expanduser('~/fda-510k-data/extraction/cache')
index_file = os.path.join(cache_dir, 'index.json')

if os.path.exists(index_file):
    with open(index_file) as f:
        index = json.load(f)
    for knumber, meta in index.items():
        device_path = os.path.join(os.path.expanduser('~/fda-510k-data/extraction'), meta['file_path'])
        if os.path.exists(device_path):
            with open(device_path) as f:
                device_data = json.load(f)
            extract_with_context(device_data.get('text', ''), knumber.upper())
else:
    # Legacy: monolithic pdf_data.json
    pdf_json = os.path.expanduser('~/fda-510k-data/extraction/pdf_data.json')
    if os.path.exists(pdf_json):
        with open(pdf_json) as f:
            data = json.load(f)
        for filename, content in data.items():
            text = content.get('text', '') if isinstance(content, dict) else str(content)
            source_id = filename.replace('.pdf', '').upper()
            extract_with_context(text, source_id)

# Compute weighted score for ranking
weighted_score = {}
all_devices = set(se_cited_by.keys()) | set(general_cited_by.keys())
for d in all_devices:
    weighted_score[d] = (se_cited_by[d] * SE_WEIGHT) + (general_cited_by[d] * GENERAL_WEIGHT)

# Sort by weighted score (highest first)
ranked = sorted(weighted_score.items(), key=lambda x: -x[1])
```

This uses **section-aware extraction** to distinguish between device numbers cited in Substantial Equivalence / predicate comparison sections (high confidence) versus those mentioned elsewhere in the document (literature reviews, background, adverse events). Device numbers found in SE sections are weighted 3× higher than those in general text, so actual predicate citations rank above incidental mentions. All device numbers are still captured — section context only affects ranking weight.

### Also check output.csv and merged_data.csv if they exist AND have relevant data

These are supplementary sources. Only use them if they contain records for the requested product code.

### Rank predicate devices by:
1. **Section context** — Devices cited in SE/predicate comparison sections weighted 3× over general text mentions
2. **Citation frequency** — How often cited (weighted by section context)
3. **Recency** — When was the predicate cleared? More recent = stronger
4. **Chain depth** — Is the predicate itself well-established (cited by many others)?
5. **Same applicant** — Predicates from the same company may indicate product line evolution
6. **Device similarity** — Match device name keywords to user's device description

### Build predicate chains

For the top predicate candidates, trace their lineage:
- What predicates did they cite?
- How many generations deep does the chain go?
- Is there a "root" device that anchors this product code?

### Cross-Product-Code Predicate Search

**CRITICAL**: If the user's device description mentions features that have little or no precedent in the primary product code, **automatically search other product codes** for supporting predicates.

For example, if the user describes a "collagen wound dressing with silver antimicrobial" and silver has <5% prevalence in KGN:

```bash
# Search ALL product codes for devices with the novel feature
python3 -c "
import csv
results = []
with open(os.path.expanduser('~/fda-510k-data/extraction/pmn96cur.txt'), encoding='latin-1') as f:
    reader = csv.reader(f, delimiter='|')
    header = next(reader)
    for row in reader:
        d = dict(zip(header, row))
        name = d.get('DEVICENAME','').upper()
        if 'SILVER' in name or 'ANTIMICROBIAL' in name:
            results.append(d)
# Group by product code and report
"
```

This helps identify **secondary predicates** from adjacent product codes that support novel features. Report these separately with clear rationale:

```
Secondary Predicate (for silver/antimicrobial claim):
  K123456 (Product Code: FRO) — Silver Wound Dressing
  - Supports your antimicrobial claim
  - Different product code but same wound management category
  - Consider citing alongside your primary KGN predicate
```

### Predicate recommendation

Based on the analysis, recommend the **top 3-5 predicate candidates** with rationale:

```
Recommended Predicates for [PRODUCT CODE]:

1. K123456 (Company A, 2023) — STRONGEST [SE]
   - Cited in SE sections by 12 devices, general text by 3 more
   - Most recent clearance with same intended use
   - Traditional 510(k) with Summary available
   - Review time: 95 days

2. K234567 (Company B, 2021) — STRONG [SE]
   - Cited in SE sections by 8 devices
   - Broader indications (your device fits within)
   - Has detailed clinical data in summary
   - Review time: 120 days

4. K567890 (Company D, 2019) — MODERATE [Ref]
   - Cited in general text by 5 devices (not found in any SE section)
   - ⚠ Verify this is an actual predicate — may be a reference device

Extraction Confidence
─────────────────────
Device numbers found in Substantial Equivalence / Predicate Comparison
sections are weighted 3× higher than those found in general body text
(literature reviews, background, adverse events).

Devices marked [SE] were cited in predicate-specific sections.
Devices marked [Ref] were found only in general text — verify these
are actual predicates before relying on them.
```

If the user provided `--intended-use`, compare their intended use against the indications associated with each predicate candidate.

If the user provided `--device-description` with novel features not found in the primary product code, include a **Secondary Predicates** section with candidates from other product codes that support those features.

## Step 4.5: Automatically Fetch Key Predicate Summaries

**CRITICAL: Do NOT ask the user to download PDFs separately.** After identifying the top 3-5 predicate candidates, check if their summary text is available. If not, **fetch it yourself**.

### Check if text is already cached

```python
import json, os

cache_dir = os.path.expanduser('~/fda-510k-data/extraction/cache')
index_file = os.path.join(cache_dir, 'index.json')

# Try per-device cache first (scalable)
if os.path.exists(index_file):
    with open(index_file) as f:
        index = json.load(f)
    for knumber in top_candidates:
        if knumber in index:
            device_path = os.path.join(os.path.expanduser('~/fda-510k-data/extraction'), index[knumber]['file_path'])
            if os.path.exists(device_path):
                print(f'{knumber}: text cached (per-device)')
            else:
                print(f'{knumber}: index entry exists but file missing — need to fetch')
        else:
            print(f'{knumber}: NOT cached — need to fetch')
else:
    # Legacy: monolithic pdf_data.json
    pdf_json = os.path.expanduser('~/fda-510k-data/extraction/pdf_data.json')
    if os.path.exists(pdf_json):
        with open(pdf_json) as f:
            data = json.load(f)
        for knumber in top_candidates:
            if knumber + '.pdf' in data:
                print(f'{knumber}: text cached (legacy pdf_data.json)')
            else:
                print(f'{knumber}: NOT cached — need to fetch')
    else:
        print('No cache found — all candidates need fetching')
```

### Fetch missing summaries directly from FDA

FDA 510(k) summary PDFs follow a predictable URL pattern:

```
https://www.accessdata.fda.gov/cdrh_docs/pdf{YY}/{KNUMBER}.pdf
```

Where `{YY}` is derived from the K-number:
- K241335 → pdf24 (first 2 digits after K)
- K183206 → pdf18
- K253710 → pdf25
- For older devices (K0xxxxx): pdf (no number) or pdf0, pdf1, etc.
- De Novo: `https://www.accessdata.fda.gov/cdrh_docs/reviews/DEN230052.pdf`

**IMPORTANT: FDA blocks simple HTTP requests.** You MUST use the same anti-detection techniques as the BatchFetch pipeline. Use **Bash with Python requests** (Method 1 below), NOT WebFetch, as the primary download method. FDA requires browser-like headers and consent cookies.

#### Method 1 (PRIMARY): Python requests with browser headers + FDA cookies

For each top predicate NOT already cached, download and extract text using Bash:

```bash
python3 << 'PYEOF'
import requests, sys, os, tempfile

knumber = "K241335"  # Replace with actual K-number
yy = knumber[1:3]    # e.g., "24" from K241335

# Try multiple URL patterns
urls = [
    f"https://www.accessdata.fda.gov/cdrh_docs/pdf{yy}/{knumber}.pdf",
    f"https://www.accessdata.fda.gov/cdrh_docs/reviews/{knumber}.pdf",
]
# For De Novo: urls = [f"https://www.accessdata.fda.gov/cdrh_docs/reviews/{denovo_number}.pdf",
#                       f"https://www.accessdata.fda.gov/cdrh_docs/pdf{yy}/{denovo_number}.pdf"]

# Use the same session/headers as BatchFetch (510BAtchFetch Working2.py)
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
})
session.cookies.update({
    'fda_gdpr': 'true',
    'fda_consent': 'true',
})

for url in urls:
    try:
        response = session.get(url, timeout=60, allow_redirects=True)
        if response.status_code == 200 and 'application/pdf' in response.headers.get('Content-Type', ''):
            # Save to temp file and extract text
            tmp = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
            tmp.write(response.content)
            tmp.close()

            # Try PyMuPDF first, then pdfplumber
            text = ""
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(tmp.name)
                text = "\n".join(page.get_text() for page in doc)
                doc.close()
            except ImportError:
                try:
                    import pdfplumber
                    with pdfplumber.open(tmp.name) as pdf:
                        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
                except ImportError:
                    print(f"ERROR: Neither PyMuPDF nor pdfplumber installed. Install with: pip install PyMuPDF pdfplumber")
                    sys.exit(1)

            os.unlink(tmp.name)

            if len(text.strip()) > 100:
                print(f"SUCCESS: Downloaded {knumber} from {url}")
                print(f"TEXT_LENGTH: {len(text)}")
                print(f"---BEGIN_TEXT---")
                print(text)
                print(f"---END_TEXT---")
                sys.exit(0)
            else:
                print(f"WARNING: PDF from {url} had minimal text ({len(text)} chars) — may be scanned/image PDF")
                os.unlink(tmp.name) if os.path.exists(tmp.name) else None
    except Exception as e:
        print(f"FAILED: {url} — {e}")

print(f"FAILED: Could not download {knumber} from any URL pattern")
sys.exit(1)
PYEOF
```

**Rate limiting**: If downloading multiple PDFs, add a 5-second delay between downloads:
```python
import time
time.sleep(5)  # Between each PDF download
```

#### Method 2 (FALLBACK): WebSearch for summary details

If the Python download fails (e.g., dependencies not installed, FDA changes their blocking), fall back to WebSearch:

```
Use WebSearch tool:
  query: "K241335 510k summary indications testing biocompatibility clinical study MARD site:accessdata.fda.gov"
```

WebSearch can retrieve substantial text from FDA pages via search result snippets — often enough for testing strategy and IFU analysis even when direct PDF download fails.

#### Method 3 (LAST RESORT): WebFetch on non-FDA sources

If both Method 1 and Method 2 fail, try fetching from secondary sources that may have the document:
- PubMed/PMC clinical study publications
- Manufacturer press releases with clinical data
- FDA Devices@FDA listing pages

### Depth controls for fetching

**For standard depth**: Fetch the top 2-3 most important predicate summaries (primary predicate + strongest secondary).
**For deep depth**: Fetch up to 5 predicate summaries.
**For quick depth**: Skip fetching — use database records only.

After fetching, use the extracted text for Steps 5 (Testing Strategy), 6 (IFU Landscape), and predicate comparison analysis. This is what makes the research report truly useful — the user gets actual data from the predicate devices, not just K-numbers.

### What to extract from fetched summaries

For each fetched predicate summary, extract and report:
- **Indications for Use** — exact IFU text for comparison with user's intended use
- **Device Description** — what the predicate device is and how it works
- **Testing performed** — specific test methods, standards, sample sizes, results
- **Clinical data** — study design, endpoints, patient count, outcomes
- **Predicates cited** — what the predicate itself cited (chain analysis)
- **Key differences** — anything that might differentiate from user's device

## Step 5: Testing Strategy

### From PDF text (cached in per-device cache or legacy pdf_data.json, OR freshly fetched in Step 4.5)

Analyze the testing sections from predicate summaries. Apply the **3-tier section detection system from `references/section-patterns.md`**:

- **Tier 1:** Use the Tier 1 regex patterns for all testing section types (Biocompatibility, Sterilization, Shelf Life, Non-Clinical Testing, Clinical, Software, Electrical Safety, Human Factors, Risk Management)
- **Tier 2:** For OCR-degraded PDFs, apply the OCR substitution table and retry (e.g., "8iocompatibility" → "Biocompatibility")
- **Tier 3:** For documents without standard headings, use the classification signal table to detect testing content by keyword density

Also apply **device-type-specific patterns** from `references/section-patterns.md` based on the product code (CGM, wound dressings, orthopedic, cardiovascular, IVD).

For each type of testing found, summarize:

**Non-Clinical / Performance Testing**:
- What test methods and standards are commonly cited? (ASTM, ISO, IEC, etc.)
- What performance endpoints are measured?
- What sample sizes are typical?

**Biocompatibility**:
- Which ISO 10993 endpoints are evaluated?
- Is this consistent across all devices or does it vary?

**Clinical Data**:
- What percentage of devices included clinical data?
- What type? (literature review, clinical study)
- Were any devices cleared WITHOUT clinical data?

**Sterilization** (if applicable):
- What sterilization methods are used?
- What validation standards are cited?

**Device-Specific Testing**: Based on the user's `--device-description`, add testing pattern searches for novel features. For example, if "silver" is mentioned, search for:
- Antimicrobial effectiveness (zone of inhibition, MIC/MBC)
- Silver content/release testing
- Silver-specific biocompatibility

### Testing recommendation

Provide a recommended testing matrix with Required/Likely Needed/Possibly Needed/Not Typically Required categories.

### Guidance vs. Predicate Testing Cross-Reference (standard and deep depth)

**Skip for `--depth quick`.**

If Step 3.75 identified applicable FDA guidance (device-specific or cross-cutting), cross-reference the guidance requirements against what the top predicate devices actually tested. This is the key value-add — not just "here's a guidance link" but "here's what it means for YOUR submission based on YOUR predicates."

Build a comparison table:

```
GUIDANCE VS. PREDICATE TESTING
────────────────────────────────────────
| Test Category     | FDA Guidance Says         | Predicate Evidence     | Gap? |
|-------------------|---------------------------|------------------------|------|
| Biocompatibility  | ISO 10993-5, -10 required | 3/3 predicates include | No   |
| Sterilization     | Validate per ISO 11135    | 2/3 used EO + 11135   | No   |
| Shelf Life        | Accelerated aging needed  | 1/3 included ASTM F1980| Flag |
| Antimicrobial     | If claimed: AATCC 100     | 0/3 included           | Flag |
| Performance       | [per guidance]            | 2/3 included bench test| No   |
| Electrical Safety | IEC 60601-1 required      | [N/A or evidence]      | Flag |
| Software V&V      | IEC 62304 lifecycle       | [N/A or evidence]      | Flag |
| Clinical          | [per guidance]            | 1/3 included lit review| Flag |
```

**How to populate each row:**
1. **"FDA Guidance Says"** column: Pull from device-specific guidance found in Step 3.75 (if any), plus cross-cutting guidance requirements. If no device-specific guidance exists, use general FDA expectations for the device class.
2. **"Predicate Evidence"** column: Count how many of the top predicate summaries (from Step 4.5/Step 5 analysis) included this test category. Use the section-patterns.md patterns to detect each test type.
3. **"Gap?"** column:
   - **No** — Guidance recommends it AND most predicates included it
   - **Flag** — Guidance recommends it BUT few or no predicates included it (user needs to plan for this)
   - **N/A** — Not applicable to this device type

Only include rows relevant to the device. Do NOT include software/cybersecurity rows for a simple wound dressing, or sterilization rows for non-sterile devices.

**Flag items prominently** — these represent potential gaps where the user's submission may need testing that predicates didn't do or didn't document. Add a brief note below the table:

```
⚠ Flagged items indicate areas where FDA guidance recommends testing but predicate
  evidence is thin. Plan to address these in your submission — either by including
  the testing or by providing a rationale for why it's not applicable.
```

## Step 6: Indications for Use Landscape

Search for IFU content in PDF text for this product code. Analyze:
- **Common IFU elements**: What anatomical sites, patient populations, clinical conditions are covered?
- **Broadest cleared IFU**: Which device has the widest indications?
- **Narrowest cleared IFU**: Which is most restrictive?
- **Evolution over time**: Have indications expanded or narrowed?
- **If user provided --intended-use**: Compare their intended use against cleared IFUs. Flag any elements that go beyond what's been cleared before.

## Step 7: Competitive Landscape

### Top applicants

```bash
grep "|PRODUCTCODE|" ~/fda-510k-data/extraction/pmn96cur.txt 2>/dev/null | cut -d'|' -f2 | sort | uniq -c | sort -rn | head -15
```

Report:
- **Market leaders**: Top companies by number of clearances
- **Recent entrants**: Companies that filed their first device in the last 3 years
- **Device name clustering**: Group device names to identify sub-categories
- **Active vs inactive**: Companies still submitting vs those who stopped

### Timeline

- Clearance volume by year (chart-like visualization using text)

### Deep Competitive Intelligence (if `--competitor-deep`)

When `--competitor-deep` flag is provided, perform extended competitive analysis:

#### Applicant Frequency Analysis

```bash
python3 << 'PYEOF'
import csv, os, re
from collections import Counter, defaultdict

product_code = "CODE"  # Replace

pmn_files = [
    os.path.expanduser('~/fda-510k-data/extraction/pmn96cur.txt'),
]

applicant_counts = Counter()
applicant_years = defaultdict(list)
device_names = defaultdict(list)

for pmn_file in pmn_files:
    if not os.path.exists(pmn_file):
        continue
    with open(pmn_file, encoding='latin-1') as f:
        reader = csv.reader(f, delimiter='|')
        header = next(reader)
        h = {name: i for i, name in enumerate(header)}
        for row in reader:
            if len(row) > h.get('PRODUCTCODE', 999) and row[h['PRODUCTCODE']] == product_code:
                applicant = row[h.get('APPLICANT', 0)]
                date = row[h.get('DECISIONDATE', 0)]
                dname = row[h.get('DEVICENAME', 0)]
                applicant_counts[applicant] += 1
                if date and len(date) >= 4:
                    applicant_years[applicant].append(date[:4])
                device_names[applicant].append(dname)

# Top 10 companies
for company, count in applicant_counts.most_common(10):
    years = sorted(set(applicant_years[company]))
    year_range = f"{years[0]}-{years[-1]}" if years else "N/A"
    unique_names = len(set(device_names[company]))
    print(f"COMPANY:{company}|count={count}|years={year_range}|unique_devices={unique_names}")

# Technology trends — device name keyword frequency by year
all_names = []
for pmn_file in pmn_files:
    if not os.path.exists(pmn_file): continue
    with open(pmn_file, encoding='latin-1') as f:
        reader = csv.reader(f, delimiter='|')
        header = next(reader)
        h = {name: i for i, name in enumerate(header)}
        for row in reader:
            if len(row) > h.get('PRODUCTCODE', 999) and row[h['PRODUCTCODE']] == product_code:
                date = row[h.get('DECISIONDATE', 0)]
                dname = row[h.get('DEVICENAME', 0)]
                if date and len(date) >= 4:
                    all_names.append((date[:4], dname.upper()))

# Keyword trends
keywords = ['TITANIUM', 'PEEK', 'CARBON', 'POROUS', '3D PRINT', 'ADDITIVE', 'EXPANDABLE', 'MINIMALLY INVASIVE', 'NAVIGATION', 'ROBOTIC']
from collections import defaultdict
year_keywords = defaultdict(Counter)
for year, name in all_names:
    for kw in keywords:
        if kw in name:
            year_keywords[kw][year] += 1

for kw in keywords:
    if year_keywords[kw]:
        trend = "|".join(f"{y}:{c}" for y, c in sorted(year_keywords[kw].items()))
        print(f"TREND:{kw}|{trend}")
PYEOF
```

#### Output Format for Deep Competitive Intelligence

```
COMPETITIVE INTELLIGENCE
────────────────────────────────────────

  Top Companies by Clearance Volume:
| # | Company | Clearances | Active Period | Device Variants |
|---|---------|-----------|---------------|----------------|
| 1 | {company} | {count} | {years} | {unique names} |
| 2 | {company} | {count} | {years} | {unique names} |
...

Technology Trends:
  {keyword}: {trend visualization — increasing/decreasing/stable}
  {keyword}: {trend}

Market Timeline:
  {Year-by-year clearance volume bar chart using text}
  2020: ████████ (25)
  2021: ██████████ (32)
  2022: ████████████ (38)
  ...

IFU Expansion Tracking:
  {Analysis of how indications have broadened or narrowed over time}
```

Store competitive intelligence in project:
```bash
# Write to project file
cat << 'EOF' > "$PROJECTS_DIR/$PROJECT_NAME/competitive_intelligence.json"
{json data}
EOF
```

## Output Format

Structure the research package as:

```
  FDA Submission Research Report
  {PRODUCT_CODE} — {DEVICE_NAME}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: {date} | Depth: {depth} | v5.18.0

PRODUCT CODE PROFILE
────────────────────────────────────────

  [Device class, regulation, advisory committee]

REGULATORY INTELLIGENCE
────────────────────────────────────────

  [Clearance stats, review times, submission types]

SAFETY INTELLIGENCE
────────────────────────────────────────

  [MAUDE events, recalls, safety flags]

APPLICABLE FDA GUIDANCE
────────────────────────────────────────

  [Device-specific guidance (if any)]
  [Cross-cutting guidance based on device characteristics]
  [Recognized consensus standards]

PREDICATE CANDIDATES (RANKED)
────────────────────────────────────────

  [Top 3-5 primary predicates from same product code]
  [Secondary predicates from other product codes if needed]

TESTING STRATEGY
────────────────────────────────────────

  [Required, likely needed, possibly needed testing]
  [Guidance vs. Predicate Testing cross-reference table]

INDICATIONS FOR USE LANDSCAPE
────────────────────────────────────────

  [IFU patterns, breadth analysis]

COMPETITIVE LANDSCAPE
────────────────────────────────────────

  [Top companies, trends, sub-categories]

RECOMMENDATIONS & NEXT STEPS
────────────────────────────────────────

  [Specific actionable next steps]

{If API_KEY_NUDGE:true was printed, add this line before the disclaimer:}
  Tip: Get 120x more API requests/day with a free key → /fda:configure --setup-key

────────────────────────────────────────
  This report is AI-generated from public FDA data.
  Verify independently. Not regulatory advice.
────────────────────────────────────────
```

**IMPORTANT**: The output should NOT have a "Data Gaps" section that lists files the user needs to create or commands to run. If a PDF is needed, fetch it yourself in Step 4.5. If a fetch fails, note the limitation gracefully (e.g., "The K241335 summary PDF was not accessible, so testing analysis is based on regulatory patterns for this device class") — do NOT tell the user to run another command.

## Depth Levels

### `--depth quick` (2-3 minutes)
- Product code profile + basic regulatory stats
- Top 3 predicate candidates (citation count only)
- Competitive landscape overview
- Skip PDF text analysis
- Skip guidance document lookup

### `--depth standard` (default, 5-10 minutes)
- Full regulatory intelligence
- Guidance document search + key requirements (device-specific + cross-cutting)
- Guidance vs. predicate testing cross-reference table
- Top 5 predicate candidates with chain analysis
- Cross-product-code search for novel features
- Testing strategy from PDF text (if available)
- IFU comparison
- Competitive landscape

### `--depth deep` (15+ minutes)
- Everything in standard
- Guidance search + WebFetch key guidance content + detailed cross-reference
- Full predicate chain mapping (all generations)
- Document-by-document section analysis
- Detailed testing method comparison tables
- IFU evolution timeline
- Export-ready tables and findings

## Step 4.75: Inline Validation for Top Predicates

**For standard depth or higher**: After identifying the top 3-5 predicate candidates and fetching their PDFs, automatically include the detailed validation profile for each — the SAME information `/fda:validate` would show. Do NOT tell the user to run `/fda:validate` separately.

### API-Enhanced Predicate Profiles

**Batch-lookup top predicate K-numbers** via the project data store. This caches results so `/fda:review` and other downstream commands can reuse them without re-querying:

```bash
# Replace K-numbers below with the actual top predicate candidates from Step 4
python3 "$FDA_PLUGIN_ROOT/scripts/fda_data_store.py" \
  --project "$PROJECT_NAME" \
  --query 510k-batch \
  --k-numbers "K241335,K234567,K345678"
```

If the API is unavailable, fall back to `grep` on flat files (pmn*.txt) as before.

For each top predicate candidate, include in the report:

```
PREDICATE PROFILE: {KNUMBER}
────────────────────────────────────────
Applicant: {from API or pmn database}
Decision: {SESE/DENG/etc.} on {date} ({review_days} days)
Product Code: {CODE} | Type: {Traditional/Special/etc.} | Summary: {Yes/No}
Advisory Committee: {panel}
Third Party Review: {Yes/No}
FDA URL: https://www.accessdata.fda.gov/cdrh_docs/pdf{YY}/{KNUMBER}.pdf

Indications for Use:
"{exact IFU text extracted from PDF}"

Predicates cited by this device: {list from PDF text}
Cited BY these other devices: {list from citation analysis}
MAUDE Events (product code): {count} total
Recalls (this device): {count} or None
PDF Summary: {text_length} chars available ({extraction status})
```

This eliminates the need for the user to run `/fda:validate` as a separate step.

## Step 5.5: Cross-Device Testing Comparison (Deep Depth Only)

**For deep depth**: After extracting testing information from predicate PDFs (Step 5), automatically compare test methods across the top 3 predicates — the SAME analysis `/fda:summarize --sections "Non-Clinical Testing"` would produce.

Use section patterns from `references/section-patterns.md` to extract testing sections from each predicate, then present as a comparison table:

```
| Test Category    | {K-number 1} | {K-number 2} | {K-number 3} |
|------------------|--------------|--------------|--------------|
| Biocompatibility | ISO 10993-5, -10 (n=X) | ISO 10993-5, -10, -23 | ISO 10993-5, -10 |
| Sterilization    | EO, ISO 11135 | Gamma, ISO 11137 | EO, ISO 11135 |
| Performance      | ASTM D1777 (n=30) | ASTM D1777 (n=20) | Not specified |
```

This eliminates the need for the user to run `/fda:summarize` as a separate step.

## Recommendations Section

End with specific, actionable next steps:

- If predicate candidates identified and user provided device description: "Use `/fda:compare-se --predicates K123456,K234567 --device-description \"your device\" --intended-use \"your IFU\"` to generate a formal Substantial Equivalence comparison table for your submission."
- If novel features found: "Your [feature] has limited precedent in [product code]. Consider consulting with your regulatory team about whether a secondary predicate from [other product code] strengthens your submission."
- Always: "Consult with regulatory affairs counsel before finalizing your submission strategy"

**NEVER recommend**: "Run `/fda:extract stage1`", "Run `/fda:extract stage2`", "Use `/fda:extract` to download PDFs", "Use `/fda:validate`" (inline it instead), or "Use `/fda:summarize --sections`" for content already covered in the research. The research command should do the work automatically. If a PDF fetch fails (404, access denied), note it gracefully and proceed with available data.

## PMA Intelligence (--include-pma)

When `--include-pma` flag is set, add a PMA analysis section to the research report. This is valuable for:
- Product codes that have both 510(k) and PMA history
- Understanding if a PMA pathway has been used for similar devices
- Identifying PMA supplements that indicate post-approval modifications

### PMA Data Collection

PMA intelligence uses inline API queries since PMA lookups are not yet part of the data store (Phase 3 migration). The `fda_api_client.py` HTTP-level cache still applies.

```bash
python3 << 'PYEOF'
import sys, os
sys.path.insert(0, os.path.join(os.environ.get("FDA_PLUGIN_ROOT", ""), "scripts"))
from fda_api_client import FDAClient

product_code = "PRODUCTCODE"  # Replace
client = FDAClient()

pma_result = client.get_pma_by_product_code(product_code, limit=100)
total = pma_result.get("meta", {}).get("results", {}).get("total", 0)
returned = len(pma_result.get("results", []))
print(f"PMA_TOTAL:{total}")
print(f"SHOWING:{returned}_OF:{total}")

if pma_result.get("results"):
    for r in pma_result["results"][:10]:
        supp = r.get("supplement_number", "")
        supp_type = r.get("supplement_type", "")
        print(f"PMA:{r.get('pma_number','?')}|{supp}|{supp_type}|{r.get('applicant','?')}|{r.get('trade_name','?')}|{r.get('decision_date','?')}|{r.get('decision_code','?')}")
PYEOF
```

### PMA Section in Report

```
PMA INTELLIGENCE
────────────────────────────────────────

  Total PMA Approvals: {count} for product code {CODE}
  Recent PMA Approvals:
    P{number} — {trade_name} by {applicant} ({date})
    P{number} — {trade_name} by {applicant} ({date})

  Supplement History: {total} supplements across all PMAs
  Most Active PMA: P{number} ({supplement_count} supplements)

  Pathway Implications:
  - PMA history exists for this product code — indicates Class III pathway
    has been used, though 510(k) may still be appropriate depending on
    your device's risk profile and predicate availability.
```

## Interactive Browse Mode (--browse)

When `--browse` flag is set, present the clearance landscape in an interactive-style format with filtering capabilities:

Browse mode uses count/aggregation queries not yet in the data store. Uses `FDAClient` directly (HTTP cache still applies).

```bash
python3 << 'PYEOF'
import sys, os
sys.path.insert(0, os.path.join(os.environ.get("FDA_PLUGIN_ROOT", ""), "scripts"))
from fda_api_client import FDAClient

product_code = "PRODUCTCODE"  # Replace
client = FDAClient()

# Top applicants by clearance count
print("=== TOP APPLICANTS ===")
applicants = client._request("510k", {"search": f'product_code:"{product_code}"', "count": "applicant.exact"})
if applicants.get("results"):
    for r in applicants["results"][:15]:
        print(f"APPLICANT:{r['term']}:{r['count']}")

# Recent clearance trends by year
print("\n=== CLEARANCE TRENDS ===")
trends = client._request("510k", {"search": f'product_code:"{product_code}"', "count": "decision_date"})
if trends.get("results"):
    year_counts = {}
    for r in trends["results"]:
        year = r["time"][:4]
        year_counts[year] = year_counts.get(year, 0) + r["count"]
    for year in sorted(year_counts.keys())[-10:]:
        print(f"YEAR:{year}:{year_counts[year]}")

# Clearance type distribution
print("\n=== CLEARANCE TYPES ===")
types = client._request("510k", {"search": f'product_code:"{product_code}"', "count": "clearance_type.exact"})
if types.get("results"):
    for r in types["results"]:
        print(f"TYPE:{r['term']}:{r['count']}")
PYEOF
```

## Clearance Timeline Analytics (--analytics)

When `--analytics` flag is set, calculate review duration statistics and clearance trends from openFDA data. This provides quantitative intelligence for submission planning.

### Analytics Data Collection

Analytics uses count/aggregation queries. Uses `FDAClient` directly (HTTP cache applies).

```bash
python3 << 'PYEOF'
import sys, os
from datetime import datetime
sys.path.insert(0, os.path.join(os.environ.get("FDA_PLUGIN_ROOT", ""), "scripts"))
from fda_api_client import FDAClient

product_code = "PRODUCTCODE"  # Replace
client = FDAClient()

# 1. Review duration statistics (last 5 years)
print("=== REVIEW DURATION ===")
recent = client._request("510k", {"search": f'product_code:"{product_code}" AND decision_date:[20200101 TO 29991231]', "limit": "100"})
durations = []
for r in recent.get("results", []):
    dr = r.get("date_received", "")
    dd = r.get("decision_date", "")
    if dr and dd:
        try:
            fmt = '%Y-%m-%d' if '-' in dr else '%Y%m%d'
            d1 = datetime.strptime(dr, fmt)
            d2 = datetime.strptime(dd, fmt)
            days = (d2 - d1).days
            if 0 < days < 1000:
                durations.append(days)
        except:
            pass

if durations:
    durations.sort()
    n = len(durations)
    median = durations[n // 2]
    p25 = durations[n // 4]
    p75 = durations[3 * n // 4]
    avg = sum(durations) // n
    print(f"DURATION:n={n}|median={median}|p25={p25}|p75={p75}|avg={avg}|min={min(durations)}|max={max(durations)}")
else:
    print("DURATION:insufficient_data")

# 2. Clearance type distribution
print("\n=== CLEARANCE TYPES ===")
types = client._request("510k", {"search": f'product_code:"{product_code}"', "count": "clearance_type.exact"})
if types.get("results"):
    for r in types["results"]:
        print(f"TYPE:{r['term']}:{r['count']}")

# 3. Clearance trends by year
print("\n=== YEARLY TRENDS ===")
trends = client._request("510k", {"search": f'product_code:"{product_code}"', "count": "decision_date"})
if trends.get("results"):
    year_counts = {}
    for r in trends["results"]:
        year = r["time"][:4]
        year_counts[year] = year_counts.get(year, 0) + r["count"]
    for year in sorted(year_counts.keys())[-15:]:
        print(f"YEAR:{year}:{year_counts[year]}")

# 4. Top applicants by volume
print("\n=== TOP APPLICANTS ===")
applicants = client._request("510k", {"search": f'product_code:"{product_code}"', "count": "applicant.exact"})
if applicants.get("results"):
    for r in applicants["results"][:10]:
        print(f"APPLICANT:{r['term']}:{r['count']}")

# 5. Decision code distribution
print("\n=== DECISION CODES ===")
decisions = client._request("510k", {"search": f'product_code:"{product_code}"', "count": "decision_code.exact"})
if decisions.get("results"):
    for r in decisions["results"]:
        print(f"DECISION:{r['term']}:{r['count']}")
PYEOF
```

### Analytics Output Format

```
CLEARANCE TIMELINE ANALYTICS
────────────────────────────────────────

  Product Code: {CODE} — {device_name}
  Analysis Period: 2020-Present ({N} clearances analyzed)

  Review Duration:
    Median: {median} days (IQR: {p25}–{p75})
    Average: {avg} days
    Fastest: {min} days | Slowest: {max} days

    Distribution:
    0-30d:   {'█' * scale} ({count})
    31-60d:  {'█' * scale} ({count})
    61-90d:  {'█' * scale} ({count})
    91-120d: {'█' * scale} ({count})
    121-180d:{'█' * scale} ({count})
    180d+:   {'█' * scale} ({count})

  Clearance Type Distribution:
    Traditional: {count} ({pct}%)
    Special:     {count} ({pct}%)
    Abbreviated: {count} ({pct}%)

  Yearly Clearance Volume:
    {year}: {'█' * scale} ({count})
    {year}: {'█' * scale} ({count})
    ...

  Top Applicants:
  | # | Company                  | Clearances | Share  |
  |---|--------------------------|-----------|--------|
  | 1 | {company}                | {count}    | {pct}% |
  | 2 | {company}                | {count}    | {pct}% |

  Decision Code Breakdown:
    SESE (Substantially Equivalent):  {count} ({pct}%)
    SEKN (SE with Conditions):        {count} ({pct}%)
    SESK (SE — Special 510k):         {count} ({pct}%)
    DENG (Denied):                    {count} ({pct}%)

  Submission Planning Insights:
  - Expected review time for your submission: ~{median} days
  - {clearance_type} is the most common pathway ({pct}%)
  - Market is {trend: growing/stable/declining} ({5yr avg} vs {10yr avg})
  - Top competitor: {company} ({count} clearances, {pct}% share)
```

## AI/ML Device Trend Analytics (--aiml)

When `--aiml` flag is set, filter analysis to AI/ML-associated product codes and provide SaMD classification insights.

### AI/ML Data Collection

AI/ML analysis uses keyword-filtered queries. Uses `FDAClient` directly (HTTP cache applies).

```bash
python3 << 'PYEOF'
import sys, os, time
sys.path.insert(0, os.path.join(os.environ.get("FDA_PLUGIN_ROOT", ""), "scripts"))
from fda_api_client import FDAClient

product_code = "PRODUCTCODE"  # Replace
client = FDAClient()

AIML_CODES = ["QAS", "QIH", "QMT", "QJU", "QKQ", "QPN", "QRZ", "DXL", "DPS", "MYN", "OTB"]
is_aiml = product_code in AIML_CODES
print(f"IS_AIML_CODE:{is_aiml}")

# Search for AI/ML keywords in device names for this product code
print("=== AI/ML DEVICE SEARCH ===")
ai_keywords = ["artificial intelligence", "machine learning", "algorithm"]
for kw in ai_keywords:
    result = client.search_510k(query=kw, product_code=product_code, limit=100)
    total = result.get("meta", {}).get("results", {}).get("total", 0)
    if total > 0:
        print(f"AI_KEYWORD:{kw}:{total}")
        for r in result.get("results", [])[:3]:
            print(f"AI_DEVICE:{r.get('k_number','')}|{r.get('device_name','')}|{r.get('decision_date','')}")
    time.sleep(0.5)

# AI/ML clearance trend across all AI/ML codes
if is_aiml:
    print("\n=== AI/ML LANDSCAPE ===")
    for code in AIML_CODES[:5]:
        result = client.get_clearances(code, limit=1)
        total = result.get("meta", {}).get("results", {}).get("total", 0)
        if total > 0:
            print(f"AIML_CODE:{code}:{total}")
        time.sleep(0.3)

# PCCP-authorized devices in this product code
print("\n=== PCCP CHECK ===")
pccp_result = client.search_510k(query="predetermined change", product_code=product_code, limit=100)
pccp_total = pccp_result.get("meta", {}).get("results", {}).get("total", 0)
print(f"PCCP_DEVICES:{pccp_total}")
PYEOF
```

### AI/ML Output Format

```
AI/ML DEVICE INTELLIGENCE
────────────────────────────────────────

  Product Code: {CODE} — {device_name}
  AI/ML Association: {Yes — known AI/ML code | Possible — AI keywords found | No direct association}

  AI/ML Devices in This Product Code:
  | K-number | Device Name | Decision Date |
  |----------|-------------|---------------|
  | {K#}     | {name}      | {date}        |

  {If is_aiml_code:}
  AI/ML Landscape (Related Product Codes):
  | Code | Description | Total Clearances |
  |------|------------|-----------------|
  | QAS  | CADe/CADx  | {count}          |
  | QIH  | AI Triage  | {count}          |
  ...

  SaMD Classification Guidance:
  Based on the device characteristics, this device would likely be classified as:
  - IMDRF Category: {II/III/IV}
  - Equivalent FDA Class: {I/II/III}

  PCCP-Authorized Devices: {count} in this product code
  {If count > 0: List them}

  Recommendations:
  - {If AI/ML}: Consider a PCCP for algorithm updates — /fda:pccp {CODE}
  - {If AI/ML}: Review FDA AI/ML action plan requirements
  - See references/aiml-device-intelligence.md for full AI/ML guidance list
```

### Browse Output Format

```
CLEARANCE LANDSCAPE BROWSER
────────────────────────────────────────

  Product Code: {CODE} — {device_name}
  Total Clearances: {N}

  Top Applicants:
  | # | Company                  | Clearances | Market Share |
  |---|--------------------------|-----------|--------------|
  | 1 | {company}                | {count}    | {pct}%       |
  | 2 | {company}                | {count}    | {pct}%       |
  ...

  Clearance Trends (Last 10 Years):
  {year}: {'█' * (count // scale)} ({count})
  {year}: {'█' * (count // scale)} ({count})
  ...

  Clearance Type Distribution:
  Traditional: {count} ({pct}%)
  Special:     {count} ({pct}%)
  Abbreviated: {count} ({pct}%)

  To search specific devices: `/fda:validate --search "device name" --product-code {CODE}`
  To see competitor details: `/fda:research {CODE} --competitor-deep`
```
