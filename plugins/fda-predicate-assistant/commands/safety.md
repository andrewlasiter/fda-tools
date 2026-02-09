---
description: Analyze adverse events (MAUDE) and recall history for a product code or device — safety intelligence for pre-submission preparation
allowed-tools: Bash, Read, Grep, Glob, Write, WebSearch
argument-hint: "--product-code CODE [--years RANGE] [--device-name TEXT] [--knumber K123456]"
---

# FDA Safety Intelligence — MAUDE Events & Recall Analysis

You are producing a safety intelligence report combining MAUDE adverse event data and recall history from the openFDA API. This is used for pre-submission preparation, risk analysis, and safety profiling.

**All queries use the openFDA API** via the template in `references/openfda-api.md`. If the API is disabled or unreachable, report that this command requires API access and suggest `/fda:configure --set openfda_enabled true`.

## Parse Arguments

From `$ARGUMENTS`, extract:

- `--product-code CODE` (required) — 3-letter FDA product code
- `--years RANGE` (optional) — Year range for events (default: last 5 years)
- `--device-name TEXT` (optional) — Filter to specific device generic name
- `--knumber K123456` (optional) — Focus on a specific device's safety profile
- `--manufacturer TEXT` (optional) — Filter by manufacturer name
- `--sample-size N` (optional) — Number of recent event narratives to analyze (default: 25, max: 100)

If no product code provided, ask the user for it.

## Step 0: Verify API Access

```bash
python3 << 'PYEOF'
import os, re
settings_path = os.path.expanduser('~/.claude/fda-predicate-assistant.local.md')
api_enabled = True
api_key = os.environ.get('OPENFDA_API_KEY')  # Env var takes priority (never enters chat)
if os.path.exists(settings_path):
    with open(settings_path) as f:
        content = f.read()
    m = re.search(r'openfda_enabled:\s*(\S+)', content)
    if m and m.group(1).lower() == 'false':
        api_enabled = False
    if not api_key:  # Only check file if env var not set
        m = re.search(r'openfda_api_key:\s*(\S+)', content)
        if m and m.group(1) != 'null':
            api_key = m.group(1)
if not api_key:
    print("API_KEY_NUDGE:true")
print(f"API_ENABLED:{api_enabled}")
print(f"API_KEY:{'yes' if api_key else 'no'}")
PYEOF
```

If API is disabled or unreachable, **degrade gracefully** instead of blocking:

1. **Check for local MAUDE data first**: Look for any locally cached safety data in the project directory:
   ```bash
   ls "$PROJECTS_DIR/$PROJECT_NAME/safety_cache/" 2>/dev/null
   ```

2. **If local data exists**: Use it. Report: "Using cached safety data from {date}. Enable API for real-time data: `/fda:configure --set openfda_enabled true`"

3. **If no local data and API disabled**: Generate a structured warning output instead of erroring:
   ```json
   {
     "safety_data_available": false,
     "reason": "openFDA API disabled and no cached safety data found",
     "product_code": "{CODE}",
     "recommendation": "Enable API with /fda:configure --set openfda_enabled true for safety intelligence",
     "risk_assessment": "UNKNOWN — safety data not available",
     "generated_at": "{timestamp}"
   }
   ```
   Report this as a warning, NOT an error. The command completes successfully with a "no data" result rather than crashing. Downstream pipeline steps can check `safety_data_available: false` and adjust accordingly.

4. **If API enabled but request fails** (timeout, HTTP error): Retry once after 5 seconds. If still failing, produce the same structured warning with `"reason": "openFDA API request failed: {error}"`.

## Step 1: Product Code Context

First, get the device classification to frame the analysis:

