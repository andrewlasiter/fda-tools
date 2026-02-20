
<!-- NOTE: This command has been migrated to use centralized FDAClient (FDA-114)
     Old pattern: urllib.request.Request + urllib.request.urlopen
     New pattern: FDAClient with caching, retry, and rate limiting
     Migration date: 2026-02-20
-->

---
description: Monitor FDA databases for new clearances, recalls, MAUDE events, and guidance updates for watched product codes
allowed-tools: Bash, Read, Write, Glob, Grep, WebSearch
argument-hint: "--check | --add-watch CODE | --remove-watch CODE | --status | --alerts | --watch-standards [--standards-report] [--notify webhook|stdout] [--cron] [--webhook-url URL] [--product-codes CODE] [--watch-companies NAME] [--project NAME]"
---

# FDA Real-Time Database Monitor

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
- `--notify webhook|stdout` — Send alerts via webhook POST or stdout JSON after --check
- `--cron` — Machine-readable JSON output suitable for cron scheduling
- `--webhook-url URL` — Override webhook URL for this check
- `--standards-report` — Generate full standards currency report (use with --watch-standards)

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
  Device Watch Dashboard
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: {date} | v5.22.0

WATCH CONFIGURATION
────────────────────────────────────────

  Product Codes: OVE, KGN
  Companies:     MEDTRONIC, STRYKER
  Last Check:    2026-02-05 12:00 UTC
  Total Checks:  5
  Last Alerts:   3 new clearances, 0 recalls

### Sources Checked

Append a sources table to every output showing which external APIs were queried and their status. See [CONNECTORS.md](../CONNECTORS.md) for the standard format. Only include rows for sources this command actually uses.

────────────────────────────────────────
  This report is AI-generated from public FDA data.
  Verify independently. Not regulatory advice.
────────────────────────────────────────
```

## Subcommand: --check

Run monitoring queries against the openFDA API:

### Check 1: New 510(k) Clearances

```bash
python3 << 'PYEOF'
import urllib.request, urllib.parse, json, os, re, time
from datetime import datetime, timedelta

settings_path = os.path.expanduser('~/.claude/fda-tools.local.md')
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

watched_codes = monitors["watches"]["product_codes"]
if watched_codes:
    # Batch OR query for all watched product codes (1 call instead of N)
    batch_search = "(" + "+OR+".join(f'product_code:"{pc}"' for pc in watched_codes) + f')+AND+decision_date:[{since_date}+TO+29991231]'
    params = {"search": batch_search, "limit": str(min(len(watched_codes) * 10, 100)), "sort": "decision_date:desc"}
    if api_key:
        params["api_key"] = api_key
    url = f"https://api.fda.gov/device/510k.json?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/5.21.0)"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            # Group results by product code
            by_pc = {pc: [] for pc in watched_codes}
            for r in data.get("results", []):
                rpc = r.get("product_code", "")
                if rpc in by_pc:
                    by_pc[rpc].append(r)
            for pc in watched_codes:
                results = by_pc.get(pc, [])
                print(f"NEW_CLEARANCES:{pc}:{len(results)}")
                for r in results[:5]:
                    print(f"CLEARANCE:{pc}|{r.get('k_number','')}|{r.get('applicant','')}|{r.get('device_name','')}|{r.get('decision_date','')}")
    except Exception as e:
        print(f"ERROR:batch:{e}")
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
  FDA Monitor Check Report
  {product_codes} — Monitoring Results
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: {date} | Period: {last_check} to {now} | v5.22.0

CHECK RESULTS
────────────────────────────────────────

  | Category              | Count |
  |-----------------------|-------|
  | New 510(k) clearances | {N}   |
  | New recalls           | {N}   |
  | New MAUDE events      | {N}   |
  | Guidance updates      | {N}   |

{If any critical alerts (Class I recall, death events):}
CRITICAL ALERTS
────────────────────────────────────────

  {alert details}

FILES WRITTEN
────────────────────────────────────────

  Alerts: ~/fda-510k-data/monitor_alerts/{today}.json

NEXT STEPS
────────────────────────────────────────

  1. Review alert details — `/fda:monitor --alerts`
  2. Run safety analysis on flagged codes — `/fda:safety --product-code CODE`
  3. Update submission if new predicates found — `/fda:review --project NAME`

