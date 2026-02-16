---
name: approval-probability
description: Score PMA supplement approval likelihood using decision tree classification on historical data with risk flags and recommended mitigations
allowed-tools:
  - Bash
  - Read
  - Write
  - Glob
  - Grep
  - AskUserQuestion
argument-hint: "--pma P170019 [--supplement S015] [--historical] [--train] [--output FILE]"
---

# Approval Probability Scorer

> **Important**: This command assists with FDA regulatory workflows but does not provide regulatory advice. Output should be reviewed by qualified regulatory professionals before being relied upon for submission decisions.

Score supplement approval probability using decision tree classification on historical PMA supplement data. Provides approval probability (0-100%), risk flags, positive factors, and recommended mitigations.

## Arguments

| Flag | Description | Example |
|------|-------------|---------|
| `--pma NUMBER` | PMA to analyze supplements for | `--pma P170019` |
| `--supplement SNUM` | Score specific supplement | `--supplement S015` |
| `--historical` | Show historical outcome analysis | (flag) |
| `--train` | Train/retrain the model | (flag) |
| `--output FILE` | Save to file | `--output scores.json` |
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

## Step 1: Run Analysis

### Score All Supplements

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/approval_probability.py \
  --pma "$PMA_NUMBER" \
  --json
```

### Score Specific Supplement

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/approval_probability.py \
  --pma "$PMA_NUMBER" \
  --supplement "$SUPPLEMENT_NUMBER" \
  --json
```

### Historical Outcome Analysis

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/approval_probability.py \
  --pma "$PMA_NUMBER" \
  --historical \
  --json
```

## Step 2: Present Results

```
  Supplement Approval Probability Analysis
  {PMA_NUMBER} -- {device_name}
------------------------------------------------------------
  Generated: {date} | Model: {model_type} v{version}

AGGREGATE ANALYSIS
------------------------------------------------------------
  Avg Approval Probability: {avg}%
  Range: {min}% - {max}%
  Classification Accuracy: {accuracy}%

SUPPLEMENT SCORES
------------------------------------------------------------
  Supp   | Type                 | Prob   | Status
  ------ | -------------------- | ------ | --------
  S001   | 180_day              | 92.0%  | [APPROVED] CORRECT
  S008   | panel_track          | 66.0%  | [DENIED]   CORRECT
  ...

RISK FLAGS
------------------------------------------------------------
  Prior Denial History: -15% (Address all prior deficiency reasons)
  Panel-Track Required: -12% (Prepare comprehensive data packages)

------------------------------------------------------------
  This analysis is AI-generated from public FDA data.
  Independent verification by qualified RA professionals required.
------------------------------------------------------------
```

## Baseline Approval Rates

| Supplement Type | Baseline Rate |
|----------------|---------------|
| 30-Day Notice | 97% |
| PAS-Related | 95% |
| Labeling | 94% |
| Manufacturing | 93% |
| 180-Day | 92% |
| Real-Time | 88% |
| Design Change | 85% |
| Indication Expansion | 82% |
| Panel-Track | 78% |

## Risk Factors

| Factor | Penalty | Mitigation |
|--------|---------|------------|
| No Clinical Data | -10% | Provide clinical evidence or literature |
| Prior Denial | -15% | Address all prior deficiency reasons |
| Panel-Track Required | -12% | Comprehensive clinical/preclinical data |
| Novel Indication | -10% | Comparative analysis + strong evidence |
| High Supplement Velocity | -5% | Consolidate changes when possible |

## Error Handling

- **No supplements**: Reports zero supplements found
- **Missing supplement**: Error message with available supplement list
- **API unavailable**: Uses cached data