```bash
python3 << 'PYEOF'
import urllib.request, urllib.parse, json, os, re

settings_path = os.path.expanduser('~/.claude/fda-predicate-assistant.local.md')
api_key = os.environ.get('OPENFDA_API_KEY')  # Env var takes priority (never enters chat)
if os.path.exists(settings_path):
    with open(settings_path) as f:
        content = f.read()
    if not api_key:  # Only check file if env var not set
        m = re.search(r'openfda_api_key:\s*(\S+)', content)
        if m and m.group(1) != 'null':
            api_key = m.group(1)

product_code = "PRODUCTCODE"  # Replace
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
except Exception as e:
    print(f"ERROR:{e}")

# Also count total clearances for context
params2 = {"search": f'product_code:"{product_code}"', "limit": "1"}
if api_key:
    params2["api_key"] = api_key
url2 = f"https://api.fda.gov/device/510k.json?{urllib.parse.urlencode(params2)}"
req2 = urllib.request.Request(url2, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/1.0)"})
try:
    with urllib.request.urlopen(req2, timeout=15) as resp2:
        data2 = json.loads(resp2.read())
        total = data2.get("meta", {}).get("results", {}).get("total", 0)
        print(f"TOTAL_CLEARANCES:{total}")
except:
    pass
PYEOF
```

## Step 1B: Peer Device Benchmarking

Query openFDA for peer devices sharing the same `regulation_number` or `review_panel` to establish a safety context baseline:

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

regulation_number = "REGULATION"  # From Step 1
product_code = "PRODUCTCODE"  # Replace

def fda_query(endpoint, search, limit=10, count_field=None):
    params = {"search": search, "limit": str(limit)}
    if count_field:
        params["count"] = count_field
    if api_key:
        params["api_key"] = api_key
    url = f"https://api.fda.gov/device/{endpoint}.json?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/1.0)"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"results": []}
        return {"error": f"HTTP {e.code}"}
    except Exception as e:
        return {"error": str(e)}

# Find peer product codes under the same regulation number
print("=== PEER DEVICE CODES ===")
peer_result = fda_query("classification", f'regulation_number:"{regulation_number}"', limit=25)
peer_codes = []
if "results" in peer_result:
    for r in peer_result["results"]:
        pc = r.get("product_code", "")
        name = r.get("device_name", "N/A")
        if pc and pc != product_code:
            peer_codes.append(pc)
            print(f"PEER:{pc}|{name}")

# Get MAUDE event counts for top peer codes (for benchmarking)
time.sleep(0.5)
print("\n=== PEER EVENT COUNTS ===")
subject_events = 0
peer_events = {}

# Get subject device event count
subj_result = fda_query("event", f'device.device_report_product_code:"{product_code}"', limit=1)
subject_events = subj_result.get("meta", {}).get("results", {}).get("total", 0)
print(f"SUBJECT:{product_code}|{subject_events}")

# Get peer event counts — single OR batch query (1 call instead of 5)
top_peers = peer_codes[:5]
if top_peers:
    peer_search = "+OR+".join(f'device.device_report_product_code:"{pc}"' for pc in top_peers)
    pr = fda_query("event", peer_search, count_field="device.device_report_product_code.exact")
    if "results" in pr:
        for r in pr["results"]:
            pc_term = r.get("term", "")
            if pc_term in top_peers:
                peer_events[pc_term] = r["count"]
                print(f"PEER_EVENTS:{pc_term}|{r['count']}")
    # Fill in zeros for any codes not returned
    for pc in top_peers:
        if pc not in peer_events:
            peer_events[pc] = 0
            print(f"PEER_EVENTS:{pc}|0")

# Calculate percentile ranking
if peer_events:
    all_counts = sorted([subject_events] + list(peer_events.values()))
    rank = all_counts.index(subject_events)
    percentile = (rank / len(all_counts)) * 100
    print(f"\nPERCENTILE:{percentile:.0f}")
    print(f"RANK:{rank+1}/{len(all_counts)}")
PYEOF
```

## Step 2: MAUDE Adverse Event Analysis

> **MAUDE data quality warning:** MAUDE reports are voluntarily self-reported by manufacturers, importers, and user facilities. Reports may be incomplete, duplicated, or inaccurate. The absence of reports does not prove absence of events. MAUDE data should inform risk assessment but not be the sole basis for safety conclusions.

### 2A: Event Count by Type

```bash
python3 << 'PYEOF'
import urllib.request, urllib.parse, json, os, re

