---
description: Recommend the optimal FDA regulatory pathway (Traditional/Special/Abbreviated 510(k), De Novo, PMA) with algorithmic scoring
allowed-tools: Bash, Read, Glob, Grep, WebSearch
argument-hint: "<product-code> [--device-description TEXT] [--novel-features TEXT] [--project NAME]"
---

# FDA Regulatory Pathway Recommendation Engine

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

You are recommending the optimal FDA regulatory pathway for a medical device based on algorithmic scoring.

## Parse Arguments

From `$ARGUMENTS`, extract:

- **Product code** (required) — 3-letter FDA product code
- `--device-description TEXT` — Description of the device
- `--novel-features TEXT` — Any novel technological features
- `--project NAME` — Use existing project data to inform recommendation
- `--own-predicate K123456` — If modifying your own previously cleared device
- `--infer` — Auto-detect product code from project data

If no product code and `--infer` active, use the same inference logic as other commands.

## Step 1: Gather Device Information

### Classification data

Query openFDA classification API (same pattern as other commands) to get:
- Device class (I, II, III)
- Regulation number
- Review panel
- Device name

### Project data (if --project provided)

Check for:
- review.json — predicate count, acceptance rate
- guidance_cache — guidance coverage
- output.csv — total clearances analyzed

### Predicate availability

```bash
python3 << 'PYEOF'
import urllib.request, urllib.parse, json, os, re, time

# Standard API key resolution
settings_path = os.path.expanduser('~/.claude/fda-predicate-assistant.local.md')
api_key = os.environ.get('OPENFDA_API_KEY')
if os.path.exists(settings_path):
    with open(settings_path) as f:
        content = f.read()
    if not api_key:
        m = re.search(r'openfda_api_key:\s*(\S+)', content)
        if m and m.group(1) != 'null':
            api_key = m.group(1)

product_code = "CODE"  # Replace
params = {"search": f'product_code:"{product_code}"', "limit": "1"}
if api_key:
    params["api_key"] = api_key

# Count total clearances
url = f"https://api.fda.gov/device/510k.json?{urllib.parse.urlencode(params)}"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/1.0)"})
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
        total = data.get("meta", {}).get("results", {}).get("total", 0)
        print(f"TOTAL_CLEARANCES:{total}")
except Exception as e:
    print(f"ERROR:{e}")

# Count recent clearances (last 5 years)
time.sleep(0.5)
params["search"] = f'product_code:"{product_code}"+AND+decision_date:[20210101+TO+29991231]'
url = f"https://api.fda.gov/device/510k.json?{urllib.parse.urlencode(params)}"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/1.0)"})
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
        recent = data.get("meta", {}).get("results", {}).get("total", 0)
        print(f"RECENT_CLEARANCES:{recent}")
except Exception as e:
    print(f"ERROR:{e}")
PYEOF
```

## Step 2: Score Each Pathway

Apply the scoring algorithm. Each pathway gets a score from 0-100:

### Traditional 510(k) Scoring

| Factor | Condition | Points |
|--------|-----------|--------|
| Predicate availability | Same product code predicates exist | +30 |
| Recent predicates | 3+ clearances in last 5 years | +20 |
| No novel technology | Device description has no novel features | +20 |
| Device class | Class II | +15 |
| Guidance exists | FDA guidance found for regulation | +15 |

### Special 510(k) Scoring

| Factor | Condition | Points |
|--------|-----------|--------|
| Own prior clearance | `--own-predicate` provided | +40 |
| Modification type | Description suggests modification | +30 |
| Design controls | Class II (design controls required) | +20 |
| No IFU change | Intended use unchanged | +10 |

### Abbreviated 510(k) Scoring

| Factor | Condition | Points |
|--------|-----------|--------|
| Strong guidance | Device-specific guidance exists | +40 |
| Consensus standards | Recognized standards cover key testing | +30 |
| Standard comparison | Straightforward predicate comparison | +20 |
| No clinical data | Clinical data not typically required | +10 |

### De Novo Scoring

| Factor | Condition | Points |
|--------|-----------|--------|
| No predicates | Zero or very few clearances for product code | +40 |
| Novel device | Novel features described | +30 |
| Low-moderate risk | Class I or II | +20 |
| De Novo granted | Could follow a De Novo-granted device as predicate | +10 |

### PMA Scoring

| Factor | Condition | Points |
|--------|-----------|--------|
| Class III | Device class is III | +40 |
| High risk | Life-sustaining or life-supporting | +30 |
| Clinical required | Clinical trial data clearly needed | +20 |
| No predicates | No suitable 510(k) predicates | +10 |

## Step 3: Present Recommendations

Rank pathways by score and present using the standard FDA Professional CLI format (see `references/output-formatting.md`):

