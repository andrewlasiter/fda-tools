---
description: Trace predicate citation chains across generations of 510(k) clearances — visualize lineage, flag recalled ancestors, and score chain health
allowed-tools: Bash, Read, Glob, Grep, Write, WebFetch
argument-hint: "--predicates K241335[,K234567] [--generations 3] [--project NAME] [--output FILE]"
---

# FDA Predicate Lineage Analysis

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

---

You are tracing predicate citation chains across multiple generations of 510(k) clearances. This reveals how predicate relationships propagate through device families and identifies safety signals in the lineage.

**KEY PRINCIPLE: No competitor platform does this well — this is our unique differentiator.** Predicate networks are critical for understanding regulatory risk (per Lancet Digital Health research on 510(k) predicate networks).

## Parse Arguments

From `$ARGUMENTS`, extract:

- `--predicates K123456[,K234567]` (required unless --infer) — Starting predicate(s) to trace
- `--generations N` (default: 3) — How many generations back to trace (max 5)
- `--project NAME` — Use data from a specific project folder; save results there
- `--infer` — Auto-detect predicates from project review.json
- `--output FILE` — Write lineage data to file (default: lineage.json in project folder)
- `--product-code CODE` — Filter lineage to same product code family
- `--full-auto` — No user prompts; all decisions deterministic

