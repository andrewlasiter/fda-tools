---
name: clinical-requirements
description: Map clinical trial requirements from PMA precedent -- study design, enrollment, endpoints, follow-up, cost and timeline estimates
allowed-tools:
  - Bash
  - Read
  - Write
  - Glob
  - Grep
  - AskUserQuestion
argument-hint: "--pma P170019 [--compare P160035,P150009] [--product-code NMH] [--output FILE]"
---

# Clinical Trial Requirements Mapper

> **Important**: This command assists with FDA regulatory workflows but does not provide regulatory advice. Output should be reviewed by qualified regulatory professionals before being relied upon for submission decisions.

Map clinical trial requirements from PMA precedent. Analyzes SSED clinical sections to extract trial design patterns, enrollment targets, endpoints, follow-up durations, and data requirements. Generates cost and timeline estimates.

## Arguments

| Flag | Description | Example |
|------|-------------|---------|
| `--pma NUMBER` | PMA number to analyze | `--pma P170019` |
| `--compare LIST` | Compare with other PMAs | `--compare P160035,P150009` |
| `--product-code CODE` | Analyze all PMAs for product code | `--product-code NMH` |
| `--output FILE` | Save report to file | `--output reqs.json` |
| `--refresh` | Force refresh from API | (flag) |

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

## Step 1: Validate Input

If no `--pma` or `--product-code` provided, ask:

```
What would you like to analyze?

1. Specific PMA (e.g., P170019) -- Extract requirements from one PMA
2. Compare PMAs (e.g., P170019 vs P160035) -- Compare requirements across PMAs
3. Product code (e.g., NMH) -- Analyze all PMAs for a product code
```

## Step 2: Run Analysis

### Single PMA Analysis

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/clinical_requirements_mapper.py \
  --pma "$PMA_NUMBER" \
  --json
```

### Multi-PMA Comparison

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/clinical_requirements_mapper.py \
  --pma "$PRIMARY_PMA" \
  --compare "$COMPARATOR_LIST" \
  --json
```

### Product Code Analysis

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/clinical_requirements_mapper.py \
  --product-code "$PRODUCT_CODE" \
  --json
```

## Step 3: Present Results

Format the output using the standard FDA Professional CLI format:

```
  Clinical Trial Requirements Analysis
  {PMA_NUMBER} -- {device_name}
------------------------------------------------------------
  Generated: {date} | Product Code: {code} | v5.32.0

STUDY DESIGN REQUIREMENTS
------------------------------------------------------------
  Trial Type: {type} ({complexity})
  Blinding: {blinding}
  Control Arm: {control}
  Randomization: {yes/no}
  Multicenter: {yes/no}
  Adaptive Design: {yes/no}

ENROLLMENT REQUIREMENTS
------------------------------------------------------------
  Observed Sample Size: {N} patients
  Recommended (with margin): {N * 1.2} patients
  Clinical Sites: {sites}
  Geographic Scope: {scope}

ENDPOINT REQUIREMENTS
------------------------------------------------------------
  Primary: {endpoint text}
  Secondary: {endpoint text}
  Safety: {endpoint text}
  Success Criteria: {threshold}

FOLLOW-UP REQUIREMENTS
------------------------------------------------------------
  Observed: {duration}
  Recommended: {months} months
  Post-Approval Study: {required/not detected}

COST ESTIMATE
------------------------------------------------------------
  Per Patient: ${cost}
  Low: ${low}  |  Mid: ${mid}  |  High: ${high}
  Key Cost Drivers:
  - {driver 1}
  - {driver 2}

TIMELINE ESTIMATE
------------------------------------------------------------
  Startup: {months} months
  Enrollment: {months} months
  Follow-up: {months} months
  Analysis: {months} months
  TOTAL: {months} months (optimistic: {opt} / pessimistic: {pess})

DATA REQUIREMENTS
------------------------------------------------------------
  Interim Analysis: {yes/no}
  DSMB: {required/no}
  Core Lab: {required/no}
  CEC: {required/no}
  AE Standards: {list}

STATISTICAL REQUIREMENTS
------------------------------------------------------------
  Analysis Populations: {ITT, PP, etc.}
  Statistical Methods: {list}
  Power: {%}
  Alpha: {level}

------------------------------------------------------------
  This report is AI-generated from PMA SSED data.
  Verify with qualified regulatory professionals.
------------------------------------------------------------
```

## Step 4: Save Output (if --output)

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/clinical_requirements_mapper.py \
  --pma "$PMA_NUMBER" \
  --json \
  --output "$OUTPUT_FILE"
```

## Error Handling

- **No PMA data**: Report that SSED sections are not available and suggest running `/fda-tools:pma-intelligence --pma {number} --download-ssed --extract-sections` first
- **No clinical sections**: Report limited confidence and provide requirements based on device category defaults
- **API unavailable**: Use cached data if available, otherwise report API status

### Sources Checked

Append a sources table showing which data sources were consulted:

| Source | Status | Data Used |
|--------|--------|-----------|
| openFDA PMA API | {OK/Error} | PMA approval data |
| PMA SSED Cache | {Available/Missing} | Extracted clinical sections |
| Historical PMA Database | {N records} | Comparable PMA requirements |