```
  FDA Regulatory Pathway Recommendation
  {CODE} — {device_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: {date} | Class: {class} | 21 CFR {regulation} | v4.6.0

RECOMMENDED PATHWAY
────────────────────────────────────────

  {Top pathway} — Score: {score}/100 ({Rating})

  Rationale:
  - {bullet points explaining why this pathway scored highest}

  Estimated Timeline: {timeline}
  Estimated Review Fee: {fee range}

SCORE BREAKDOWN
────────────────────────────────────────

  {factor}: +{points} — {explanation}
  {factor}: +{points} — {explanation}

ALL PATHWAYS RANKED
────────────────────────────────────────

  | # | Pathway | Score | Key Factor | Timeline | Fee |
  |---|---------|-------|-----------|----------|-----|
  | 1 | {pathway} | {score}/100 ({Rating}) | {reason} | {time} | {fee} |
  | 2 | {pathway} | {score}/100 ({Rating}) | {reason} | {time} | {fee} |
  | 3 | {pathway} | {score}/100 ({Rating}) | {reason} | {time} | {fee} |
  | 4 | {pathway} | {score}/100 ({Rating}) | {reason} | {time} | {fee} |
  | 5 | {pathway} | {score}/100 ({Rating}) | {reason} | {time} | {fee} |

KEY CONSIDERATIONS
────────────────────────────────────────

  {pathway-specific considerations and risks}

NEXT STEPS
────────────────────────────────────────

  1. {Based on recommended pathway}
  2. {Specific actions}
  3. Confirm pathway with FDA — `/fda:presub {CODE}`

────────────────────────────────────────
  This report is AI-generated from public FDA data.
  Verify independently. Not regulatory advice.
────────────────────────────────────────
```

## Step 2.5: PMA Intelligence for Pathway Scoring

**If the openFDA API is available**, query the PMA endpoint to check if this product code has PMA history. PMA history is a strong signal for pathway scoring:

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

product_code = "CODE"  # Replace
params = {"search": f'product_code:"{product_code}"', "limit": "1"}
if api_key:
    params["api_key"] = api_key

# Count PMA approvals
url = f"https://api.fda.gov/device/pma.json?{urllib.parse.urlencode(params)}"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/4.7.0)"})
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
        total = data.get("meta", {}).get("results", {}).get("total", 0)
        print(f"PMA_COUNT:{total}")
        if data.get("results"):
            r = data["results"][0]
            print(f"PMA_RECENT:{r.get('pma_number','?')}|{r.get('trade_name','?')}|{r.get('decision_date','?')}")
except Exception as e:
    print(f"PMA_ERROR:{e}")
PYEOF
```

### PMA History Impact on Scoring

If `PMA_COUNT > 0`:
- **PMA pathway**: +15 bonus points (established PMA pathway for this product code)
- **Traditional 510(k)**: No change (510(k) and PMA can coexist for same product code)
- **De Novo**: -10 points (if PMA path exists, De Novo is less likely)

Include PMA context in the recommendations:

```
PMA PATHWAY CONTEXT
────────────────────────────────────────

  PMA History: {count} PMAs found for product code {CODE}
  Most Recent: {P-number} — {trade_name} ({date})
  Supplement Activity: {supplements count}

  This product code has established PMA precedent.
  {If device_class == 3}: PMA is the primary pathway for Class III devices
    in this product code.
  {If device_class == 2}: While PMA history exists, most submissions for
    this product code use 510(k). PMA may be appropriate for higher-risk
    variants or novel technology.
```

## Step 2.75: Review Timeline Estimation

**If the openFDA API is available**, calculate expected review timelines from historical data:

```bash
python3 << 'PYEOF'
import urllib.request, urllib.parse, json, os, re, time
from datetime import datetime

settings_path = os.path.expanduser('~/.claude/fda-predicate-assistant.local.md')
api_key = os.environ.get('OPENFDA_API_KEY')
if os.path.exists(settings_path):
    with open(settings_path) as f:
        content = f.read()
    if not api_key:
        m = re.search(r'openfda_api_key:\s*(\S+)', content)
        if m and m.group(1) != 'null':
            api_key = m.group(1)

product_code = "CODE"  # Replace
params = {"search": f'product_code:"{product_code}"+AND+decision_date:[20200101+TO+29991231]', "limit": "100"}
if api_key:
    params["api_key"] = api_key

url = f"https://api.fda.gov/device/510k.json?{urllib.parse.urlencode(params)}"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/4.7.0)"})

try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
        durations = []
        for r in data.get("results", []):
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
            median = durations[len(durations)//2]
            p25 = durations[len(durations)//4]
            p75 = durations[3*len(durations)//4]
            avg = sum(durations) // len(durations)
            print(f"REVIEW_STATS:n={len(durations)}|median={median}|p25={p25}|p75={p75}|avg={avg}|min={min(durations)}|max={max(durations)}")
        else:
            print("REVIEW_STATS:insufficient_data")
except Exception as e:
    print(f"REVIEW_ERROR:{e}")
PYEOF
```

Include review timeline in the pathway recommendation:

```
EXPECTED REVIEW TIMELINE
────────────────────────────────────────

  Based on {N} recent {product_code} clearances:
  Median review time: {median} days ({p25}-{p75} IQR)
  Average: {avg} days | Fastest: {min} days | Slowest: {max} days

  Expected timeline for your submission:
  Traditional 510(k): {median} days (typical for {CODE})
  Special 510(k):     {estimated — typically 20-30% faster}
  Abbreviated 510(k): {estimated — similar to traditional}
  De Novo:            {typically 150-300 days}
  PMA:                {typically 180-400 days}
```

## Error Handling

- **No product code**: Ask the user, or use --infer logic
- **API unavailable**: Score based on classification data from flat files (reduced accuracy)
- **Novel device with no clearances**: Strongly recommend De Novo, suggest Pre-Sub meeting
