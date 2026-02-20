---
name: monitor-approvals
description: Configure and view FDA approval monitoring with product code watchlists, severity-classified alerts, deduplication, and daily/weekly digest generation
allowed-tools:
  - Bash
  - Read
  - Write
  - Glob
  - Grep
  - AskUserQuestion
argument-hint: "--watch-product-codes NMH,QAS [--frequency daily|weekly] [--severity-filter WARNING,CRITICAL] [--output alerts.txt]"
---

# FDA Approval Monitor

> **Important**: This command assists with FDA regulatory workflows but does not provide regulatory advice. Alerts are informational and should be verified by qualified regulatory professionals before action.

Monitor FDA PMA approvals, supplements, and recalls with configurable product code watchlists. Generates severity-classified alerts with deduplication and historical baseline comparison.

## Arguments

| Flag | Description | Example |
|------|-------------|---------|
| `--watch-product-codes CODES` | Add product codes to watchlist | `--watch-product-codes NMH,QAS` |
| `--remove-product-codes CODES` | Remove codes from watchlist | `--remove-product-codes QAS` |
| `--frequency TYPE` | Digest frequency | `--frequency weekly` |
| `--severity-filter LEVELS` | Filter alert severity | `--severity-filter WARNING,CRITICAL` |
| `--output FILE` | Output digest file | `--output alerts.txt` |
| `--show-watchlist` | Show current watchlist | (flag) |
| `--check` | Check for updates now | (flag) |
| `--digest` | Generate digest report | (flag) |
| `--history` | Show alert history | (flag) |

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

## Step 1: Configure Watchlist

### Add Product Codes

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/fda_approval_monitor.py \
  --watch-product-codes "$PRODUCT_CODES" --json
```

### View Watchlist

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/fda_approval_monitor.py \
  --show-watchlist --json
```

## Step 2: Check for Updates

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/fda_approval_monitor.py \
  --check --json
```

## Step 3: Generate Digest

### Daily Digest

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/fda_approval_monitor.py \
  --digest --frequency daily --json
```

### Weekly Digest with Output File

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/fda_approval_monitor.py \
  --digest --frequency weekly --output "$OUTPUT_PATH" --json
```

### Filtered by Severity

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/fda_approval_monitor.py \
  --digest --severity-filter "WARNING,CRITICAL" --json
```

## Step 4: View Alert History

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/fda_approval_monitor.py \
  --history --json
```

## Step 5: Present Results

```
============================================================
  FDA Approval Monitor - Daily Digest
============================================================
  Period: 2024-01-15 to 2024-01-16
  Total Alerts: {N}
  Watchlist: NMH, QAS

  [CRITICAL] ({N} alerts)
------------------------------------------------------------
  - MAUDE safety alert: {N} death report(s) for NMH
    Source: openFDA MAUDE API
    Detected: 2024-01-16T08:30:00

  [WARNING] ({N} alerts)
------------------------------------------------------------
  - Recall event RE-2024-001 for NMH: {reason}
    Source: openFDA Recall API
    Detected: 2024-01-16T08:30:00

  [INFO] ({N} alerts)
------------------------------------------------------------
  - New PMA P240001 (APPR) approved for NMH
    Source: openFDA PMA API
    Detected: 2024-01-16T08:30:00

============================================================
  DISCLAIMER: This digest is AI-generated from public FDA
  data. Independent verification required before action.
============================================================
```

## Alert Severity Levels

| Level | Description | MedWatch Alignment |
|-------|-------------|-------------------|
| CRITICAL | Class I recall, death reports | Serious injury/death events |
| WARNING | Class II recall, safety supplements | Labeling safety changes |
| INFO | New approval, routine update | Routine notification |

## Deduplication

- Each alert receives a unique dedup key based on type, PMA number, and data
- Seen keys are persisted to prevent repeat notifications
- Effectiveness target: >=99% deduplication rate

## Error Handling

- **Empty watchlist**: Prompts user to add product codes
- **API unavailable**: Skips source, continues monitoring other codes
- **No new alerts**: Reports clean status
