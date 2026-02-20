---
description: Interactive review of extracted predicates — reclassify, score confidence, flag risks, accept or reject each predicate with tracked rationale
allowed-tools: Bash, Read, Glob, Grep, Write, AskUserQuestion
argument-hint: "[--project NAME] [--knumber K123456] [--auto] [--full-auto] [--auto-threshold N]"
---

# FDA Predicate Review & Validation

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

## Check Available Data

Before making API calls, check what data already exists for this project:

```bash
python3 $FDA_PLUGIN_ROOT/scripts/fda_data_store.py --project "$PROJECT_NAME" --show-manifest 2>/dev/null
```

If the manifest shows cached data that matches your needs (same product code, not expired), **use the cached summaries** instead of re-querying. This prevents redundant API calls and ensures consistency across commands.

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

# SYNC: Tier 1 "Predicate / SE" pattern from references/section-patterns.md
# If this regex finds no SE section, apply Tier 2 (OCR substitution table) then
# Tier 3 (semantic signals: "predicate", K-number, "substantially equivalent",
# "comparison", "subject device", "technological characteristics" — 2+ required).
# See references/section-patterns.md for full 3-tier detection system.
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

For each predicate candidate, batch-lookup via the project data store (caches results for cross-command reuse):

```bash
# Replace K-numbers below with actual device numbers to check
python3 "$FDA_PLUGIN_ROOT/scripts/fda_data_store.py" \
  --project "$PROJECT_NAME" \
  --query 510k-batch \
  --k-numbers "K123456,K234567"
```

The output includes PRODUCT_CODE, DECISION_DATE, APPLICANT, DEVICE_NAME for each device.

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

Query recalls and adverse events for predicate product codes via the project data store. If `/fda:research` or `/fda:safety` already ran for this project, the manifest will have cached recall and event data.

```bash
# For each unique product code among the predicate candidates:
python3 "$FDA_PLUGIN_ROOT/scripts/fda_data_store.py" \
  --project "$PROJECT_NAME" \
  --query recalls \
  --product-code "$PREDICATE_PRODUCT_CODE"

python3 "$FDA_PLUGIN_ROOT/scripts/fda_data_store.py" \
  --project "$PROJECT_NAME" \
  --query events \
  --product-code "$PREDICATE_PRODUCT_CODE" \
  --count event_type.exact
```

The recall output includes TOTAL_RECALLS, ACTIVE_RECALLS, CLASS_I/II/III counts.
The event output includes TOTAL_EVENTS, DEATHS, INJURIES, MALFUNCTIONS.

Apply points: Clean → 10pts, Minor concerns → 5pts, Major concerns → 0pts.

### 3F: Predicate Legal Status Verification

**CRITICAL**: Verify each predicate candidate has not had its clearance withdrawn or been subject to an enforcement action that would make it legally unmarketable.

```bash
# For each unique product code among the predicate candidates:
python3 "$FDA_PLUGIN_ROOT/scripts/fda_data_store.py" \
  --project "$PROJECT_NAME" \
  --query enforcement \
  --product-code "$PREDICATE_PRODUCT_CODE"
```

**Deliberation:** If `SHOWING:X_OF:Y` where Y > X, note to the user that additional enforcement results exist beyond the returned batch and offer to fetch more if the initial results don't contain the expected data.

If enforcement action found with `classification: "Class I"` or `status: "Ongoing"`: Flag `ENFORCEMENT_ACTION`.
If any predicate's clearance has been revoked or withdrawn (check enforcement `reason_for_recall` for "withdrawal" or "revocation" language): Flag `WITHDRAWN`. A withdrawn predicate is **NOT legally marketed** and cannot serve as a valid predicate device.

### 3G: Check Exclusion List

```bash
python3 << 'PYEOF'
import json, os, re

# Read exclusion list path from settings
settings_path = os.path.expanduser('~/.claude/fda-tools.local.md')
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

### 3.5: Web-Based Predicate Validation

**NEW ENHANCEMENT**: Comprehensive validation against FDA web sources (recalls, enforcement, warning letters).

Run the web validator on all unique predicate candidates:

```bash
# Collect all unique K-numbers from predicate candidates
UNIQUE_KNUMBERS=$(python3 << 'PYEOF'
import sys, json

# Load extraction results (from Step 1)
# Extract unique K-numbers from predicates and references
knumbers = set()
# ... collect from parsed output.csv ...
print(','.join(sorted(knumbers)))
PYEOF
)

# Run web validation
python3 "$FDA_PLUGIN_ROOT/scripts/web_predicate_validator.py" \
  --k-numbers "$UNIQUE_KNUMBERS" \
  --format json > "$PROJECTS_DIR/$PROJECT_NAME/web_validation.json"
```

Parse the validation results:

```python
import json

with open(f'{project_dir}/web_validation.json') as f:
    validation = json.load(f)

for k_number, result in validation.items():
    flag = result['flag']  # 'GREEN', 'YELLOW', or 'RED'
    rationale = result['rationale']  # List of reasons

    # Apply validation scoring:
    if flag == 'RED':
        # Class I recall, withdrawn, or active enforcement
        # AUTO-REJECT in --full-auto mode
        # In interactive mode, warn user prominently
        validation_score = -50  # Penalty to push below acceptance threshold
    elif flag == 'YELLOW':
        # Class II recall, >10 years old, minor enforcement
        validation_score = -10  # Minor penalty
    else:  # GREEN
        validation_score = 0  # No penalty

    # Store in predicate data
    predicate_data[k_number]['web_validation'] = {
        'flag': flag,
        'rationale': rationale,
        'score_adjustment': validation_score,
        'recalls': result.get('recalls', []),
        'enforcement_actions': result.get('enforcement_actions', []),
        'warning_letters': result.get('warning_letters', [])
    }
