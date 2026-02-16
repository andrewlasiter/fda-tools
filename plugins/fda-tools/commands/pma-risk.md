---
name: pma-risk
description: Systematic FMEA-style risk assessment for PMA devices with Risk Priority Numbers, risk matrices, and evidence requirement mapping
allowed-tools:
  - Bash
  - Read
  - Write
  - Glob
  - Grep
  - AskUserQuestion
argument-hint: "--pma P170019 [--compare P160035,P150009] [--product-code NMH] [--output FILE]"
---

# PMA Risk Assessment

> **Important**: This command assists with FDA regulatory workflows but does not provide regulatory advice. Output should be reviewed by qualified regulatory professionals before being relied upon for submission decisions.

Perform systematic FMEA-style risk analysis for PMA devices. Identifies device, clinical, regulatory, and manufacturing risks from SSED safety sections. Generates risk matrices with Severity x Probability x Detectability scoring (RPN), maps high-priority risks to evidence requirements, and compares risk profiles across PMAs.

## Arguments

| Flag | Description | Example |
|------|-------------|---------|
| `--pma NUMBER` | PMA to assess | `--pma P170019` |
| `--compare LIST` | Compare risk profiles | `--compare P160035,P150009` |
| `--product-code CODE` | Risk landscape analysis | `--product-code NMH` |
| `--output FILE` | Save to file | `--output risk.json` |
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

## Step 1: Run Assessment

### Single PMA Risk Assessment

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/risk_assessment.py \
  --pma "$PMA_NUMBER" \
  --json
```

### Risk Profile Comparison

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/risk_assessment.py \
  --pma "$PMA_NUMBER" \
  --compare "$COMPARATOR_LIST" \
  --json
```

### Product Code Risk Landscape

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/risk_assessment.py \
  --product-code "$PRODUCT_CODE" \
  --json
```

## Step 2: Present Results

```
  PMA Risk Assessment Report
  {PMA_NUMBER} -- {device_name}
------------------------------------------------------------
  Generated: {date} | Panel: {committee} | Confidence: {%} | v5.32.0

RISK SUMMARY
------------------------------------------------------------
  Total Risks Identified: {N}
  HIGH Priority: {N}  |  MEDIUM: {N}  |  LOW: {N}
  Residual Risk Level: {HIGH/MODERATE/LOW}
  Categories: device={N}, clinical={N}, regulatory={N}, manufacturing={N}

RISK MATRIX (Probability vs Severity)
------------------------------------------------------------
           | Minor | Moderate | Serious | Critical | Catastrophic
  Frequent |  {ids}|   {ids}  |  {ids}  |  {ids}   |    {ids}
  Likely   |  {ids}|   {ids}  |  {ids}  |  {ids}   |    {ids}
  Possible |  {ids}|   {ids}  |  {ids}  |  {ids}   |    {ids}
  Unlikely |  {ids}|   {ids}  |  {ids}  |  {ids}   |    {ids}
  Rare     |  {ids}|   {ids}  |  {ids}  |  {ids}   |    {ids}

TOP RISKS BY RPN
------------------------------------------------------------
  Risk                            S   P   D    RPN  Priority
  ------------------------------ --- --- --- ----- --------
  {risk_label}                     4   3   3    36  HIGH
  {risk_label}                     3   2   3    18  MEDIUM
  ...

MITIGATION STRATEGIES
------------------------------------------------------------
  [{type}] {description}

EVIDENCE REQUIREMENTS (HIGH/MEDIUM priority)
------------------------------------------------------------
  {risk_label} [HIGH]:
    - {evidence requirement 1}
    - {evidence requirement 2}

------------------------------------------------------------
  This assessment is AI-generated from PMA SSED data.
  Independent risk analysis by qualified professionals required.
------------------------------------------------------------
```

## Risk Scoring Reference

### Severity Scale (S)
| Score | Label | Description |
|-------|-------|-------------|
| 1 | Minor | Temporary discomfort, no medical intervention |
| 2 | Moderate | Medical intervention required but non-serious |
| 3 | Serious | Hospitalization or significant disability |
| 4 | Critical | Life-threatening or permanent impairment |
| 5 | Catastrophic | Death or irreversible major disability |

### Probability Scale (P)
| Score | Label | Rate |
|-------|-------|------|
| 1 | Rare | < 0.01% |
| 2 | Unlikely | 0.01-0.1% |
| 3 | Possible | 0.1-1% |
| 4 | Likely | 1-10% |
| 5 | Frequent | > 10% |

### Risk Priority Number (RPN)
- **HIGH** (RPN >= 100): Immediate mitigation required
- **MEDIUM** (RPN 50-99): Mitigation recommended
- **LOW** (RPN < 50): Monitor and document

## Error Handling

- **No SSED safety data**: Report limited confidence, identify risks from device classification only
- **API unavailable**: Use cached data if available
- **No clinical data**: Skip AE-based probability estimation, use default values
