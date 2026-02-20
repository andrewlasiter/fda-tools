---
description: Search ClinicalTrials.gov for clinical studies involving similar medical devices — find trial designs, endpoints, enrollment, and evidence for 510(k) submissions
allowed-tools: Bash, Read, Glob, Grep, Write, WebFetch, WebSearch
argument-hint: "<device name or condition> [--sponsor NAME] [--status completed|recruiting|all] [--product-code CODE] [--limit N] [--project NAME] [--save]"
---

# ClinicalTrials.gov Device Study Search

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

You are searching **ClinicalTrials.gov** for clinical studies involving medical devices similar to the user's device. This data strengthens 510(k) submissions by:

1. **Identifying clinical endpoints** used for similar devices (informs testing strategy)
2. **Finding published study results** (clinical evidence for SE arguments)
3. **Discovering ongoing trials** (competitive intelligence and market context)
4. **Benchmarking enrollment/design** (sample size, study design precedent)

## Parse Arguments

From `$ARGUMENTS`, extract:

- **Device name, condition, or keyword** — Required. Primary search term
- `--sponsor NAME` — Filter by sponsor/company name
- `--status STATUS` — Filter: `completed`, `recruiting`, `active`, `all` (default: `all`)
- `--product-code CODE` — If provided, first look up the device name from openFDA, then search trials
- `--device-only` — Only show device interventions (exclude drugs/procedures)
- `--with-results` — Only show studies that have posted results
- `--limit N` — Max results (default 20)
- `--project NAME` — Associate results with a project
- `--save` — Save results to project folder

## Step 1: Resolve Device Context (if --product-code)

If `--product-code` is provided, first look up the device type name from openFDA:

```bash
python3 << 'PYEOF'
import urllib.request, urllib.parse, json
code = "PRODUCT_CODE"  # Replace with actual
url = f"https://api.fda.gov/device/classification.json?search=product_code:{code}&limit=100"
try:
    with urllib.request.urlopen(url, timeout=10) as resp:
        data = json.loads(resp.read())
        total = data.get("meta", {}).get("results", {}).get("total", 0)
        print(f"CLASSIFICATION_MATCHES:{total}")
        for r in data.get("results", []):
            print(f"DEVICE_NAME:{r.get('device_name', '')}")
            print(f"DEFINITION:{r.get('definition', '')[:200]}")
except Exception as e:
    print(f"ERROR:{e}")
PYEOF
```

Use the device name as the search term for ClinicalTrials.gov.

## Step 2: Search ClinicalTrials.gov API v2

Build the query URL:

