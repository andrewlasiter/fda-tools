---
description: Interactive review of extracted predicates — reclassify, score confidence, flag risks, accept or reject each predicate with tracked rationale
allowed-tools: Bash, Read, Glob, Grep, Write
argument-hint: "[--project NAME] [--knumber K123456] [--auto] [--full-auto] [--auto-threshold N]"
---

# FDA Predicate Review & Validation

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

You are conducting an interactive predicate review session. After extraction, this command scores, flags, and lets the user accept/reject each predicate with tracked rationale.

**KEY PRINCIPLE: Use the scoring algorithm from `references/confidence-scoring.md` consistently.** All scoring logic, flag definitions, and reclassification rules are defined there — this command applies them.

## Parse Arguments

From `$ARGUMENTS`, extract:

- `--project NAME` — Use data from a specific project folder
- `--knumber K123456` — Review predicates for a single device only
- `--auto` — Auto-accept predicates scoring 80+, auto-reject scoring below 20, present 20-79 for manual review
- `--full-auto` — Fully autonomous mode: all predicates get deterministic decisions based on score thresholds (never prompts user)
- `--auto-threshold N` — Threshold for auto-accept in --full-auto mode (default: 70)
- `--re-review` — Re-review previously reviewed predicates (overwrite existing review.json)
- `--export csv|json|md` — Export format for reviewed results (default: both json and csv)

## Step 1: Load Extraction Data

### Locate the project

```bash
# Check settings for projects_dir
PROJECTS_DIR=$(python3 -c "
import os, re
settings = os.path.expanduser('~/.claude/fda-predicate-assistant.local.md')
if os.path.exists(settings):
    with open(settings) as f:
        m = re.search(r'projects_dir:\s*(.+)', f.read())
        if m:
            print(os.path.expanduser(m.group(1).strip()))
            exit()
print(os.path.expanduser('~/fda-510k-data/projects'))
")
echo "PROJECTS_DIR=$PROJECTS_DIR"
```

If `--project NAME` provided, use `$PROJECTS_DIR/NAME/`. Otherwise, list available projects and ask the user to choose:

```bash
ls -d "$PROJECTS_DIR"/*/query.json 2>/dev/null
```

### Load output.csv

Read the extraction results from the project folder:

```bash
cat "$PROJECTS_DIR/$PROJECT_NAME/output.csv"
```

Parse the CSV: columns are typically `K-number, ProductCode, Predicate1, Predicate2, ..., Reference1, Reference2, ...`

If `--knumber K123456` is provided, filter to only rows where the K-number column matches.

### Load PDF text cache

Check for cached PDF text in the project folder or global cache:

```python
import json, os

project_dir = os.path.expanduser(f'~/fda-510k-data/projects/{project_name}')
pdf_cache = {}

# Try project-local pdf_data.json first
pdf_json = os.path.join(project_dir, 'pdf_data.json')
if os.path.exists(pdf_json):
    with open(pdf_json) as f:
        pdf_cache = json.load(f)

# Also try per-device cache
cache_dir = os.path.expanduser('~/fda-510k-data/extraction/cache')
index_file = os.path.join(cache_dir, 'index.json')
if os.path.exists(index_file):
    with open(index_file) as f:
        index = json.load(f)
```

### Check for existing review

If `review.json` already exists and `--re-review` is NOT set:

```bash
cat "$PROJECTS_DIR/$PROJECT_NAME/review.json" 2>/dev/null
```

If found, report: "A previous review exists with {N} accepted, {N} rejected, {N} deferred predicates. Use `--re-review` to start fresh, or I can show the existing review."

## Step 2: Reclassify Using Section-Aware Extraction

For each source device in output.csv, re-extract device numbers from its PDF text with section context. This replicates the proven logic from `research.md`:

```python
import re
from collections import Counter

device_pattern = re.compile(r'\b(?:K\d{6}|P\d{6}|DEN\d{6}|N\d{4,5})\b', re.IGNORECASE)

# SE section header detection (from references/section-patterns.md)
se_header = re.compile(r'(?i)(substantial\s+equivalence|se\s+comparison|predicate\s+(comparison|device|analysis|identification)|comparison\s+to\s+predicate|technological\s+characteristics|comparison\s+(table|chart|matrix)|similarities\s+and\s+differences|comparison\s+of\s+(the\s+)?(features|technological|device))')

SE_WINDOW = 2000  # chars after SE header
SE_WEIGHT = 3
GENERAL_WEIGHT = 1

def classify_with_context(text, source_id):
    """Returns dict mapping device_number -> {'se': bool, 'general': bool, 'se_count': int, 'general_count': int}"""
    results = {}

    # Find SE section boundaries
    se_zones = []
    for m in se_header.finditer(text):
        start = m.start()
        end = min(m.start() + SE_WINDOW, len(text))
        se_zones.append((start, end))

    for m in device_pattern.finditer(text):
        num = m.group().upper()
        if num == source_id.upper():
            continue  # Skip self-references
        in_se = any(start <= m.start() <= end for start, end in se_zones)
        if num not in results:
            results[num] = {'se': False, 'general': False, 'se_count': 0, 'general_count': 0}
        if in_se:
            results[num]['se'] = True
            results[num]['se_count'] += 1
        else:
            results[num]['general'] = True
            results[num]['general_count'] += 1

    return results
```