```

**Important**: RED-flagged predicates should be automatically rejected in `--full-auto` mode and prominently warned in interactive mode.

### 3.6: FDA Predicate Criteria Compliance Check

**NEW ENHANCEMENT**: Systematic verification against FDA's 2014 guidance criteria.

Apply the compliance checklist from `references/fda-predicate-criteria-2014.md`:

```python
def check_fda_predicate_criteria(k_number, subject_ifu, subject_product_code, predicate_data):
    """
    Verify predicate meets FDA selection criteria per 510(k) Program (2014) Section IV.B

    Returns: {compliant: bool, flags: [issues], rationale: str}
    """
    flags = []
    compliant = True

    # Criterion 1: Legally Marketed
    web_val = predicate_data.get('web_validation', {})
    if web_val.get('flag') == 'RED':
        if 'withdrawn' in str(web_val.get('rationale', [])).lower():
            flags.append('WITHDRAWN — Not legally marketed')
            compliant = False

    # Criterion 2: Regulatory Pathway (510(k) only)
    if k_number.startswith('P'):
        flags.append('PMA_DEVICE — Cannot serve as 510(k) predicate')
        compliant = False
    elif k_number.startswith('H'):
        flags.append('HDE_DEVICE — Cannot serve as 510(k) predicate')
        compliant = False
    # De Novo (DEN) devices CAN serve as predicates

    # Criterion 3: Not Recalled (Class I = fail)
    recalls = web_val.get('recalls', [])
    class_i_recalls = [r for r in recalls if r.get('classification') == 'Class I']
    if class_i_recalls:
        flags.append(f'CLASS_I_RECALL — {len(class_i_recalls)} Class I recall(s)')
        compliant = False

    # Criterion 4: Same Intended Use
    # Compare IFU text from predicate PDF (if available) to subject IFU
    # For now, check product code as proxy
    pred_product_code = predicate_data.get('device_info', {}).get('product_code')
    if pred_product_code and pred_product_code != subject_product_code:
        # Different product code — may still be valid if same panel
        # Get panel from classification (if available)
        # For now, flag for manual review
        flags.append(f'DIFFERENT_PRODUCT_CODE — {pred_product_code} vs {subject_product_code}')
        # Don't auto-fail, but flag for review

    # Criterion 5: Same/Similar Technological Characteristics
    # This requires device description comparison — defer to manual review
    # Flag only if obvious mismatch (e.g., different energy source)

    if compliant:
        rationale = 'All FDA criteria met per 510(k) Program guidance (2014) Section IV.B'
    else:
        rationale = f"Failed FDA criteria: {', '.join(flags)}"

    return {
        'compliant': compliant,
        'flags': flags,
        'rationale': rationale,
        'citation': '510(k) Program (2014) Section IV.B; 21 CFR 807.92'
    }
```

Apply to each predicate:

```python
for k_number in predicate_candidates:
    compliance = check_fda_predicate_criteria(
        k_number,
        subject_device_ifu,
        subject_device_product_code,
        predicate_data[k_number]
    )

    predicate_data[k_number]['fda_criteria_compliance'] = compliance

    # Adjust scoring based on compliance
    if not compliance['compliant']:
        # Non-compliant predicates should be rejected
        predicate_data[k_number]['confidence_score'] = 0
        predicate_data[k_number]['auto_reject_reason'] = compliance['rationale']
```

**Integration with Scoring:**
- Non-compliant predicates → score = 0 (auto-reject)
- Compliant with flags → no penalty, but flag for review
- Fully compliant → no change

## Step 4: Apply Risk Flags

After scoring, apply risk flags per the definitions in `references/confidence-scoring.md`:

For each predicate candidate, check:

| Flag | Check |
|------|-------|
| `RECALLED` | Any recall found in Step 3E |
| `RECALLED_CLASS_I` | Class I recall found via `/device/enforcement` for same product code |
| `WITHDRAWN` | Clearance withdrawn or revoked per enforcement API |
| `ENFORCEMENT_ACTION` | Active enforcement action (warning letter, consent decree) against predicate applicant |
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

**Pre-validation:** Before scoring decisions, apply web validation and FDA criteria checks:

1. **RED-flagged predicates** (Class I recall, withdrawn, active enforcement):
   - AUTO-REJECT immediately regardless of score
   - Rationale: `"Auto-rejected (full-auto): {validation_rationale}"`

2. **Non-compliant with FDA criteria** (failed required criteria):
   - AUTO-REJECT immediately regardless of score
   - Rationale: `"Auto-rejected (full-auto): Failed FDA predicate criteria - {flags}"`

**Scoring decisions** (for predicates that pass validation):

- **Score >= {auto-threshold, default 70}**: Auto-accept with rationale `"Auto-accepted (full-auto, score >= {threshold})"`
- **Score 40 to {threshold-1}**: Auto-defer with rationale `"Auto-deferred for manual review (full-auto, ambiguous score {score})"`
- **Score < 40**: Auto-reject with rationale `"Auto-rejected (full-auto, low confidence score {score})"`

**Special cases:**

- **YELLOW-flagged predicates** (Class II recall, >10 years old):
  - Apply normal scoring thresholds
  - Add note to rationale: `"Note: YELLOW validation flag - {reason}"`

All auto-decisions are logged with `"auto_decision": true` in review.json.

Report full-auto results:
```
Full-Auto Review Results:
  Auto-accepted (score >= {threshold}): {N} predicates
  Auto-deferred (score 40-{threshold-1}): {N} predicates
  Auto-rejected (score < 40): {N} predicates
  Auto-rejected (RED validation flag): {N} predicates
  Auto-rejected (FDA criteria non-compliant): {N} predicates

  Web Validation Summary:
    ✓ GREEN (safe): {N}
    ⚠ YELLOW (review): {N}
    ✗ RED (avoid): {N}

  FDA Criteria Compliance:
    ✓ Compliant: {N}
    ⚠ Compliant with flags: {N}
    ✗ Non-compliant: {N}

  Total: {N} predicates processed with 0 user interactions