settings_path = os.path.expanduser('~/.claude/fda-predicate-assistant.local.md')
api_key = os.environ.get('OPENFDA_API_KEY')  # Env var takes priority (never enters chat)
if os.path.exists(settings_path):
    with open(settings_path) as f:
        content = f.read()
    if not api_key:  # Only check file if env var not set
        m = re.search(r'openfda_api_key:\s*(\S+)', content)
        if m and m.group(1) != 'null':
            api_key = m.group(1)

product_code = "PRODUCTCODE"  # Replace

def fda_query(endpoint, search, limit=10, count_field=None):
    params = {"search": search, "limit": str(limit)}
    if count_field:
        params["count"] = count_field
    if api_key:
        params["api_key"] = api_key
    url = f"https://api.fda.gov/device/{endpoint}.json?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/1.0)"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"results": []}
        return {"error": f"HTTP {e.code}"}
    except Exception as e:
        return {"error": str(e)}

# Event count by type
print("=== EVENT TYPE DISTRIBUTION ===")
result = fda_query("event", f'device.device_report_product_code:"{product_code}"', count_field="event_type.exact")
if "results" in result:
    total = sum(r["count"] for r in result["results"])
    print(f"TOTAL_EVENTS:{total}")
    for r in result["results"]:
        print(f"EVENT_TYPE:{r['term']}:{r['count']}")
else:
    print(f"ERROR:{result.get('error', 'Unknown')}")

# Event count by year — single count query with date_received (1 call instead of 7)
import time
time.sleep(0.5)
print("\n=== EVENTS BY YEAR ===")
yr_result = fda_query("event",
    f'device.device_report_product_code:"{product_code}"',
    count_field="date_received")
if "results" in yr_result:
    # count_field="date_received" returns daily buckets — aggregate by year
    year_totals = {}
    for bucket in yr_result["results"]:
        date_str = str(bucket.get("time", ""))[:4]  # YYYY from YYYYMMDD
        if date_str.isdigit():
            yr = int(date_str)
            if 2020 <= yr <= 2026:
                year_totals[yr] = year_totals.get(yr, 0) + bucket["count"]
    for year in sorted(year_totals):
        print(f"YEAR:{year}:{year_totals[year]}")

# Top device names reporting events
time.sleep(0.5)
print("\n=== TOP DEVICE NAMES ===")
name_result = fda_query("event", f'device.device_report_product_code:"{product_code}"',
    count_field="device.generic_name.exact")
if "results" in name_result:
    for r in name_result["results"][:10]:
        print(f"DEVICE_NAME:{r['term']}:{r['count']}")

# Top manufacturers reporting events
time.sleep(0.5)
print("\n=== TOP MANUFACTURERS ===")
mfr_result = fda_query("event", f'device.device_report_product_code:"{product_code}"',
    count_field="device.manufacturer_d_name.exact")
if "results" in mfr_result:
    for r in mfr_result["results"][:10]:
        print(f"MANUFACTURER:{r['term']}:{r['count']}")
PYEOF
```

### 2B: Narrative Analysis — Recent Events

Fetch recent event narratives to identify common failure modes:

```bash
python3 << 'PYEOF'
import urllib.request, urllib.parse, json, os, re

settings_path = os.path.expanduser('~/.claude/fda-predicate-assistant.local.md')
api_key = os.environ.get('OPENFDA_API_KEY')  # Env var takes priority (never enters chat)
if os.path.exists(settings_path):
    with open(settings_path) as f:
        content = f.read()
    if not api_key:  # Only check file if env var not set
        m = re.search(r'openfda_api_key:\s*(\S+)', content)
        if m and m.group(1) != 'null':
            api_key = m.group(1)

product_code = "PRODUCTCODE"  # Replace

params = {
    "search": f'device.device_report_product_code:"{product_code}"+AND+date_received:[20230101+TO+20261231]',
    "limit": "25",  # Default sample size; use --sample-size flag to override (max 100)
    "sort": "date_received:desc"  # Most recent events first
}
if api_key:
    params["api_key"] = api_key