### Sources Checked

Append a sources table to every output showing which external APIs were queried and their status. See [CONNECTORS.md](../CONNECTORS.md) for the standard format. Only include rows for sources this command actually uses.

────────────────────────────────────────
  This report is AI-generated from public FDA data.
  Verify independently. Not regulatory advice.
────────────────────────────────────────
```

## Subcommand: --notify (Alert Delivery)

After `--check` completes and alerts are generated, deliver them via the specified method using the bundled `alert_sender.py`.

### Usage Examples

```bash
# Webhook POST
/fda:monitor --check --notify webhook --webhook-url https://your-webhook-endpoint.example.com/notify

# Machine-readable JSON for cron
/fda:monitor --check --notify stdout --cron

# Cron setup (check every hour, stdout JSON):
# */60 * * * * claude -p "Run /fda:monitor --check --notify stdout --cron"
```

### Delivery via alert_sender.py

```bash
python3 "$FDA_PLUGIN_ROOT/scripts/alert_sender.py" \
  --method {webhook|stdout} \
  --alert-dir ~/fda-510k-data/monitor_alerts \
  --since {last_check_date} \
  {--cron if --cron flag set} \
  {--webhook-url URL if provided}
```

If `--cron` is set, always use `--method stdout --cron` regardless of `--notify` value. This outputs machine-readable JSON suitable for piping to downstream tools.

### Webhook Payload Format

```json
{
  "source": "fda-tools-monitor",
  "version": "4.8.0",
  "timestamp": "2026-02-07T12:00:00Z",
  "alert_count": 3,
  "alerts": [
    {"type": "new_clearance", "product_code": "OVE", ...},
    {"type": "recall", "product_code": "OVE", ...}
  ]
}
```

## Subcommand: --watch-standards

Track FDA recognized consensus standards changes that affect your projects.

### How it works

1. Read the project's `guidance_cache/standards_list.json` to get the list of applicable standards
2. Load the built-in supersession data from `references/standards-tracking.md`
3. Query FDA's standards database for updates:

```
WebSearch: site:fda.gov "recognized consensus standards" update 2026
WebSearch: site:fda.gov "{standard_name}" recognition medical device 2025 OR 2026
```

4. For each standard in the project:
   - Check if a newer version has been recognized by FDA
   - Check if the current version has been withdrawn from FDA recognition
   - Check transition deadlines (alert if within 6 months)
   - Assess impact on project requirements

5. **Supersession Detection** — Use built-in supersession database:

```bash
python3 << 'PYEOF'
import json, os, re
from datetime import datetime, date

# Known supersessions (from standards-tracking.md)
SUPERSESSIONS = {
    "ISO 10993-1:2018": {"new": "ISO 10993-1:2025", "transition": "2027-11-18", "action": "Update biocompatibility testing plan to reference 2025 edition"},
    "ISO 11137-1:2006": {"new": "ISO 11137-1:2025", "transition": "2027-06-01", "action": "Update radiation sterilization validation references"},
    "ISO 17665-1:2006": {"new": "ISO 17665:2024", "transition": "2026-12-01", "action": "Update moist heat sterilization references"},
    "ISO 10993-1:2009": {"new": "ISO 10993-1:2025", "transition": "2027-11-18", "action": "Update biocompatibility evaluation framework"},
}

# Load project's cited standards
project_dir = os.path.expanduser("~/fda-510k-data/projects/PROJECT_NAME")  # Replace
standards_files = [
    os.path.join(project_dir, "test_plan.md"),
    os.path.join(project_dir, "guidance_cache", "standards_list.json"),
]

cited = set()
std_pattern = re.compile(r"(ISO|IEC|ASTM|AAMI|UL)\s*[\d]+(?:-\d+)?(?::\d{4})?")

for sf in standards_files:
    if os.path.exists(sf):
        with open(sf) as f:
            content = f.read()
        for m in std_pattern.finditer(content):
            cited.add(m.group())

