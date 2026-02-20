---
name: pas-monitor
description: Monitor PMA Post-Approval Study obligations -- requirement detection, milestone tracking, compliance assessment, and alerts per 21 CFR 814.82
allowed-tools:
  - Bash
  - Read
  - Write
  - Glob
  - Grep
  - AskUserQuestion
argument-hint: "--pma P170019 [--milestones] [--compliance] [--alerts] [--output FILE]"
---

# Post-Approval Study (PAS) Monitor

> **Important**: This command assists with FDA regulatory workflows but does not provide regulatory advice. Output should be reviewed by qualified regulatory professionals before being relied upon for submission decisions.

Monitor post-approval study (PAS) obligations for PMA devices per 21 CFR 814.82. Detects PAS requirements from approval data and supplement history, tracks study milestones, assesses compliance status, and generates alerts for overdue or at-risk studies.

## Arguments

| Flag | Description | Example |
|------|-------------|---------|
| `--pma NUMBER` | PMA number to analyze | `--pma P170019` |
| `--batch LIST` | Multiple PMAs | `--batch P170019,P200024` |
| `--milestones` | Show milestone timeline only | (flag) |
| `--compliance` | Show compliance assessment only | (flag) |
| `--alerts` | Show alerts only | (flag) |
| `--output FILE` | Save to file | `--output pas.json` |
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

## Step 1: Generate PAS Report

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/pas_monitor.py \
  --pma "$PMA_NUMBER" \
  $( [ "$REFRESH" = "true" ] && echo "--refresh" ) \
  --json
```

## Step 2: Present Results

```
  Post-Approval Study (PAS) Monitoring Report
  {PMA_NUMBER} -- {device_name}
------------------------------------------------------------
  Generated: {date} | Applicant: {applicant} | v5.33.0
  PAS Required: YES/NO

PAS REQUIREMENTS
------------------------------------------------------------
  [continued_approval] Continued Approval Study
    CFR: 21 CFR 814.82(a)(2) | Source: ao_statement | Conf: 95%

  [section_522] Section 522 Post-Market Surveillance
    CFR: 21 CFR 822 | Source: supplement_history | Conf: 80%

PAS STATUS
------------------------------------------------------------
  Overall: in_progress
  Continued Approval Study: enrolling (3 related supplements)
  Section 522 Surveillance: protocol_review (1 related supplement)

MILESTONE TIMELINE
------------------------------------------------------------
  Milestone                      Expected    Actual      Status
  ------------------------------ ----------  ----------  ----------
  Protocol Submission             {date}      {date}     completed
  Protocol Approval by FDA        {date}      {date}     completed
  Enrollment Initiation           {date}      ---        overdue
  First Interim Report            {date}      ---        upcoming
  50% Enrollment Milestone        {date}      ---        future
  Enrollment Completion           {date}      ---        future
  Second Interim Report           {date}      ---        future
  Follow-up Completion            {date}      ---        future
  Final Report Submission         {date}      ---        future
  FDA Review Complete             {date}      ---        future

COMPLIANCE ASSESSMENT
------------------------------------------------------------
  Status: ON_TRACK
  Score: 45%
  Completed: 2/10 milestones
  Overdue: 1

ALERTS
------------------------------------------------------------
  [WARNING] Milestone 'Enrollment Initiation' is overdue. Expected by: {date}
  [INFO] Continued Approval Study detected. Source: ao_statement. Confidence: 95%

------------------------------------------------------------
  PAS data is inferred from public FDA supplement history.
  Cross-reference with internal study records for accuracy.
------------------------------------------------------------
```

## PAS Types Reference

### Continued Approval Study (21 CFR 814.82(a)(2))
- Required as condition of PMA approval
- Verifies long-term safety and effectiveness
- Typical duration: 5-7 years
- Non-compliance may lead to PMA withdrawal

### Section 522 Post-Market Surveillance (21 CFR 822)
- FDA-ordered post-market surveillance
- Required when questions about safety/effectiveness remain
- Typical duration: 3-5 years
- Mandatory compliance under federal law

### Pediatric Study
- Per Pediatric Medical Device Safety Act
- Evaluates safety in pediatric populations
- Often longer duration (7+ years)
- May be condition of approval

### Voluntary Study
- Manufacturer-initiated
- Additional clinical evidence gathering
- Variable duration and scope

## Compliance Risk Levels

| Status | Description |
|--------|-------------|
| COMPLIANT | All milestones met on schedule |
| ON_TRACK | Active progress, some milestones pending |
| AT_RISK | 1-2 required milestones overdue |
| NON_COMPLIANT | 3+ required milestones overdue |
| INSUFFICIENT_DATA | Not enough data to assess |

## Error Handling

- **No PAS detected**: "No PAS requirements found. This does not guarantee compliance -- verify with approval order."
- **No supplements**: "Cannot assess PAS from supplement data. Check internal study management records."
- **API unavailable**: Use cached data where available.

## Examples

```bash
# Full PAS report
/fda-tools:pas-monitor --pma P170019

# Milestone timeline only
/fda-tools:pas-monitor --pma P170019 --milestones

# Compliance assessment
/fda-tools:pas-monitor --pma P170019 --compliance

# Alerts only
/fda-tools:pas-monitor --pma P170019 --alerts

# Batch monitoring
/fda-tools:pas-monitor --batch P170019,P200024

# Save report
/fda-tools:pas-monitor --pma P170019 --output ~/reports/pas_report.json
```