url = f"https://api.fda.gov/device/event.json?{urllib.parse.urlencode(params)}"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/1.0)"})

try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
        if data.get("results"):
            for i, event in enumerate(data["results"]):
                event_type = event.get("event_type", "Unknown")
                date = event.get("date_received", "N/A")
                devices = event.get("device", [])
                brand = devices[0].get("brand_name", "N/A") if devices else "N/A"
                mfr = devices[0].get("manufacturer_d_name", "N/A") if devices else "N/A"

                # Get narrative text
                narratives = event.get("mdr_text", [])
                desc_text = ""
                for n in narratives:
                    if n.get("text_type_code") in ("Description of Event or Problem", "B. ADDITIONAL MANUFACTURER NARRATIVE"):
                        desc_text = n.get("text", "")[:300]
                        break
                if not desc_text and narratives:
                    desc_text = narratives[0].get("text", "")[:300]

                print(f"EVENT:{i+1}|{event_type}|{date}|{brand}|{mfr}")
                if desc_text:
                    print(f"NARRATIVE:{desc_text}")
                print()
except Exception as e:
    print(f"ERROR:{e}")
PYEOF
```

**Analyze the narratives** to identify:
- **Common failure modes**: Group events by root cause (e.g., adhesion failure, sensor malfunction, infection, etc.)
- **Severity pattern**: Is injury/death disproportionately high vs malfunctions?
- **Specific device issues**: Any brand names or manufacturers with outsized event counts?
- **Recurring keywords**: Extract and count key terms from narratives (infection, bleeding, pain, failure, etc.)

## Step 3: Recall History

```bash
python3 << 'PYEOF'
import urllib.request, urllib.parse, json, os, re, time

settings_path = os.path.expanduser('~/.claude/fda-predicate-assistant.local.md')
api_key = os.environ.get('OPENFDA_API_KEY')  # Env var takes priority (never enters chat)
if os.path.exists(settings_path):
    with open(settings_path) as f:
        content = f.read()
    if not api_key:  # Only check file if env var not set
        m = re.search(r'openfda_api_key:\s*(\S+)', content)
        if m and m.group(1) != 'null':
            api_key = m.group(1)

product_code = "PRODUCTCODE"  # Replace

def fda_query(endpoint, search, limit=10, count_field=None, sort=None):
    params = {"search": search, "limit": str(limit)}
    if count_field:
        params["count"] = count_field
    if sort:
        params["sort"] = sort
    if api_key:
        params["api_key"] = api_key
    url = f"https://api.fda.gov/device/{endpoint}.json?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/1.0)"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"results": []}
        return {"error": f"HTTP {e.code}"}
    except Exception as e:
        return {"error": str(e)}

# Recall count by status
print("=== RECALL STATUS DISTRIBUTION ===")
class_result = fda_query("recall", f'product_code:"{product_code}"', count_field="recall_status")
if "results" in class_result:
    total = sum(r["count"] for r in class_result["results"])
    print(f"TOTAL_RECALLS:{total}")
    for r in class_result["results"]:
        print(f"RECALL_STATUS:{r['term']}:{r['count']}")
else:
    print("TOTAL_RECALLS:0")

# Recent recalls with details — sorted by most recent termination date
time.sleep(0.5)
print("\n=== RECENT RECALLS ===")
recent = fda_query("recall", f'product_code:"{product_code}"', limit=20, sort="event_date_terminated:desc")
if recent.get("results"):
    for r in recent["results"]:
        event_num = r.get("res_event_number", "N/A")
        status = r.get("recall_status", "N/A")
        firm = r.get("recalling_firm", "N/A")
        date = r.get("event_date_initiated", "N/A")
        reason = r.get("reason_for_recall", "N/A")[:200]
        product = r.get("product_description", "N/A")[:100]
        print(f"RECALL:{event_num}|{status}|{firm}|{date}")
        print(f"PRODUCT:{product}")
        print(f"REASON:{reason}")
        print()