If `--infer` AND `--project`:
1. Check review.json for accepted predicates → use all accepted
2. Check output.csv → use top cited predicates
3. If neither available: ERROR (don't prompt)

## Step 1: Build Generation 0 (Starting Devices)

For each starting predicate, query openFDA for its clearance data:

```bash
python3 << 'PYEOF'
import urllib.request, urllib.parse, json, os, re, time

settings_path = os.path.expanduser('~/.claude/fda-predicate-assistant.local.md')
api_key = os.environ.get('OPENFDA_API_KEY')
if os.path.exists(settings_path):
    with open(settings_path) as f:
        content = f.read()
    if not api_key:
        m = re.search(r'openfda_api_key:\s*(\S+)', content)
        if m and m.group(1) != 'null':
            api_key = m.group(1)

predicates = ["K241335"]  # Replace with actual

# Batch lookup: single OR query for all starting predicates (1 call instead of N)
batch_search = "+OR+".join(f'k_number:"{kn}"' for kn in predicates)
params = {"search": batch_search, "limit": str(len(predicates))}
if api_key:
    params["api_key"] = api_key
# Fix URL encoding: replace + with space before urlencode (openFDA expects + as spaces)
params["search"] = params["search"].replace("+", " ")
url = f"https://api.fda.gov/device/510k.json?{urllib.parse.urlencode(params)}"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/5.21.0)"})
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
        results_by_k = {r.get("k_number", ""): r for r in data.get("results", [])}
        for kn in predicates:
            r = results_by_k.get(kn)
            if r:
                print(f"GEN0:{kn}|{r.get('applicant','?')}|{r.get('device_name','?')}|{r.get('product_code','?')}|{r.get('decision_date','?')}")
            else:
                print(f"ERROR:{kn}:not_found")
except Exception as e:
    for kn in predicates:
        print(f"ERROR:{kn}:{e}")
PYEOF
```

## Step 2: Trace Upstream (Ancestors)

For each generation, find what predicates the current generation cited:

### Method 1: PDF Text Extraction (Best)

If PDF text is available (from project pdf_data.json or cache), extract cited K-numbers from each device's 510(k) summary PDF:

1. Download or load the PDF for each device in the current generation
2. Extract K/P/N numbers from the SE section using the **3-tier section detection system from `references/section-patterns.md`** — older (pre-2010) PDFs often have OCR-degraded headers that require Tier 2 correction
3. These are the device's predicates (generation N+1)

### Method 2: openFDA Cross-Reference (Fallback)

Query openFDA to find devices that cite the current generation device:

```bash
# Find what K-numbers the target device cited as predicates
# This requires PDF text — openFDA doesn't directly store predicate relationships
# Fallback: search for same product_code devices cleared just before this one
```

### Method 3: Flat File Lookup

Check if the predicate relationships are in the extraction output.csv from any project.

### Build the Chain

For each generation up to `--generations`:
1. Start with current generation devices
2. Extract their cited predicates (methods above)
3. Query openFDA for each ancestor's clearance data
4. Check for recalls on each ancestor
5. Move to next generation

## Step 3: Check Safety Signals

For each device in the lineage chain:

```bash
python3 << 'PYEOF'
import urllib.request, urllib.parse, json, os, re, time

# ... (standard API setup) ...

# Batch recall check: single OR query for all devices in the chain (1 call instead of N)
devices_to_check = ["K241335", "K200123", "K180456"]  # Replace
batch_search = "+OR+".join(f'k_numbers:"{kn}"' for kn in devices_to_check)
params = {"search": batch_search, "limit": "100"}
if api_key:
    params["api_key"] = api_key
# Fix URL encoding: replace + with space before urlencode
params["search"] = params["search"].replace("+", " ")
url = f"https://api.fda.gov/device/recall.json?{urllib.parse.urlencode(params)}"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/5.21.0)"})
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
        # Build map of K-number -> recall info
        recalled_kns = set()
        for r in data.get("results", []):
            for rk in r.get("k_numbers", []):
                if rk in devices_to_check:
                    recalled_kns.add(rk)
                    print(f"RECALLED:{rk}|{r.get('recall_status','?')}|{r.get('reason_for_recall','?')[:100]}")
        for kn in devices_to_check:
            if kn not in recalled_kns:
                print(f"CLEAN:{kn}")
except:
    for kn in devices_to_check:
        print(f"CHECK_FAILED:{kn}")
PYEOF
```

## Step 4: Score Chain Health

Calculate a "Chain Health Score" (0-100) based on:

| Factor | Points | Criteria |
|--------|--------|----------|
| No recalled/withdrawn ancestors | 30 | -10 per recalled ancestor, -20 for Class I recall, -30 for withdrawn clearance |
| Product code consistency | 20 | All ancestors share same product code |
| Chain depth available | 15 | Full chain traced (vs incomplete) |
| Recency | 15 | Average ancestor age <10 years |
| Clearance rate | 10 | No revoked/withdrawn ancestors |
| Single-ancestor avoidance | 10 | Not a single-thread chain (multiple paths) |

**Interpretation:**
- 80-100: Strong chain — low regulatory risk
- 50-79: Moderate chain — some concerns, discuss in Pre-Sub
- 0-49: Weak chain — high risk, consider alternative predicates

## Step 5: Generate Visualization

### Text Tree (always generated)

```
  FDA Predicate Lineage Report
  K241335 — Cervical Fusion Cage
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: {date} | Chain Health: 72/100 (Moderate) | v5.22.0

LINEAGE TREE
────────────────────────────────────────

K241335 (2024) — Cervical Fusion Cage — COMPANY A [CLEAN]
├── K200123 (2020) — Cervical Interbody Device — COMPANY B [CLEAN]
│   ├── K170456 (2017) — Cervical Cage — COMPANY C [RECALLED Class II]
│   │   └── K120789 (2012) — Spinal Fusion Device — COMPANY D [CLEAN]
│   └── K180999 (2018) — Cervical Fusion — COMPANY A [CLEAN]
│       └── K120789 (2012) — Spinal Fusion Device — COMPANY D [CLEAN]
└── K190555 (2019) — PEEK Cervical Cage — COMPANY E [CLEAN]
    └── K150333 (2015) — Cervical Interbody — COMPANY F [CLEAN]
        └── K100111 (2010) — Spinal Implant — COMPANY G [CLEAN]

  Legend: [CLEAN] = No recalls  [RECALLED Class X] = Recall found
          (YYYY) = Clearance year
```

### Lineage JSON (for programmatic use)

Write `lineage.json` to the project folder:

```json
{
  "version": 1,
  "generated_at": "2026-02-05T12:00:00Z",
  "starting_predicates": ["K241335"],
  "generations_traced": 3,
  "chain_health_score": 72,
  "chain_health_rating": "Moderate",
  "total_devices_in_chain": 8,
  "recalled_devices": 1,
  "nodes": {
    "K241335": {
      "generation": 0,
      "device_name": "Cervical Fusion Cage",
      "applicant": "COMPANY A",
      "product_code": "OVE",
      "decision_date": "20240315",
      "recalled": false,
      "predicates_cited": ["K200123", "K190555"]
    }
  },
  "edges": [
    {"from": "K241335", "to": "K200123", "relationship": "predicate"},
    {"from": "K241335", "to": "K190555", "relationship": "predicate"}
  ],
  "warnings": [
    "K170456: Class II recall found — device may fracture under load"
  ]
}
```

## Step 6: Recommendations

Based on the lineage analysis:

```
RECOMMENDATIONS
────────────────────────────────────────

  1. RECALLED ANCESTOR: K170456 (Gen 2) has a Class II recall.
     → Impact: This device is 2 generations removed from your predicate.
     → Action: Address the recall failure mode (fracture) in your testing plan.
     → Mention in Pre-Sub: Yes — FDA may ask about this.

  2. CHAIN DIVERSITY: Your predicate chain has 2 independent paths.
     → This is good — not a single-thread dependency.

  3. PRODUCT CODE: All ancestors share product code OVE.
     → Strong consistency — supports SE argument.

  4. AGE: Oldest ancestor is K100111 (2010, 16 years ago).
     → Consider if the technology has evolved significantly since then.

NEXT STEPS
────────────────────────────────────────

  1. Address recalled ancestor in testing plan — `/fda:test-plan`
  2. Discuss chain concerns in Pre-Sub — `/fda:presub`
  3. Run safety analysis on the product code — `/fda:safety --product-code OVE`

────────────────────────────────────────
  This report is AI-generated from public FDA data.
  Verify independently. Not regulatory advice.
────────────────────────────────────────
```

## Step 6.5: PMA Supplement Chain Tracing

When any P-number is encountered in the lineage (either as a starting predicate or discovered during tracing), trace its supplement chain:

```bash
python3 << 'PYEOF'
import urllib.request, urllib.parse, json, os, re, time

settings_path = os.path.expanduser('~/.claude/fda-predicate-assistant.local.md')
api_key = os.environ.get('OPENFDA_API_KEY')
if os.path.exists(settings_path):
    with open(settings_path) as f:
        content = f.read()
    if not api_key:
        m = re.search(r'openfda_api_key:\s*(\S+)', content)
        if m and m.group(1) != 'null':
            api_key = m.group(1)

pma_number = "P870024"  # Replace with actual P-number found in lineage
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
            supp = r.get("supplement_number", "")
            print(f"PMA_SUPP:{r.get('pma_number','?')}|{supp}|{r.get('supplement_type','')}|{r.get('trade_name','?')}|{r.get('decision_date','?')}|{r.get('decision_code','?')}")
except Exception as e:
    print(f"PMA_ERROR:{e}")
PYEOF
```

### PMA Lineage Visualization

Include PMA supplement chains alongside the 510(k) predicate tree:

```
PMA SUPPLEMENT CHAIN
────────────────────────────────────────

P870024 (1987) — Original PMA — {trade_name} — {applicant}
├── P870024/S001 (1988) — Labeling update
├── P870024/S015 (1995) — New indication
├── P870024/S042 (2005) — Design change
└── P870024/S099 (2023) — Manufacturing update
    Total supplements: {count}
    Active supplement types: {type distribution}
```

### Mixed 510(k)/PMA Lineage

When both K-numbers and P-numbers appear in the same lineage, visualize both chains:

```
LINEAGE TREE (Mixed 510(k) + PMA)
────────────────────────────────────────

K241335 (2024) — Cervical Fusion Cage — COMPANY A [CLEAN]
├── K200123 (2020) — Cervical Interbody — COMPANY B [CLEAN]
│   └── K170456 (2017) — Cervical Cage — COMPANY C [CLEAN]
└── P870024 (1987) — Original PMA [PMA - {trade_name}]
    └── {supplement_count} supplements through {latest_year}

Legend: [CLEAN] = No recalls  [PMA] = PMA approval (not 510(k))
```

## Error Handling

- **No predicates provided**: ERROR with usage example
- **API unavailable**: Attempt flat-file lookup. If no data: "Lineage tracing requires openFDA API or local extraction data. Enable API or run /fda:extract first."
- **Incomplete chain**: Report what was found. Note: "Chain incomplete at generation N — PDF text not available for {K-number}."
- **Circular reference**: Detect and break cycles. Note: "Circular predicate reference detected: {K1} → {K2} → {K1}."
