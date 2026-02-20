---
name: refresh-data
description: Trigger automated data refresh workflows for PMA data, MAUDE events, recalls, and supplements with intelligent TTL-based prioritization and audit trails
allowed-tools:
  - Bash
  - Read
  - Write
  - Glob
  - Grep
  - AskUserQuestion
argument-hint: "[--schedule daily|weekly|monthly] [--priority safety|all] [--dry-run] [--background] [--pma P170019] [--status]"
---

# FDA Data Refresh Orchestrator

> **Important**: This command assists with FDA regulatory workflows but does not provide regulatory advice. Output should be reviewed by qualified regulatory professionals before being relied upon for submission decisions.

Trigger automated data refresh workflows for PMA data with intelligent prioritization based on TTL tiers: 24h for safety-critical data (MAUDE events, recalls), 168h for classification/approval data. Includes rate limiting, error recovery, and comprehensive audit trails.

## Arguments

| Flag | Description | Example |
|------|-------------|---------|
| `--schedule TYPE` | Refresh schedule | `--schedule daily` |
| `--priority LEVEL` | Priority filter | `--priority safety` |
| `--dry-run` | Report what would be refreshed without executing | (flag) |
| `--background` | Run refresh in background | (flag) |
| `--pma P_NUMBER` | Specific PMA(s) to refresh | `--pma P170019` |
| `--status` | Show current refresh status | (flag) |

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

## Step 1: Check Refresh Status

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/data_refresh_orchestrator.py \
  --status --json
```

## Step 2: Execute Refresh

### Daily Safety Refresh (Default)

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/data_refresh_orchestrator.py \
  --schedule daily --priority safety --json
```

### Weekly Full Refresh

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/data_refresh_orchestrator.py \
  --schedule weekly --priority all --json
```

### Dry Run (Preview)

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/data_refresh_orchestrator.py \
  --schedule daily --dry-run --json
```

### Specific PMA Refresh

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/data_refresh_orchestrator.py \
  --pma "$PMA_NUMBER" --json
```

### Background Refresh

```bash
cd "$FDA_PLUGIN_ROOT" && python3 scripts/data_refresh_orchestrator.py \
  --schedule weekly --background --json
```

## Step 3: Present Results

```
  FDA Data Refresh Orchestrator v1.0.0
============================================================
  Schedule:    {daily|weekly|monthly}
  Priority:    {safety|all}
  Candidates:  {N} items

  TTL Tiers:
    Safety-Critical (24h):   {N} items stale
    Supplements (24h):       {N} items stale
    Approval Data (168h):    {N} items stale
    Static Documents:        Never auto-refresh

  Results:
    Refreshed:  {N}
    Skipped:    {N}
    Errors:     {N}
    API Calls:  {N}
    Time:       {N}s

  Audit Log: ~/fda-510k-data/pma_cache/refresh_logs/{session}.json
------------------------------------------------------------
  DISCLAIMER: Data is for research purposes only.
  Verify independently before use in FDA submissions.
============================================================
```

## TTL Tier Reference

| Tier | TTL | Data Types | Priority |
|------|-----|------------|----------|
| Safety-Critical | 24h | MAUDE events, Recalls | 1 (highest) |
| Supplements | 24h | PMA supplements | 2 |
| Approval Data | 168h (7d) | PMA approvals, Classification | 3 |
| Static Documents | Never | SSEDs, Extracted sections | 4 (lowest) |

## Rate Limiting

- FDA API: 240 requests/minute, 1000 requests/5 minutes
- Token bucket algorithm prevents HTTP 429 errors
- Automatic backoff on rate limit responses

## Error Handling

- **API timeout**: Retries with exponential backoff (2s, 4s, 8s)
- **Rate limited**: Extended wait with double backoff
- **Server error**: Up to 3 retries per item
- **No data**: Falls back to stale cache if available
