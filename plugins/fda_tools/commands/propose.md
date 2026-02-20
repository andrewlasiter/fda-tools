
<!-- NOTE: This command has been migrated to use centralized FDAClient (FDA-114)
     Old pattern: urllib.request.Request + urllib.request.urlopen
     New pattern: FDAClient with caching, retry, and rate limiting
     Migration date: 2026-02-20
-->

---
description: Manually propose predicate and reference devices for a 510(k) submission — validates against openFDA, scores confidence, compares IFU, writes review.json
allowed-tools: Bash, Read, Glob, Grep, Write, WebFetch, WebSearch
argument-hint: "--predicates K123456[,K234567] --project NAME [--references K345678] [--rationale TEXT]"
---

# FDA Manual Predicate Proposal

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

If `$FDA_PLUGIN_ROOT` is empty, report an error: "Could not locate the FDA Predicate Assistant plugin installation. Make sure the plugin is installed and enabled."

---

You are helping the user manually declare predicate and reference devices for a 510(k) submission. Unlike `/fda:review` (which requires extraction data from output.csv), this command takes user-specified predicates directly and validates them against FDA databases.

**KEY PRINCIPLE: Write the same `predicates` schema as `/fda:review` so all downstream commands work unchanged.** The review.json produced here must be compatible with `/fda:presub`, `/fda:compare-se --infer`, `/fda:draft`, `/fda:lineage --infer`, and all other commands that read review.json.

## Parse Arguments

From `$ARGUMENTS`, extract:

- `--predicates K123456[,K234567]` (required) — Proposed predicate K-numbers, comma-separated
- `--references K345678[,K456789]` (optional) — Reference devices (not predicates, cited for specific features)
- `--project NAME` (required) — Project to associate the proposal with
- `--product-code CODE` (optional) — 3-letter FDA product code; auto-detect from predicates if omitted
- `--device-description TEXT` (optional) — Description of the subject device
- `--intended-use TEXT` (optional) — Proposed indications for use
- `--rationale "text"` (optional) — Justification for predicate selection (applied to all predicates, or per-predicate if semicolon-separated matching predicate count)
- `--skip-validation` — Skip openFDA validation (use when offline or API unavailable)
- `--force` — Overwrite existing review.json without prompting
- `--full-auto` — Never prompt the user; fail on missing required arguments

**Validation:**
- If `--predicates` missing and NOT `--full-auto`: ask the user for predicate K-numbers
- If `--predicates` missing and `--full-auto`: **ERROR**: "In --full-auto mode, --predicates is required."
- If `--project` missing and NOT `--full-auto`: ask the user for a project name
- If `--project` missing and `--full-auto`: **ERROR**: "In --full-auto mode, --project is required."

## Step 1: Resolve Project Directory

```bash
PROJECTS_DIR=$(python3 -c "
import os, re
settings = os.path.expanduser('~/.claude/fda-tools.local.md')
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

Create the project directory if it doesn't exist:
```bash
mkdir -p "$PROJECTS_DIR/$PROJECT_NAME"
```

### Check for existing review.json

```bash
ls -la "$PROJECTS_DIR/$PROJECT_NAME/review.json" 2>/dev/null
```

If review.json exists and `--force` is NOT set:
- If NOT `--full-auto`: Ask the user if they want to overwrite
- If `--full-auto`: **ERROR**: "review.json already exists. Use --force to overwrite."

## Step 2: Validate Device Number Format

For each predicate and reference device number, validate format:

```python
from fda_tools.scripts.fda_api_client import FDAClient

client = FDAClient()
# Use client methods:
# - client.get_510k(k_number)
# - client.get_classification(product_code)
# - client.get_clearances(product_code, limit=100)
# - client.get_events(product_code)
# - client.get_recalls(product_code)
# - client.search_pma(product_code=code, applicant=name)

import re

valid_pattern = re.compile(r'^[KPN]\d{6}$|^DEN\d{6,8}$')