### Apply reclassification rules

Per the reclassification table in `references/confidence-scoring.md`:

- **Original "Predicate" + found in SE section** → Confirmed Predicate (high confidence)
- **Original "Predicate" + found in general text only** → Uncertain (may be reference device)
- **Original "Reference" + found in SE section** → Reclassify to Predicate (likely misclassified)
- **Original "Reference" + found in general text only** → Confirmed Reference

Report any reclassifications to the user:

```
Reclassification Results:
  K234567: Reference → Predicate (found in SE section of K241335)
  K345678: Predicate → Uncertain (found only in general text of K241335)
  3 predicates confirmed, 2 references confirmed, 1 reclassified, 1 uncertain
```

## Step 3: Score Each Predicate

Apply the 5-component scoring algorithm from `references/confidence-scoring.md`:

### 3A: Section Context (40 pts)

Already determined in Step 2:
- SE section → 40 points
- Mixed → 25 points
- General only → 10 points

### 3B: Citation Frequency (20 pts)

Count how many unique source documents cited this device (from the full extraction dataset):

```python
# Build citation counts across all source documents
citation_counts = Counter()
se_citation_counts = Counter()

for source_id, text in pdf_cache.items():
    context = classify_with_context(text, source_id)
    for device_num, ctx in context.items():
        citation_counts[device_num] += 1
        if ctx['se']:
            se_citation_counts[device_num] += 1

# Weighted citation count
def weighted_citations(device_num):
    se = se_citation_counts.get(device_num, 0)
    general_only = citation_counts.get(device_num, 0) - se
    return se + (general_only * 0.5)
```

Apply points per the scoring table: 5+ → 20pts, 3-4 → 15pts, 2 → 10pts, 1 → 5pts.

### 3C: Product Code Match (15 pts)

For each predicate candidate, check if it shares a product code with the source device(s):

```bash
python3 << 'PYEOF'
import urllib.request, urllib.parse, json, os, re, time

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

# Replace with actual device numbers to look up
devices_to_check = ["K123456", "K234567"]

if api_enabled:
    for knumber in devices_to_check:
        params = {"search": f'k_number:"{knumber}"', "limit": "1"}
        if api_key:
            params["api_key"] = api_key
        url = f"https://api.fda.gov/device/510k.json?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/1.0)"})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
                if data.get("results"):
                    r = data["results"][0]
                    print(f"{knumber}|PRODUCT_CODE:{r.get('product_code', '?')}|DECISION_DATE:{r.get('decision_date', '?')}|APPLICANT:{r.get('applicant', '?')}|DEVICE_NAME:{r.get('device_name', '?')}|STATEMENT_OR_SUMMARY:{r.get('statement_or_summary', '?')}")
                else:
                    print(f"{knumber}|NOT_FOUND")
        except Exception as e:
            print(f"{knumber}|ERROR:{e}")
        time.sleep(0.5)
else:
    # Fallback to flat files
    print("API_DISABLED:use_flatfiles")
PYEOF
```

If API disabled, fall back to grep on flat files:
```bash
grep "KNUMBER" ~/fda-510k-data/extraction/pmn96cur.txt 2>/dev/null
```

Apply points: Same code → 15pts, same panel → 8pts, different → 0pts.

### 3D: Recency (15 pts)

From the decision date obtained in 3C:
- < 5 years → 15pts
- 5-10 years → 10pts
- 10-15 years → 5pts
- > 15 years → 2pts
- Unknown → 5pts

### 3E: Regulatory History (10 pts)

Query openFDA for recalls and adverse events:

