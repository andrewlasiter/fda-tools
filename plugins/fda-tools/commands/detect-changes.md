---
name: detect-changes
description: Detect and track changes in PMA data between refresh cycles with diff generation, significance scoring, and change history logging
allowed-tools:
  - Bash
  - Read
  - Write
  - Glob
  - Grep
  - AskUserQuestion
argument-hint: "--pma P170019 [--since YYYY-MM-DD] [--change-types supplements,maude,decisions] [--output changes.json]"
---

# FDA Change Detection Engine

> **Important**: This command assists with FDA regulatory workflows but does not provide regulatory advice. Detected changes should be verified by qualified regulatory professionals before action.

Detect changes in PMA data between refresh cycles. Tracks new supplements, decision code changes, AO statement updates, MAUDE event spikes, and more with significance scoring (0-100) and before/after snapshots.

## Arguments

| Flag | Description | Example |
|------|-------------|---------|
| `--pma P_NUMBER` | PMA number to check | `--pma P170019` |
| `--since YYYY-MM-DD` | Compare against date | `--since 2024-01-01` |
| `--change-types TYPES` | Filter change types | `--change-types supplements,maude` |
| `--output FILE` | Output file path | `--output changes.json` |
| `--history` | Show change history | (flag) |
| `--report` | Generate full change report | (flag) |

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

## Step 1: Detect Changes

### Basic Change Detection

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/change_detection.py \
  --pma "$PMA_NUMBER" --json
```

### Changes Since Specific Date

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/change_detection.py \
  --pma "$PMA_NUMBER" --since "$SINCE_DATE" --json
```

### Filtered by Change Type

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/change_detection.py \
  --pma "$PMA_NUMBER" --change-types "supplements,decisions" --json
```

## Step 2: Generate Full Report

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/change_detection.py \
  --pma "$PMA_NUMBER" --report --output "$OUTPUT_PATH" --json
```

## Step 3: View Change History

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/change_detection.py \
  --pma "$PMA_NUMBER" --history --json
```

## Step 4: Present Results

```
  FDA Change Detection Report
  PMA: P170019
============================================================
  Status:            COMPLETED
  Total Changes:     {N}
  Max Significance:  {N}/100
  Previous Snapshot: 2024-01-10T12:00:00Z

  CHANGES (sorted by significance):
------------------------------------------------------------
  [90] Decision Code Change
       Before: APPR  After: WDRN
       Impact: Critical -- indicates regulatory status change

  [75] AO Statement Update
       Approval order statement modified
       Impact: May indicate new conditions of approval

  [60] New Supplement S015
       Type: 180-Day Supplement
       Reason: New indication expansion
       Impact: May indicate device evolution

  RECOMMENDATIONS:
------------------------------------------------------------
  [HIGH] Review Decision Code Change immediately.
         Critical -- indicates regulatory status change.

  [MEDIUM] Monitor AO Statement Update.
           May indicate new conditions of approval.
============================================================
```

## Change Types

| Type | Base Significance | Description |
|------|-------------------|-------------|
| `decision_code_change` | 90 | Decision code changed (APPR/DENY/WDRN) |
| `recall_event` | 85 | New recall event detected |
| `maude_spike` | 80 | >20% increase in adverse events |
| `ao_statement_update` | 75 | Approval order statement modified |
| `new_supplement` | 60 | New supplement filed or approved |
| `supplement_count_change` | 50 | Total supplement count changed |
| `applicant_change` | 40 | Manufacturer/applicant changed |
| `device_name_change` | 30 | Trade name changed |

## Significance Scoring (0-100)

Base scores are modified by:
- Decision denial/withdrawal: +10
- Safety-related supplement: +15
- Denied supplement: +10
- MAUDE spike >100%: +15
- MAUDE spike >50%: +10

## Error Handling

- **No previous snapshot**: Saves current data as baseline
- **API unavailable**: Uses cached data for comparison
- **Missing fields**: Skips comparison for that field