```

**CRITICAL**: When `--full-auto` is active, proceed directly to **Step 6: Write Outputs**. Do NOT enter the "Interactive review" subsection below. Do NOT present individual predicate cards. Do NOT call AskUserQuestion under any circumstances. All decisions have been made deterministically above.

### If NOT --full-auto mode: Interactive review

**IMPORTANT: This entire subsection is SKIPPED when `--full-auto` is active.** The `--full-auto` path above handles all decisions deterministically. Only enter this block for `--auto` (partial) or default (fully interactive) modes.

For each predicate that needs manual review (or all predicates if `--auto` not set), present:

```
  FDA Predicate Review Card
  K234567 — Score: 62/100 (Moderate)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DEVICE INFO
────────────────────────────────────────

  Device: {device_name} by {applicant}
  Product Code: {code} | Cleared: {date} | Review: {days} days
  Classification: Predicate → Uncertain (reclassified)

SCORE BREAKDOWN
────────────────────────────────────────

  Section Context:    10/40  (general text only)
  Citation Frequency: 15/20  (cited by 3 source documents)
  Product Code Match: 15/15  (same product code)
  Recency:           12/15  (cleared 4 years ago)
  Regulatory History: 10/10  (clean)

  Flags: OLD

VALIDATION STATUS (NEW)
────────────────────────────────────────

  Web Validation: ⚠ YELLOW (Class II recall 2023)
  FDA Criteria:   ✓ COMPLIANT (all criteria met)

  Recalls: 1 Class II recall (device label error, resolved)
  Enforcement: None
  Compliance: Meets all FDA predicate selection criteria per 2014 guidance

CONTEXT
────────────────────────────────────────

  - K241335: general text, paragraph about "prior art wound dressings..."
  - K251234: SE comparison section, row 3 of comparison table
  - K248765: general text, literature review section

  Original: Predicate (extraction script)
  Reclassified: Uncertain (SE section in 1/3 sources)

JUSTIFICATION
────────────────────────────────────────

  {Generated narrative — see algorithm below}
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

### Justification Narrative Algorithm

For each predicate, generate a 1-3 sentence justification narrative. This narrative is stored in `review.json` as `justification_narrative` and provides human-readable rationale.

**Sentence 1 — Overall Assessment (based on score tier):**
- Score 80-100: "{K-number} is a strong predicate candidate with high confidence ({score}/100)."
- Score 60-79: "{K-number} is a moderate predicate candidate ({score}/100) that warrants review."
- Score 40-59: "{K-number} is a marginal predicate candidate ({score}/100) with limited supporting evidence."
- Score 20-39: "{K-number} is a weak candidate ({score}/100) and likely not a true predicate."
- Score 0-19: "{K-number} should be rejected ({score}/100) — insufficient evidence for predicate status."

**Sentence 2 — Top Contributing Factors (pick top 2 by points):**
Template phrases per scoring component:
- Section Context (high): "Found in {N} SE comparison sections, indicating direct predicate citation."
- Section Context (low): "Found only in general text, suggesting incidental mention."
- Citation Frequency (high): "Cited by {N} different source documents, establishing broad recognition."
- Citation Frequency (low): "Cited by only {N} source, requiring manual verification."
- Product Code Match: "Shares product code {CODE} with the subject device." / "Different product code ({CODE}) — may be a reference device."
- Recency (high): "Cleared {N} years ago, representing current technology." / Recency (low): "Cleared {N} years ago — consider finding a more recent alternative."
- Regulatory History (clean): "Clean regulatory record with no recalls or safety signals." / (concerns): "Has {concerns} — evaluate risk to predicate chain."

**Sentence 3 — Risk Flag Caveat (optional, only if flags present):**
- "Note: {flag descriptions, e.g., 'RECALLED (Class II, 2024), OLD (>10 years)'}"

**Generate narrative in all modes** (interactive, auto, full-auto). Store as `justification_narrative` field in review.json alongside each predicate entry.

## Audit Logging

After all predicate decisions are made, write audit log entries using `fda_audit_logger.py`.

### Log each predicate decision

For **each** predicate that was accepted, rejected, or deferred, run:

```bash
# Build exclusion JSON from the rejected alternatives in this review session
# EXCLUSIONS_JSON should be a JSON object mapping rejected K-numbers to reasons
# e.g., '{"K222222":"Different product code (KGN), score 35","K111111":"Class I recall 2024, score 12"}'

# ALTERNATIVES_JSON should list ALL predicates evaluated (including the chosen one)
# e.g., '["K241335","K222222","K111111"]'

AUDIT_OUTPUT=$(python3 "$FDA_PLUGIN_ROOT/scripts/fda_audit_logger.py" \
  --project "$PROJECT_NAME" \
  --command review \
  --action predicate_accepted \
  --subject "$K_NUMBER" \
  --decision accepted \
  --confidence "$SCORE" \
  --mode "$REVIEW_MODE" \
  --decision-type "$DECISION_TYPE" \
  --rationale "$JUSTIFICATION_NARRATIVE" \
  --data-sources "output.csv,openFDA 510k API,openFDA recall API" \
  --alternatives "$ALTERNATIVES_JSON" \
  --exclusions "$EXCLUSIONS_JSON" \
  --metadata "{\"score_breakdown\":{\"section_context\":$SC,\"citation_frequency\":$CF,\"product_code_match\":$PCM,\"recency\":$REC,\"regulatory_history\":$RH}}" \
  --files-written "$PROJECTS_DIR/$PROJECT_NAME/review.json")
AUDIT_ENTRY_ID=$(echo "$AUDIT_OUTPUT" | grep "AUDIT_ENTRY_ID:" | cut -d: -f2)
# Store $AUDIT_ENTRY_ID — write it into the predicate's review.json entry as "audit_entry_id"
```

Use `predicate_rejected` or `predicate_deferred` for the corresponding decisions. The `--decision-type` should be `auto` for `--full-auto` mode, `manual` for interactive decisions, and `deferred` for deferred predicates.

### Log reclassifications

For each reclassified predicate:

```bash
python3 "$FDA_PLUGIN_ROOT/scripts/fda_audit_logger.py" \
  --project "$PROJECT_NAME" \
  --command review \
  --action predicate_reclassified \
  --subject "$K_NUMBER" \
  --decision "$NEW_CLASSIFICATION" \
  --mode "$REVIEW_MODE" \
  --rationale "Reclassified from $ORIGINAL to $NEW_CLASSIFICATION based on SE section context"
```

### Log review completion

After all decisions:

```bash
python3 "$FDA_PLUGIN_ROOT/scripts/fda_audit_logger.py" \
  --project "$PROJECT_NAME" \
  --command review \
  --action review_completed \
  --decision "completed" \
  --mode "$REVIEW_MODE" \
  --rationale "Review complete: $ACCEPTED accepted, $REJECTED rejected, $DEFERRED deferred, $RECLASSIFIED reclassified" \
  --metadata "{\"accepted\":$ACCEPTED,\"rejected\":$REJECTED,\"deferred\":$DEFERRED,\"reclassified\":$RECLASSIFIED}" \
  --files-written "$PROJECTS_DIR/$PROJECT_NAME/review.json,$PROJECTS_DIR/$PROJECT_NAME/output_reviewed.csv"
```

## Step 5: RA Professional Final Review

**IMPORTANT**: After all predicate decisions are made (accepted/rejected/deferred), invoke the RA professional advisor agent for final regulatory sign-off before writing outputs. This step ensures the final predicate selection meets FDA compliance standards and provides a professional regulatory rationale for audit defense.

### When to invoke RA final review

Invoke RA advisor when:
- User has made all predicate accept/reject decisions (interactive or --full-auto mode)
- At least 1 predicate was accepted
- Project is intended for actual FDA submission (not just exploratory research)

**Skip this step for**:
- `--dry-run` mode
- Projects with 0 accepted predicates
- Quick exploratory reviews

### RA Advisor Final Review Scope

The RA advisor performs final regulatory sign-off on:

1. **Accepted Predicates Compliance**
   - Do all accepted predicates meet FDA predicate selection criteria (21 CFR 807.92)?
   - Are predicates legally marketed, not recalled (verified via web validation)?
   - Do accepted predicates support the intended SE pathway?
   - Any predicates with YELLOW or RED validation flags that need mitigation?

2. **Rejected Predicates Rationale**
   - Are rejection rationales defensible in FDA review?
   - Were any borderline predicates rejected that should have been reconsidered?
   - Is the rejection of different-product-code predicates appropriate?

3. **FDA Criteria Compliance Verification**
   - Verify all 5 FDA predicate criteria met for each accepted predicate:
     1. Legally marketed in U.S.
     2. 510(k) pathway (not PMA/HDE)
     3. Not recalled or NSE
     4. Same intended use as subject device
     5. Same/similar technological characteristics
   - Flag any accepted predicates that don't meet all 5 criteria

4. **Risk Assessment**
   - Overall predicate chain health (recalls, chain depth, age)
   - Testing strategy gaps from accepted predicates
   - Novel features with thin precedent
   - Regulatory risks that require Pre-Submission discussion

5. **Professional Sign-Off or Escalation**
   - **GREEN Sign-Off**: Accepted predicates are defensible, proceed with SE comparison
   - **YELLOW Review Required**: Minor concerns, specific mitigations recommended
   - **RED Escalation**: Major regulatory risks, recommend Pre-Submission or pathway reconsideration

### How to invoke RA advisor

