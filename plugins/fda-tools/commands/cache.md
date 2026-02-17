---
description: Show cached FDA data for a project — what has been fetched, freshness, and summary
allowed-tools: Bash, Read
argument-hint: "--project NAME [--clear] [--refresh-all]"
---

# FDA Data Cache Manager

> **Important**: This command assists with FDA regulatory workflows but does not provide regulatory advice. Output should be reviewed by qualified regulatory professionals before being relied upon for submission decisions.

> For external API dependencies and connection status, see [CONNECTORS.md](../CONNECTORS.md).

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

If `$FDA_PLUGIN_ROOT` is empty, report an error: "Could not locate the FDA Predicate Assistant plugin installation. Make sure the plugin is installed and enabled."

---

You are showing the user what FDA data has been cached for their project. This helps them understand what data is available without re-querying APIs, and allows them to manage cache freshness.

## Parse Arguments

From `$ARGUMENTS`, extract:

- `--project NAME` (required) — Project name
- `--clear` — Clear all cached data for the project (removes data_manifest.json)
- `--refresh-all` — Mark all entries as stale (forces re-fetch on next use)

If no `--project` specified, list available projects:

```bash
python3 -c "
import os, json, re, glob

settings_path = os.path.expanduser('~/.claude/fda-tools.local.md')
projects_dir = os.path.expanduser('~/fda-510k-data/projects')
if os.path.exists(settings_path):
    with open(settings_path) as f:
        m = re.search(r'projects_dir:\s*(.+)', f.read())
        if m:
            projects_dir = os.path.expanduser(m.group(1).strip())

manifests = glob.glob(os.path.join(projects_dir, '*/data_manifest.json'))
if manifests:
    print('Projects with cached data:')
    for mp in sorted(manifests):
        name = os.path.basename(os.path.dirname(mp))
        with open(mp) as f:
            data = json.load(f)
        queries = len(data.get('queries', {}))
        updated = data.get('last_updated', 'unknown')
        print(f'  {name}: {queries} cached queries (updated: {updated})')
else:
    print('No projects with cached data found.')
    print(f'Projects dir: {projects_dir}')
"
```

Then ask the user which project to show.

## Show Manifest

```bash
python3 "$FDA_PLUGIN_ROOT/scripts/fda_data_store.py" --project "$PROJECT_NAME" --show-manifest
```

Present the output in a formatted report:

```
  FDA Data Cache
  Project: {name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Last Updated: {date} | v5.22.0

CACHED QUERIES
────────────────────────────────────────

  {For each CACHED entry:}
  ✓ {query_key} — {compact_summary} ({time_ago})

  {For each STALE entry:}
  ✗ {query_key} — {compact_summary} ({time_ago}) [EXPIRED]

SUMMARY
────────────────────────────────────────

  Cached: {N} queries
  Stale:  {N} queries (will re-fetch on next use)

ACTIONS
────────────────────────────────────────

  Refresh all:  /fda:cache --project {name} --refresh-all
  Clear cache:  /fda:cache --project {name} --clear

────────────────────────────────────────
```

## Clear Cache

If `--clear` flag:

```bash
python3 "$FDA_PLUGIN_ROOT/scripts/fda_data_store.py" --project "$PROJECT_NAME" --clear
```

Report: "Cleared all cached data for project {name}. Next command runs will re-fetch from APIs."

## Refresh All

If `--refresh-all` flag:

```bash
python3 "$FDA_PLUGIN_ROOT/scripts/fda_data_store.py" --project "$PROJECT_NAME" --refresh-all
```

Report: "Marked {N} entries as stale for project {name}. Data will be re-fetched on next use."