for device in all_devices:
    device = device.strip().upper()
    if not valid_pattern.match(device):
        print(f"INVALID:{device}")
    else:
        print(f"VALID:{device}")
```

If any device number is invalid, report:
- "Invalid device number format: {number}. Expected K/P/N followed by 6 digits (e.g., K192345) or DEN followed by 6-8 digits (e.g., DEN20210001)."
- Do NOT proceed with invalid numbers.

## Step 3: Validate Against openFDA

**Skip this step entirely if `--skip-validation` is set.** Report: "Validation skipped per --skip-validation flag. Predicate data will not be auto-populated."

For each predicate and reference device, query openFDA:

```bash
python3 << 'PYEOF'
import urllib.request, urllib.parse, json, os, re, time

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

# Batch lookup: single OR query for ALL predicate + reference K-numbers (1 call instead of N)
all_knumbers = ["K123456", "K234567"]  # Replace with all device numbers

if not api_enabled:
    print("API:disabled")
    exit(0)

batch_search = "+OR+".join(f'k_number:"{kn}"' for kn in all_knumbers)
params = {"search": batch_search, "limit": str(len(all_knumbers))}
if api_key:
    params["api_key"] = api_key
# Fix URL encoding: replace + with space before urlencode
params["search"] = params["search"].replace("+", " ")
url = f"https://api.fda.gov/device/510k.json?{urllib.parse.urlencode(params)}"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/5.5.0)"})
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
        results_by_k = {r.get("k_number", ""): r for r in data.get("results", [])}
        for knumber in all_knumbers:
            print(f"=== {knumber} ===")
            r = results_by_k.get(knumber)
            if r:
                print(f"DEVICE_NAME:{r.get('device_name', 'N/A')}")
                print(f"APPLICANT:{r.get('applicant', 'N/A')}")
                print(f"PRODUCT_CODE:{r.get('product_code', 'N/A')}")
                print(f"DECISION_DATE:{r.get('decision_date', 'N/A')}")
                print(f"DECISION_CODE:{r.get('decision_code', 'N/A')}")
                print(f"CLEARANCE_TYPE:{r.get('clearance_type', 'N/A')}")
                print(f"STATEMENT_OR_SUMMARY:{r.get('statement_or_summary', 'N/A')}")
                print(f"THIRD_PARTY:{r.get('third_party_flag', 'N/A')}")
                print("SOURCE:api")
            else:
                print(f"NOT_FOUND:{knumber}")
except Exception as e:
    for knumber in all_knumbers:
        print(f"=== {knumber} ===")
        print(f"API_ERROR:{e}")
PYEOF
```

Add 1-second delay between API calls for multiple devices.

### Risk Flag Checks

For each validated predicate, run additional checks:

**Decision code flags:**
- `SESD` or `SESU` (Substantially Equivalent with conditions): Flag `CONDITIONAL_SE`
- `DENG` (De Novo Granted): Flag `DE_NOVO` — valid but note it's a De Novo, not a 510(k)

**Product code mismatch:**
- If `--product-code` provided and predicate product_code differs: Flag `PRODUCT_CODE_MISMATCH`
- If no `--product-code` provided: auto-detect from first predicate's product code

**Recall check:**

```bash
python3 << 'PYEOF'
import urllib.request, urllib.parse, json, os, re

settings_path = os.path.expanduser('~/.claude/fda-tools.local.md')
api_key = os.environ.get('OPENFDA_API_KEY')
if os.path.exists(settings_path):
    with open(settings_path) as f:
        content = f.read()
    if not api_key:
        m = re.search(r'openfda_api_key:\s*(\S+)', content)
        if m and m.group(1) != 'null':
            api_key = m.group(1)

