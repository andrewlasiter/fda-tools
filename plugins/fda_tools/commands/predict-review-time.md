---
name: predict-review-time
description: Predict PMA or supplement review duration using ML models trained on historical FDA approval timelines with confidence intervals and risk factor analysis
allowed-tools:
  - Bash
  - Read
  - Write
  - Glob
  - Grep
  - AskUserQuestion
argument-hint: "--pma P170019 [--product-code NMH] [--historical] [--train] [--output FILE]"
---

# Predict Review Time

> **Important**: This command assists with FDA regulatory workflows but does not provide regulatory advice. Output should be reviewed by qualified regulatory professionals before being relied upon for submission decisions.

Predict FDA review duration for PMA submissions using machine learning models trained on historical approval timelines. Provides expected review days, confidence intervals, risk factor analysis, and milestone predictions.

## Arguments

| Flag | Description | Example |
|------|-------------|---------|
| `--pma NUMBER` | PMA to predict review time for | `--pma P170019` |
| `--product-code CODE` | Predict for new submission by product code | `--product-code NMH` |
| `--historical` | Show historical review time analysis | (flag) |
| `--train` | Train/retrain the prediction model | (flag) |
| `--output FILE` | Save to file | `--output prediction.json` |
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

### Single PMA Review Time Prediction

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/review_time_predictor.py \
  --pma "$PMA_NUMBER" \
  --json
```

### Product Code Historical Analysis

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/review_time_predictor.py \
  --product-code "$PRODUCT_CODE" \
  --historical \
  --json
```

### New Submission Prediction (by Product Code)

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/review_time_predictor.py \
  --product-code "$PRODUCT_CODE" \
  --json
```

### Train/Retrain Model

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/review_time_predictor.py \
  --train \
  --json
```

## Step 2: Present Results

```
  PMA Review Time Prediction
  {PMA_NUMBER} -- {device_name}
------------------------------------------------------------
  Generated: {date} | Model: {model_type} v{version}

PREDICTION
------------------------------------------------------------
  Expected Review:  {expected_days} days ({expected_months} months)
  80% Confidence:   {lower_days}-{upper_days} days
  Model Confidence: {confidence}%

RISK FACTORS
------------------------------------------------------------
  {factor_label}: +{impact_days} days
  {factor_label}: -{impact_days} days
  ...

ADJUSTMENTS (from baseline)
------------------------------------------------------------
  Baseline ({panel}):     {baseline_days} days
  {adjustment_label}:     {impact} days
  Total Adjustment:       {total_adj} days

------------------------------------------------------------
  This prediction is AI-generated from public FDA data.
  Independent verification by qualified RA professionals required.
------------------------------------------------------------
```

## Risk Factor Reference

| Factor | Impact | Description |
|--------|--------|-------------|
| Novel Technology | +60 days | First-of-kind or breakthrough device |
| Complex Clinical | +90 days | Large RCT, long follow-up, adaptive design |
| Advisory Panel Meeting | +75 days | Device requires panel review |
| Combination Product | +45 days | Drug-device or biologic-device |
| Pediatric Indication | +30 days | Pediatric patient population |
| Expedited Review | -60 days | Breakthrough or priority pathway |
| Applicant Experience | -30 days | Prior PMA approval experience |

## Model Types

- **sklearn_gradient_boosting**: ML model (requires scikit-learn, 10+ training examples)
- **statistical_baseline**: Rule-based model using panel-specific empirical baselines

## Error Handling

- **No PMA data**: Reports error with available cache status
- **No training data**: Uses empirical baseline model
- **API unavailable**: Falls back to cached data