```bash
# Create RA final review context file
cat << 'EOF' > "$PROJECTS_DIR/$PROJECT_NAME/ra_final_review_context.json"
{
  "stage": "final_predicate_approval",
  "product_code": "$PRODUCT_CODE",
  "device_name": "$DEVICE_NAME",
  "review_mode": "$REVIEW_MODE",
  "summary": {
    "total_evaluated": $TOTAL_PREDICATES,
    "accepted": $ACCEPTED,
    "rejected": $REJECTED,
    "deferred": $DEFERRED,
    "reclassified": $RECLASSIFIED
  },
  "accepted_predicates": [
    {
      "k_number": "K123456",
      "score": 92,
      "classification": "Predicate",
      "web_validation": {
        "flag": "GREEN",
        "rationale": []
      },
      "fda_criteria_compliance": {
        "compliant": true,
        "flags": []
      },
      "decision_rationale": "Strong predicate with SE section citations...",
      "risk_flags": []
    }
  ],
  "rejected_predicates": [
    {
      "k_number": "K234567",
      "score": 35,
      "reason": "Different product code (KGN), only found in general text",
      "web_validation": {
        "flag": "YELLOW",
        "rationale": ["Class II recall 2023"]
      }
    }
  ],
  "overall_validation_summary": {
    "green": 5,
    "yellow": 2,
    "red": 1
  },
  "compliance_summary": {
    "compliant": 6,
    "compliant_with_flags": 1,
    "non_compliant": 1
  }
}
EOF

# Invoke RA advisor agent with Task tool
```

Use the Task tool to launch the `ra-professional-advisor` agent with this prompt:

```
Perform final regulatory sign-off for 510(k) predicate selection:

Context file: $PROJECTS_DIR/$PROJECT_NAME/ra_final_review_context.json

Your final review must verify:
1. All accepted predicates meet FDA predicate selection criteria (21 CFR 807.92, 510(k) Program 2014 Section IV.B)
2. Web validation flags (YELLOW/RED) have appropriate mitigation
3. FDA criteria compliance verified for all accepted predicates
4. Rejection rationales are defensible in FDA review
5. Overall predicate strategy supports SE pathway

Provide professional sign-off:
- **Sign-Off Level**: GREEN (proceed) | YELLOW (review required) | RED (escalate)
- **FDA Criteria Verification**: List any compliance concerns
- **Risk Mitigation**: Specific actions required for YELLOW/RED predicates
- **Regulatory Rationale**: Professional justification for acceptance decisions
- **Pre-Submission Recommendation**: Yes/No + specific discussion topics

Expected output: Professional RA sign-off suitable for regulatory audit defense.
```

### Integrate RA final review into review.json

After RA advisor completes final review, add findings to review.json:

```json
{
  "ra_final_review": {
    "reviewed_at": "2026-02-13T16:30:00Z",
    "sign_off_level": "GREEN|YELLOW|RED",
    "fda_criteria_verified": true|false,
    "compliance_concerns": [
      {
        "k_number": "K234567",
        "concern": "YELLOW validation flag (Class II recall)",
        "mitigation": "Verify recall was addressed, document in SE justification"
      }
    ],
    "regulatory_rationale": "All accepted predicates meet FDA predicate selection criteria per 21 CFR 807.92 and 510(k) Program (2014) Section IV.B. Predicates are legally marketed, not subject to Class I recalls, and support SE determination for the subject device.",
    "risk_assessment": "Low regulatory risk. Primary predicate (K241335) has clean record and recent clearance. Secondary predicate (K234567) has resolved Class II recall but provides strong technological precedent.",
    "recommended_actions": [
      "Proceed with formal SE comparison (/fda:compare-se)",
      "Document Class II recall mitigation in SE justification",
      "Include predicate testing data in submission"
    ],
    "presub_meeting": {
      "recommended": false,
      "rationale": "SE pathway is clear with strong predicate precedent. No novel features requiring FDA pre-clearance discussion."
    },
    "professional_sign_off": "Accepted predicates are defensible and meet FDA standards. Proceed with 510(k) submission preparation.",
    "ra_citation": "21 CFR 807.92, FDA Guidance 'The 510(k) Program: Evaluating Substantial Equivalence' (2014) Section IV.B"
  }
}
```

### Display RA final review in output

Present RA final review to user:

```
RA PROFESSIONAL FINAL REVIEW
────────────────────────────────────────

Sign-Off Level: ✓ GREEN (Proceed with SE Comparison)

FDA Criteria Verified: ✓ All accepted predicates compliant

{If YELLOW or RED sign-off:}
Compliance Concerns:
  • K234567: YELLOW validation flag (Class II recall 2023)
    → Mitigation: Verify recall resolved, document in SE justification

Regulatory Rationale:
  {RA advisor's professional justification}

Risk Assessment: {Low|Medium|High} regulatory risk
  {RA advisor's risk summary}

Recommended Actions:
  1. {Action 1}
  2. {Action 2}

Pre-Submission Meeting: {Recommended|Optional|Not Needed}
  {Rationale}

Professional Sign-Off:
  "{RA advisor's final statement}"

  Citation: 21 CFR 807.92, FDA Guidance "The 510(k) Program" (2014) Section IV.B

────────────────────────────────────────
```

### Fallback if RA advisor unavailable

If Task tool fails or RA advisor unavailable:

