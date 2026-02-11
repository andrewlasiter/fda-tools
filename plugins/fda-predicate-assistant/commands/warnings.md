---
description: Search FDA warning letters and enforcement actions for medical devices — GMP violation analysis, company risk profiles, and product code enforcement trends
allowed-tools: Bash, Read, Glob, Grep, Write, WebFetch, WebSearch
argument-hint: "<company-or-product-code> [--recalls] [--years RANGE] [--violations] [--risk-profile] [--save]"
---

# FDA Warning Letters & Enforcement Intelligence

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

You are searching FDA enforcement intelligence to find warning letters, recall enforcement actions, and GMP violation patterns relevant to medical device regulatory work.

**KEY PRINCIPLE: Provide actionable risk intelligence, not just raw data.** Analyze violation patterns, identify risk signals for submission planning, and map findings to GMP readiness.

## Parse Arguments

From `$ARGUMENTS`, extract:

- **Search term** (required) — Company name, product code, or FEI number
- `--recalls` — Include openFDA device enforcement (recall) data
- `--years RANGE` — Limit to specific years (e.g., `2024-2025`, default: last 3 years)
- `--violations` — Analyze 21 CFR violation patterns from warning letter text
- `--risk-profile` — Generate consolidated risk profile combining all sources
- `--product-code CODE` — Filter by FDA product code
- `--class I|II|III` — Filter recalls by classification
- `--project NAME` — Associate with a project folder
- `--save` — Save enforcement data to project

If no search term provided, ask the user what company or product code to investigate.

## Step 1: Determine Search Type

Classify the search term:
- **3-letter code** → Product code search
- **Numeric (7-10 digits)** → FEI number
- **Otherwise** → Company name

## Step 2: openFDA Device Enforcement (Recalls)

Query the openFDA enforcement API for recall data:

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

# Build search query based on search type
search_term = "SEARCH_TERM"  # Replace with actual term
search_type = "SEARCH_TYPE"   # company, product_code, or fei

if search_type == "product_code":
    query = f'product_code:"{search_term}"'
elif search_type == "fei":
    query = f'openfda.fei_number:"{search_term}"'
else:
    query = f'recalling_firm:"{search_term}"'

params = {"search": query, "limit": "100", "sort": "report_date:desc"}
if api_key:
    params["api_key"] = api_key

url = f"https://api.fda.gov/device/enforcement.json?{urllib.parse.urlencode(params)}"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/1.0)"})
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
        total = data.get("meta", {}).get("results", {}).get("total", 0)
        returned = len(data.get("results", []))
        print(f"TOTAL_RECALLS:{total}")
        print(f"SHOWING:{returned}_OF:{total}")
        for r in data.get("results", []):
            print(f"RECALL:{r.get('recall_number','N/A')}|{r.get('classification','N/A')}|{r.get('recalling_firm','N/A')}|{r.get('product_description','N/A')[:80]}|{r.get('recall_initiation_date','N/A')}|{r.get('reason_for_recall','N/A')[:100]}|{r.get('status','N/A')}|{r.get('voluntary_mandated','N/A')}")
except urllib.error.HTTPError as e:
    if e.code == 404:
        print("TOTAL_RECALLS:0")
    else:
        print(f"API_ERROR:{e.code} {e.reason}")
except Exception as e:
    print(f"API_ERROR:{e}")
