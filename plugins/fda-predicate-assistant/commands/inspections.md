---
description: Look up FDA inspection history, CFR citations, compliance actions, and import refusals for device manufacturers
allowed-tools: Bash, Read, Glob, Grep, Write, WebFetch, WebSearch
argument-hint: "<company name or FEI number> [--citations] [--compliance] [--imports] [--product-code CODE] [--years RANGE]"
---

# FDA Inspection & Enforcement Intelligence

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

You are looking up **FDA enforcement intelligence** using the FDA Data Dashboard API. This provides data from FDA inspections, CFR citations, compliance actions (warning letters, injunctions, seizures), and import refusals — information NOT available through openFDA.

## Check for API Credentials

Read the user's local settings file:

```bash
cat ~/.claude/fda-predicate-assistant.local.md 2>/dev/null
```

Look for `fda_dashboard_user` and `fda_dashboard_key` in the YAML frontmatter.

If credentials are not configured:

```
  FDA Data Dashboard API credentials are not configured.

  The FDA Data Dashboard API requires free credentials from FDA.
  To register:

    1. Visit the FDA Data Dashboard: https://datadashboard.fda.gov
    2. Click "API Documentation" at the bottom of the page
    3. Follow the link to the OII Unified Logon application
    4. Register with your email, name, and organization
    5. You'll receive an Authorization-Key via email

  Then configure the plugin:

    /fda:configure --dashboard-key
```

If credentials are not available, you can still provide useful guidance based on publicly available inspection data from the FDA website, but you cannot make programmatic API calls. Inform the user and offer to search the FDA website manually.

## Parse Arguments

Parse `$ARGUMENTS` for:
- **Company name or FEI number** — Required. The firm to look up
- `--citations` — Include CFR citation details from inspections
- `--compliance` — Include compliance actions (warning letters, injunctions, seizures)
- `--imports` — Include import refusal history
- `--product-code CODE` — Filter import refusals by product code
- `--years RANGE` — Fiscal year filter (e.g., `2023-2025`)
- `--all` — Include all data types (citations + compliance + imports)

If no flags are specified, default to showing inspection classifications only.

## API Configuration

```
BASE_URL: https://api-datadashboard.fda.gov/v1
HEADERS:
  Content-Type: application/json
  Authorization-User: {fda_dashboard_user}
  Authorization-Key: {fda_dashboard_key}
```

## Step 1: Inspection Classifications

Query the inspections_classifications endpoint:

```bash
curl -s -X POST "https://api-datadashboard.fda.gov/v1/inspections_classifications" \
  -H "Content-Type: application/json" \
  -H "Authorization-User: $FDA_DASHBOARD_USER" \
  -H "Authorization-Key: $FDA_DASHBOARD_KEY" \
  -d '{
    "sort": "InspectionEndDate",
    "sortorder": "DESC",
    "filters": {
      "ProductType": ["Devices"],
      "LegalName": ["COMPANY_NAME"]
    },
    "columns": ["LegalName", "FEINumber", "City", "State", "CountryName", "InspectionEndDate", "Classification", "ClassificationCode", "PostedCitations", "ProjectArea"],
    "rows": 50,
    "start": 1,
    "returntotalcount": true
  }'
```

If `--years` is provided, add fiscal year filter:
```json
"FiscalYear": ["2023", "2024", "2025"]
```

If the argument looks like an FEI number (all digits, 7-10 chars), use `FEINumber` instead of `LegalName`.

## Step 2: CFR Citations (if --citations or --all)

For each inspection with `PostedCitations: true`, query the citations endpoint:

```bash
curl -s -X POST "https://api-datadashboard.fda.gov/v1/inspections_citations" \
  -H "Content-Type: application/json" \
  -H "Authorization-User: $FDA_DASHBOARD_USER" \
  -H "Authorization-Key: $FDA_DASHBOARD_KEY" \
  -d '{
    "sort": "InspectionEndDate",
    "sortorder": "DESC",
    "filters": {
      "LegalName": ["COMPANY_NAME"]
    },
    "columns": ["LegalName", "InspectionEndDate", "ActCFRNumber", "ShortDescription", "LongDescription"],
    "rows": 100,
    "start": 1,
    "returntotalcount": true
  }'
```

## Step 3: Compliance Actions (if --compliance or --all)

```bash
curl -s -X POST "https://api-datadashboard.fda.gov/v1/compliance_actions" \
  -H "Content-Type: application/json" \
  -H "Authorization-User: $FDA_DASHBOARD_USER" \
  -H "Authorization-Key: $FDA_DASHBOARD_KEY" \
  -d '{
    "sort": "ActionTakenDate",
    "sortorder": "DESC",
    "filters": {
      "ProductType": ["Devices"],
      "LegalName": ["COMPANY_NAME"]
    },
    "columns": ["LegalName", "ActionType", "ActionTakenDate", "Center", "CaseInjunctionID"],
    "rows": 50,
    "start": 1,
    "returntotalcount": true
  }'
```