```bash
python3 << 'PYEOF'
import urllib.request, urllib.parse, json

# Search parameters (replace placeholders)
search_term = "SEARCH_TERM"
sponsor = None  # or "SPONSOR_NAME"
status_filter = None  # or "COMPLETED", "RECRUITING", etc.
device_only = False  # True if --device-only
with_results = False  # True if --with-results
limit = 20

# Build query
params = {
    "format": "json",
    "pageSize": str(limit),
    "countTotal": "true",
}

# Build query.term with AREA syntax for device filtering
query_parts = [search_term]
if device_only:
    query_parts.append("AREA[InterventionType]DEVICE")

params["query.term"] = " AND ".join(query_parts)

if sponsor:
    params["query.spons"] = sponsor

# Status filter
status_map = {
    "completed": "COMPLETED",
    "recruiting": "RECRUITING",
    "active": "ACTIVE_NOT_RECRUITING",
}
if status_filter and status_filter != "all":
    params["filter.overallStatus"] = status_map.get(status_filter, status_filter.upper())

if with_results:
    params["sort"] = "ResultsFirstPostDate:desc"

url = f"https://clinicaltrials.gov/api/v2/studies?{urllib.parse.urlencode(params)}"

try:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FDA-Plugin/5.10.0)"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read())

    total = data.get("totalCount", 0)
    returned = len(data.get("studies", []))
    print(f"TOTAL:{total}")
    print(f"SHOWING:{returned}_OF:{total}")

    for study in data.get("studies", []):
        proto = study.get("protocolSection", {})
        ident = proto.get("identificationModule", {})
        status_mod = proto.get("statusModule", {})
        design = proto.get("designModule", {})
        arms = proto.get("armsInterventionsModule", {})
        outcomes = proto.get("outcomesModule", {})
        elig = proto.get("eligibilityModule", {})
        desc = proto.get("descriptionModule", {})

        nct_id = ident.get("nctId", "N/A")
        title = ident.get("briefTitle", "N/A")
        org = ident.get("organization", {}).get("fullName", "N/A")
        overall_status = status_mod.get("overallStatus", "N/A")

        start = status_mod.get("startDateStruct", {}).get("date", "N/A")
        completion = status_mod.get("completionDateStruct", {}).get("date", "N/A")

        study_type = design.get("studyType", "N/A")
        phases = ",".join(design.get("phases", ["N/A"]))
        enrollment = design.get("enrollmentInfo", {})
        enroll_count = enrollment.get("count", "N/A")
        enroll_type = enrollment.get("type", "")

        design_info = design.get("designInfo", {})
        allocation = design_info.get("allocation", "N/A")
        model = design_info.get("interventionModel", "N/A")
        purpose = design_info.get("primaryPurpose", "N/A")
        masking = design_info.get("maskingInfo", {}).get("masking", "N/A")

        # Interventions
        interventions = arms.get("interventions", [])
        device_interventions = [i for i in interventions if i.get("type") == "DEVICE"]

        # Primary outcomes
        primary_outcomes = outcomes.get("primaryOutcomes", [])

        # Conditions
        conditions = proto.get("conditionsModule", {}).get("conditions", [])

        print(f"=== STUDY ===")
        print(f"NCT_ID:{nct_id}")
        print(f"TITLE:{title}")
        print(f"SPONSOR:{org}")
        print(f"STATUS:{overall_status}")
        print(f"START:{start}")
        print(f"COMPLETION:{completion}")
        print(f"TYPE:{study_type}")
        print(f"PHASES:{phases}")
        print(f"ENROLLMENT:{enroll_count} ({enroll_type})")
        print(f"ALLOCATION:{allocation}")
        print(f"MODEL:{model}")
        print(f"PURPOSE:{purpose}")
        print(f"MASKING:{masking}")
        print(f"CONDITIONS:{'; '.join(conditions)}")
        for di in device_interventions:
            print(f"DEVICE_INTERVENTION:{di.get('name', 'N/A')}|{di.get('description', '')[:150]}")
        for po in primary_outcomes[:3]:
            print(f"PRIMARY_OUTCOME:{po.get('measure', 'N/A')}|{po.get('timeFrame', 'N/A')}")
        summary = desc.get("briefSummary", "")[:300]
        print(f"SUMMARY:{summary}")
        print()

except urllib.error.HTTPError as e:
    print(f"ERROR:HTTP {e.code}")
except Exception as e:
    print(f"ERROR:{e}")
PYEOF
```

## Step 3: Present Results