1. Skip this step (do not block review completion)
2. Add warning to review.json:
   ```json
   {
     "ra_final_review": {
       "status": "not_performed",
       "warning": "RA professional review was not completed. Verify accepted predicates meet FDA criteria (21 CFR 807.92) before proceeding.",
       "recommendation": "Consult regulatory affairs professional to verify predicate selection defensibility."
     }
   }
   ```
3. Display warning to user:
   ```
   ⚠ RA Professional Review Not Completed

   Before proceeding with SE comparison, verify:
   - All accepted predicates meet FDA predicate selection criteria
   - Web validation flags (YELLOW/RED) are addressed
   - FDA criteria compliance confirmed for each predicate

   See plugins/fda-tools/references/fda-predicate-criteria-2014.md
   ```

### Audit logging

```bash
python3 "$FDA_PLUGIN_ROOT/scripts/fda_audit_logger.py" \
  --project "$PROJECT_NAME" \
  --command review \
  --action ra_final_review_completed \
  --decision "{sign_off_level}" \
  --mode "$REVIEW_MODE" \
  --rationale "{RA advisor's sign-off statement}" \
  --metadata "{\"sign_off_level\":\"$SIGN_OFF_LEVEL\",\"compliance_verified\":$COMPLIANCE_BOOL,\"presub_recommended\":$PRESUB_BOOL,\"concerns_count\":$CONCERN_COUNT}"
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
      "web_validation": {
        "flag": "GREEN",
        "rationale": ["No enforcement actions or recalls found"],
        "score_adjustment": 0,
        "recalls": [],
        "enforcement_actions": [],
        "warning_letters": []
      },
      "fda_criteria_compliance": {
        "compliant": true,
        "flags": [],
        "rationale": "All FDA criteria met per 510(k) Program guidance (2014) Section IV.B",
        "citation": "510(k) Program (2014) Section IV.B; 21 CFR 807.92"
      },
      "original_classification": "Predicate",
      "reclassification": "Predicate",
      "auto_decision": false,
      "justification_narrative": "K234567 is a strong predicate candidate with high confidence (85/100). Found in 2 SE comparison sections, indicating direct predicate citation. Cited by 3 different source documents, establishing broad recognition.",
      "audit_entry_id": "a1b2c3d4",
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
  FDA Predicate Review Summary
  Project: {name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: {date} | v5.22.0

RESULTS
────────────────────────────────────────

  Accepted predicates:     8
  Rejected (reference):    4
  Rejected (noise):        1
  Deferred:                2
  Reclassified:            3 (2 upgraded, 1 downgraded)

TOP ACCEPTED PREDICATES
────────────────────────────────────────

  | # | K-Number | Score | Device | Applicant |
  |---|----------|-------|--------|-----------|
  | 1 | K241335  | 92/100 (Strong) | Collagen Wound Dressing | COMPANY A |
  | 2 | K238901  | 87/100 (Strong) | Foam Dressing | COMPANY B |
  | 3 | K225678  | 85/100 (Strong) | Antimicrobial Dressing | COMPANY C |

RISK FLAGS
────────────────────────────────────────

  RECALLED: 1 device (K111111 — excluded)
  OLD: 3 devices (all >10 years)
  HIGH_MAUDE: 0

FILES WRITTEN
────────────────────────────────────────

  review.json          — Full review data with scores and decisions
  output_reviewed.csv  — Reclassified output with confidence column

NEXT STEPS
────────────────────────────────────────

  1. Build SE comparison table — `/fda:compare-se --predicates K241335,K238901`
  2. Look up guidance documents — `/fda:guidance {PRODUCT_CODE}`
  3. Review deferred predicates when more data is available

────────────────────────────────────────
  This report is AI-generated from public FDA data.
  Verify independently. Not regulatory advice.
────────────────────────────────────────
```

## Step 8: Predicate Diversity Analysis (Sprint 6 - NEW)

After predicate review is complete, analyze the diversity of accepted predicates to identify "echo chamber" risk (where all predicates are too similar).

**Purpose:** Ensure SE argument strength through diverse predicate set. FDA may question submissions where all predicates share the same manufacturer, technology, or narrow time range.

### Run Diversity Analysis