```bash
python3 << 'PYEOF'
import urllib.request, urllib.parse, json, os, re, time

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
    print("SAFETY_SKIP:api_disabled")
    exit(0)

# Replace with actual K-numbers and their product codes
devices = [
    {"knumber": "K123456", "product_code": "KGN", "applicant": "COMPANY"},
]

def fda_query(endpoint, search, limit=5):
    params = {"search": search, "limit": str(limit)}
    if api_key:
        params["api_key"] = api_key
    url = f"https://api.fda.gov/device/{endpoint}.json?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/1.0)"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"results": [], "meta": {"results": {"total": 0}}}
        return {"error": f"HTTP {e.code}"}
    except Exception as e:
        return {"error": str(e)}

for device in devices:
    kn = device["knumber"]
    pc = device["product_code"]
    applicant = device["applicant"]
    print(f"=== {kn} ===")

    # Check recalls for this specific device/applicant
    recalls = fda_query("recall", f'product_code:"{pc}"+AND+recalling_firm:"{applicant}"')
    total_recalls = recalls.get("meta", {}).get("results", {}).get("total", 0)
    if recalls.get("results"):
        for r in recalls["results"][:3]:
            print(f"RECALL:{r.get('classification', '?')}|{r.get('recall_status', '?')}|{r.get('reason_for_recall', 'N/A')[:80]}")
    print(f"TOTAL_RECALLS:{total_recalls}")

    time.sleep(0.5)

    # Check MAUDE events for this product code
    events = fda_query("event", f'device.product_code:"{pc}"', limit=1)
    total_events = events.get("meta", {}).get("results", {}).get("total", 0)
    print(f"TOTAL_MAUDE_EVENTS:{total_events}")

    # Check for death events specifically
    time.sleep(0.5)
    deaths = fda_query("event", f'device.product_code:"{pc}"+AND+event_type:"Death"', limit=1)
    total_deaths = deaths.get("meta", {}).get("results", {}).get("total", 0)
    print(f"DEATH_EVENTS:{total_deaths}")

    time.sleep(0.5)
PYEOF
```

Apply points: Clean → 10pts, Minor concerns → 5pts, Major concerns → 0pts.

### 3F: Check Exclusion List

```bash
python3 << 'PYEOF'
import json, os, re

# Read exclusion list path from settings
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
        for kn, info in devices.items():
            print(f"EXCLUDED:{kn}|{info.get('reason', 'No reason given')}")
    else:
        print("EXCLUSION_LIST:empty")
else:
    print("EXCLUSION_LIST:not_found")
PYEOF
```

## Step 4: Apply Risk Flags

After scoring, apply risk flags per the definitions in `references/confidence-scoring.md`:

For each predicate candidate, check:

| Flag | Check |
|------|-------|
| `RECALLED` | Any recall found in Step 3E |
| `RECALLED_CLASS_I` | Class I recall in Step 3E |
| `PMA_ONLY` | Device number starts with `P` |
| `CLASS_III` | Classification lookup shows Class 3 |
| `OLD` | Decision date > 10 years ago |
| `HIGH_MAUDE` | > 100 adverse events for product code |
| `DEATH_EVENTS` | Any death events for product code |
| `EXCLUDED` | On user's exclusion list |
| `STATEMENT_ONLY` | statement_or_summary field = "Statement" |
| `SUPPLEMENT` | K-number contains `/S` suffix |

## Step 5: Present Review to User

### If `--auto` mode

Auto-process based on score thresholds:
- **Score 80-100**: Auto-accept as predicate
- **Score 20-79**: Present to user for manual review
- **Score 0-19**: Auto-reject (flag as reference device or noise)

Report auto-decisions:
```
Auto-Review Results:
  Auto-accepted (score 80+): 5 predicates
  Auto-rejected (score <20): 2 devices
  Needs manual review (score 20-79): 3 devices

Proceeding with manual review of 3 devices...
```

### If `--full-auto` mode

Fully autonomous processing — **NEVER call AskUserQuestion**. All decisions are deterministic:

- **Score >= {auto-threshold, default 70}**: Auto-accept with rationale `"Auto-accepted (full-auto, score >= {threshold})"`
- **Score 40 to {threshold-1}**: Auto-defer with rationale `"Auto-deferred for manual review (full-auto, ambiguous score {score})"`
- **Score < 40**: Auto-reject with rationale `"Auto-rejected (full-auto, low confidence score {score})"`

All auto-decisions are logged with `"auto_decision": true` in review.json.

Report full-auto results:
```
Full-Auto Review Results:
  Auto-accepted (score >= {threshold}): {N} predicates
  Auto-deferred (score 40-{threshold-1}): {N} predicates
  Auto-rejected (score < 40): {N} predicates

  Total: {N} predicates processed with 0 user interactions
```

**Important**: When `--full-auto` is active, skip the entire "Interactive review" subsection. Do NOT present individual predicate cards or call AskUserQuestion.

### Interactive review

For each predicate that needs manual review (or all predicates if `--auto` not set), present:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PREDICATE REVIEW: K234567  (Score: 62/100 — Moderate)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Device: {device_name} by {applicant}
Product Code: {code} | Cleared: {date} | Review: {days} days
Classification: Predicate → Uncertain (reclassified)