```
  ClinicalTrials.gov Device Study Search
  {search context}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: {date} | Source: ClinicalTrials.gov API v2 | v5.22.0
  Total studies found: {total}

STUDY OVERVIEW
────────────────────────────────────────

  | # | NCT ID       | Title (abbreviated)        | Sponsor     | Status    | Enrollment | Completion |
  |---|-------------|---------------------------|-------------|-----------|-----------|------------|
  | 1 | NCT12345678 | Randomized Trial of...     | Medtronic   | Completed | 200       | 2024-06    |
  | 2 | NCT23456789 | Prospective Study of...    | DePuy       | Recruiting| 150       | 2026-12    |
  | 3 | NCT34567890 | Post-Market Surveillance... | Stryker     | Active    | 500       | 2025-09    |

DETAILED RESULTS
────────────────────────────────────────

  Study 1: {Full Title}
  ─────────────────
  NCT ID: {nctId} | Status: {status}
  Sponsor: {organization}
  Dates: {start} to {completion}

  Design:
    Type: Interventional | Phase: N/A (typical for devices)
    Allocation: Randomized | Model: Parallel
    Purpose: Treatment | Masking: Single-blind
    Enrollment: {count} ({actual/estimated})

  Device Intervention:
    Name: {device_name}
    Description: {device_description}

  Primary Outcomes:
    1. {measure} — Timeframe: {timeFrame}
    2. {measure} — Timeframe: {timeFrame}

  Conditions: {condition1}; {condition2}

  Summary: {briefSummary}

  URL: https://clinicaltrials.gov/study/{nctId}

  ---

  Study 2: ...

CLINICAL EVIDENCE ANALYSIS
────────────────────────────────────────

  Based on the {total} studies found:

  **Study Design Patterns:**
  - Most common design: {randomized/prospective/retrospective}
  - Typical enrollment: {range}
  - Typical duration: {range}
  - Most common endpoints: {list}

  **Relevance to Your 510(k):**
  - {N} completed studies with results — potential clinical evidence sources
  - {N} recruiting studies — indicates active clinical interest in this device type
  - Common primary outcomes: {list} — these may be expected by FDA reviewers
  - Typical comparators: {predicate devices or standard of care}

  {If no device trials found:}
  No clinical trials specifically for this device type were found.
  This may indicate:
  - The device class relies primarily on bench/preclinical testing
  - Clinical evidence may come from published literature instead
  - Consider: /fda:literature {search term} for published evidence

NEXT STEPS
────────────────────────────────────────

  - View full study details: https://clinicaltrials.gov/study/{nctId}
  - For published evidence: `/fda:literature {search term}`
  - To draft clinical section: `/fda:draft clinical --project NAME`
  - For testing strategy: `/fda:test-plan --product-code CODE`

────────────────────────────────────────
  Data source: ClinicalTrials.gov (U.S. National Library of Medicine)
  This report is AI-generated. Verify independently.
  Not regulatory advice.
────────────────────────────────────────
```

## Step 4: Save Results (--save)

If `--save` is specified, write results to `$PROJECTS_DIR/$PROJECT_NAME/clinical_trials.json`:

```json
{
  "query": {"term": "cervical fusion cage", "sponsor": null, "status": "all"},
  "total_results": 42,
  "studies": [
    {
      "nct_id": "NCT12345678",
      "title": "...",
      "sponsor": "...",
      "status": "COMPLETED",
      "enrollment": 200,
      "design": {"allocation": "RANDOMIZED", "model": "PARALLEL"},
      "primary_outcomes": [{"measure": "Fusion Rate", "timeFrame": "12 months"}],
      "device_interventions": [{"name": "...", "description": "..."}],
      "url": "https://clinicaltrials.gov/study/NCT12345678"
    }
  ],
  "queried_at": "2026-02-08T12:00:00Z"
}
```



## Output Format

### Sources Checked

Append a sources table to every output showing which external APIs were queried and their status. See [CONNECTORS.md](../CONNECTORS.md) for the standard format. Only include rows for sources this command actually uses.

## Error Handling

- **No results**: "No clinical trials found for this search. Try broader terms or check the device/condition name."
- **Rate limited (429)**: "ClinicalTrials.gov rate limit reached. Wait 60 seconds and try again."
- **API timeout**: Retry once. ClinicalTrials.gov can be slow for complex queries.
- **No search term**: Show usage examples:
  - `/fda:trials cervical fusion cage`
  - `/fda:trials --product-code OVE --status completed`
  - `/fda:trials wound dressing --sponsor "3M" --with-results`