```bash
python3 << 'PYEOF'
import json
import os
import sys
import re

# Add lib directory to Python path
plugin_root = os.environ.get('FDA_PLUGIN_ROOT', '')
if not plugin_root:
    installed_plugins_path = os.path.expanduser('~/.claude/plugins/installed_plugins.json')
    if os.path.exists(installed_plugins_path):
        with open(installed_plugins_path) as ipf:
            installed_data = json.load(ipf)
            for key, value in installed_data.get('plugins', {}).items():
                if key.startswith('fda-tools@') or key.startswith('fda-tools@'):
                    for entry in value:
                        install_path = entry.get('installPath', '')
                        if os.path.isdir(install_path):
                            plugin_root = install_path
                            break
                if plugin_root:
                    break

if plugin_root:
    sys.path.insert(0, os.path.join(plugin_root, 'lib'))

from predicate_diversity import PredicateDiversityAnalyzer

# Load review.json to get accepted predicates
settings_path = os.path.expanduser('~/.claude/fda-tools.local.md')
projects_dir = os.path.expanduser('~/fda-510k-data/projects')
if os.path.exists(settings_path):
    with open(settings_path) as f:
        m = re.search(r'projects_dir:\s*(.+)', f.read())
        if m:
            projects_dir = os.path.expanduser(m.group(1).strip())

project = "PROJECT"  # Replace with actual project name
pdir = os.path.join(projects_dir, project)

review_path = os.path.join(pdir, 'review.json')
if not os.path.exists(review_path):
    print("DIVERSITY_ANALYSIS:SKIPPED - review.json not found")
    sys.exit(0)

with open(review_path) as f:
    review_data = json.load(f)

# Extract accepted predicates only
accepted_predicates = [
    p for p in review_data.get('predicates', [])
    if p.get('decision') == 'accept'
]

if len(accepted_predicates) == 0:
    print("DIVERSITY_ANALYSIS:SKIPPED - no accepted predicates")
    sys.exit(0)

print(f"DIVERSITY_ANALYSIS:RUNNING - {len(accepted_predicates)} accepted predicates")

# Run diversity analysis
analyzer = PredicateDiversityAnalyzer(accepted_predicates)
diversity_report = analyzer.analyze()

# Display scorecard
print("\n" + "="*60)
print("PREDICATE DIVERSITY SCORECARD")
print("="*60)
print(f"\nTotal Score: {diversity_report['total_score']}/100 ({diversity_report['grade']})\n")

print(f"Manufacturer Diversity: {diversity_report['manufacturer_score']}/30")
print(f"  {diversity_report['unique_manufacturers']} manufacturers: {', '.join(diversity_report['manufacturer_list'][:5])}")
if len(diversity_report['manufacturer_list']) > 5:
    print(f"    (+ {len(diversity_report['manufacturer_list']) - 5} more)")

print(f"\nTechnology Diversity: {diversity_report['technology_score']}/30")
print(f"  {diversity_report['unique_technologies']} technologies: {', '.join(diversity_report['technology_list'][:5])}")
if len(diversity_report['technology_list']) > 5:
    print(f"    (+ {len(diversity_report['technology_list']) - 5} more)")

print(f"\nAge Diversity: {diversity_report['age_score']}/25")
if diversity_report['most_recent_year']:
    print(f"  Clearance year span: {diversity_report['clearance_year_span']} years ({diversity_report['oldest_year']}-{diversity_report['most_recent_year']})")
    print(f"  Most recent: {diversity_report['most_recent_year']}")
else:
    print(f"  No clearance date data available")

print(f"\nRegulatory Pathway: {diversity_report['pathway_score']}/10")
print(f"Geographic Diversity: {diversity_report['geographic_score']}/10")

print(f"\nGRADE: {diversity_report['grade']}")

# Show warning for poor diversity
if diversity_report['grade'] in ['POOR', 'FAIR']:
    print("\n⚠️  WARNING: Weak predicate diversity may result in FDA questions")

# Show recommendations
if diversity_report['recommendations']:
    print("\nRECOMMENDATIONS:")
    for i, rec in enumerate(diversity_report['recommendations'], 1):
        print(f"  {i}. {rec}")

# Suggest specific actions for improvement
if diversity_report['total_score'] < 60:
    print("\nSUGGESTED ACTIONS TO IMPROVE DIVERSITY:")

    # Get product code from first predicate
    product_code = accepted_predicates[0].get('product_code', 'UNKNOWN')

    if diversity_report['manufacturer_score'] < 20:
        current_mfrs = diversity_report['manufacturer_list']
        print(f"  - Run: /fda:batchfetch --product-code {product_code} --manufacturer '<different manufacturer>'")
        print(f"    Current manufacturers: {', '.join(current_mfrs)}")
        print(f"    Look for: Competing manufacturers in same device category")

    if diversity_report['technology_score'] < 20:
        current_tech = diversity_report['technology_list'][0] if diversity_report['technology_list'] else 'generic'
        print(f"  - Look for predicates with different technology approach")
        print(f"    Current technology: {current_tech}")
        print(f"    Consider: Different materials, coatings, or mechanisms")

    if diversity_report['age_score'] < 15:
        most_recent = diversity_report.get('most_recent_year')
        oldest = diversity_report.get('oldest_year')
        if most_recent and oldest:
            print(f"  - Include predicates spanning wider time range")
            print(f"    Current range: {oldest}-{most_recent} ({diversity_report['clearance_year_span']} years)")
            print(f"    Recommended: 5+ year span for historical context")

print("\n" + "="*60)

# Save diversity report to review.json
review_data['predicate_diversity'] = diversity_report

with open(review_path, 'w') as f:
    json.dump(review_data, f, indent=2)

print(f"\nDIVERSITY_REPORT:SAVED to review.json")

PYEOF
```

### Diversity Scorecard Interpretation

**Grading Scale:**
- **80-100 (EXCELLENT):** Strong diversity across all dimensions, low echo chamber risk
- **60-79 (GOOD):** Adequate diversity, minor improvements possible
- **40-59 (FAIR):** Moderate diversity concerns, consider adding more diverse predicates
- **0-39 (POOR):** High echo chamber risk, FDA may question SE argument strength

**Scoring Breakdown:**

1. **Manufacturer Diversity (0-30 points)**
   - 1 manufacturer: 0 points ❌ CRITICAL RISK
   - 2 manufacturers: 10 points ⚠️ MODERATE
   - 3 manufacturers: 20 points ✅ GOOD
   - 4+ manufacturers: 30 points ✅ EXCELLENT

