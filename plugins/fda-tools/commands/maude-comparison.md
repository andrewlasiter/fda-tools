---
name: maude-comparison
description: Compare adverse event profiles across PMA devices using MAUDE data with outlier detection, safety signal alerts, and event frequency heatmaps
allowed-tools:
  - Bash
  - Read
  - Write
  - Glob
  - Grep
  - AskUserQuestion
argument-hint: "--pma P170019 [--compare P160035,P150009] [--product-code NMH] [--signals] [--heatmap] [--output FILE]"
---

# MAUDE Peer Comparison

> **Important**: This command assists with FDA regulatory workflows but does not provide regulatory advice. Output should be reviewed by qualified regulatory professionals before being relied upon for submission decisions.

Compare adverse event profiles across similar PMA devices using MAUDE (Manufacturer and User Facility Device Experience) data. Identifies event type frequency, severity distribution, reporting trends, statistical outliers, and safety signals.

## Arguments

| Flag | Description | Example |
|------|-------------|---------|
| `--pma NUMBER` | Primary PMA to compare | `--pma P170019` |
| `--compare LIST` | Comma-separated comparators | `--compare P160035,P150009` |
| `--product-code CODE` | Analyze by product code | `--product-code NMH` |
| `--signals` | Detect safety signals | (flag) |
| `--heatmap` | Generate event heatmap data | (flag) |
| `--output FILE` | Save to file | `--output comparison.json` |
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

## Step 1: Run Comparison

### PMA Peer Comparison (Auto-Discover Peers)

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/maude_comparison.py \
  --pma "$PMA_NUMBER" \
  --json
```

### PMA Comparison with Specific Comparators

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/maude_comparison.py \
  --pma "$PMA_NUMBER" \
  --compare "$COMPARATOR_LIST" \
  --json
```

### Product Code Safety Signals

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/maude_comparison.py \
  --product-code "$PRODUCT_CODE" \
  --signals \
  --json
```

### Event Heatmap Data

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/maude_comparison.py \
  --product-code "$PRODUCT_CODE" \
  --heatmap \
  --json
```

## Step 2: Present Results

```
  MAUDE Peer Comparison Analysis
  {PMA_NUMBER} -- {device_name}
------------------------------------------------------------
  Product Code: {code} | Devices Compared: {N}

PRIMARY DEVICE EVENTS
------------------------------------------------------------
  Total Events:   {N}
  Deaths:         {N}
  Injuries:       {N}
  Malfunctions:   {N}

PEER BENCHMARKS
------------------------------------------------------------
  Mean Total Events: {mean}
  Range: {min} - {max}

OUTLIER DETECTION
------------------------------------------------------------
  [HIGH] Death: count (N) is 2.3 std dev above peer mean (M)
  [MEDIUM] Malfunction: count (N) is 1.8 std dev below peer mean (M)

SAFETY SIGNALS
------------------------------------------------------------
  [CRITICAL] death_reports: N death report(s) found
  [WARNING] increasing_trend: 1.5x increase in recent years

COMPARATOR DEVICES
------------------------------------------------------------
  P160035: Device Name | Events: N
  P150009: Device Name | Events: N

------------------------------------------------------------
  This analysis is AI-generated from public MAUDE data.
  Independent verification by qualified RA professionals required.
------------------------------------------------------------
```

## Safety Signal Types

| Signal | Severity | Trigger |
|--------|----------|---------|
| Death Reports | CRITICAL | >= 3 death reports |
| Elevated Death Rate | CRITICAL | Death rate > 2x peer mean |
| High Malfunction Rate | WARNING | > 60% malfunction events |
| Increasing Trend | WARNING | Recent avg > 1.5x historical |
| High Event Volume | WARNING | Total events > 2x peer mean |
| High Injury Rate | CAUTION | > 40% injury events |

## Outlier Detection

Uses Z-score analysis (threshold: 2.0 standard deviations) to identify event types where the primary device significantly deviates from peer group benchmarks.

## Error Handling

- **No MAUDE data**: Reports zero events with advisory
- **No peer devices**: Performs single-device analysis
- **API unavailable**: Uses cached data if available