# Top recalling firms
time.sleep(0.5)
print("\n=== TOP RECALLING FIRMS ===")
firm_result = fda_query("recall", f'product_code:"{product_code}"', count_field="recalling_firm.exact")
if "results" in firm_result:
    for r in firm_result["results"][:10]:
        print(f"FIRM:{r['term']}:{r['count']}")
PYEOF
```

## Step 4: Risk Profile Summary

Combine MAUDE + recall data into a safety summary. Calculate:

- **Events per clearance ratio**: Total MAUDE events / Total 510(k) clearances for this product code
  - <1.0 = Low event rate
  - 1.0-10.0 = Moderate event rate
  - >10.0 = High event rate (flag for pre-submission discussion)

- **Recall severity profile**:
  - Any Class I recalls = Serious safety concern in this device category
  - Mostly Class II = Moderate regulatory risk
  - Class III only = Low recall severity

- **Trend analysis**: Is the event count increasing or decreasing year-over-year?

## Step 5: If `--knumber` Specified — Device-Specific Safety

If a specific K-number was provided, also check:

```bash
python3 << 'PYEOF'
import urllib.request, urllib.parse, json, os, re

settings_path = os.path.expanduser('~/.claude/fda-predicate-assistant.local.md')
api_key = os.environ.get('OPENFDA_API_KEY')  # Env var takes priority (never enters chat)
if os.path.exists(settings_path):
    with open(settings_path) as f:
        content = f.read()
    if not api_key:  # Only check file if env var not set
        m = re.search(r'openfda_api_key:\s*(\S+)', content)
        if m and m.group(1) != 'null':
            api_key = m.group(1)

knumber = "KNUMBER"  # Replace

def fda_query(endpoint, search, limit=10):
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
            return {"results": []}
        return {"error": f"HTTP {e.code}"}
    except Exception as e:
        return {"error": str(e)}

# Recalls for this specific K-number
print("=== DEVICE-SPECIFIC RECALLS ===")
recalls = fda_query("recall", f'k_numbers:"{knumber}"', limit=10)
if recalls.get("results"):
    print(f"DEVICE_RECALLS:{len(recalls['results'])}")
    for r in recalls["results"]:
        print(f"RECALL:{r.get('res_event_number','N/A')}|{r.get('recall_status','N/A')}|{r.get('reason_for_recall','N/A')[:150]}")
else:
    print("DEVICE_RECALLS:0")
PYEOF
```

## Output Format

Structure the report using the standard FDA Professional CLI format (see `references/output-formatting.md`):

```
  FDA Safety Intelligence Report
  {CODE} — {DEVICE NAME}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: {date} | Class: {CLASS} | Regulation: {REG} | v5.16.0

DEVICE CONTEXT
────────────────────────────────────────

  Product Code: {CODE} | Panel: {PANEL}
  Total 510(k) Clearances: {N}

ADVERSE EVENT SUMMARY (MAUDE)
────────────────────────────────────────

  Total events: {N} (updated weekly)

  | Event Type   | Count | % of Total |
  |--------------|-------|------------|
  | Malfunction  | {N}   | {%}        |
  | Injury       | {N}   | {%}        |
  | Death        | {N}   | {%}        |

  Events per clearance: {ratio} ({Low/Moderate/High})

  Year    Events
  2020    {N}  ████████░░░░░░░░░░░░
  2021    {N}  ██████████░░░░░░░░░░
  2022    {N}  ████████████████████
  2023    {N}  ██████████████░░░░░░
  2024    {N}  ████████████░░░░░░░░
  2025    {N}  ██████░░░░░░░░░░░░░░

  Top Device Names: {list}
  Top Manufacturers: {list}

COMMON FAILURE MODES
────────────────────────────────────────

  Based on analysis of {N} recent event narratives:
  - {Mode 1}: {count} events — {brief description}
  - {Mode 2}: {count} events — {brief description}
  - {Mode 3}: {count} events — {brief description}