# Batch recall check for all proposed devices (1 call instead of N)
all_knumbers_recall = ["K123456", "K234567"]  # Replace with all device numbers
batch_recall_search = "+OR+".join(f'k_number:"{kn}"' for kn in all_knumbers_recall)
params = {"search": batch_recall_search, "limit": "100"}
if api_key:
    params["api_key"] = api_key
# Fix URL encoding: replace + with space before urlencode
params["search"] = params["search"].replace("+", " ")
url = f"https://api.fda.gov/device/recall.json?{urllib.parse.urlencode(params)}"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/5.5.0)"})
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
        # Group recalls by K-number
        recalls_by_k = {}
        for r in data.get('results', []):
            for rk in r.get('k_numbers', []):
                if rk not in recalls_by_k:
                    recalls_by_k[rk] = []
                recalls_by_k[rk].append(r)
        for kn in all_knumbers_recall:
            kn_recalls = recalls_by_k.get(kn, [])
            print(f"RECALL_COUNT:{kn}:{len(kn_recalls)}")
            for r in kn_recalls[:3]:
                print(f"RECALL:{kn}|{r.get('res_event_number', 'N/A')}|{r.get('event_type', 'N/A')}")
except Exception as e:
    print(f"RECALL_ERROR:{e}")
PYEOF
```

If recalls found: Flag `RECALLED`

**Enforcement / withdrawal check:**

```bash
python3 << 'PYEOF'
import urllib.request, urllib.parse, json, os, re

settings_path = os.path.expanduser('~/.claude/fda-tools.local.md')
api_key = os.environ.get('OPENFDA_API_KEY')
if os.path.exists(settings_path):
    with open(settings_path) as f:
        content = f.read()
    if not api_key:
        m = re.search(r'openfda_api_key:\s*(\S+)', content)
        if m and m.group(1) != 'null':
            api_key = m.group(1)

# Batch enforcement check for all proposed device product codes (1 call instead of N)
product_codes_enforce = ["PC1", "PC2"]  # Replace with unique product codes
if product_codes_enforce:
    enforce_search = "+OR+".join(f'product_code:"{pc}"' for pc in product_codes_enforce)
    params = {"search": enforce_search, "limit": "100"}
    if api_key:
        params["api_key"] = api_key
    params["search"] = params["search"].replace("+", " ")
    url = f"https://api.fda.gov/device/enforcement.json?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/5.16.0)"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            for r in data.get('results', [])[:5]:
                print(f"ENFORCEMENT:{r.get('product_code', '?')}|{r.get('classification', '?')}|{r.get('status', '?')}|{r.get('reason_for_recall', 'N/A')[:80]}")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print("ENFORCEMENT:none")
        else:
            print(f"ENFORCEMENT_ERROR:{e}")
    except Exception as e:
        print(f"ENFORCEMENT_ERROR:{e}")
PYEOF
```

If enforcement action found: Flag `ENFORCEMENT_ACTION`
If clearance withdrawal/revocation language found: Flag `WITHDRAWN` — **a withdrawn predicate is not legally marketed and cannot serve as a valid predicate device**. Present a CRITICAL warning to the user.

**MAUDE death check:**

```bash
python3 << 'PYEOF'
import urllib.request, urllib.parse, json, os, re

settings_path = os.path.expanduser('~/.claude/fda-tools.local.md')
api_key = os.environ.get('OPENFDA_API_KEY')
if os.path.exists(settings_path):
    with open(settings_path) as f:
        content = f.read()
    if not api_key:
        m = re.search(r'openfda_api_key:\s*(\S+)', content)
        if m and m.group(1) != 'null':
            api_key = m.group(1)

