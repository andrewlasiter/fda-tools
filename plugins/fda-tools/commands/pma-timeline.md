---
name: pma-timeline
description: Predict PMA approval timeline with milestones, risk factors, and confidence intervals from historical FDA data
allowed-tools:
  - Bash
  - Read
  - Write
  - Glob
  - Grep
  - AskUserQuestion
argument-hint: "--pma P170019 [--product-code NMH] [--submission-date 2026-06-01] [--historical]"
---

# PMA Approval Timeline Predictor

> **Important**: This command assists with FDA regulatory workflows but does not provide regulatory advice. Output should be reviewed by qualified regulatory professionals before being relied upon for submission decisions.

Predict FDA PMA review timelines based on device characteristics, historical approval data, and risk factors. Generates optimistic/realistic/pessimistic scenarios with milestone dates and confidence intervals.

## Arguments

| Flag | Description | Example |
|------|-------------|---------|
| `--pma NUMBER` | Device-specific prediction | `--pma P170019` |
| `--product-code CODE` | Product code prediction | `--product-code NMH` |
| `--submission-date DATE` | Planned submission date | `--submission-date 2026-06-01` |
| `--historical` | Show historical analysis only | (flag) |
| `--applicant NAME` | Applicant track record | `--applicant "Medtronic"` |
| `--output FILE` | Save to file | `--output timeline.json` |
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

## Step 1: Run Prediction

### Device-Specific Prediction

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/timeline_predictor.py \
  --pma "$PMA_NUMBER" \
  $( [ -n "$SUBMISSION_DATE" ] && echo "--submission-date $SUBMISSION_DATE" ) \
  --json
```

### Product Code Prediction

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/timeline_predictor.py \
  --product-code "$PRODUCT_CODE" \
  $( [ -n "$SUBMISSION_DATE" ] && echo "--submission-date $SUBMISSION_DATE" ) \
  --json
```

### Historical Analysis

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/timeline_predictor.py \
  --product-code "$PRODUCT_CODE" \
  --historical \
  --json
```

## Step 2: Present Results

```
  PMA Approval Timeline Prediction
  {PMA/Product Code} -- {device_name}
------------------------------------------------------------
  Generated: {date} | Panel: {committee} | v5.32.0

TIMELINE PREDICTION
------------------------------------------------------------
  Optimistic:   {days} days ({months} months)
  Realistic:    {days} days ({months} months)
  Pessimistic:  {days} days ({months} months)

KEY MILESTONES
------------------------------------------------------------
  Day {N} ({date}): Filing/RTA Decision
  Day {N} ({date}): MDUFA 180-Day Review Clock
  Day {N} ({date}): Scientific Review Complete
  Day {N} ({date}): Advisory Panel Meeting (if required)
  Day {N} ({date}): FDA Approval Decision

RISK FACTORS
------------------------------------------------------------
  [{probability}%] {factor} (+{days} days)
      {rationale}

SCENARIOS
------------------------------------------------------------
  Best Case: {days} days
    - Complete submission accepted first review
    - No major deficiencies
    - No advisory panel

  Expected: {days} days
    - Based on {N} historical PMAs
    - Risk adjustment: +{days} days

  Worst Case: {days} days
    - All risk factors materialize
    - Major deficiency likely
    - Advisory panel required

RECOMMENDATIONS
------------------------------------------------------------
  1. {recommendation}
  2. {recommendation}

HISTORICAL CONTEXT
------------------------------------------------------------
  PMAs Analyzed: {N}
  Historical Median: {days} days
  Year Range: {start}-{end}

------------------------------------------------------------
  This prediction is AI-generated from historical FDA data.
  Actual timelines vary significantly. Not regulatory advice.
------------------------------------------------------------
```

## Post-Approval Milestones (Phase 3 Integration)

For approved PMAs, the timeline includes post-approval obligations:

### Post-Approval Timeline
```
  POST-APPROVAL MILESTONES
  ------------------------------------------------------------
    Day {N} ({date}): Annual Report #1 Due (21 CFR 814.84)
    Day {N} ({date}): Annual Report #1 Grace Deadline (+60 days)
    Day {N} ({date}): PAS Protocol Submission (if required)
    Day {N} ({date}): PAS Enrollment Initiation
    Day {N} ({date}): PAS First Interim Report
    Day {N} ({date}): Annual Report #2 Due
    Day {N} ({date}): PAS 50% Enrollment Milestone
    Day {N} ({date}): Annual Report #3 Due
    Day {N} ({date}): PAS Enrollment Completion
    Day {N} ({date}): PAS Final Report Submission
```

### Generating Post-Approval Milestones

If the PMA has approval data, include post-approval milestones from Phase 3 modules:

```bash
# Get annual report due dates
cd "$FDA_PLUGIN_ROOT" && python3 scripts/annual_report_tracker.py \
  --pma "$PMA_NUMBER" --calendar --json

# Get PAS milestones (if PAS detected)
cd "$FDA_PLUGIN_ROOT" && python3 scripts/pas_monitor.py \
  --pma "$PMA_NUMBER" --milestones --json
```

Merge these into the main timeline view, sorted chronologically.

### Cross-Reference Commands

For detailed post-approval tracking, see:
```bash
# Full annual report compliance calendar
/fda-tools:annual-reports --pma P170019

# Post-approval study milestone tracking
/fda-tools:pas-monitor --pma P170019 --milestones

# Supplement lifecycle tracking
/fda-tools:pma-supplements --pma P170019
```

## Error Handling

- **No historical data**: Report limited prediction confidence and use empirical FDA baseline estimates
- **No SSED data**: Skip clinical complexity assessment, use product code defaults
- **API unavailable**: Use cached data if available
