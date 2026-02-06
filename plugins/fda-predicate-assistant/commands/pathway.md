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
| Automatic Class II | Could request automatic Class II | +10 |

### PMA Scoring

| Factor | Condition | Points |
|--------|-----------|--------|
| Class III | Device class is III | +40 |
| High risk | Life-sustaining or life-supporting | +30 |
| Clinical required | Clinical trial data clearly needed | +20 |
| No predicates | No suitable 510(k) predicates | +10 |

## Step 3: Present Recommendations

Rank pathways by score and present:

```
FDA Regulatory Pathway Recommendation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Product Code: {CODE} — {device_name}
Device Class: {class}
Regulation: 21 CFR {regulation}

RECOMMENDED PATHWAY: {Top pathway} (Score: {score}/100)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Rationale:
  {bullet points explaining why this pathway scored highest}

Estimated Timeline: {timeline}
Estimated Review Fee: {fee range}

Score Breakdown:
  {factor}: +{points} — {explanation}
  {factor}: +{points} — {explanation}
  ...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

All Pathways Ranked:

| # | Pathway | Score | Key Factor | Timeline | Fee |
|---|---------|-------|-----------|----------|-----|
| 1 | {pathway} | {score}/100 | {key reason} | {timeline} | {fee} |
| 2 | {pathway} | {score}/100 | {key reason} | {timeline} | {fee} |
| 3 | {pathway} | {score}/100 | {key reason} | {timeline} | {fee} |
| 4 | {pathway} | {score}/100 | {key reason} | {timeline} | {fee} |
| 5 | {pathway} | {score}/100 | {key reason} | {timeline} | {fee} |

Key Considerations:
  {pathway-specific considerations and risks}

Next Steps:
  1. {Based on recommended pathway}
  2. {Specific actions}
  3. Consider Pre-Sub meeting to confirm pathway with FDA

DISCLAIMER: Pathway recommendation is algorithmic and AI-generated.
  FDA makes final classification and pathway decisions. Consult regulatory
  affairs professionals. This is not regulatory advice.
```

## Error Handling

- **No product code**: Ask the user, or use --infer logic
- **API unavailable**: Score based on classification data from flat files (reduced accuracy)
- **Novel device with no clearances**: Strongly recommend De Novo, suggest Pre-Sub meeting
