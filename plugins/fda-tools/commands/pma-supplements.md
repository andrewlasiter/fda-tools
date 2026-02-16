---
name: pma-supplements
description: Track PMA supplement lifecycle -- regulatory classification, change impact analysis, risk flags, and compliance monitoring per 21 CFR 814.39
allowed-tools:
  - Bash
  - Read
  - Write
  - Glob
  - Grep
  - AskUserQuestion
argument-hint: "--pma P170019 [--impact] [--risk-flags] [--output FILE]"
---

# PMA Supplement Lifecycle Tracker

> **Important**: This command assists with FDA regulatory workflows but does not provide regulatory advice. Output should be reviewed by qualified regulatory professionals before being relied upon for submission decisions.

Track comprehensive supplement lifecycle for PMA devices. Classifies supplements by regulatory type (21 CFR 814.39), analyzes cumulative change impact, detects risk flags, tracks supplement dependencies, and generates compliance intelligence.

## Arguments

| Flag | Description | Example |
|------|-------------|---------|
| `--pma NUMBER` | PMA number to analyze | `--pma P170019` |
| `--impact` | Show change impact analysis only | (flag) |
| `--risk-flags` | Show risk flags only | (flag) |
| `--output FILE` | Save report to file | `--output supps.json` |
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

## Step 1: Validate Input

If no `--pma` provided, ask:

```
Which PMA would you like to track supplements for?

Enter a PMA number (e.g., P170019):
```

Validate format: starts with P, followed by 6 digits.

## Step 2: Generate Supplement Report

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/supplement_tracker.py \
  --pma "$PMA_NUMBER" \
  $( [ "$REFRESH" = "true" ] && echo "--refresh" ) \
  --json
```

## Step 3: Present Results

### Full Report Format

```
  PMA Supplement Tracking Report
  {PMA_NUMBER} -- {device_name}
------------------------------------------------------------
  Generated: {date} | Applicant: {applicant} | v5.33.0

SUPPLEMENT SUMMARY
------------------------------------------------------------
  Total Supplements: {N}
  Approval Status: approved={N}, denied={N}, withdrawn={N}

REGULATORY TYPE DISTRIBUTION
------------------------------------------------------------
  180-Day Supplement (21 CFR 814.39(d)):  {N} ({%}%)
  Real-Time Supplement (21 CFR 814.39(c)):  {N} ({%}%)
  30-Day Notice (21 CFR 814.39(e)):  {N} ({%}%)
  Panel-Track Supplement (21 CFR 814.39(f)):  {N} ({%}%)
  PAS-Related (21 CFR 814.82):  {N} ({%}%)
  Manufacturing Change:  {N} ({%}%)
  Other/Unclassified:  {N} ({%}%)

CHANGE IMPACT ANALYSIS
------------------------------------------------------------
  Impact Level: {HIGH/MODERATE/LOW/MINIMAL}
  Burden Score: {N}
  Indication Changes: {N}
  Design Changes: {N}
  Manufacturing Changes: {N}
  High-Risk Supplements: {N}

FREQUENCY ANALYSIS
------------------------------------------------------------
  Average/year: {N}
  Active years: {start}-{end}
  Peak: {year} ({N} supplements)
  Trend: {accelerating/stable/decelerating}

RISK FLAGS
------------------------------------------------------------
  [{severity}] {description}

LIFECYCLE PHASES
------------------------------------------------------------
  {date}: Initial Approval
  {date}: First Indication Expansion
  {date}: First Design Modification
  {date}: PAS Reporting

TIMELINE (recent)
------------------------------------------------------------
  {date} | {status} | {description}

------------------------------------------------------------
  This report is AI-generated from public FDA data.
  Independent verification by qualified RA professionals required.
------------------------------------------------------------
```

### Impact Analysis Only (--impact)

Show only the change impact section.

### Risk Flags Only (--risk-flags)

Show only the risk flags section.

## Step 4: Export Options

If `--output FILE`:

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/supplement_tracker.py \
  --pma "$PMA_NUMBER" --output "$OUTPUT_FILE" --json
```

## Supplement Type Reference

### 180-Day Supplement (21 CFR 814.39(d))
- **Typical Changes:** Labeling, new/expanded indications, contraindications
- **Review Time:** Up to 180 days
- **Risk:** Low to Medium

### Real-Time Supplement (21 CFR 814.39(c))
- **Typical Changes:** Design changes with clinical data, manufacturing performance changes
- **Review Time:** 180+ days
- **Risk:** Medium to High

### 30-Day Notice (21 CFR 814.39(e))
- **Typical Changes:** Minor labeling, minor manufacturing without performance impact
- **Review Time:** 30 days
- **Risk:** Low

### Panel-Track Supplement (21 CFR 814.39(f))
- **Typical Changes:** Significant design or indication changes
- **Review Time:** 365+ days (requires advisory committee)
- **Risk:** High

### PAS-Related (21 CFR 814.82)
- **Typical Changes:** Post-approval study results, protocol amendments
- **Review Time:** 90 days
- **Risk:** Medium (compliance obligation)

## Error Handling

- **PMA not found**: "PMA {number} not found. Verify the PMA number."
- **No supplements**: "No supplements found for {PMA}. This PMA may not have any post-approval changes."
- **API errors**: "FDA API temporarily unavailable. Using cached data where available."

## Examples

```bash
# Full supplement report
/fda-tools:pma-supplements --pma P170019

# Change impact analysis only
/fda-tools:pma-supplements --pma P170019 --impact

# Risk flags only
/fda-tools:pma-supplements --pma P170019 --risk-flags

# Save JSON report
/fda-tools:pma-supplements --pma P170019 --output ~/reports/P170019_supplements.json
```