PYEOF
```

## Step 3: FDA Warning Letters Web Search

Search for CDRH warning letters:

```
WebSearch: "{search_term}" warning letter site:fda.gov/inspections-compliance-enforcement-and-criminal-investigations CDRH "medical device"
```

For product code searches, also search by device type name:
```
WebSearch: "{device_name}" warning letter "21 CFR 820" site:fda.gov
```

### Process Warning Letter Results

For each warning letter found:
1. Note the company name, date, and URL
2. If `--violations` flag set, use WebFetch on the warning letter URL to extract:
   - All 21 CFR sections cited
   - Specific observations (FDA-483 items)
   - Severity of violations
   - Whether corrective actions were adequate

## Step 4: Violation Pattern Analysis (if `--violations`)

Cross-reference the `fda-enforcement-intelligence.md` reference for common violation patterns:

```
Read: $FDA_PLUGIN_ROOT/skills/fda-510k-knowledge/references/fda-enforcement-intelligence.md
```

Map each cited CFR section to its violation category:

| CFR Section | Category |
|------------|----------|
| 21 CFR 820.30 | Design Controls |
| 21 CFR 820.40 | Document Controls |
| 21 CFR 820.50 | Purchasing Controls |
| 21 CFR 820.75 | Process Validation |
| 21 CFR 820.90 | CAPA |
| 21 CFR 820.184 | Device History Record |
| 21 CFR 820.198 | Complaint Handling |
| 21 CFR 803 | MDR Reporting |

Identify trends: Which violations appear most frequently? Are there repeat offenders?

## Step 5: Risk Profile (if `--risk-profile`)

Combine all data sources into a consolidated risk assessment:

1. **Recall History**: Count by class (I/II/III), status, recent activity
2. **Warning Letters**: Count, recency, violation categories
3. **Inspection Data**: If available from `/fda:inspections` data, include OAI/VAI history
4. **MAUDE Events**: If available, include adverse event counts

### Risk Score Calculation

```
Risk Score = (Class_I_recalls × 10) + (Class_II_recalls × 3) + (Class_III_recalls × 1)
           + (Warning_letters_3yr × 8) + (OAI_inspections_3yr × 5)
           + (MAUDE_deaths × 15) + (MAUDE_injuries × 2)
```

| Score Range | Risk Level | Interpretation |
|------------|-----------|---------------|
| 0-5 | Low | Clean enforcement history |
| 6-20 | Moderate | Some enforcement activity, monitor |
| 21-50 | Elevated | Significant enforcement history, exercise caution |
| 51+ | High | Major enforcement concerns, thorough due diligence required |

## Step 6: Output

### Report Format

```
  FDA Enforcement Intelligence
  {SEARCH_TERM}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: {date} | Search: {type} | Years: {range} | v5.22.0

RECALL ENFORCEMENT
────────────────────────────────────────

  Total recalls found: {N}

  Class I (Most Serious):
    {recall_number} — {product_description}
    Initiated: {date} | Status: {status}
    Reason: {reason}

  Class II:
    {recall_number} — {product_description}
    ...

  Class III:
    ...

WARNING LETTERS
────────────────────────────────────────

  {date} — {company_name}
  {url}
  Violations: 21 CFR {sections}

  {date} — {company_name}
  ...

[If --violations]
GMP VIOLATION ANALYSIS
────────────────────────────────────────

  Most Cited Violations:
  1. CAPA (21 CFR 820.90) — {count} citations
  2. Design Controls (21 CFR 820.30) — {count} citations
  3. Complaint Handling (21 CFR 820.198) — {count} citations
  ...

  QMSR Note:
  As of Feb 2, 2026, 21 CFR 820 has been replaced by QMSR
  (ISO 13485-aligned). New citations reference QMSR sections.

[If --risk-profile]
RISK ASSESSMENT
────────────────────────────────────────

  Risk Score: {score} / {level}

  Recall History:    {class_I} Class I | {class_II} Class II | {class_III} Class III
  Warning Letters:   {count} in last 3 years
  OAI Inspections:   {count} (if available)
  MAUDE Events:      {deaths} deaths | {injuries} injuries (if available)

  Implications for 510(k):
  - {risk interpretation specific to search context}
  - {recommendations for submission strategy}

NEXT STEPS
────────────────────────────────────────

  1. Check inspection history — `/fda:inspections {search_term}`
  2. Review adverse events — `/fda:safety --company {company}`
  3. Deep predicate analysis — `/fda:research {product_code}`

────────────────────────────────────────
  This report is AI-generated from public FDA data.
  Verify independently. Not regulatory advice.
────────────────────────────────────────
```

## Step 7: Save (if `--save`)

If `--save` and `--project` specified, write enforcement data to:
```
~/fda-510k-data/projects/{PROJECT_NAME}/enforcement/
  enforcement_summary.json   ← Consolidated enforcement data
  recalls.json              ← Raw recall data
  warning_letters.json      ← Warning letter references
```

### Sources Checked

Append a sources table to every output showing which external APIs were queried and their status. See [CONNECTORS.md](../CONNECTORS.md) for the standard format. Only include rows for sources this command actually uses.

## Error Handling

- **No results found**: "No enforcement actions found for '{search_term}'. This may indicate a clean enforcement record, or the entity may operate under a different name. Try alternate company names or FEI number."
- **API error**: Fall back to WebSearch only. Note: "openFDA API unavailable — results based on web search only."
- **Rate limit**: "API rate limit reached. Results may be incomplete. Use `--save` to cache data for offline review."
