---
description: Monitor FDA databases for new clearances, recalls, MAUDE events, and guidance updates for watched product codes
allowed-tools: Bash, Read, Write, Glob, Grep, WebSearch
argument-hint: "--check | --add-watch CODE | --remove-watch CODE | --status | --alerts [--product-codes CODE] [--watch-companies NAME] [--project NAME]"
---

# FDA Real-Time Database Monitor

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

If `$FDA_PLUGIN_ROOT` is empty, report an error: "Could not locate the FDA Predicate Assistant plugin installation."

---

You are monitoring FDA databases for changes relevant to the user's product codes and companies.

## Parse Arguments

From `$ARGUMENTS`, extract the subcommand:

- `--add-watch CODE` — Add a product code to the watch list
- `--remove-watch CODE` — Remove a product code from the watch list
- `--check` — Run a monitoring check now against all watched items
- `--status` — Show current watch configuration and last check time
- `--alerts` — Display recent alerts
- `--product-codes CODE[,CODE2]` — Initial product codes to watch (used with --add-watch or --check)
- `--watch-companies NAME[;NAME2]` — Companies to monitor
- `--project NAME` — Associate alerts with a project
- `--since YYYY-MM-DD` — Only show alerts since this date

## State Management

All monitor state is stored in `~/fda-510k-data/monitors.json`:

```json
{
  "version": 1,
  "watches": {
    "product_codes": ["OVE", "KGN"],
    "companies": ["MEDTRONIC", "STRYKER"],
    "created_at": "2026-02-05T12:00:00Z",
    "last_checked": "2026-02-05T12:00:00Z"
  },
  "check_history": [
    {
      "timestamp": "2026-02-05T12:00:00Z",
      "new_clearances": 3,
      "new_recalls": 0,
      "new_events": 15,
      "guidance_updates": 1
    }
  ]
}
```

Alerts are stored in `~/fda-510k-data/monitor_alerts/YYYY-MM-DD.json`:

```json
{
  "date": "2026-02-05",
  "alerts": [
    {
      "type": "new_clearance",
      "product_code": "OVE",
      "device_name": "Cervical Fusion Device",
      "knumber": "K263456",
      "applicant": "COMPANY INC",
      "decision_date": "20260203",
      "severity": "info",
      "url": "https://www.accessdata.fda.gov/cdrh_docs/pdf26/K263456.pdf"
    },
    {
      "type": "recall",
      "product_code": "OVE",
      "recalling_firm": "COMPANY INC",
      "classification": "Class II",
      "reason": "Device may fracture under load",
      "severity": "warning",
      "url": "https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfres/res.cfm"
    },
    {
      "type": "maude_event",
      "product_code": "OVE",
      "event_type": "Injury",
      "count_since_last": 15,
      "severity": "info"
    },
    {
      "type": "guidance_update",
      "title": "New Draft Guidance: Spinal Fusion Devices",
      "url": "https://www.fda.gov/...",
      "severity": "info"
    }
  ]
}
```

## Subcommand: --add-watch

```bash
python3 << 'PYEOF'
import json, os
from datetime import datetime

monitors_file = os.path.expanduser('~/fda-510k-data/monitors.json')
os.makedirs(os.path.dirname(monitors_file), exist_ok=True)

if os.path.exists(monitors_file):
    with open(monitors_file) as f:
        data = json.load(f)
else:
    data = {"version": 1, "watches": {"product_codes": [], "companies": [], "created_at": datetime.utcnow().isoformat() + "Z", "last_checked": None}, "check_history": []}

product_code = "CODE"  # Replace with actual
if product_code not in data["watches"]["product_codes"]:
    data["watches"]["product_codes"].append(product_code)
    with open(monitors_file, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Added {product_code} to watch list")
else:
    print(f"{product_code} already on watch list")

print(f"Current watches: {', '.join(data['watches']['product_codes'])}")
PYEOF
```

## Subcommand: --remove-watch

Similar to --add-watch but removes from the list.

## Subcommand: --status

Read monitors.json and display:
```
FDA Monitor Status
━━━━━━━━━━━━━━━━━
Watched Product Codes: OVE, KGN
Watched Companies:     MEDTRONIC, STRYKER
Last Check:           2026-02-05 12:00 UTC
Total Checks:         5
Last Alert Count:     3 new clearances, 0 recalls
```

## Subcommand: --check

Run monitoring queries against the openFDA API:

### Check 1: New 510(k) Clearances

```bash
python3 << 'PYEOF'
import urllib.request, urllib.parse, json, os, re, time
from datetime import datetime, timedelta

settings_path = os.path.expanduser('~/.claude/fda-predicate-assistant.local.md')
api_key = os.environ.get('OPENFDA_API_KEY')
if os.path.exists(settings_path):
    with open(settings_path) as f:
        content = f.read()
    if not api_key:
        m = re.search(r'openfda_api_key:\s*(\S+)', content)
        if m and m.group(1) != 'null':
            api_key = m.group(1)

monitors_file = os.path.expanduser('~/fda-510k-data/monitors.json')
with open(monitors_file) as f:
    monitors = json.load(f)

last_checked = monitors["watches"].get("last_checked")
if last_checked:
    since_date = last_checked[:10].replace("-", "")
else:
    since_date = (datetime.utcnow() - timedelta(days=30)).strftime("%Y%m%d")

for pc in monitors["watches"]["product_codes"]:
    search = f'product_code:"{pc}"+AND+decision_date:[{since_date}+TO+29991231]'
    params = {"search": search, "limit": "10", "sort": "decision_date:desc"}
    if api_key:
        params["api_key"] = api_key
    url = f"https://api.fda.gov/device/510k.json?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/1.0)"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            total = data.get("meta", {}).get("results", {}).get("total", 0)
            print(f"NEW_CLEARANCES:{pc}:{total}")
            for r in data.get("results", [])[:5]:
                print(f"CLEARANCE:{pc}|{r.get('k_number','')}|{r.get('applicant','')}|{r.get('device_name','')}|{r.get('decision_date','')}")
    except Exception as e:
        print(f"ERROR:{pc}:{e}")
    time.sleep(0.5)
PYEOF
```

### Check 2: New Recalls

Similar query against `/device/recall.json` for each watched product code, filtered by `report_date` since last check.

### Check 3: New MAUDE Events

Query `/device/event.json` for each watched product code, count events since last check.

### Check 4: Guidance Updates

```
WebSearch: "{product_code}" OR "{device_name}" guidance site:fda.gov 2026
```

Check results against previously seen guidance URLs.

### Save Results

Update monitors.json with new `last_checked` timestamp and check history.
Write alerts to `~/fda-510k-data/monitor_alerts/{today}.json`.

Report:
```
FDA Monitor Check Complete
━━━━━━━━━━━━━━━━━━━━━━━━━
Checked: {N} product codes, {N} companies
Period: {last_check} to {now}

Results:
  New 510(k) clearances: {N}
  New recalls:           {N}
  New MAUDE events:      {N}
  Guidance updates:      {N}

{If any critical alerts (Class I recall, death events):}
CRITICAL ALERTS:
  {alert details}

Alerts saved to: ~/fda-510k-data/monitor_alerts/{today}.json
```

## Subcommand: --alerts

Read alert files from `~/fda-510k-data/monitor_alerts/` and display recent alerts. If `--since` provided, filter by date.

## Error Handling

- **No watches configured**: "No product codes or companies being monitored. Use `--add-watch CODE` to start monitoring."
- **API unavailable**: "openFDA API unavailable. Monitor requires API access for real-time data."
- **No new data**: "No new events since last check ({date})."