# Batch MAUDE death event check for all unique product codes (1 call instead of N)
product_codes_to_check = ["PC1", "PC2"]  # Replace with unique product codes from validated devices
if product_codes_to_check:
    death_search = "(" + "+OR+".join(f'device.device_report_product_code:"{pc}"' for pc in product_codes_to_check) + ')+AND+event_type:"Death"'
    params = {"search": death_search, "limit": "1"}
    if api_key:
        params["api_key"] = api_key
    # Fix URL encoding: replace + with space before urlencode
    params["search"] = params["search"].replace("+", " ")
    url = f"https://api.fda.gov/device/event.json?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/5.5.0)"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            total = data.get('meta', {}).get('results', {}).get('total', 0)
            print(f"DEATH_EVENTS:{total}")
    except Exception as e:
        print(f"MAUDE_ERROR:{e}")
PYEOF
```

If death events > 0: Flag `DEATH_EVENTS`

**Predicate age check:**
- Parse `decision_date` from openFDA response
- If >10 years old: Flag `OLD`

## Step 4: Compute Confidence Scores

Use the scoring algorithm from `references/confidence-scoring.md` with manual proposal adjustments:

### Manual Proposal Scoring Components

| Component | Max Points | Manual Proposal Logic |
|-----------|------------|----------------------|
| Section Context | 30 pts | Fixed 30 pts (user explicitly selected as predicate) |
| Citation Frequency | 20 pts | 10 pts (single citation = user's declaration) |
| Product Code Match | 15 pts | 15 pts if match, 0 if mismatch, 8 if unknown |
| Recency | 15 pts | Standard: 15 pts if <5yr, 10 if 5-10yr, 5 if 10-15yr, 0 if >15yr |
| Regulatory History | 10 pts | 10 if clean, 5 if SESD/SESU, 0 if recalled |

**Score interpretation (same as review.md):**
- 80-100: Strong predicate
- 60-79: Good predicate
- 40-59: Moderate — consider alternatives
- 20-39: Weak — may face FDA questions
- 0-19: Poor — reconsider

All manually proposed predicates get `"decision": "accepted"` by default (the user explicitly chose them). Flags inform the user about potential issues but don't auto-reject.

## Step 5: IFU Comparison (if --intended-use provided)

When `--intended-use` is provided, perform automatic IFU comparison against each predicate.

### Fetch predicate IFU text

For each predicate, try to retrieve IFU text:

1. Check project `pdf_data.json` cache for predicate text → extract IFU section using the **3-tier section detection system from `references/section-patterns.md`**
2. If not cached, fetch the predicate PDF from FDA using the same download approach as `compare-se.md` Step 2
3. Extract IFU text from the downloaded PDF
4. If PDF fetch fails, fall back to the `statement_or_summary` field from openFDA API (limited but available)

### Compare IFU

```python
def compare_ifu(subject_ifu, predicate_ifu):
    """Compare subject IFU against predicate IFU using keyword overlap."""
    import re

    def extract_keywords(text):
        """Extract meaningful medical/regulatory keywords."""
        text = text.lower()
        # Remove common stopwords
        stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                     'for', 'to', 'of', 'in', 'on', 'at', 'by', 'and', 'or', 'with',
                     'this', 'that', 'these', 'those', 'it', 'its', 'as', 'from',
                     'which', 'who', 'whom', 'has', 'have', 'had', 'do', 'does',
                     'not', 'but', 'if', 'than', 'when', 'where', 'how', 'all',
                     'each', 'every', 'both', 'such', 'no', 'nor', 'any', 'other'}
        words = set(re.findall(r'\b[a-z]{3,}\b', text)) - stopwords
        return words

    subject_kw = extract_keywords(subject_ifu)
    pred_kw = extract_keywords(predicate_ifu)

    if not subject_kw or not pred_kw:
        return {"overlap": 0, "assessment": "Unable to compare — insufficient text"}

    overlap = subject_kw & pred_kw
    union = subject_kw | pred_kw
    jaccard = len(overlap) / len(union) if union else 0

    subject_only = subject_kw - pred_kw
    pred_only = pred_kw - subject_kw

    if jaccard >= 0.6:
        assessment = "STRONG OVERLAP — intended uses are substantially similar"
    elif jaccard >= 0.35:
        assessment = "MODERATE OVERLAP — some differences that may require justification"
    else:
        assessment = "LOW OVERLAP — significantly different intended uses; predicate may face FDA scrutiny"

    return {
        "overlap_score": round(jaccard * 100),
        "shared_keywords": sorted(overlap)[:20],
        "subject_unique": sorted(subject_only)[:10],
        "predicate_unique": sorted(pred_only)[:10],
        "assessment": assessment
    }