Score Breakdown:
  Section Context:    10/40  (general text only)
  Citation Frequency: 15/20  (cited by 3 source documents)
  Product Code Match: 15/15  (same product code)
  Recency:           12/15  (cleared 4 years ago)
  Regulatory History: 10/10  (clean)

Flags: OLD

Context (where found):
  - K241335: general text, paragraph about "prior art wound dressings..."
  - K251234: SE comparison section, row 3 of comparison table
  - K248765: general text, literature review section

Original classification: Predicate (from extraction script)
Section-aware reclassification: Uncertain (found in SE section of 1/3 sources)
```

Then ask the user using AskUserQuestion:

```
Decision for K234567?
  [Accept as Predicate] — Confirm this is a valid predicate
  [Reject — Reference Device] — This is a reference device, not a predicate
  [Reject — Noise] — This is an incidental mention, not meaningful
  [Defer] — Skip for now, come back later
```

If the user accepts or rejects, ask for optional rationale:
```
Optional: Add a note about your decision for K234567?
(Press Enter to skip, or type your rationale)
```

## Step 6: Write Outputs

### review.json

Write structured review data to the project folder:

```json
{
  "version": 1,
  "project": "PROJECT_NAME",
  "reviewed_at": "2026-02-05T12:00:00Z",
  "review_mode": "interactive|auto|full-auto",
  "summary": {
    "total_devices_reviewed": 15,
    "accepted_predicates": 8,
    "rejected_reference": 4,
    "rejected_noise": 1,
    "deferred": 2,
    "reclassified": 3
  },
  "predicates": {
    "K234567": {
      "decision": "accepted",
      "rationale": "Well-established predicate in KGN space, cited in 3 SE sections",
      "confidence_score": 85,
      "score_breakdown": {
        "section_context": 40,
        "citation_frequency": 15,
        "product_code_match": 15,
        "recency": 10,
        "regulatory_history": 5
      },
      "original_classification": "Predicate",
      "reclassification": "Predicate",
      "auto_decision": false,
      "flags": ["OLD"],
      "cited_by": ["K241335", "K251234", "K248765"],
      "se_citations": 2,
      "general_citations": 1,
      "device_info": {
        "device_name": "Collagen Wound Dressing",
        "applicant": "COMPANY INC",
        "product_code": "KGN",
        "decision_date": "20210315",
        "decision_code": "SESE"
      }
    }
  },
  "excluded_devices": {
    "K111111": {
      "reason": "Recalled in 2024",
      "source": "exclusion_list"
    }
  }
}
```

Write to: `$PROJECTS_DIR/$PROJECT_NAME/review.json`

### output_reviewed.csv

Create an enhanced version of output.csv with confidence scores and review decisions:

```csv
K-number,ProductCode,Device,Classification,ConfidenceScore,ReviewDecision,Flags,Rationale,CitedBy_SE,CitedBy_General
K241335,KGN,"Collagen Dressing",Predicate,85,accepted,"OLD","Well-established predicate",2,1
K234567,KGN,"Foam Dressing",Reference,35,rejected_reference,"","Found only in general text — literature reference",0,3
```

Write to: `$PROJECTS_DIR/$PROJECT_NAME/output_reviewed.csv`

## Step 7: Post-Review Summary

After all predicates are reviewed, present a summary:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REVIEW COMPLETE — PROJECT: {name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Results:
  Accepted predicates:     8
  Rejected (reference):    4
  Rejected (noise):        1
  Deferred:                2
  Reclassified:            3 (2 upgraded, 1 downgraded)

Top Accepted Predicates:
  1. K241335 (Score: 92) — Collagen Wound Dressing by COMPANY A
  2. K238901 (Score: 87) — Foam Dressing by COMPANY B
  3. K225678 (Score: 85) — Antimicrobial Dressing by COMPANY C

Risk Flags Summary:
  RECALLED: 1 device (K111111 — excluded)
  OLD: 3 devices (all >10 years)
  HIGH_MAUDE: 0

Files Written:
  review.json          — Full review data with scores and decisions
  output_reviewed.csv  — Reclassified output with confidence column

Next Steps:
  • Use accepted predicates in /fda:compare-se to build SE comparison table
  • Run /fda:guidance {PRODUCT_CODE} to find applicable guidance documents
  • Review deferred predicates when more data is available
```

## Error Handling

- **No output.csv found**: "No extraction results found for project '{name}'. Run `/fda:extract both --project {name}` first."
- **No PDF text cache**: "PDF text cache not found. Review will score using database records only (section context scoring unavailable — all devices get 10/40 for section context)."
- **API unavailable**: "openFDA API unavailable. Regulatory history scoring defaults to 5/10 for all devices. Recall and MAUDE flags will not be applied."
- **Empty extraction results**: "output.csv contains no predicate or reference devices. Nothing to review."