RECALL HISTORY
────────────────────────────────────────

  Total recalls: {N}

  | Class     | Count | Severity |
  |-----------|-------|----------|
  | Class I   | {N}   | Serious  |
  | Class II  | {N}   | Moderate |
  | Class III | {N}   | Low      |

  Active recalls: {N}
  Top recalling firms: {list}

  Recent Recalls:
  - {Event#}: {Firm} — Class {I/II/III} ({status}) — {reason}

PEER DEVICE COMPARISON
────────────────────────────────────────

  Regulation: 21 CFR {regulation_number}
  Peer product codes under same regulation: {N}

  | Product Code | Device Name | MAUDE Events |
  |-------------|-------------|--------------|
  | {CODE} (subject) | {name} | {N} |
  | {peer1} | {name} | {N} |
  | {peer2} | {name} | {N} |

  Percentile ranking: {N}th percentile among peers
  ({interpretation — e.g., "Below median event rate for this device family"})

RISK PROFILE
────────────────────────────────────────

  Event Rate:      {Low/Moderate/High} ({ratio} events per clearance)
  Recall Severity: {Low/Moderate/Serious} ({Class I count} Class I recalls)
  Trend:           {Increasing/Stable/Decreasing} event volume
  Death Events:    {N} ({flag if >0})
  Peer Ranking:    {percentile}th percentile ({above/below} median for regulation family)

  Pre-Submission Considerations:
  - {Specific safety considerations based on the data}
  - {Common failure modes to address in design/testing}
  - {Recall root causes to mitigate}

NEXT STEPS
────────────────────────────────────────

  1. Address failure modes in testing plan — `/fda:test-plan CODE`
  2. Discuss high-risk findings in Pre-Sub — `/fda:presub CODE`
  3. Build SE comparison addressing safety — `/fda:compare-se`

{If API_KEY_NUDGE:true was printed, add this line before the disclaimer:}
  Tip: Get 120x more API requests/day with a free key → /fda:configure --setup-key

────────────────────────────────────────
  This report is AI-generated from public FDA data.
  Verify independently. Not regulatory advice.
────────────────────────────────────────
```

Adapt the format to what data is actually available. If a section has no data (e.g., zero recalls), note it briefly rather than showing an empty table.

## Complaint Handling Template (--complaint-template flag)

When `--complaint-template` is specified, generate a complaint handling procedure template customized for the device's product code and risk profile. Reference `references/complaint-handling-framework.md` for templates.

**Output structure**:

```
COMPLAINT HANDLING PROCEDURE — {product_code}
════════════════════════════════════════════════

1. COMPLAINT INTAKE
────────────────────────────────────────
Required fields: Complaint ID, Date received, Source,
Product (name/model/lot/serial), Description,
Patient involvement (Y/N), Injury/death (Y/N),
Device available for investigation (Y/N)

2. MDR REPORTABILITY ASSESSMENT
────────────────────────────────────────
Decision tree per 21 CFR 803:
  • Death → REPORTABLE (5 working days)
  • Serious injury → REPORTABLE (30 calendar days)
  • Malfunction that COULD cause death/serious injury → REPORTABLE (30 calendar days)
  • None of above → NOT REPORTABLE (document decision)

Serious injury definition (21 CFR 803.3):
  Life-threatening, permanent impairment, or
  necessitates medical/surgical intervention

3. COMPLAINT CATEGORIES FOR {product_code}
────────────────────────────────────────
{Auto-populate from MAUDE data if available:}
  • Common event types for this product code
  • Historical malfunction patterns
  • Known failure modes from MAUDE narratives

4. TREND ANALYSIS
────────────────────────────────────────
Track quarterly: Total complaints, Malfunctions,
Injuries, Deaths, MDRs filed
Thresholds:
  • >50% increase quarter-over-quarter → Investigation
  • New failure mode → Root cause analysis
  • Any injury increase → Immediate review
  • Any death → Immediate escalation

5. INTEGRATION WITH MONITORING
────────────────────────────────────────
  • /fda:safety --product-code {CODE} for MAUDE benchmarking
  • /fda:monitor --check for ongoing safety signals

> Customize this template per 21 CFR 820.198 (complaint files)
> and 21 CFR 803 (MDR reporting requirements).
```