```

## Step 6: Write review.json

Write the review.json file in the same schema as `/fda:review`:

```json
{
  "version": 1,
  "project": "PROJECT_NAME",
  "reviewed_at": "2026-02-07T12:00:00Z",
  "review_mode": "manual",
  "manual_proposal": true,
  "summary": {
    "total_devices_reviewed": 3,
    "accepted_predicates": 2,
    "accepted_references": 1,
    "rejected_reference": 0,
    "rejected_noise": 0,
    "deferred": 0,
    "reclassified": 0
  },
  "predicates": {
    "K123456": {
      "decision": "accepted",
      "rationale": "Manually proposed as primary predicate. User rationale: [provided or 'No rationale specified']",
      "confidence_score": 75,
      "score_breakdown": {
        "section_context": 30,
        "citation_frequency": 10,
        "product_code_match": 15,
        "recency": 15,
        "regulatory_history": 5
      },
      "original_classification": "Predicate",
      "reclassification": "Predicate",
      "auto_decision": false,
      "manual_proposal": true,
      "flags": [],
      "cited_by": [],
      "se_citations": 0,
      "general_citations": 0,
      "device_info": {
        "device_name": "Device Name from openFDA",
        "applicant": "COMPANY INC",
        "product_code": "OVE",
        "decision_date": "20230615",
        "decision_code": "SESE"
      },
      "ifu_comparison": {
        "overlap_score": 72,
        "assessment": "STRONG OVERLAP — intended uses are substantially similar",
        "shared_keywords": ["wound", "dressing", "management"],
        "subject_unique": ["antimicrobial"],
        "predicate_unique": ["foam"]
      }
    }
  },
  "reference_devices": {
    "K345678": {
      "decision": "reference",
      "rationale": "Cited as reference device for specific feature comparison",
      "device_info": {
        "device_name": "Reference Device Name",
        "applicant": "REFERENCE COMPANY",
        "product_code": "KGN",
        "decision_date": "20220101",
        "decision_code": "SESE"
      },
      "flags": []
    }
  },
  "excluded_devices": {}
}
```

**CRITICAL COMPATIBILITY:** The `predicates` key uses the exact same schema as `/fda:review`. The new `reference_devices` key is a top-level sibling that won't break existing commands (they only read `predicates`).

### Write query.json if not exists

If no `query.json` exists in the project folder, create one:

```json
{
  "project_name": "PROJECT_NAME",
  "created_at": "2026-02-07T12:00:00Z",
  "source": "manual_proposal",
  "product_codes": ["OVE"],
  "proposed_predicates": ["K123456", "K234567"],
  "proposed_references": ["K345678"]
}
```

If `query.json` exists, do NOT overwrite it — the project may have extraction data.

## Step 7: Audit Logging

Write audit log entries per `references/audit-logging.md`:

- `proposal_created` entry with predicate count, reference count, and validation status
- For each validated device: `device_validated` entry with openFDA data source
- For each flag raised: `risk_flag` entry with flag type and device
- If IFU comparison performed: `ifu_compared` entry with overlap scores
- At completion: `review_json_written` entry with output path

Append all entries to `$PROJECTS_DIR/$PROJECT_NAME/audit_log.jsonl`.

## Step 8: Present Summary

Report the proposal summary to the user:

```
  FDA Predicate Proposal
  {project_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: {date} | v5.22.0

PROPOSED PREDICATES
────────────────────────────────────────

  | # | K-Number | Device Name | Applicant | Cleared | Score | Flags |
  |---|----------|-------------|-----------|---------|-------|-------|
  | 1 | K123456  | {name}      | {company} | {date}  | 75/100 | — |
  | 2 | K234567  | {name}      | {company} | {date}  | 62/100 | OLD |

REFERENCE DEVICES
────────────────────────────────────────

  | # | K-Number | Device Name | Applicant | Cleared |
  |---|----------|-------------|-----------|---------|
  | 1 | K345678  | {name}      | {company} | {date}  |

{If --intended-use was provided:}
IFU COMPARISON
────────────────────────────────────────

  | Predicate | Overlap | Assessment |
  |-----------|---------|------------|
  | K123456   | 72%     | STRONG OVERLAP — substantially similar |
  | K234567   | 45%     | MODERATE OVERLAP — may need justification |

VALIDATION RESULTS
────────────────────────────────────────

  openFDA lookup     ✓  All devices validated
  Format check       ✓  All K-numbers valid
  Recall check       ✓  No active recalls
  Product code       ✓  All match {CODE}
  MAUDE deaths       ⚠  {N} death events for product code

{If flags were raised:}
RISK FLAGS
────────────────────────────────────────

  ⚠ K234567: OLD — Cleared >10 years ago (2013). FDA may question predicate relevance.
  ⚠ K345678: PRODUCT_CODE_MISMATCH — Product code {X} differs from project code {Y}.

NEXT STEPS
────────────────────────────────────────

  1. Review flags above and decide if predicate changes are needed
  2. Run /fda:compare-se --infer --project {name} for SE comparison table
  3. Run /fda:presub {CODE} --project {name} for Pre-Sub package
  4. Run /fda:lineage --infer --project {name} for predicate chain analysis

────────────────────────────────────────
  review.json written to: {path}
  This report is AI-generated from public FDA data.
  Verify independently. Not regulatory advice.
────────────────────────────────────────
```

## Audit Logging

After proposal validation is complete, log the result using `fda_audit_logger.py`:

### Log predicate proposal

```bash
python3 "$FDA_PLUGIN_ROOT/scripts/fda_audit_logger.py" \
  --project "$PROJECT_NAME" \
  --command propose \
  --action predicate_proposed \
  --subject "$K_NUMBER" \
  --decision "$VALIDATION_OUTCOME" \
  --confidence "$CONFIDENCE_SCORE" \
  --mode interactive \
  --decision-type manual \
  --rationale "$VALIDATION_SUMMARY" \
  --data-sources "openFDA 510k API,openFDA recall API,openFDA classification" \
  --metadata "{\"product_code_match\":$PC_MATCH,\"ifu_overlap\":$IFU_OVERLAP,\"recall_check\":\"$RECALL_STATUS\"}" \
  --files-written "$PROJECTS_DIR/$PROJECT_NAME/review.json"
```

### Log validation failures

If validation finds issues (recall, withdrawn, wrong class):

```bash
python3 "$FDA_PLUGIN_ROOT/scripts/fda_audit_logger.py" \
  --project "$PROJECT_NAME" \
  --command propose \
  --action predicate_validation_result \
  --subject "$K_NUMBER" \
  --decision "validation_$RESULT" \
  --mode interactive \
  --decision-type auto \
  --rationale "$VALIDATION_ISSUE_DETAIL"
```

## Error Handling

- **Invalid K-number format**: Report specific format error, suggest correction
- **Device not found in openFDA**: "Device {K-number} not found in openFDA 510(k) database. It may be a very old or foreign submission. Use --skip-validation to proceed without validation."
- **API unavailable**: Degrade to format validation only. Report: "openFDA API unavailable. Device data not validated. Run again later or use --skip-validation."
- **review.json exists**: Prompt for confirmation unless --force
- **No project directory**: Create it automatically
- **PDF fetch fails for IFU**: Fall back to keyword comparison of IFU text from openFDA device_name and statement_or_summary fields
