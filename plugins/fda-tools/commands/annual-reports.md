---
name: annual-reports
description: Track PMA annual report obligations per 21 CFR 814.84 -- due dates, required sections, compliance calendar, and risk assessment
allowed-tools:
  - Bash
  - Read
  - Write
  - Glob
  - Grep
  - AskUserQuestion
argument-hint: "--pma P170019 [--calendar] [--compliance-status] [--batch PMA1,PMA2] [--output FILE]"
---

# PMA Annual Report Compliance Calendar

> **Important**: This command assists with FDA regulatory workflows but does not provide regulatory advice. Output should be reviewed by qualified regulatory professionals before being relied upon for submission decisions.

Track PMA annual report obligations per 21 CFR 814.84. Calculates due dates based on approval anniversary, determines required reporting sections based on device characteristics, generates compliance calendars, and identifies compliance risks.

## Arguments

| Flag | Description | Example |
|------|-------------|---------|
| `--pma NUMBER` | PMA number to analyze | `--pma P170019` |
| `--batch LIST` | Multiple PMAs (comma-separated) | `--batch P170019,P200024` |
| `--calendar` | Show full calendar view | (flag) |
| `--compliance-status` | Show compliance risks only | (flag) |
| `--years-forward N` | Years to project (default 3) | `--years-forward 5` |
| `--output FILE` | Save to file | `--output calendar.json` |
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

## Step 1: Generate Calendar

### Single PMA

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/annual_report_tracker.py \
  --pma "$PMA_NUMBER" \
  --years-forward 3 \
  $( [ "$REFRESH" = "true" ] && echo "--refresh" ) \
  --json
```

### Batch PMAs

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/annual_report_tracker.py \
  --batch "$PMA_LIST" \
  --json
```

## Step 2: Present Results

```
  PMA Annual Report Compliance Calendar
  {PMA_NUMBER} -- {device_name}
------------------------------------------------------------
  Generated: {date} | CFR: 21 CFR 814.84 | v5.33.0
  Approval Date: {date} | Grace Period: 60 days

NEXT DUE DATE
------------------------------------------------------------
  Report #{N}
  Anniversary: {date}
  Grace Deadline: {date}
  Reporting Period: {start} to {end}

REQUIRED REPORT SECTIONS (21 CFR 814.84(b))
------------------------------------------------------------
  [REQUIRED] Device Distribution Data (21 CFR 814.84(b)(1))
  [REQUIRED] Summary of Device Modifications (21 CFR 814.84(b)(2))
  [REQUIRED] Corrections and Removals (21 CFR 814.84(b)(3))
  [REQUIRED] Adverse Event Summaries (21 CFR 814.84(b)(4))
  [REQUIRED] Clinical Studies / PAS (21 CFR 814.84(b)(5))
  [REQUIRED] Manufacturing Changes (21 CFR 814.84(b)(6))
  [CONDITIONAL] Sterilization Failures (21 CFR 814.84(b)(7))
  [CONDITIONAL] Other Information (21 CFR 814.84(b)(8))

CALENDAR
------------------------------------------------------------
    #  Due Date    Grace       Status
   ---  ----------  ----------  ----------
     1  {date}      {date}      past_due
     2  {date}      {date}      past_due
     ...
     N  {date}      {date}      due_now
   N+1  {date}      {date}      future

COMPLIANCE RISKS
------------------------------------------------------------
  [{severity}] {description}

------------------------------------------------------------
  Annual report compliance is not publicly tracked by FDA.
  This calendar is for planning purposes only.
------------------------------------------------------------
```

## Annual Report Requirements Reference (21 CFR 814.84)

### Timing
- Due within **60 days** of approval anniversary
- First report: 1 year after original approval
- Frequency: Annual (every approval anniversary)

### Required Sections
1. **Device Distribution** - Units distributed, returned, complaints received
2. **Device Modifications** - Supplements and 30-day notices filed
3. **Corrections/Removals** - Recalls per 21 CFR Part 806
4. **Adverse Events** - MDR summaries per 21 CFR Part 803
5. **Clinical Studies** - PAS updates, voluntary study progress
6. **Manufacturing Changes** - Non-supplement process changes
7. **Sterilization Failures** - For sterile devices only
8. **Other** - Per conditions of approval

### Non-Compliance Consequences
- FDA may issue warning letters
- Potential suspension of PMA
- Potential withdrawal of PMA approval

## Error Handling

- **No approval date**: "Cannot determine approval date for annual report calculations."
- **API unavailable**: Use cached data where available.

## Examples

```bash
# Full compliance calendar
/fda-tools:annual-reports --pma P170019

# Compliance status only
/fda-tools:annual-reports --pma P170019 --compliance-status

# Batch calendar for multiple PMAs
/fda-tools:annual-reports --batch P170019,P200024,P160035

# Project 5 years forward
/fda-tools:annual-reports --pma P170019 --years-forward 5

# Save JSON
/fda-tools:annual-reports --pma P170019 --output ~/reports/annual_calendar.json
```