alerts = []
for std_cited in sorted(cited):
    if std_cited in SUPERSESSIONS:
        info = SUPERSESSIONS[std_cited]
        transition = datetime.strptime(info["transition"], "%Y-%m-%d").date()
        days_remaining = (transition - date.today()).days
        severity = "critical" if days_remaining < 90 else "warning" if days_remaining < 180 else "info"
        alerts.append({
            "type": "standard_update",
            "standard": std_cited.split(":")[0],
            "old_version": std_cited.split(":")[-1] if ":" in std_cited else "unknown",
            "new_version": info["new"].split(":")[-1],
            "transition_deadline": info["transition"],
            "days_remaining": days_remaining,
            "severity": severity,
            "action_required": info["action"],
        })
        status = "SUPERSEDED" if days_remaining > 0 else "EXPIRED"
        print(f"{status}:{std_cited}|{info['new']}|{info['transition']}|{days_remaining}d remaining")
    else:
        print(f"CURRENT:{std_cited}")

if alerts:
    # Save to alert file
    today = date.today().isoformat()
    alert_dir = os.path.expanduser("~/fda-510k-data/monitor_alerts")
    os.makedirs(alert_dir, exist_ok=True)
    alert_file = os.path.join(alert_dir, f"{today}.json")
    if os.path.exists(alert_file):
        with open(alert_file) as f:
            existing = json.load(f)
    else:
        existing = {"date": today, "alerts": []}
    existing["alerts"].extend(alerts)
    with open(alert_file, "w") as f:
        json.dump(existing, f, indent=2)
    print(f"\nSaved {len(alerts)} standard alerts to {alert_file}")
PYEOF
```

6. Generate standards impact report:

```markdown
## Standards Watch Report

| Standard | Current | Latest Recognized | Status | Transition | Impact |
|----------|---------|-------------------|--------|------------|--------|
| ISO 10993-1 | 2018 | 2025 | SUPERSEDED | 2027-11-18 | Update biocompat plan |
| IEC 62304 | 2015 | 2015 | CURRENT | — | No action |
| ISO 11135 | 2014 | 2014 | CURRENT | — | No action |
| ISO 17665-1 | 2006 | 2024 | SUPERSEDED | 2026-12-01 | Update steam sterilization refs |
| ASTM F1980 | 2016 | 2021 | UPDATE AVAILABLE | — | Review aging protocol |
```

7. Save results to `~/fda-510k-data/monitor_alerts/{today}.json` with `type: "standard_update"`

### Standards Report (--standards-report)

When `--standards-report` is combined with `--watch-standards`, generate a comprehensive standards currency report:

```
  FDA Standards Currency Report
  {project_name} — Full Audit
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: {date} | v5.22.0

STANDARDS CURRENCY STATUS
────────────────────────────────────────

  ✓ Current:     {N} standards up to date
  ⚠ Superseded:  {N} standards need updating
  ✗ Expired:     {N} standards past transition deadline

SUPERSEDED STANDARDS (Action Required)
────────────────────────────────────────

  ISO 10993-1:2018 → ISO 10993-1:2025
    Transition deadline: 2027-11-18 ({N} days remaining)
    Impact: Update biocompatibility testing plan
    FDA Recognition: Recognized 2025-11-18

  ISO 17665-1:2006 → ISO 17665:2024
    Transition deadline: 2026-12-01 ({N} days remaining)
    Impact: Update moist heat sterilization references

CURRENT STANDARDS (No Action)
────────────────────────────────────────

  ✓ ISO 14971:2019        Risk management
  ✓ IEC 62304:2006+A1     Software lifecycle
  ✓ ISO 13485:2016        Quality management

RECOMMENDATIONS
────────────────────────────────────────

  1. Update test plans to reference superseded standard editions
  2. Review submission documents for outdated citations
  3. For detailed standard lookup: /fda:standards --check-currency

### Sources Checked

Append a sources table to every output showing which external APIs were queried and their status. See [CONNECTORS.md](../CONNECTORS.md) for the standard format. Only include rows for sources this command actually uses.

────────────────────────────────────────
  This report is AI-generated from public FDA data.
  Verify independently. Not regulatory advice.
────────────────────────────────────────
```

See `references/standards-tracking.md` for standard families, supersession data, and alert schema.

## Subcommand: --alerts

Read alert files from `~/fda-510k-data/monitor_alerts/` and display recent alerts. If `--since` provided, filter by date.

## Error Handling

- **No watches configured**: "No product codes or companies being monitored. Use `--add-watch CODE` to start monitoring."
- **API unavailable**: "openFDA API unavailable. Monitor requires API access for real-time data."
- **No new data**: "No new events since last check ({date})."
