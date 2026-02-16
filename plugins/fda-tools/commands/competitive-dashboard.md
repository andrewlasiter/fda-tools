---
name: competitive-dashboard
description: Generate market intelligence dashboard for PMA device categories with market share, approval trends, clinical endpoints, and interactive HTML output
allowed-tools:
  - Bash
  - Read
  - Write
  - Glob
  - Grep
  - AskUserQuestion
argument-hint: "--product-code NMH [--html dashboard.html] [--csv data.csv] [--summary] [--output FILE]"
---

# Competitive Intelligence Dashboard

> **Important**: This command assists with FDA regulatory workflows but does not provide regulatory advice. Output should be reviewed by qualified regulatory professionals before being relied upon for submission decisions.

Generate comprehensive market intelligence dashboards for PMA device categories. Analyzes market share by applicant, approval trends, clinical endpoints, supplement activity, and MAUDE safety profiles with HTML dashboard export.

## Arguments

| Flag | Description | Example |
|------|-------------|---------|
| `--product-code CODE` | FDA product code to analyze | `--product-code NMH` |
| `--html FILE` | Export HTML dashboard | `--html dashboard.html` |
| `--csv FILE` | Export CSV data table | `--csv data.csv` |
| `--summary` | Show concise market summary | (flag) |
| `--output FILE` | Save JSON data | `--output data.json` |
| `--refresh` | Force API refresh | (flag) |

## Resolve Plugin Root

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

## Step 1: Generate Dashboard

### Full Dashboard (Text)

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/competitive_dashboard.py \
  --product-code "$PRODUCT_CODE" \
  --json
```

### HTML Dashboard Export

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/competitive_dashboard.py \
  --product-code "$PRODUCT_CODE" \
  --html "$OUTPUT_HTML_PATH"
```

### CSV Data Export

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/competitive_dashboard.py \
  --product-code "$PRODUCT_CODE" \
  --csv "$OUTPUT_CSV_PATH"
```

### Concise Market Summary

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/competitive_dashboard.py \
  --product-code "$PRODUCT_CODE" \
  --summary \
  --json
```

## Step 2: Present Results

```
  PMA Competitive Intelligence Dashboard
  Product Code: {CODE}
------------------------------------------------------------
  Total PMAs:    {N}
  Applicants:    {N}
  Approval Rate: {N}%
  Year Range:    {start}-{end}

MARKET SHARE (by PMA Count)
------------------------------------------------------------
  Applicant                             | PMAs | Share
  ------------------------------------- | ---- | -----
  Company A                             |   12 | 35.3%
  Company B                             |    8 | 23.5%
  Company C                             |    5 | 14.7%
  Market Concentration: competitive (HHI: 1234)

APPROVAL TRENDS
------------------------------------------------------------
  2020:   3 ###
  2021:   5 #####
  2022:   4 ####
  2023:   7 #######
  Peak Year: 2023 (7 approvals)

MAUDE SAFETY SUMMARY
------------------------------------------------------------
  Total Events:   {N}
  Deaths:         {N} ({rate}%)
  Injuries:       {N} ({rate}%)
  Malfunctions:   {N}

RECENT APPROVALS
------------------------------------------------------------
  PMA        | Device                  | Applicant     | Date
  P230001    | Device Name             | Company A     | 20230615

------------------------------------------------------------
  This dashboard is AI-generated from public FDA data.
  Independent verification by qualified RA professionals required.
------------------------------------------------------------
```

## HTML Dashboard Features

The HTML dashboard includes:
- **Key metrics cards**: Total PMAs, applicants, approval rate, year span
- **Market share table**: With visual bar chart per applicant
- **Approval trends**: Year-by-year with visual bars
- **Recent approvals table**: Sortable with status badges
- **MAUDE safety summary**: Event counts and rates
- **Supplement activity**: Activity level across PMAs

## Market Concentration (HHI)

| HHI Score | Classification | Description |
|-----------|---------------|-------------|
| < 1500 | Competitive | Multiple active competitors |
| 1500-2500 | Moderately Concentrated | Few dominant players |
| > 2500 | Highly Concentrated | 1-2 dominant players |

## Error Handling

- **No PMA data**: Reports no approvals found for product code
- **No MAUDE data**: Safety section shows no data available
- **API unavailable**: Uses cached data if available