2. **Technology Diversity (0-30 points)**
   - 1 technology type: 0 points ❌ CRITICAL RISK
   - 2 technology types: 10 points ⚠️ MODERATE
   - 3 technology types: 20 points ✅ GOOD
   - 4+ technology types: 30 points ✅ EXCELLENT

3. **Age Diversity (0-25 points)**
   - Base score (0-15): Year span from oldest to newest predicate
   - Recency bonus (+10): Most recent predicate within last 2 years
   - Goal: 5+ year span with recent predicates

4. **Regulatory Pathway (0-10 points)**
   - Mix of Traditional, Special, Abbreviated 510(k), De Novo: 10 points
   - Single pathway: 0 points

5. **Geographic Diversity (0-10 points)**
   - 2+ countries: 10 points
   - Single country: 0 points

### Example Output (Poor Diversity)

```
============================================================
PREDICATE DIVERSITY SCORECARD
============================================================

Total Score: 20/100 (POOR)

Manufacturer Diversity: 0/30
  1 manufacturers: Boston Scientific

Technology Diversity: 0/30
  1 technologies: drug-eluting

Age Diversity: 10/25
  Clearance year span: 2 years (2021-2023)
  Most recent: 2023

Regulatory Pathway: 0/10
Geographic Diversity: 10/10

GRADE: POOR

⚠️  WARNING: Weak predicate diversity may result in FDA questions

RECOMMENDATIONS:
  1. CRITICAL: Add predicate from different manufacturer (avoid echo chamber risk)
    → Current manufacturer: Boston Scientific
    → Search for predicates from competing manufacturers (Boston Scientific, Medtronic, Abbott, etc.)
  2. CRITICAL: Add predicate with different technology approach
    → Current technology: drug-eluting
    → Consider predicates with different materials, coatings, or mechanisms
  3. MAJOR: Expand clearance date range (current span: 2 years)
    → Include predicates spanning wider time range (5+ years recommended)
    → Most recent: 2023, consider adding older predicates for historical context

SUGGESTED ACTIONS TO IMPROVE DIVERSITY:
  - Run: /fda:batchfetch --product-code DQY --manufacturer '<different manufacturer>'
    Current manufacturers: Boston Scientific
    Look for: Competing manufacturers in same device category
  - Look for predicates with different technology approach
    Current technology: drug-eluting
    Consider: Different materials, coatings, or mechanisms
  - Include predicates spanning wider time range
    Current range: 2021-2023 (2 years)
    Recommended: 5+ year span for historical context

============================================================

DIVERSITY_REPORT:SAVED to review.json
```

### Example Output (Excellent Diversity)

```
============================================================
PREDICATE DIVERSITY SCORECARD
============================================================

Total Score: 90/100 (EXCELLENT)

Manufacturer Diversity: 30/30
  4 manufacturers: Abbott, Boston Scientific, Cook Medical, Medtronic

Technology Diversity: 30/30
  5 technologies: bare-metal, coated, drug-eluting, manual, single-use

Age Diversity: 20/25
  Clearance year span: 7 years (2017-2024)
  Most recent: 2024

Regulatory Pathway: 10/10
Geographic Diversity: 0/10

GRADE: EXCELLENT

RECOMMENDATIONS:
  1. Excellent predicate diversity - no improvements needed

============================================================

DIVERSITY_REPORT:SAVED to review.json
```

### Integration with Step 7 Summary

Update the post-review summary to include diversity score:

```
  FDA Predicate Review Summary
  Project: {name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: {date} | v5.22.0

RESULTS
────────────────────────────────────────

  Accepted predicates:     8
  Rejected (reference):    4
  Rejected (noise):        1
  Deferred:                2
  Reclassified:            3 (2 upgraded, 1 downgraded)

PREDICATE DIVERSITY
────────────────────────────────────────

  Diversity Score:  {score}/100 ({grade})
  Manufacturers:    {n} unique
  Technology Types: {n} unique
  Year Span:        {n} years ({oldest}-{newest})

  {If POOR or FAIR grade:}
  ⚠️  WARNING: Weak diversity - consider adding more diverse predicates

TOP ACCEPTED PREDICATES
────────────────────────────────────────

  | # | K-Number | Score | Device | Applicant |
  |---|----------|-------|--------|-----------|
  | 1 | K241335  | 92/100 (Strong) | Collagen Wound Dressing | COMPANY A |
  | 2 | K238901  | 87/100 (Strong) | Foam Dressing | COMPANY B |
  | 3 | K225678  | 85/100 (Strong) | Antimicrobial Dressing | COMPANY C |

NEXT STEPS
────────────────────────────────────────

  1. Build SE comparison table — `/fda:compare-se --predicates K241335,K238901`
  2. Look up guidance documents — `/fda:guidance {PRODUCT_CODE}`
  {If diversity score < 60:}
  3. Improve predicate diversity — see recommendations in diversity scorecard above
```

## Error Handling

- **No output.csv found**: "No extraction results found for project '{name}'. Run `/fda:extract both --project {name}` first."
- **No PDF text cache**: "PDF text cache not found. Review will score using database records only (section context scoring unavailable — all devices get 10/40 for section context)."
- **API unavailable**: "openFDA API unavailable. Regulatory history scoring defaults to 5/10 for all devices. Recall and MAUDE flags will not be applied."
- **Empty extraction results**: "output.csv contains no predicate or reference devices. Nothing to review."