## Step 4: Import Refusals (if --imports or --all)

```bash
curl -s -X POST "https://api-datadashboard.fda.gov/v1/import_refusals" \
  -H "Content-Type: application/json" \
  -H "Authorization-User: $FDA_DASHBOARD_USER" \
  -H "Authorization-Key: $FDA_DASHBOARD_KEY" \
  -d '{
    "sort": "RefusalDate",
    "sortorder": "DESC",
    "filters": {
      "ProductType": ["Devices"],
      "LegalName": ["COMPANY_NAME"]
    },
    "columns": ["LegalName", "CountryName", "ProductCode", "RefusalDate", "RefusalCharges"],
    "rows": 50,
    "start": 1,
    "returntotalcount": true
  }'
```

If `--product-code` is provided, add to filters:
```json
"ProductCode": ["KGN"]
```

## Output Format

Present results using the standard FDA Professional CLI format:

```
  FDA Enforcement Intelligence
  {Company Name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Generated: {date} | v5.22.0
  Source: FDA Data Dashboard API

INSPECTION HISTORY
────────────────────────────────────────

  | Date       | Classification | Citations | Project Area       |
  |------------|---------------|-----------|-------------------|
  | 2025-03-15 | VAI           | Yes       | BIMO              |
  | 2024-06-01 | NAI           | No        | Pre-Approval      |
  | 2023-11-20 | OAI           | Yes       | Compliance FU     |

  Summary: {N} inspections ({N} NAI, {N} VAI, {N} OAI)

  Facilities:
  | FEI        | Location              |
  |------------|----------------------|
  | 3012345678 | Minneapolis, MN, US  |
  | 9876543210 | Galway, Ireland      |

CFR CITATIONS (if --citations)
────────────────────────────────────────

  | Date       | CFR Section    | Description                          |
  |------------|---------------|--------------------------------------|
  | 2025-03-15 | 21 CFR 820.30 | Design Controls                      |
  | 2025-03-15 | 21 CFR 820.90 | Nonconforming Product                |
  | 2023-11-20 | 21 CFR 820.75 | Process Validation                   |

  Most cited: 21 CFR 820.30 (Design Controls) — {N} times

COMPLIANCE ACTIONS (if --compliance)
────────────────────────────────────────

  | Date       | Action Type     | Case ID       |
  |------------|----------------|---------------|
  | 2023-12-01 | Warning Letter  | INJ-2023-001  |

  **WARNING**: This firm has {N} compliance action(s) on record.
  Review the warning letter for deficiency patterns relevant to your device type.

IMPORT REFUSALS (if --imports)
────────────────────────────────────────

  | Date       | Country | Product Code | Charges                        |
  |------------|---------|-------------|-------------------------------|
  | 2024-08-15 | China   | KGN         | Adulteration - 21 USC 351(h)  |

RISK ASSESSMENT
────────────────────────────────────────

  Based on the enforcement data:

  - **Inspection trend**: {Improving/Stable/Declining} — {rationale}
  - **Quality system risk**: {Low/Medium/High} — {based on OAI count, citation patterns}
  - **Relevance to your submission**: {Context-specific note if product code or device type matches}

  {If predicate manufacturer has OAI or warning letters:}
  **NOTE**: If this is a predicate device manufacturer, consider whether FDA
  enforcement history affects your SE argument. FDA reviewers may scrutinize
  predicates from manufacturers with significant compliance issues.

NEXT STEPS
────────────────────────────────────────

  {Context-dependent recommendations:}
  - If OAI found: "Review the specific citations — they may indicate areas where FDA expects rigorous documentation"
  - If warning letters found: "Analyze the warning letter topics — they signal current FDA enforcement priorities"
  - If clean record: "No enforcement concerns identified for this manufacturer"
  - For deeper analysis: `/fda:safety {company}` for MAUDE events and recalls

────────────────────────────────────────
  Data source: FDA Data Dashboard (datadashboard.fda.gov)
  This report is AI-generated. Verify independently.
  Not regulatory advice.
────────────────────────────────────────
```



## Output Format

### Sources Checked

Append a sources table to every output showing which external APIs were queried and their status. See [CONNECTORS.md](../CONNECTORS.md) for the standard format. Only include rows for sources this command actually uses.

## Error Handling

- **401 Unauthorized** — Credentials invalid or expired. Guide user to re-register.
- **No results** — Company name may not match exactly. Try partial name or FEI number.
- **API timeout** — The Data Dashboard API can be slow. Retry once after 5 seconds.
- **No credentials configured** — Offer to search FDA website manually via WebFetch, or guide to credential setup.
